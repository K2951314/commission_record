import frappe
from frappe.model.document import Document
from frappe.utils import flt, cint
from frappe import _

@frappe.whitelist()
def get_contacts_with_unpaid_commission(doctype, txt, searchfield, start, page_len, filters):
    """获取有未支付分成的联系人列表"""
    contacts_with_unpaid = frappe.db.sql("""
        WITH contact_commission AS (
            SELECT 
                cr.contact,
                c.first_name,
                SUM(cr.commission_amount) as total_commission,
                IFNULL(
                    (
                        SELECT SUM(cpa.allocated_amount)
                        FROM `tabCommission Payment Allocation` cpa
                        INNER JOIN `tabCommission Payment` cp ON cp.name = cpa.parent
                        WHERE cpa.commission_record = cr.name
                        AND cp.docstatus = 1
                    ),
                    0
                ) as paid_amount
            FROM `tabCommission Record` cr
            INNER JOIN `tabContact` c ON c.name = cr.contact
            WHERE cr.docstatus = 1
            AND (cr.contact LIKE %(txt)s OR c.first_name LIKE %(txt)s)
            GROUP BY cr.contact, c.first_name
            HAVING (total_commission - paid_amount) > 0
        )
        SELECT 
            contact as value,
            first_name as description
        FROM contact_commission
        ORDER BY first_name
        LIMIT %(start)s, %(page_len)s
    """, {
        'txt': f"%{txt}%",
        'start': cint(start),
        'page_len': cint(page_len),
        'unpaid_label': _('未支付分成')
    }, as_list=1)

    return contacts_with_unpaid

@frappe.whitelist()
def get_unpaid_commission_records(contact, payment_amount):
    """获取联系人的未支付分成记录并计算分配金额"""
    if not contact or not payment_amount:
        return []
        
    payment_amount = flt(payment_amount)
    if payment_amount <= 0:
        return []
        
    records = frappe.get_all(
        "Commission Record",
        filters={
            "contact": contact,
            "docstatus": 1,
            "remaining_commission": [">", 0]
        },
        fields=["name", "commission_amount", "remaining_commission", "creation"],
        order_by="creation asc"
    )
    
    remaining_payment = payment_amount
    result = []
    
    for record in records:
        if remaining_payment <= 0:
            break
            
        allocated_amount = min(
            remaining_payment,
            flt(record.remaining_commission)
        )
        
        result.append({
            "name": record.name,
            "commission_amount": record.commission_amount,
            "allocated_amount": allocated_amount,
            "remaining_amount": flt(record.remaining_commission) - allocated_amount
        })
        
        remaining_payment -= allocated_amount
    
    return result

class CommissionPayment(Document):
    def validate(self):
        self.validate_payment_amount()
        self.validate_allocations()
        self.calculate_amounts()
        
        # 设置初始状态
        if self.docstatus == 0:
            self.status = "Draft"
            
        if not self.flags.ignore_auto_allocate:
            self.auto_allocate_if_needed()
        self.flags.ignore_validate = True  # 防止重复验证
    
    def on_submit(self):
        # 更新状态为已提交
        self.status = "Submitted"
        frappe.db.set_value(self.doctype, self.name, 'status', 'Submitted', update_modified=False)
        
        # 更新关联记录
        self.update_commission_records()
        self.update_contact_commission()

        # 记录调试信息
        frappe.logger().debug(f"Successfully submitted Commission Payment {self.name}")
    
    def on_cancel(self):
        # 更新状态为已取消
        self.status = "Cancelled"
        frappe.db.set_value(self.doctype, self.name, 'status', 'Cancelled', update_modified=False)
        
        # 更新关联记录
        self.update_commission_records(cancel=True)
        self.update_contact_commission()

        # 记录调试信息
        frappe.logger().debug(f"Successfully cancelled Commission Payment {self.name}")
    
    def on_update_after_submit(self):
        """提交后更新时重新计算并更新相关记录"""
        self.calculate_amounts()
        self.update_commission_records()
        self.update_contact_commission()
    
    def validate_payment_amount(self):
        """验证支付金额"""
        if not self.payment_amount or flt(self.payment_amount) <= 0:
            frappe.throw(_("支付金额必须大于0"))
    
    def validate_allocations(self):
        """验证分配明细"""
        if not self.allocations:
            return
        
        for allocation in self.allocations:
            comm_record = frappe.get_doc("Commission Record", allocation.commission_record)
            if comm_record.docstatus != 1:
                frappe.throw(_("分成记录 {0} 必须是已提交状态").format(allocation.commission_record))
            
            if comm_record.contact != self.contact:
                frappe.throw(_("分成记录 {0} 的联系人与当前支付记录不一致").format(allocation.commission_record))
            
            if flt(allocation.allocated_amount) <= 0:
                frappe.throw(_("分配金额必须大于0"))
    
    def calculate_amounts(self):
        """计算总分配金额和未分配金额"""
        self.total_allocated_amount = sum(flt(d.allocated_amount) for d in self.allocations)
        self.remaining_amount = flt(self.payment_amount) - flt(self.total_allocated_amount)
        
        # 确保分配金额不超过支付金额
        if flt(self.total_allocated_amount) > flt(self.payment_amount):
            frappe.throw(_("分配总金额不能超过支付金额"))
    
    def auto_allocate_if_needed(self):
        """自动分配支付金额到未完全支付的分成记录"""
        pass

    def update_commission_records(self, cancel=False):
        """更新分成记录的支付状态和剩余金额"""
        # 如果没有分配明细，则直接返回
        if not self.allocations:
            return
            
        # 遍历所有分配明细
        for allocation in self.allocations:
            # 获取分成记录文档
            record = frappe.get_doc("Commission Record", allocation.commission_record)
            
            # 重新计算分成记录的剩余分成金额
            record.calculate_remaining_commission()
            
            # 更新支付状态
            record.update_payment_status()
            
            # 保存更新到数据库
            record.db_update()

    def update_contact_commission(self):
        """更新联系人的分成总额和剩余分成"""
        # 如果没有联系人，则直接返回
        if not self.contact:
            return
            
        # 获取联系人文档
        contact = frappe.get_doc("Contact", self.contact)
        
        # 计算联系人的所有分成记录总额
        total_commission = frappe.db.sql("""
            SELECT IFNULL(SUM(commission_amount), 0)
            FROM `tabCommission Record`
            WHERE contact = %s
            AND docstatus = 1
        """, self.contact)[0][0]
        
        # 计算联系人的所有已支付金额
        total_paid = frappe.db.sql("""
            SELECT IFNULL(SUM(cpa.allocated_amount), 0)
            FROM `tabCommission Payment Allocation` cpa
            INNER JOIN `tabCommission Payment` cp ON cp.name = cpa.parent
            INNER JOIN `tabCommission Record` cr ON cr.name = cpa.commission_record
            WHERE cr.contact = %s
            AND cp.docstatus = 1
        """, self.contact)[0][0]
        
        # 更新联系人的分成总额和剩余分成
        contact.db_set('total_commission', total_commission)
        contact.db_set('remaining_commission', flt(total_commission) - flt(total_paid))
        contact.notify_update() 

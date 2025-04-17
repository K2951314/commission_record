
import frappe
from frappe.model.document import Document
from frappe.utils import flt

class CommissionPayment(Document):
    def validate(self):
        self.validate_payment_amount()
        self.validate_allocations()
        self.calculate_amounts()
    
    def validate_payment_amount(self):
        """验证支付金额"""
        if not self.payment_amount or flt(self.payment_amount) <= 0:
            frappe.throw("支付金额必须大于0")
    
    def validate_allocations(self):
        """验证分配明细"""
        if not self.allocations:
            frappe.throw("必须至少有一条分配明细")
        
        # 验证每条分配明细
        for allocation in self.allocations:
            # 验证分成记录状态
            comm_record = frappe.get_doc("Commission Record", allocation.commission_record)
            if comm_record.docstatus != 1:
                frappe.throw(f"分成记录 {allocation.commission_record} 必须是已提交状态")
            
            # 验证联系人一致性
            if comm_record.contact != self.contact:
                frappe.throw(f"分成记录 {allocation.commission_record} 的联系人与当前支付记录不一致")
            
            # 验证分配金额
            if flt(allocation.allocated_amount) <= 0:
                frappe.throw("分配金额必须大于0")
            
            # 验证分配金额不超过分成金额
            if flt(allocation.allocated_amount) > flt(comm_record.commission_amount):
                frappe.throw(f"分配金额不能超过分成金额 {comm_record.commission_amount}")
    
    def calculate_amounts(self):
        """计算总分配金额和未分配金额"""
        self.total_allocated_amount = sum(flt(d.allocated_amount) for d in self.allocations)
        self.remaining_amount = flt(self.payment_amount) - flt(self.total_allocated_amount)
        
        # 如果总分配金额超过支付金额，显示警告
        if self.total_allocated_amount > self.payment_amount:
            frappe.throw(f"总分配金额 ({self.total_allocated_amount}) 不能超过支付金额 ({self.payment_amount})")
    
    def on_submit(self):
        self.update_commission_records()
        self.update_contact_commission()
    
    def on_cancel(self):
        self.update_commission_records(cancel=True)
        self.update_contact_commission()
    
    def update_commission_records(self, cancel=False):
        """更新相关分成记录"""
        # 获取所有相关的分成记录
        commission_records = list(set(d.commission_record for d in self.allocations))
        
        for record_name in commission_records:
            comm_record = frappe.get_doc("Commission Record", record_name)
            
            # 获取该分成记录的所有已分配金额（不包括当前记录）
            total_allocated = frappe.db.sql("""
                SELECT IFNULL(SUM(cpa.allocated_amount), 0)
                FROM `tabCommission Payment Allocation` cpa
                INNER JOIN `tabCommission Payment` cp ON cp.name = cpa.parent
                WHERE cpa.commission_record = %s
                AND cp.docstatus = 1
                AND cp.name != %s
            """, (record_name, self.name))[0][0]
            
            # 加上当前支付记录的分配金额
            if not cancel:
                for allocation in self.allocations:
                    if allocation.commission_record == record_name:
                        total_allocated += flt(allocation.allocated_amount)
            
            # 更新分成记录的剩余分成和支付状态
            remaining_commission = flt(comm_record.commission_amount) - total_allocated
            comm_record.db_set('remaining_commission', remaining_commission)
            
            # 更新支付状态
            if remaining_commission <= 0:
                payment_status = "已支付"
            elif remaining_commission < flt(comm_record.commission_amount):
                payment_status = "部分支付"
            else:
                payment_status = "未支付"
            
            comm_record.db_set('payment_status', payment_status)
            comm_record.notify_update()
    
    def update_contact_commission(self):
        """更新联系人的分成信息"""
        if not self.contact:
            return
            
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
            WHERE cp.contact = %s
            AND cp.docstatus = 1
        """, self.contact)[0][0]
        
        # 更新联系人的分成总额和剩余分成
        contact.db_set('total_commission', total_commission)
        contact.db_set('remaining_commission', flt(total_commission) - flt(total_paid))
        contact.notify_update()

@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def get_contacts_with_unpaid_commission(doctype, txt, searchfield, start, page_len, filters):
    """获取有未支付分成的联系人列表"""
    return frappe.db.sql("""
        SELECT DISTINCT c.name, c.first_name
        FROM `tabContact` c
        INNER JOIN `tabCommission Record` cr ON cr.contact = c.name
        WHERE cr.docstatus = 1
        AND cr.payment_status IN ('未支付', '部分支付')
        AND (c.name LIKE %(txt)s OR c.first_name LIKE %(txt)s)
    """, {
        'txt': f'%{txt}%'
    })

@frappe.whitelist()
def get_unpaid_records(contact):
    """获取联系人的未完全支付的分成记录"""
    if not contact:
        return []
        
    return frappe.get_all(
        "Commission Record",
        filters={
            "contact": contact,
            "payment_status": ["in", ["未支付", "部分支付"]],
            "docstatus": 1
        },
        fields=["name", "commission_amount", "remaining_commission"],
        order_by="creation asc"
    )
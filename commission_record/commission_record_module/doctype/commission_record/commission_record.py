
import frappe
from frappe.model.document import Document
from frappe.utils import flt

class CommissionRecord(Document):
    def validate(self):
        self.calculate_totals()
        self.calculate_remaining_commission()
    
    def on_submit(self):
        """提交时更新联系人分成信息"""
        self.update_contact_commission()
    
    def on_cancel(self):
        """取消提交时更新联系人分成信息"""
        self.update_contact_commission()
    
    def on_update_after_submit(self):
        """提交后更新时重新计算剩余分成"""
        self.calculate_remaining_commission()
        self.update_payment_status()
        self.db_update()
        self.update_contact_commission()
    
    def calculate_totals(self):
        """计算总额和分成金额"""
        total_sales = 0
        total_purchase = 0
        total_shipping = 0
        
        for order in self.orders:
            total_sales += flt(order.sales_amount)
            total_purchase += flt(order.purchase_cost)
            total_shipping += flt(order.shipping_fee)
        
        self.total_sales = total_sales
        self.total_purchase = total_purchase
        self.total_shipping = total_shipping
        
        # 分成金额 = (销售总额 - 采购总额 - 快递总额) * 分成比例
        commission_percentage = flt(self.commission_percentage)
        self.commission_amount = flt((total_sales - total_purchase - total_shipping) * (commission_percentage / 100))
        
    def calculate_remaining_commission(self):
        """计算剩余分成金额"""
        if not self.commission_amount:
            self.remaining_commission = 0
            return
            
        # 获取所有已提交的分成支付记录中分配给此记录的金额总和
        total_paid = frappe.db.sql("""
            SELECT IFNULL(SUM(cpa.allocated_amount), 0)
            FROM `tabCommission Payment Allocation` cpa
            INNER JOIN `tabCommission Payment` cp ON cp.name = cpa.parent
            WHERE cpa.commission_record = %s
            AND cp.docstatus = 1
        """, self.name)[0][0]
        
        self.remaining_commission = flt(self.commission_amount) - flt(total_paid)
        
    def update_payment_status(self):
        """更新支付状态"""
        if flt(self.remaining_commission) <= 0:
            self.payment_status = "已支付"
        elif flt(self.remaining_commission) < flt(self.commission_amount):
            self.payment_status = "部分支付"
        else:
            self.payment_status = "未支付"
    
    def update_contact_commission(self):
        """更新联系人的分成总额和剩余分成"""
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
            INNER JOIN `tabCommission Record` cr ON cr.name = cpa.commission_record
            WHERE cr.contact = %s
            AND cp.docstatus = 1
        """, self.contact)[0][0]
        
        # 更新联系人的分成总额和剩余分成
        contact.db_set('total_commission', total_commission)
        contact.db_set('remaining_commission', flt(total_commission) - flt(total_paid))
        contact.notify_update()
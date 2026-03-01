import frappe
from frappe.model.document import Document
from frappe.utils import flt

class CommissionRecordDetail(Document):
    def validate(self):
        self.validate_amounts()
    
    def validate_amounts(self):
        """验证金额"""
        if self.sales_order:
            # 确保销售金额正确
            sales_amount = frappe.db.get_value("Sales Order", self.sales_order, "base_net_total")
            if sales_amount:
                self.sales_amount = flt(sales_amount)
        
        if self.purchase_order:
            # 确保采购成本正确
            purchase_cost = frappe.db.get_value("Purchase Order", self.purchase_order, "base_net_total")
            if purchase_cost:
                self.purchase_cost = flt(purchase_cost)
        
        # 确保快递费为非负数
        if flt(self.shipping_fee) < 0:
            frappe.throw("快递费不能为负数")
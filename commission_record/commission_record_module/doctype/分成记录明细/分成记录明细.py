# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class 分成记录明细(Document):
    def validate(self):
        self.validate_amounts()
    
    def validate_amounts(self):
        """验证金额"""
        if self.sales_order:
            # 确保销售金额正确
            sales_amount = frappe.db.get_value("Sales Order", self.sales_order, "base_net_total")
            if sales_amount:
                self.sales_amount = sales_amount
        
        if self.purchase_order:
            # 确保采购成本正确
            purchase_cost = frappe.db.get_value("Purchase Order", self.purchase_order, "base_net_total")
            if purchase_cost:
                self.purchase_cost = purchase_cost
        
        # 确保快递费为非负数
        if self.shipping_fee and self.shipping_fee < 0:
            frappe.throw("快递费不能为负数")
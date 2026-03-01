# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import flt

class CommissionPaymentAllocation(Document):
    def validate(self):
        self.validate_allocated_amount()
        self.calculate_remaining_amount()
    
    def validate_allocated_amount(self):
        """验证分配金额"""
        if not self.allocated_amount or flt(self.allocated_amount) <= 0:
            frappe.throw("分配金额必须大于0")
    
    def calculate_remaining_amount(self):
        """计算剩余金额"""
        # 获取该分成记录已分配的总金额（不包括当前分配）
        total_allocated = frappe.db.sql("""
            SELECT IFNULL(SUM(allocated_amount), 0)
            FROM `tabCommission Payment Allocation` cpa
            INNER JOIN `tabCommission Payment` cp ON cp.name = cpa.parent
            WHERE cpa.commission_record = %s
            AND cp.docstatus = 1
            AND cpa.name != %s
        """, (self.commission_record, self.name))[0][0]
        
        # 确保剩余金额计算逻辑与分成记录一致
        self.remaining_amount = flt(self.commission_amount) - flt(total_allocated) - flt(self.allocated_amount)
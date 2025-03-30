
import frappe
from frappe.model.document import Document
from frappe.utils import flt

class CommissionPaymentAllocation(Document):
    def validate(self):
        self.validate_allocated_amount()
    
    def validate_allocated_amount(self):
        """验证分配金额"""
        if not self.allocated_amount or flt(self.allocated_amount) <= 0:
            frappe.throw("分配金额必须大于0")
        
        # 验证分配金额不超过分成金额
        if flt(self.allocated_amount) > flt(self.commission_amount):
            frappe.throw(f"分配金额 ({self.allocated_amount}) 不能超过分成金额 ({self.commission_amount})")
        
        # 获取父文档
        parent = frappe.get_doc("Commission Payment", self.parent) if self.parent else None
        if parent:
            # 计算当前行之外的已分配总额
            total_allocated = sum(
                flt(d.allocated_amount) 
                for d in parent.allocations 
                if d.name != self.name
            )
            
            # 验证总分配金额不超过支付金额
            if flt(total_allocated) + flt(self.allocated_amount) > flt(parent.payment_amount):
                frappe.throw(
                    f"总分配金额 ({flt(total_allocated) + flt(self.allocated_amount)}) "
                    f"不能超过支付金额 ({parent.payment_amount})"
                )
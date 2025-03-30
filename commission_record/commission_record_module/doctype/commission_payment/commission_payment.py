
import frappe
from frappe.model.document import Document
from frappe.utils import flt

class CommissionPayment(Document):
    def validate(self):
        self.validate_payment_amount()
        self.validate_allocations()
        self.calculate_amounts()
        self.auto_allocate_if_needed()
    
    def on_submit(self):
        self.update_commission_records()
        self.update_contact_commission()
    
    def on_cancel(self):
        self.update_commission_records(cancel=True)
        self.update_contact_commission()
    
    def on_update_after_submit(self):
        """提交后更新时重新计算并更新相关记录"""
        self.calculate_amounts()
        self.update_commission_records()
        self.update_contact_commission()
    
    def validate_payment_amount(self):
        """验证支付金额"""
        if not self.payment_amount or flt(self.payment_amount) <= 0:
            frappe.throw("支付金额必须大于0")
    
    def validate_allocations(self):
        """验证分配明细"""
        if not self.allocations:
            return  # 允许没有分配明细，后续会自动分配
        
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
    
    def calculate_amounts(self):
        """计算总分配金额和未分配金额"""
        self.total_allocated_amount = sum(flt(d.allocated_amount) for d in self.allocations)
        self.remaining_amount = flt(self.payment_amount) - flt(self.total_allocated_amount)
    
    def auto_allocate_if_needed(self):
        """如果有未分配金额，自动分配到未完全支付的分成记录"""
        if flt(self.remaining_amount) <= 0:
            return
            
        # 查找该联系人的未完全支付的分成记录
        unpaid_records = frappe.get_list(
            "Commission Record",
            filters={
                "contact": self.contact,
                "docstatus": 1
            },
            fields=["name", "commission_amount", "remaining_commission"],
            order_by="creation asc"
        )
        
        remaining = flt(self.remaining_amount)
        for record in unpaid_records:
            # 跳过已完全支付的记录
            if flt(record.remaining_commission) <= 0:
                continue
                
            # 检查该记录是否已在现有分配中
            if any(d.commission_record == record.name for d in self.allocations):
                continue
            
            # 创建新的分配记录
            allocation_amount = min(remaining, flt(record.remaining_commission))
            self.append("allocations", {
                "commission_record": record.name,
                "commission_amount": record.commission_amount,
                "allocated_amount": allocation_amount,
                "remaining_amount": flt(record.remaining_commission) - allocation_amount
            })
            
            remaining -= allocation_amount
            if remaining <= 0:
                break
        
        # 重新计算总金额
        self.calculate_amounts()
        
        # 如果还有未分配金额，显示提示
        if flt(self.remaining_amount) > 0:
            frappe.msgprint(
                f"注意：还有 {self.remaining_amount} 的金额未分配到任何分成记录",
                indicator='orange',
                alert=True
            )
    
    def update_commission_records(self, cancel=False):
        """更新相关分成记录"""
        # 获取所有相关的分成记录
        commission_records = list(set(d.commission_record for d in self.allocations))
        
        for record_name in commission_records:
            comm_record = frappe.get_doc("Commission Record", record_name)
            # 触发分成记录的更新
            comm_record.flags.ignore_validate_update_after_submit = True
            comm_record.save(ignore_permissions=True)
    
    def update_contact_commission(self):
        """更新联系人的分成信息"""
        if not self.contact:
            return
            
        # 获取一个相关的分成记录并触发其更新
        # 这将自动更新联系人的分成信息
        if self.allocations:
            record_name = self.allocations[0].commission_record
            comm_record = frappe.get_doc("Commission Record", record_name)
            comm_record.flags.ignore_validate_update_after_submit = True
            comm_record.save(ignore_permissions=True)
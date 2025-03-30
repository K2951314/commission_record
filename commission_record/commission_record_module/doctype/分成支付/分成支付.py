# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import flt

class 分成支付(Document):
    def validate(self):
        self.validate_payment_amount()
        self.calculate_remaining_amount()
        self.validate_commission_record()
    
    def on_submit(self):
        self.update_commission_record()
        self.update_contact_remaining_commission()
        if self.remaining_amount > 0:
            self.handle_excess_payment()
    
    def on_cancel(self):
        self.update_commission_record(cancel=True)
        self.update_contact_remaining_commission(cancel=True)
    
    def validate_payment_amount(self):
        """验证支付金额"""
        if not self.payment_amount or self.payment_amount <= 0:
            frappe.throw("支付金额必须大于0")
    
    def calculate_remaining_amount(self):
        """计算剩余金额（超额支付的部分）"""
        self.remaining_amount = max(0, flt(self.payment_amount) - flt(self.commission_amount))
    
    def validate_commission_record(self):
        """验证分成记录"""
        if not self.commission_record:
            frappe.throw("必须选择分成记录")
        
        comm_record = frappe.get_doc("分成记录", self.commission_record)
        if comm_record.docstatus != 1:
            frappe.throw("只能为已提交的分成记录创建支付记录")
        
        if comm_record.payment_status == "已支付":
            frappe.throw("该分成记录已完全支付")
    
    def update_commission_record(self, cancel=False):
        """更新分成记录的支付状态"""
        if not self.commission_record:
            return
            
        comm_record = frappe.get_doc("分成记录", self.commission_record)
        
        if cancel:
            # 取消提交时，将状态改回未支付
            comm_record.payment_status = "未支付"
        else:
            # 提交时，根据支付金额更新状态
            payment_amount = min(self.payment_amount, self.commission_amount)
            if payment_amount >= self.commission_amount:
                comm_record.payment_status = "已支付"
            else:
                comm_record.payment_status = "部分支付"
        
        comm_record.db_update()
        comm_record.notify_update()
    
    def update_contact_remaining_commission(self, cancel=False):
        """更新联系人的剩余分成"""
        if not self.contact:
            return
            
        contact = frappe.get_doc("Contact", self.contact)
        payment_amount = min(self.payment_amount, self.commission_amount)
        
        if cancel:
            # 取消提交时，增加剩余分成
            contact.db_set('remaining_commission',
                          flt(contact.remaining_commission) + payment_amount)
        else:
            # 提交时，减少剩余分成
            contact.db_set('remaining_commission',
                          flt(contact.remaining_commission) - payment_amount)
        
        contact.notify_update()
    
    def handle_excess_payment(self):
        """处理超额支付的情况"""
        if self.remaining_amount <= 0:
            return
            
        # 查找该联系人的其他未支付或部分支付的分成记录
        unpaid_records = frappe.get_list(
            "分成记录",
            filters={
                "contact": self.contact,
                "payment_status": ["in", ["未支付", "部分支付"]],
                "name": ["!=", self.commission_record],
                "docstatus": 1
            },
            order_by="creation asc"
        )
        
        remaining = self.remaining_amount
        for record in unpaid_records:
            if remaining <= 0:
                break
                
            comm_record = frappe.get_doc("分成记录", record.name)
            
            # 创建新的分成支付记录
            payment = frappe.get_doc({
                "doctype": "分成支付",
                "commission_record": comm_record.name,
                "contact": comm_record.contact,
                "payment_amount": min(remaining, comm_record.commission_amount),
                "payment_date": self.payment_date
            })
            payment.insert()
            payment.submit()
            
            remaining -= payment.payment_amount
            
            if remaining <= 0:
                break
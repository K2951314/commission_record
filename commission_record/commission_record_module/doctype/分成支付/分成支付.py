# -*- coding: utf-8 -*-
# 文件编码声明，确保支持中文
from __future__ import unicode_literals  # 确保字符串统一使用unicode
import frappe  # 导入Frappe框架核心模块
from frappe.model.document import Document  # 导入Frappe文档基类
from frappe.utils import flt  # 导入浮点数处理工具

# 分成支付文档类，继承自Frappe的Document基类
# 该类处理与分成支付相关的所有业务逻辑
class 分成支付(Document):
    def validate(self):
        """文档验证方法，在保存前自动调用"""
        self.validate_payment_amount()  # 验证支付金额是否有效
        self.calculate_remaining_amount()  # 计算支付后的剩余金额
        self.validate_commission_record()  # 验证关联的分成记录是否有效
    
    def on_submit(self):
        """文档提交时的处理逻辑
        1. 更新关联的分成记录状态
        2. 更新联系人的剩余分成金额
        3. 如果有超额支付，处理超额部分
        """
        self.update_commission_record()  # 更新分成记录状态
        self.update_contact_remaining_commission()  # 更新联系人剩余分成
        if self.remaining_amount > 0:  # 检查是否有超额支付
            self.handle_excess_payment()  # 处理超额支付部分
    
    def on_cancel(self):
        """文档取消时的处理逻辑
        1. 恢复关联的分成记录状态
        2. 恢复联系人的剩余分成金额
        """
        self.update_commission_record(cancel=True)  # 取消时更新分成记录状态
        self.update_contact_remaining_commission(cancel=True)  # 取消时更新联系人剩余分成
    
    def validate_payment_amount(self):
        """验证支付金额"""
        if not self.payment_amount or self.payment_amount <= 0:
            frappe.throw("支付金额必须大于0")
    
    def calculate_remaining_amount(self):
        """计算剩余金额（超额支付的部分）
        
        计算逻辑：
        1. 支付金额减去应支付的分成金额
        2. 使用max(0, x)确保结果不小于0
        3. 使用flt()确保浮点数计算精度
        """
        self.remaining_amount = max(0, flt(self.payment_amount) - flt(self.commission_amount))
    
    def validate_commission_record(self):
        """验证关联的分成记录是否有效
        
        检查内容：
        1. 是否选择了分成记录
        2. 分成记录是否已提交
        3. 分成记录是否已完全支付
        
        如果任何检查失败，抛出异常阻止保存
        """
        if not self.commission_record:
            frappe.throw("必须选择分成记录")  # 检查是否选择了分成记录
        
        comm_record = frappe.get_doc("分成记录", self.commission_record)
        if comm_record.docstatus != 1:
            frappe.throw("只能为已提交的分成记录创建支付记录")  # 检查文档状态
        
        if comm_record.payment_status == "已支付":
            frappe.throw("该分成记录已完全支付")  # 检查支付状态
    
    def update_commission_record(self, cancel=False):
        """更新关联的分成记录支付状态
        
        参数:
            cancel (bool): 是否为取消操作
        
        逻辑:
        1. 检查是否有关联的分成记录
        2. 如果是取消操作:
           - 将支付状态重置为"未支付"
        3. 如果是提交操作:
           - 计算实际支付金额(取支付金额和应支付金额中的较小值)
           - 如果支付金额>=应支付金额，状态设为"已支付"
           - 否则状态设为"部分支付"
        4. 直接更新数据库(db_update)并通知前端更新(notify_update)
        """
        if not self.commission_record:
            return  # 没有关联记录则直接返回
            
        comm_record = frappe.get_doc("分成记录", self.commission_record)
        
        if cancel:
            # 取消提交时，将状态改回未支付
            comm_record.payment_status = "未支付"
        else:
            # 提交时，根据支付金额更新状态
            payment_amount = min(self.payment_amount, self.commission_amount)
            if payment_amount >= self.commission_amount:
                comm_record.payment_status = "已支付"  # 完全支付
            else:
                comm_record.payment_status = "部分支付"  # 部分支付
        
        comm_record.db_update()  # 直接更新数据库，不触发验证
        comm_record.notify_update()  # 通知前端更新显示
    
    def update_contact_remaining_commission(self, cancel=False):
        """更新联系人记录的剩余分成金额
        
        参数:
            cancel (bool): 是否为取消操作
        
        逻辑:
        1. 检查是否有关联的联系人
        2. 计算实际支付金额(取支付金额和应支付金额中的较小值)
        3. 根据操作类型调整剩余金额:
           - 取消操作:增加剩余金额(恢复)
           - 提交操作:减少剩余金额(扣除)
        4. 使用db_set直接更新数据库字段
        5. 通知前端更新显示
        
        注意:
        - 使用flt()确保浮点数计算精度
        - db_set只更新指定字段，不触发完整文档保存
        """
        if not self.contact:
            return  # 没有关联联系人则直接返回
            
        contact = frappe.get_doc("Contact", self.contact)
        payment_amount = min(self.payment_amount, self.commission_amount)  # 计算实际支付金额
        
        if cancel:
            # 取消提交时，增加剩余分成(恢复金额)
            contact.db_set('remaining_commission',
                          flt(contact.remaining_commission) + payment_amount)
        else:
            # 提交时，减少剩余分成(扣除金额)
            contact.db_set('remaining_commission',
                          flt(contact.remaining_commission) - payment_amount)
        
        contact.notify_update()  # 通知前端更新显示
    
    def handle_excess_payment(self):
        """处理超额支付的情况(将超额部分分配给其他未支付记录)
        
        逻辑:
        1. 检查是否有超额支付(remaining_amount > 0)
        2. 查找该联系人的其他未支付或部分支付的分成记录:
           - 排除当前记录
           - 只查找已提交的记录
           - 按创建时间排序(先处理较早的记录)
        3. 循环处理超额金额:
           - 为每个未支付记录创建新的支付记录
           - 支付金额为剩余超额金额和记录金额中的较小值
           - 自动提交新创建的支付记录
           - 更新剩余超额金额
        4. 当超额金额用完或没有更多未支付记录时停止
        
        注意:
        - 使用frappe.get_list查询符合条件的记录
        - 使用frappe.get_doc创建新支付记录
        - 自动提交新创建的支付记录
        """
        if self.remaining_amount <= 0:
            return  # 没有超额支付则直接返回
            
        # 查找该联系人的其他未支付或部分支付的分成记录
        unpaid_records = frappe.get_list(
            "分成记录",
            filters={
                "contact": self.contact,  # 相同联系人
                "payment_status": ["in", ["未支付", "部分支付"]],  # 未完成支付的记录
                "name": ["!=", self.commission_record],  # 排除当前记录
                "docstatus": 1  # 只查找已提交的记录
            },
            order_by="creation asc"  # 按创建时间排序(先处理较早的记录)
        )
        
        remaining = self.remaining_amount  # 初始化剩余超额金额
        for record in unpaid_records:
            if remaining <= 0:
                break  # 超额金额已用完
                
            comm_record = frappe.get_doc("分成记录", record.name)
            
            # 创建新的分成支付记录
            payment = frappe.get_doc({
                "doctype": "分成支付",
                "commission_record": comm_record.name,  # 关联目标分成记录
                "contact": comm_record.contact,  # 相同联系人
                "payment_amount": min(remaining, comm_record.commission_amount),  # 支付金额
                "payment_date": self.payment_date  # 使用原支付日期
            })
            payment.insert()  # 创建记录
            payment.submit()  # 自动提交
            
            remaining -= payment.payment_amount  # 更新剩余超额金额
            
            if remaining <= 0:
                break  # 超额金额已用完
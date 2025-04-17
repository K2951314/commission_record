# -*- coding: utf-8 -*-
# 文件编码声明，确保支持中文
from __future__ import unicode_literals  # 确保字符串统一使用unicode
import frappe  # 导入Frappe框架核心模块
from frappe.model.document import Document  # 导入Frappe文档基类
from frappe.utils import flt  # 浮点数处理工具

# 分成记录明细文档类，继承自Frappe的Document基类
# 该类处理分成记录明细相关的金额验证逻辑
class 分成记录明细(Document):
    """
    分成记录明细文档类
    功能：处理与分成记录明细相关的所有业务逻辑和验证
    """
    
    def validate(self):
        """
        文档保存前的自动验证方法（Frappe框架自动调用）
        主要职责：
        1. 调用所有子验证方法
        2. 确保文档数据完整性
        """
        self.validate_amounts()  # 执行金额相关字段验证

    def validate_amounts(self):
        """
        金额字段验证和计算
        执行顺序：
        1. 验证销售订单金额
        2. 验证采购订单金额 
        3. 验证快递费
        4. 计算分成金额
        """
        # 1. 销售订单金额处理
        if self.sales_order:  # 如果关联了销售订单
            # 从销售订单获取最新税前总额
            sales_amount = frappe.db.get_value(
                "Sales Order",         # 文档类型
                self.sales_order,      # 订单名称
                "base_net_total"       # 要获取的字段
            )
            if sales_amount:
                self.sales_amount = sales_amount  # 更新当前记录的销售金额

        # 2. 采购订单金额处理
        if self.purchase_order:  # 如果关联了采购订单
            # 从采购订单获取最新税前总额
            purchase_cost = frappe.db.get_value(
                "Purchase Order",      # 文档类型
                self.purchase_order,   # 订单名称
                "base_net_total"      # 要获取的字段
            )
            if purchase_cost:
                self.purchase_cost = purchase_cost  # 更新当前记录的采购成本

        # 3. 快递费验证
        if self.shipping_fee and self.shipping_fee < 0:
            # 如果快递费为负数，抛出异常阻止保存
            frappe.throw("快递费不能为负数")
            
        # 4. 分成金额计算
        if self.sales_amount and self.commission_percentage:
            # 计算公式：销售金额 × 分成比例 ÷ 100
            # flt()确保浮点数精度，2表示保留2位小数
            self.commission_amount = flt(
                self.sales_amount * self.commission_percentage / 100, 
                2
            )  # 更新当前记录的分成金额
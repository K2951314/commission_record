# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

def before_install():
    """安装前检查"""
    if not frappe.db.exists("DocType", "Sales Order"):
        frappe.throw("请先安装 ERPNext")

def after_install():
    """安装后设置"""
    setup_custom_fields()
    setup_initial_values()

def setup_custom_fields():
    """设置自定义字段"""
    custom_fields = {
        "Contact": [
            {
                "fieldname": "total_commission",
                "label": "分成总额",
                "fieldtype": "Currency",
                "insert_after": "is_primary_contact",
                "read_only": 1,
                "default": "0"
            },
            {
                "fieldname": "remaining_commission",
                "label": "剩余分成",
                "fieldtype": "Currency",
                "insert_after": "total_commission",
                "read_only": 1,
                "default": "0"
            }
        ]
    }
    
    create_custom_fields(custom_fields)

def setup_initial_values():
    """设置初始值"""
    # 为现有联系人添加初始值
    if frappe.db.exists("DocType", "Contact"):
        contacts = frappe.get_all("Contact")
        for contact in contacts:
            doc = frappe.get_doc("Contact", contact.name)
            if not hasattr(doc, "total_commission"):
                doc.db_set("total_commission", 0, update_modified=False)
            if not hasattr(doc, "remaining_commission"):
                doc.db_set("remaining_commission", 0, update_modified=False)

@frappe.whitelist()
def validate_contact(doc, method):
    """验证联系人文档"""
    # 确保分成相关字段存在且为数字
    if not hasattr(doc, "total_commission"):
        doc.total_commission = 0
    if not hasattr(doc, "remaining_commission"):
        doc.remaining_commission = 0
    
    # 确保值为非负数
    doc.total_commission = max(0, float(doc.total_commission))
    doc.remaining_commission = max(0, float(doc.remaining_commission))
# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import frappe
from frappe import _
from frappe.utils import flt

def execute(filters=None):
    columns = get_columns()
    data = get_data(filters)
    return columns, data

def get_columns():
    """获取报表列定义"""
    return [
        {
            "fieldname": "contact",
            "label": _("联系人"),
            "fieldtype": "Link",
            "options": "Contact",
            "width": 180
        },
        {
            "fieldname": "contact_name",
            "label": _("联系人姓名"),
            "fieldtype": "Data",
            "width": 180
        },
        {
            "fieldname": "total_commission",
            "label": _("分成总额"),
            "fieldtype": "Currency",
            "width": 120
        },
        {
            "fieldname": "paid_amount",
            "label": _("已支付金额"),
            "fieldtype": "Currency",
            "width": 120
        },
        {
            "fieldname": "unpaid_amount",
            "label": _("未支付金额"),
            "fieldtype": "Currency",
            "width": 120
        },
        {
            "fieldname": "commission_count",
            "label": _("分成记录数"),
            "fieldtype": "Int",
            "width": 100
        },
        {
            "fieldname": "commission_records",
            "label": _("分成记录"),
            "fieldtype": "Link",
            "options": "Commission Record",
            "width": 140,
            "link_onclick": "frappe.route_options = {'contact': doc.contact}; frappe.set_route('List', 'Commission Record');"
        },
        {
            "fieldname": "commission_payments",
            "label": _("分成支付"),
            "fieldtype": "Link",
            "options": "Commission Payment",
            "width": 140,
            "link_onclick": "frappe.route_options = {'contact': doc.contact}; frappe.set_route('List', 'Commission Payment');"
        }
    ]

def get_data(filters):
    """获取报表数据"""
    data = []
    
    # 获取所有有分成记录的联系人
    contacts = frappe.db.sql("""
        SELECT DISTINCT contact 
        FROM `tab分成记录`
        WHERE docstatus = 1
        ORDER BY creation DESC
    """, as_dict=1)
    
    for contact_dict in contacts:
        contact = contact_dict.contact
        contact_name = frappe.db.get_value("Contact", contact, "first_name")
        
        # 获取该联系人的所有已提交的分成记录
        commission_records = frappe.get_all(
            "分成记录",
            filters={
                "contact": contact,
                "docstatus": 1
            },
            fields=["name", "commission_amount", "payment_status"]
        )
        
        total_commission = 0
        paid_amount = 0
        unpaid_amount = 0
        
        for record in commission_records:
            total_commission += flt(record.commission_amount)
            
            # 获取该分成记录的已支付金额
            paid = frappe.db.sql("""
                SELECT IFNULL(SUM(
                    LEAST(payment_amount, commission_amount)
                ), 0) as paid
                FROM `tab分成支付`
                WHERE commission_record = %s
                AND docstatus = 1
            """, record.name)[0][0]
            
            paid_amount += flt(paid)
            unpaid_amount += flt(record.commission_amount) - flt(paid)
        
        # 获取该联系人的分成记录和支付记录数量
        commission_record_count = frappe.db.count(
            "Commission Record",
            filters={"contact": contact, "docstatus": 1}
        )
        commission_payment_count = frappe.db.count(
            "Commission Payment",
            filters={"contact": contact, "docstatus": 1}
        )

        row = {
            "contact": contact,
            "contact_name": contact_name,
            "total_commission": total_commission,
            "paid_amount": paid_amount,
            "unpaid_amount": unpaid_amount,
            "commission_count": len(commission_records),
            "commission_records": f"{commission_record_count} 条记录",
            "commission_payments": f"{commission_payment_count} 条支付"
        }
        
        data.append(row)
    
    return data
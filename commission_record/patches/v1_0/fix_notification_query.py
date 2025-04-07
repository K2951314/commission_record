
import frappe
import json

def execute():
    """修复通知系统中的查询逻辑"""
    
    # 更新Commission Record的links配置
    if frappe.db.exists('DocType', 'Commission Record'):
        doc = frappe.get_doc('DocType', 'Commission Record')
        links = []
        
        # 清除现有的links
        doc.links = []
        
        # 添加正确的链接配置
        doc.append("links", {
            "group": "支付",
            "link_doctype": "Commission Payment",
            "link_fieldname": "commission_payment",
            "table_fieldname": None
        })
        doc.save()
    

    # 更新现有的分成记录中的commission_payment字段
    commission_records = frappe.get_all(
        "Commission Record",
        filters={"docstatus": 1},
        fields=["name"]
    )
    
    for record in commission_records:
        # 查找最后一次支付记录
        payment_allocation = frappe.db.sql("""
            SELECT cp.name
            FROM `tabCommission Payment` cp
            INNER JOIN `tabCommission Payment Allocation` cpa ON cpa.parent = cp.name
            WHERE cpa.commission_record = %s
            AND cp.docstatus = 1
            ORDER BY cp.creation DESC
            LIMIT 1
        """, record.name)
        
        if payment_allocation:
            frappe.db.set_value(
                "Commission Record",
                record.name,
                "commission_payment",
                payment_allocation[0][0],
                update_modified=False
            )
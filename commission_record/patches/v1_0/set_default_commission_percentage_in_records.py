
import frappe

def execute():
    """为所有分成记录设置默认分成比例为50%"""
    frappe.db.sql("""
        UPDATE `tabCommission Record`
        SET commission_percentage = 50
        WHERE commission_percentage IS NULL
    """)
    frappe.db.commit()
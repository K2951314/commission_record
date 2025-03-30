from frappe.utils import flt

def execute():
    """更新现有联系人的分成值"""
    if not frappe.db.exists("DocType", "Contact"):
        return
    
    # 获取所有联系人
    contacts = frappe.get_all("Contact")
    
    for contact in contacts:
        update_contact_commission(contact.name)

def update_contact_commission(contact_name):
    """更新指定联系人的分成值"""
    # 获取该联系人的所有分成记录
    commission_records = frappe.get_all(
        "分成记录",
        filters={
            "contact": contact_name,
            "docstatus": 1
        },
        fields=["name", "commission_amount"]
    )
    
    total_commission = 0
    remaining_commission = 0
    
    # 计算分成总额和剩余分成
    for record in commission_records:
        total_commission += flt(record.commission_amount)
        
        # 获取已支付金额
        paid_amount = frappe.db.sql("""
            SELECT IFNULL(SUM(
                LEAST(payment_amount, commission_amount)
            ), 0) as paid
            FROM `tab分成支付`
            WHERE commission_record = %s
            AND docstatus = 1
        """, record.name)[0][0]
        
        remaining_commission += flt(record.commission_amount) - flt(paid_amount)
    
    # 更新联系人字段
    frappe.db.set_value(
        "Contact",
        contact_name,
        {
            "total_commission": total_commission,
            "remaining_commission": remaining_commission
        },
        update_modified=False
    )

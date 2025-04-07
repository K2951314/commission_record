
import frappe

def execute():
    """修复分成记录和分成支付单据之间的关联关系"""
    
    # 获取所有已提交的分成支付单据
    payments = frappe.get_all(
        "Commission Payment",
        filters={"docstatus": 1},
        fields=["name"]
    )
    
    for payment in payments:
        # 获取该支付单据的所有分配记录
        allocations = frappe.get_all(
            "Commission Payment Allocation",
            filters={"parent": payment.name},
            fields=["commission_record"]
        )
        
        # 更新每个分成记录的commission_payment字段
        for allocation in allocations:
            if allocation.commission_record:
                frappe.db.set_value(
                    "Commission Record",
                    allocation.commission_record,
                    "commission_payment",
                    payment.name,
                    update_modified=False
                )
    
    # 更新通知计数器的查询
    if frappe.db.exists('Notification Counter', {'reference_doctype': 'Commission Record'}):
        counter = frappe.get_doc('Notification Counter', {
            'reference_doctype': 'Commission Record'
        })
        
        # 更新filters字段中的条件
        if counter.filters:
            filters = frappe.parse_json(counter.filters)
            if 'commission_record' in filters:
                filters['commission_payment'] = filters.pop('commission_record')
                counter.filters = frappe.as_json(filters)
                counter.save()
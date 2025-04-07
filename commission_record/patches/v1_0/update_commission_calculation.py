
import frappe
from frappe.utils import flt

def execute():
    """更新分成计算逻辑和翻译"""
    
    # 更新所有未提交的分成记录的分成金额计算
    records = frappe.get_all(
        "Commission Record",
        filters={"docstatus": 0},
        fields=["name", "total_sales", "total_purchase", "total_shipping"]
    )
    
    for record in records:
        # 使用新的计算逻辑：(销售总额 - 采购总额 - 快递总额) / 2
        commission_amount = flt((record.total_sales - record.total_purchase - record.total_shipping) / 2)
        
        # 更新分成金额
        frappe.db.set_value(
            "Commission Record",
            record.name,
            "commission_amount",
            commission_amount,
            update_modified=False
        )
    
    # 确保翻译已添加
    translations = [
        ("Commission Payment", "分成支付"),
        ("Commission Record", "分成记录"),
        ("Commission Record Detail", "分成记录明细"),
        ("Commission Payment Allocation", "分成支付分配"),
        ("Payment Amount", "支付金额"),
        ("Payment Date", "支付日期"),
        ("Total Sales Amount", "销售总额"),
        ("Total Purchase Amount", "采购总额"),
        ("Total Shipping Cost", "快递总额"),
        ("Commission Amount", "分成金额"),
        ("Remaining Commission", "剩余分成"),
        ("Allocated Amount", "分配金额"),
        ("Remaining Amount", "剩余金额"),
        ("Orders", "订单"),
        ("Basic Information", "基本信息"),
        ("Amount Information", "金额信息")
    ]
    
    for source_text, translated_text in translations:
        # 检查翻译是否存在
        existing = frappe.db.get_value(
            "Translation",
            {
                "source_text": source_text,
                "language": "zh"
            }
        )
        
        if not existing:
            # 添加新翻译
            frappe.get_doc({
                "doctype": "Translation",
                "language": "zh",
                "source_text": source_text,
                "translated_text": translated_text
            }).insert(ignore_permissions=True)
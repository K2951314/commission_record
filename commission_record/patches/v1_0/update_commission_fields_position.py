
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

def execute():
    """更新联系人分成字段的位置"""
    custom_fields = {
        "Contact": [
            {
                "fieldname": "total_commission",
                "label": "分成总额",
                "fieldtype": "Currency",
                "insert_after": "first_name",
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
    
    # 更新现有字段
    create_custom_fields(custom_fields, update=True)
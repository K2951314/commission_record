from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

def execute():
    """创建联系人的分成字段"""
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
    
    create_custom_fields(custom_fields, ignore_validate=True)

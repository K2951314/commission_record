from __future__ import unicode_literals
from frappe import _

def get_data():
    return [
        {
            "label": _("Commission Record Module"),
            "icon": "octicon octicon-file-directory",
            "items": [
                {
                    "type": "doctype",
                    "name": "Commission Record",
                    "label": _("分成记录"),
                    "description": _("管理分成记录")
                },
                {
                    "type": "doctype",
                    "name": "Commission Payment",
                    "label": _("分成支付"),
                    "description": _("管理分成支付")
                },
                {
                    "type": "report",
                    "name": "Commission Report",
                    "doctype": "Commission Record",
                    "is_query_report": True,
                    "label": _("分成统计表")
                }
            ]
        }
    ]
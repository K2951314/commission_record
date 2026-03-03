# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe.utils import cint

LEGACY_DOCTYPES = ["Commission Record", "Commission Payment"]
ALLOWED_LEGACY_ROLES = {"System Manager"}
LOCKED_PERMISSION_FIELDS = [
    "select",
    "read",
    "write",
    "create",
    "delete",
    "submit",
    "cancel",
    "amend",
    "report",
    "export",
    "import",
    "share",
    "print",
    "email",
]


def before_install():
    """安装前检查"""
    if not frappe.db.exists("DocType", "Sales Order"):
        frappe.throw("请先安装 ERPNext")


def after_install():
    """安装后设置"""
    setup_custom_fields()
    setup_initial_values()
    enforce_legacy_write_scope()


def after_migrate():
    """迁移后强化权限并重算汇总，保证新旧数据口径一致"""
    setup_custom_fields()
    enforce_legacy_write_scope()

    try:
        from commission_record.api.recovery import recalculate_contact_totals

        recalculate_contact_totals()
    except Exception:
        # 避免迁移过程中因历史脏数据中断站点升级
        frappe.log_error(frappe.get_traceback(), "Commission Record after_migrate")


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
                "default": "0",
            },
            {
                "fieldname": "remaining_commission",
                "label": "剩余分成",
                "fieldtype": "Currency",
                "insert_after": "total_commission",
                "read_only": 1,
                "default": "0",
            },
        ]
    }

    create_custom_fields(custom_fields, update=True)


def setup_initial_values():
    """设置初始值"""
    if not frappe.db.exists("DocType", "Contact"):
        return

    contacts = frappe.get_all("Contact", pluck="name")
    for contact_name in contacts:
        doc = frappe.get_doc("Contact", contact_name)
        if not hasattr(doc, "total_commission"):
            doc.db_set("total_commission", 0, update_modified=False)
        if not hasattr(doc, "remaining_commission"):
            doc.db_set("remaining_commission", 0, update_modified=False)


def enforce_legacy_write_scope():
    """旧流程仅保留管理员角色，避免业务侧继续从旧 Doctype 录入"""
    perm_doctypes = ["DocPerm", "Custom DocPerm"]

    for doctype in LEGACY_DOCTYPES:
        for perm_doctype in perm_doctypes:
            if not frappe.db.exists("DocType", perm_doctype):
                continue

            meta = frappe.get_meta(perm_doctype)
            editable_fields = [f for f in LOCKED_PERMISSION_FIELDS if meta.has_field(f)]
            if not editable_fields:
                continue

            perms = frappe.get_all(
                perm_doctype,
                filters={"parent": doctype},
                fields=["name", "role"] + editable_fields,
                limit_page_length=0,
            )

            for perm in perms:
                if perm.role in ALLOWED_LEGACY_ROLES:
                    continue

                updates = {}
                for fieldname in editable_fields:
                    if cint(perm.get(fieldname)):
                        updates[fieldname] = 0

                if updates:
                    frappe.db.set_value(
                        perm_doctype,
                        perm.name,
                        updates,
                        update_modified=False,
                    )

        frappe.clear_cache(doctype=doctype)


def validate_contact(doc, method):
    """验证联系人文档"""
    if not hasattr(doc, "total_commission"):
        doc.total_commission = 0
    if not hasattr(doc, "remaining_commission"):
        doc.remaining_commission = 0

    doc.total_commission = max(0, float(doc.total_commission))
    doc.remaining_commission = max(0, float(doc.remaining_commission))

import json

import frappe
from frappe import _
from frappe.utils import cint, cstr, flt


COMMISSION_FIELDS = [
    "contact",
    "commission_ratio_numerator",
    "commission_ratio_denominator",
    "commission_percentage",
    "payment_status",
    "total_sales",
    "total_purchase",
    "total_shipping",
    "commission_amount",
    "remaining_commission",
    "docstatus",
    "creation",
    "modified",
]
DEFAULT_WORKSPACE_ROLES = {
    "System Manager",
    "Sales User",
    "Sales Manager",
    "Accounts User",
    "Accounts Manager",
}


def _to_dict(payload):
    if isinstance(payload, dict):
        return payload

    if isinstance(payload, str):
        return json.loads(payload)

    frappe.throw(_("payload 必须是 JSON 字符串或对象"))


def _get_workspace_roles():
    configured = frappe.conf.get("commission_workspace_roles")
    if not configured:
        return set(DEFAULT_WORKSPACE_ROLES)

    if isinstance(configured, str):
        roles = [r.strip() for r in configured.split(",") if r.strip()]
        return set(roles) or set(DEFAULT_WORKSPACE_ROLES)

    if isinstance(configured, (list, tuple, set)):
        roles = [cstr(r).strip() for r in configured if cstr(r).strip()]
        return set(roles) or set(DEFAULT_WORKSPACE_ROLES)

    return set(DEFAULT_WORKSPACE_ROLES)


def _ensure_workspace_access():
    if frappe.session.user == "Guest":
        frappe.throw(_("请先登录"), frappe.PermissionError)

    allowed_roles = _get_workspace_roles()
    user_roles = set(frappe.get_roles(frappe.session.user))
    if user_roles.intersection(allowed_roles):
        return

    frappe.throw(
        _("无权限访问 Commission Workspace，请在 site_config 设置 commission_workspace_roles"),
        frappe.PermissionError,
    )


def _ensure_positive_int(value, label):
    parsed = cint(value)
    if parsed <= 0:
        frappe.throw(_("{0}必须大于 0").format(label))
    return parsed


def _normalize_action(action):
    action = cstr(action or "save").strip().lower()
    if action not in {"save", "submit", "cancel"}:
        frappe.throw(_("action 仅支持 save/submit/cancel"))
    return action


@frappe.whitelist()
def preview_calculation(lines, numerator, denominator):
    _ensure_workspace_access()

    if isinstance(lines, str):
        lines = json.loads(lines)

    if not isinstance(lines, list):
        frappe.throw(_("lines 必须是数组"))

    numerator = _ensure_positive_int(numerator, _("分子"))
    denominator = _ensure_positive_int(denominator, _("分母"))

    total_sales = 0
    total_purchase = 0
    total_shipping = 0

    for row in lines:
        total_sales += flt(row.get("sales_amount"))
        total_purchase += flt(row.get("purchase_cost"))
        total_shipping += flt(row.get("shipping_fee"))

    ratio = flt(numerator) / flt(denominator)
    commission_amount = flt((total_sales - total_purchase - total_shipping) * ratio)

    return {
        "total_sales": flt(total_sales),
        "total_purchase": flt(total_purchase),
        "total_shipping": flt(total_shipping),
        "commission_ratio_numerator": numerator,
        "commission_ratio_denominator": denominator,
        "commission_percentage": flt(ratio * 100, 6),
        "commission_amount": commission_amount,
    }


@frappe.whitelist()
def list_commission_records(filters=None, start=0, page_len=20):
    _ensure_workspace_access()
    filters = _to_dict(filters or {})

    query_filters = {}
    if filters.get("contact"):
        query_filters["contact"] = filters["contact"]
    if filters.get("docstatus") is not None and filters.get("docstatus") != "":
        query_filters["docstatus"] = cint(filters.get("docstatus"))
    if filters.get("payment_status"):
        query_filters["payment_status"] = filters["payment_status"]

    fields = ["name"] + COMMISSION_FIELDS
    data = frappe.get_all(
        "Commission Record",
        filters=query_filters,
        fields=fields,
        start=cint(start),
        page_length=cint(page_len),
        order_by="modified desc",
    )

    return data


@frappe.whitelist()
def get_commission_record(name):
    _ensure_workspace_access()
    if not name:
        frappe.throw(_("缺少单据名称"))
    doc = frappe.get_doc("Commission Record", name)
    return doc.as_dict()


@frappe.whitelist()
def save_commission_record(payload):
    _ensure_workspace_access()
    data = _to_dict(payload)

    name = data.get("name")
    action = _normalize_action(data.get("action"))

    if action == "cancel":
        if not name:
            frappe.throw(_("取消操作必须传入 name"))
        if not frappe.db.exists("Commission Record", name):
            frappe.throw(_("单据不存在: {0}").format(name))

        doc = frappe.get_doc("Commission Record", name)
        if doc.docstatus != 1:
            frappe.throw(_("仅已提交单据可以取消"))
        doc.flags.ignore_permissions = True
        doc.cancel()
        return {
            "ok": True,
            "name": doc.name,
            "docstatus": doc.docstatus,
            "doc": doc.as_dict(),
        }

    if name and frappe.db.exists("Commission Record", name):
        doc = frappe.get_doc("Commission Record", name)
        if doc.docstatus != 0:
            frappe.throw(_("已提交/已取消单据不可通过保存接口修改"))
    else:
        doc = frappe.new_doc("Commission Record")

    if not data.get("contact"):
        frappe.throw(_("联系人不能为空"))

    doc.contact = data.get("contact")
    doc.commission_ratio_numerator = _ensure_positive_int(
        data.get("commission_ratio_numerator"), _("分子")
    )
    doc.commission_ratio_denominator = _ensure_positive_int(
        data.get("commission_ratio_denominator"), _("分母")
    )

    orders = data.get("orders") or []
    if not orders:
        frappe.throw(_("至少需要一行订单明细"))

    doc.set("orders", [])
    for row in orders:
        doc.append(
            "orders",
            {
                "sales_order": row.get("sales_order"),
                "sales_amount": flt(row.get("sales_amount")),
                "purchase_order": row.get("purchase_order"),
                "purchase_cost": flt(row.get("purchase_cost")),
                "shipping_fee": flt(row.get("shipping_fee")),
            },
        )

    doc.flags.ignore_permissions = True
    doc.save()

    if action == "submit" and doc.docstatus == 0:
        doc.flags.ignore_permissions = True
        doc.submit()

    return {
        "ok": True,
        "name": doc.name,
        "docstatus": doc.docstatus,
        "doc": doc.as_dict(),
    }

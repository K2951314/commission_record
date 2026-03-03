import json
import os
from datetime import datetime

import frappe
from frappe import _
from frappe.utils import cint, flt

BUNDLE_VERSION = 1
MAX_NAME_LEN = 140
COLLISION_MODES = {"rename", "skip"}


def _now_stamp():
    return datetime.now().strftime("%Y%m%d%H%M%S")


def _looks_like_path(value):
    if not isinstance(value, str):
        return False
    return (
        value.startswith("/")
        or value.startswith("\\")
        or value.startswith("./")
        or value.startswith("../")
        or value.startswith("files/")
        or value.startswith("private/files/")
        or value.endswith(".json")
        or ":" in value  # Windows path
    )


def _to_bool(value):
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def _ensure_system_manager():
    user_roles = set(frappe.get_roles(frappe.session.user))
    if frappe.session.user == "Guest" or "System Manager" not in user_roles:
        frappe.throw(_("仅 System Manager 可执行恢复/清理操作"), frappe.PermissionError)


def _resolve_collision_mode(collision_mode, file_path):
    if file_path in COLLISION_MODES and collision_mode not in COLLISION_MODES:
        collision_mode, file_path = file_path, collision_mode

    if collision_mode in (None, ""):
        collision_mode = "rename"

    if collision_mode not in COLLISION_MODES:
        if _looks_like_path(collision_mode) and not file_path:
            return "rename", collision_mode
        frappe.throw(_("不支持的 collision_mode: {0}").format(collision_mode))

    return collision_mode, file_path


def _resolve_file_path(file_path):
    if not file_path:
        frappe.throw(_("缺少 file_path 参数"))

    if file_path.startswith("/private/files/"):
        return frappe.get_site_path("private", "files", os.path.basename(file_path))

    if file_path.startswith("/files/"):
        return frappe.get_site_path("public", "files", os.path.basename(file_path))

    if file_path.startswith("private/files/"):
        return frappe.get_site_path(file_path)

    if file_path.startswith("files/"):
        return frappe.get_site_path("public", file_path)

    if os.path.isabs(file_path):
        return file_path

    return frappe.get_site_path(file_path)


def _latest_bundle_file():
    private_files = frappe.get_site_path("private", "files")
    if not os.path.isdir(private_files):
        return None

    candidates = []
    for filename in os.listdir(private_files):
        if not filename.startswith("commission_bundle_") or not filename.endswith(".json"):
            continue
        full_path = os.path.join(private_files, filename)
        candidates.append((os.path.getmtime(full_path), full_path))

    if not candidates:
        return None

    candidates.sort(key=lambda x: x[0], reverse=True)
    return candidates[0][1]


def _write_private_json(filename, data):
    file_path = frappe.get_site_path("private", "files", filename)
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)

    return {
        "filename": filename,
        "file_path": file_path,
        "file_url": f"/private/files/{filename}",
    }


def _get_parent_docs(doctype):
    names = frappe.get_all(doctype, pluck="name", order_by="creation asc")
    return [frappe.get_doc(doctype, name).as_dict() for name in names]


def _get_contact_totals_snapshot():
    if not frappe.db.has_column("Contact", "total_commission"):
        return []

    return frappe.get_all(
        "Contact",
        fields=["name", "total_commission", "remaining_commission"],
        limit_page_length=0,
    )


def _summed_commission_by_contact():
    rows = frappe.db.sql(
        """
        SELECT contact, IFNULL(SUM(commission_amount), 0) AS total_commission
        FROM `tabCommission Record`
        WHERE docstatus = 1
        GROUP BY contact
        """,
        as_dict=1,
    )
    return {row.contact: flt(row.total_commission) for row in rows}


def _summed_paid_by_contact():
    rows = frappe.db.sql(
        """
        SELECT cr.contact, IFNULL(SUM(cpa.allocated_amount), 0) AS total_paid
        FROM `tabCommission Payment Allocation` cpa
        INNER JOIN `tabCommission Payment` cp ON cp.name = cpa.parent
        INNER JOIN `tabCommission Record` cr ON cr.name = cpa.commission_record
        WHERE cp.docstatus = 1
        GROUP BY cr.contact
        """,
        as_dict=1,
    )
    return {row.contact: flt(row.total_paid) for row in rows}


def _resolve_target_name(doctype, source_name, collision_mode, suffix):
    if not source_name:
        return None

    if not frappe.db.exists(doctype, source_name):
        return source_name

    if collision_mode == "skip":
        return None

    base = f"{source_name}-OLD-{suffix}"
    candidate = base[:MAX_NAME_LEN]
    i = 1
    while frappe.db.exists(doctype, candidate):
        marker = f"-{i}"
        candidate = f"{base[: MAX_NAME_LEN - len(marker)]}{marker}"
        i += 1

    return candidate


def _normalize_child_row(raw_row, child_doctype):
    meta = frappe.get_meta(child_doctype)
    row = {"doctype": child_doctype}

    for df in meta.fields:
        if df.fieldtype == "Table":
            continue
        fieldname = df.fieldname
        if fieldname in raw_row:
            row[fieldname] = raw_row.get(fieldname)

    return row


def _normalize_doc_payload(raw_doc, doctype):
    meta = frappe.get_meta(doctype)
    payload = {"doctype": doctype}

    for df in meta.fields:
        fieldname = df.fieldname
        if fieldname not in raw_doc:
            continue

        if df.fieldtype == "Table":
            payload[fieldname] = [
                _normalize_child_row(row, df.options) for row in (raw_doc.get(fieldname) or [])
            ]
            continue

        payload[fieldname] = raw_doc.get(fieldname)

    return payload, cint(raw_doc.get("docstatus", 0))


def _insert_doc_with_status(payload, target_name, original_docstatus):
    doc = frappe.get_doc(payload)
    doc.insert(ignore_permissions=True, ignore_links=True, set_name=target_name)

    if original_docstatus == 1:
        doc.flags.ignore_permissions = True
        doc.submit()
    elif original_docstatus == 2:
        doc.flags.ignore_permissions = True
        doc.submit()
        doc.flags.ignore_permissions = True
        doc.cancel()

    return doc.name


def _build_data_profile():
    counts = {
        "commission_record": cint(frappe.db.count("Commission Record")),
        "commission_payment": cint(frappe.db.count("Commission Payment")),
        "commission_payment_allocation": cint(frappe.db.count("Commission Payment Allocation")),
        "commission_record_detail": cint(frappe.db.count("Commission Record Detail")),
    }

    total_by_contact = _summed_commission_by_contact()
    paid_by_contact = _summed_paid_by_contact()

    non_zero_contacts = 0
    mismatches = []

    if frappe.db.has_column("Contact", "total_commission"):
        contacts = frappe.get_all(
            "Contact",
            fields=["name", "total_commission", "remaining_commission"],
            limit_page_length=0,
        )

        for row in contacts:
            stored_total = flt(row.total_commission)
            stored_remaining = flt(row.remaining_commission)
            expected_total = flt(total_by_contact.get(row.name, 0))
            expected_remaining = flt(expected_total - paid_by_contact.get(row.name, 0))

            if stored_total > 0 or stored_remaining > 0:
                non_zero_contacts += 1

            if abs(stored_total - expected_total) > 0.01 or abs(stored_remaining - expected_remaining) > 0.01:
                mismatches.append(
                    {
                        "contact": row.name,
                        "stored_total": stored_total,
                        "expected_total": expected_total,
                        "stored_remaining": stored_remaining,
                        "expected_remaining": expected_remaining,
                    }
                )

    return {
        "generated_at": frappe.utils.now_datetime().isoformat(),
        "counts": counts,
        "contacts_with_non_zero_totals": non_zero_contacts,
        "mismatch_count": len(mismatches),
        "mismatches": mismatches,
    }


@frappe.whitelist()
def export_data_profile_report(filename="pre_recovery_report.json"):
    _ensure_system_manager()
    report = _build_data_profile()
    file_info = _write_private_json(filename, report)
    return {
        "ok": True,
        "report": report,
        "report_file": file_info,
    }


@frappe.whitelist()
def export_bundle(filename=None):
    _ensure_system_manager()
    suffix = _now_stamp()
    filename = filename or f"commission_bundle_{suffix}.json"

    bundle = {
        "bundle_version": BUNDLE_VERSION,
        "exported_at": frappe.utils.now_datetime().isoformat(),
        "commission_record": _get_parent_docs("Commission Record"),
        "commission_record_detail": frappe.get_all(
            "Commission Record Detail", fields=["*"], limit_page_length=0
        ),
        "commission_payment": _get_parent_docs("Commission Payment"),
        "commission_payment_allocation": frappe.get_all(
            "Commission Payment Allocation", fields=["*"], limit_page_length=0
        ),
        "contact_snapshot": _get_contact_totals_snapshot(),
    }

    file_info = _write_private_json(filename, bundle)
    return {
        "ok": True,
        "bundle_counts": {
            "commission_record": len(bundle["commission_record"]),
            "commission_payment": len(bundle["commission_payment"]),
            "commission_record_detail": len(bundle["commission_record_detail"]),
            "commission_payment_allocation": len(bundle["commission_payment_allocation"]),
            "contact_snapshot": len(bundle["contact_snapshot"]),
        },
        "bundle_file": file_info,
    }


@frappe.whitelist()
def import_bundle(collision_mode="rename", file_path=None):
    _ensure_system_manager()

    collision_mode, file_path = _resolve_collision_mode(collision_mode, file_path)
    source = _resolve_file_path(file_path) if file_path else _latest_bundle_file()

    if not source:
        frappe.throw(_("未找到可导入的数据包，请先执行 export_bundle() 或传入 file_path"))

    if not os.path.exists(source):
        frappe.throw(_("数据包文件不存在: {0}").format(source))

    with open(source, "r", encoding="utf-8") as f:
        bundle = json.load(f)

    if not isinstance(bundle, dict):
        frappe.throw(_("数据包格式不正确"))

    bundle_version = cint(bundle.get("bundle_version") or BUNDLE_VERSION)
    if bundle_version > BUNDLE_VERSION:
        frappe.throw(_("数据包版本过高: {0}").format(bundle_version))

    suffix = _now_stamp()
    record_name_map = {}
    payment_name_map = {}
    skipped = []

    inserted = {
        "commission_record": 0,
        "commission_payment": 0,
    }

    try:
        for raw_doc in bundle.get("commission_record", []):
            source_name = raw_doc.get("name")
            target_name = _resolve_target_name("Commission Record", source_name, collision_mode, suffix)

            if not target_name:
                skipped.append({"doctype": "Commission Record", "name": source_name, "reason": "skip_or_invalid"})
                continue

            payload, original_docstatus = _normalize_doc_payload(raw_doc, "Commission Record")
            payload["name"] = target_name

            inserted_name = _insert_doc_with_status(payload, target_name, original_docstatus)
            record_name_map[source_name] = inserted_name
            inserted["commission_record"] += 1

        for raw_doc in bundle.get("commission_payment", []):
            source_name = raw_doc.get("name")
            target_name = _resolve_target_name("Commission Payment", source_name, collision_mode, suffix)

            if not target_name:
                skipped.append({"doctype": "Commission Payment", "name": source_name, "reason": "skip_or_invalid"})
                continue

            payload, original_docstatus = _normalize_doc_payload(raw_doc, "Commission Payment")
            payload["name"] = target_name

            allocations = payload.get("allocations", [])
            for row in allocations:
                old_record = row.get("commission_record")
                if old_record in record_name_map:
                    row["commission_record"] = record_name_map[old_record]

            inserted_name = _insert_doc_with_status(payload, target_name, original_docstatus)
            payment_name_map[source_name] = inserted_name
            inserted["commission_payment"] += 1

        recalc = recalculate_contact_totals(commit=False)
        report = _build_data_profile()
        report_file = _write_private_json("post_recovery_report.json", report)

        name_map_payload = {
            "generated_at": frappe.utils.now_datetime().isoformat(),
            "collision_mode": collision_mode,
            "source_bundle": source,
            "record_name_map": record_name_map,
            "payment_name_map": payment_name_map,
            "skipped": skipped,
        }
        name_map_file = _write_private_json("name_map.json", name_map_payload)
        stamped_name_map_file = _write_private_json(f"name_map_{suffix}.json", name_map_payload)

        frappe.db.commit()

        return {
            "ok": True,
            "collision_mode": collision_mode,
            "source_bundle": source,
            "inserted": inserted,
            "skipped": skipped,
            "recalculate": recalc,
            "report": report,
            "name_map_file": name_map_file,
            "name_map_snapshot_file": stamped_name_map_file,
            "post_recovery_report_file": report_file,
        }
    except Exception:
        frappe.db.rollback()
        raise


@frappe.whitelist()
def recalculate_contact_totals(commit=True):
    _ensure_system_manager()
    if not frappe.db.has_column("Contact", "total_commission"):
        return {"ok": False, "message": "Contact 未包含分成汇总字段"}

    frappe.db.sql(
        """
        UPDATE `tabContact`
        SET total_commission = 0,
            remaining_commission = 0
        """
    )

    total_by_contact = _summed_commission_by_contact()
    paid_by_contact = _summed_paid_by_contact()

    updated = 0
    missing_contacts = []
    for contact, total in total_by_contact.items():
        if not frappe.db.exists("Contact", contact):
            missing_contacts.append(contact)
            continue

        remaining = flt(total) - flt(paid_by_contact.get(contact, 0))
        frappe.db.set_value(
            "Contact",
            contact,
            {
                "total_commission": flt(total),
                "remaining_commission": flt(remaining),
            },
            update_modified=False,
        )
        updated += 1

    if _to_bool(commit):
        frappe.db.commit()

    return {
        "ok": True,
        "updated_contacts": updated,
        "missing_contacts_count": len(missing_contacts),
        "missing_contacts": missing_contacts[:100],
    }


@frappe.whitelist()
def purge_all_commission_data(confirm=False):
    _ensure_system_manager()
    if not _to_bool(confirm):
        frappe.throw(_("危险操作：请传入 confirm=1 后再执行"))

    counts_before = {
        "commission_record": cint(frappe.db.count("Commission Record")),
        "commission_payment": cint(frappe.db.count("Commission Payment")),
        "commission_payment_allocation": cint(frappe.db.count("Commission Payment Allocation")),
        "commission_record_detail": cint(frappe.db.count("Commission Record Detail")),
    }

    try:
        frappe.db.sql("DELETE FROM `tabCommission Payment Allocation`")
        frappe.db.sql("DELETE FROM `tabCommission Payment`")
        frappe.db.sql("DELETE FROM `tabCommission Record Detail`")
        frappe.db.sql("DELETE FROM `tabCommission Record`")

        recalc = recalculate_contact_totals(commit=False)
        report = _build_data_profile()
        file_info = _write_private_json("post_purge_report.json", report)

        frappe.db.commit()
    except Exception:
        frappe.db.rollback()
        raise

    return {
        "ok": True,
        "deleted_counts": counts_before,
        "recalculate": recalc,
        "report": report,
        "post_purge_report_file": file_info,
    }

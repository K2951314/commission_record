from fractions import Fraction

import frappe
from frappe.utils import cint, flt


def execute():
    if not frappe.db.has_column("Commission Record", "commission_ratio_numerator"):
        return

    rows = frappe.get_all(
        "Commission Record",
        fields=[
            "name",
            "commission_percentage",
            "commission_ratio_numerator",
            "commission_ratio_denominator",
        ],
        limit_page_length=0,
    )

    for row in rows:
        numerator = cint(row.commission_ratio_numerator)
        denominator = cint(row.commission_ratio_denominator)

        if numerator > 0 and denominator > 0:
            continue

        pct = flt(row.commission_percentage)
        if pct <= 0:
            numerator, denominator = 1, 2
        else:
            ratio = Fraction(str(pct / 100)).limit_denominator(10000)
            numerator, denominator = ratio.numerator, ratio.denominator

        frappe.db.set_value(
            "Commission Record",
            row.name,
            {
                "commission_ratio_numerator": numerator,
                "commission_ratio_denominator": denominator,
                "commission_percentage": flt((numerator / denominator) * 100, 6),
            },
            update_modified=False,
        )

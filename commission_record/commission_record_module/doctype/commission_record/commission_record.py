import frappe
from fractions import Fraction
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt


class CommissionRecord(Document):
    def validate(self):
        self.normalize_ratio_fields()
        self.calculate_totals()
        self.calculate_remaining_commission()
        self.update_payment_status()

    def on_submit(self):
        """提交时更新联系人分成信息"""
        self.update_contact_commission()

    def on_cancel(self):
        """取消提交时更新联系人分成信息"""
        self.update_contact_commission()

    def on_update_after_submit(self):
        """提交后更新时重新计算剩余分成"""
        self.normalize_ratio_fields()
        self.calculate_remaining_commission()
        self.update_payment_status()
        self.db_update()
        self.update_contact_commission()

    def normalize_ratio_fields(self):
        """统一分子/分母并回写兼容百分比字段"""
        numerator = _to_int(self.commission_ratio_numerator)
        denominator = _to_int(self.commission_ratio_denominator)

        if numerator <= 0 or denominator <= 0:
            numerator, denominator = self._derive_ratio_from_percentage()

        if denominator <= 0:
            frappe.throw(_("分成分母必须大于 0"))

        self.commission_ratio_numerator = numerator
        self.commission_ratio_denominator = denominator
        self.commission_percentage = flt((numerator / denominator) * 100, 6)

    def _derive_ratio_from_percentage(self):
        pct = flt(self.commission_percentage)
        if pct <= 0:
            return 1, 2

        ratio = Fraction(str(pct / 100)).limit_denominator(10000)
        return ratio.numerator, ratio.denominator

    def calculate_totals(self):
        """计算总额和分成金额"""
        total_sales = 0
        total_purchase = 0
        total_shipping = 0

        for order in self.orders:
            total_sales += flt(order.sales_amount)
            total_purchase += flt(order.purchase_cost)
            total_shipping += flt(order.shipping_fee)

        self.total_sales = total_sales
        self.total_purchase = total_purchase
        self.total_shipping = total_shipping

        ratio = flt(self.commission_ratio_numerator) / flt(self.commission_ratio_denominator)
        self.commission_amount = flt((total_sales - total_purchase - total_shipping) * ratio)

    def calculate_remaining_commission(self):
        """计算剩余分成金额"""
        if not self.commission_amount:
            self.remaining_commission = 0
            return

        total_paid = frappe.db.sql(
            """
            SELECT IFNULL(SUM(cpa.allocated_amount), 0)
            FROM `tabCommission Payment Allocation` cpa
            INNER JOIN `tabCommission Payment` cp ON cp.name = cpa.parent
            WHERE cpa.commission_record = %s
            AND cp.docstatus = 1
            """,
            self.name,
        )[0][0]

        self.remaining_commission = flt(self.commission_amount) - flt(total_paid)

    def update_payment_status(self):
        """更新支付状态"""
        if flt(self.remaining_commission) <= 0:
            self.payment_status = "已支付"
        elif flt(self.remaining_commission) < flt(self.commission_amount):
            self.payment_status = "部分支付"
        else:
            self.payment_status = "未支付"

    def update_contact_commission(self):
        """更新联系人的分成总额和剩余分成"""
        if not self.contact:
            return

        contact = frappe.get_doc("Contact", self.contact)

        total_commission = frappe.db.sql(
            """
            SELECT IFNULL(SUM(commission_amount), 0)
            FROM `tabCommission Record`
            WHERE contact = %s
            AND docstatus = 1
            """,
            self.contact,
        )[0][0]

        total_paid = frappe.db.sql(
            """
            SELECT IFNULL(SUM(cpa.allocated_amount), 0)
            FROM `tabCommission Payment Allocation` cpa
            INNER JOIN `tabCommission Payment` cp ON cp.name = cpa.parent
            INNER JOIN `tabCommission Record` cr ON cr.name = cpa.commission_record
            WHERE cr.contact = %s
            AND cp.docstatus = 1
            """,
            self.contact,
        )[0][0]

        contact.db_set("total_commission", total_commission)
        contact.db_set("remaining_commission", flt(total_commission) - flt(total_paid))
        contact.notify_update()


def _to_int(value):
    try:
        return int(flt(value))
    except Exception:
        return 0

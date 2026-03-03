// 佣金记录表单客户端脚本

function get_ratio(frm) {
    const numerator = cint(frm.doc.commission_ratio_numerator || 0);
    const denominator = cint(frm.doc.commission_ratio_denominator || 0);
    if (denominator <= 0) {
        return { numerator, denominator: 0, ratio: 0 };
    }

    return {
        numerator,
        denominator,
        ratio: numerator / denominator
    };
}

frappe.ui.form.on('Commission Record', {
    setup: function(frm) {
        frm.set_query('sales_order', 'orders', function() {
            return { filters: { docstatus: 1 } };
        });

        frm.set_query('purchase_order', 'orders', function() {
            return { filters: { docstatus: 1 } };
        });
    },

    refresh: function(frm) {
        frm.trigger('calculate_totals');

        if (frm.doc.docstatus === 0) {
            frm.page.set_primary_action(__('提交'), function() {
                frm.savesubmit();
            });
        } else if (frm.doc.docstatus === 1) {
            frm.page.set_secondary_action(__('取消'), function() {
                frm.savecancel();
            });
        }
    },

    commission_ratio_numerator: function(frm) {
        frm.trigger('calculate_totals');
    },

    commission_ratio_denominator: function(frm) {
        frm.trigger('calculate_totals');
    },

    commission_percentage: function(frm) {
        // 兼容旧数据，仍允许手工改百分比时回算分数
        const pct = flt(frm.doc.commission_percentage || 0);
        if (pct <= 0) {
            return;
        }

        frm.set_value('commission_ratio_numerator', Math.round(pct));
        frm.set_value('commission_ratio_denominator', 100);
        frm.trigger('calculate_totals');
    },

    calculate_totals: function(frm) {
        let total_sales = 0;
        let total_purchase = 0;
        let total_shipping = 0;

        (frm.doc.orders || []).forEach(function(row) {
            total_sales += flt(row.sales_amount);
            total_purchase += flt(row.purchase_cost);
            total_shipping += flt(row.shipping_fee);
        });

        frm.set_value('total_sales', total_sales);
        frm.set_value('total_purchase', total_purchase);
        frm.set_value('total_shipping', total_shipping);

        const ratio = get_ratio(frm);
        if (ratio.denominator <= 0) {
            frm.set_value('commission_amount', 0);
            frm.set_value('commission_percentage', 0);
            return;
        }

        frm.set_value('commission_percentage', flt(ratio.ratio * 100, 6));

        const commission = (total_sales - total_purchase - total_shipping) * ratio.ratio;
        frm.set_value('commission_amount', commission);
    },

    orders_add: function(frm) {
        frm.trigger('calculate_totals');
    },

    orders_remove: function(frm) {
        frm.trigger('calculate_totals');
    }
});

frappe.ui.form.on('Commission Record Detail', {
    sales_order: function(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        if (!row.sales_order) {
            return;
        }

        frappe.call({
            method: 'frappe.client.get_value',
            args: {
                doctype: 'Sales Order',
                filters: { name: row.sales_order },
                fieldname: 'base_net_total'
            },
            callback: function(r) {
                if (!r.message) {
                    return;
                }

                frappe.model.set_value(cdt, cdn, 'sales_amount', r.message.base_net_total);
                frm.trigger('calculate_totals');
            }
        });
    },

    purchase_order: function(frm, cdt, cdn) {
        const row = locals[cdt][cdn];
        if (!row.purchase_order) {
            return;
        }

        frappe.call({
            method: 'frappe.client.get_value',
            args: {
                doctype: 'Purchase Order',
                filters: { name: row.purchase_order },
                fieldname: 'base_net_total'
            },
            callback: function(r) {
                if (!r.message) {
                    return;
                }

                frappe.model.set_value(cdt, cdn, 'purchase_cost', r.message.base_net_total);
                frm.trigger('calculate_totals');
            }
        });
    },

    shipping_fee: function(frm) {
        frm.trigger('calculate_totals');
    }
});

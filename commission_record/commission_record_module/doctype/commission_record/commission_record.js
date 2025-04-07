
frappe.ui.form.on('Commission Record', {
    setup: function(frm) {
        // 设置销售订单字段的过滤器
        frm.set_query('sales_order', 'orders', function() {
            return {
                filters: {
                    docstatus: 1
                }
            };
        });

        // 设置采购订单字段的过滤器
        frm.set_query('purchase_order', 'orders', function() {
            return {
                filters: {
                    docstatus: 1
                }
            };
        });
    },

    refresh: function(frm) {
        frm.trigger('calculate_totals');

        // 添加提交和取消按钮
        if (frm.doc.docstatus === 0) {  // 草稿状态
            frm.page.set_primary_action(__('提交'), function() {
                frm.savesubmit();
            });
        } else if (frm.doc.docstatus === 1) {  // 已提交状态
            frm.page.set_secondary_action(__('取消'), function() {
                frm.savecancel();
            });
        }
    },

    calculate_totals: function(frm) {
        let total_sales = 0;
        let total_purchase = 0;
        let total_shipping = 0;

        // 计算所有订单的总额
        (frm.doc.orders || []).forEach(function(row) {
            total_sales += flt(row.sales_amount);
            total_purchase += flt(row.purchase_cost);
            total_shipping += flt(row.shipping_fee);
        });

        // 更新总额字段
        frm.set_value('total_sales', total_sales);
        frm.set_value('total_purchase', total_purchase);
        frm.set_value('total_shipping', total_shipping);

        // 计算分成金额：(销售总额 - 采购总额 - 快递总额) / 2
        let commission = (total_sales - total_purchase - total_shipping) / 2;
        frm.set_value('commission_amount', commission);
    }
});

frappe.ui.form.on('Commission Record Detail', {
    orders_add: function(frm, cdt, cdn) {
        frm.trigger('calculate_totals');
    },

    orders_remove: function(frm, cdt, cdn) {
        frm.trigger('calculate_totals');
    },

    sales_order: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        if (row.sales_order) {
            frappe.call({
                method: 'frappe.client.get_value',
                args: {
                    doctype: 'Sales Order',
                    filters: { name: row.sales_order },
                    fieldname: 'base_net_total'
                },
                callback: function(r) {
                    if (r.message) {
                        frappe.model.set_value(cdt, cdn, 'sales_amount', r.message.base_net_total);
                        frm.trigger('calculate_totals');
                    }
                }
            });
        }
    },

    purchase_order: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        if (row.purchase_order) {
            frappe.call({
                method: 'frappe.client.get_value',
                args: {
                    doctype: 'Purchase Order',
                    filters: { name: row.purchase_order },
                    fieldname: 'base_net_total'
                },
                callback: function(r) {
                    if (r.message) {
                        frappe.model.set_value(cdt, cdn, 'purchase_cost', r.message.base_net_total);
                        frm.trigger('calculate_totals');
                    }
                }
            });
        }
    },

    shipping_fee: function(frm, cdt, cdn) {
        frm.trigger('calculate_totals');
    }
});
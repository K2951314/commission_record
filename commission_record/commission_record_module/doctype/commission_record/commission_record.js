
// 佣金记录表单客户端脚本
// 主要功能：处理佣金记录表单的各种交互逻辑和计算

// 注册佣金记录表单的事件处理器
frappe.ui.form.on('Commission Record', {
    // 表单初始化设置
    setup: function(frm) {
        // 设置销售订单字段的查询过滤器
        // 只允许选择已提交的销售订单(docstatus=1)
        frm.set_query('sales_order', 'orders', function() {
            return {
                filters: {
                    docstatus: 1  // 只查询已提交的文档
                }
            };
        });

        // 设置采购订单字段的查询过滤器
        // 只允许选择已提交的采购订单(docstatus=1)
        frm.set_query('purchase_order', 'orders', function() {
            return {
                filters: {
                    docstatus: 1  // 只查询已提交的文档
                }
            };
        });
    },

    // 表单刷新时触发的逻辑
    refresh: function(frm) {
        // 每次刷新表单时重新计算总额
        frm.trigger('calculate_totals');

        // 根据文档状态设置按钮
        if (frm.doc.docstatus === 0) {  // 草稿状态
            // 添加提交按钮作为主要操作
            frm.page.set_primary_action(__('提交'), function() {
                frm.savesubmit();  // 保存并提交文档
            });
        } else if (frm.doc.docstatus === 1) {  // 已提交状态
            // 添加取消按钮作为次要操作
            frm.page.set_secondary_action(__('取消'), function() {
                frm.savecancel();  // 保存并取消文档
            });
        }
    },

    // 分成比例字段变更事件
    commission_percentage: function(frm) {
        // 当分成比例变更时，重新计算总额
        frm.trigger('calculate_totals');
    },

    // 计算各种总额的方法
    calculate_totals: function(frm) {
        // 初始化总额变量
        let total_sales = 0;      // 销售总额
        let total_purchase = 0;   // 采购总额
        let total_shipping = 0;   // 快递总额

        // 遍历所有订单行项目，计算各项总额
        (frm.doc.orders || []).forEach(function(row) {
            // 累加每行的金额
            total_sales += flt(row.sales_amount);      // 销售金额
            total_purchase += flt(row.purchase_cost);  // 采购成本
            total_shipping += flt(row.shipping_fee);   // 快递费用
        });

        // 更新表单中的总额字段
        frm.set_value('total_sales', total_sales);        // 设置销售总额
        frm.set_value('total_purchase', total_purchase);  // 设置采购总额
        frm.set_value('total_shipping', total_shipping);  // 设置快递总额

        // 计算分成金额：(销售总额 - 采购总额 - 快递总额) * 分成比例
        let commission = (total_sales - total_purchase - total_shipping) * (frm.doc.commission_percentage / 100);
        frm.set_value('commission_amount', commission);  // 设置分成金额
    }
});

// 注册佣金记录明细表的事件处理器
frappe.ui.form.on('Commission Record Detail', {
    // 当添加新订单行时触发
    orders_add: function(frm, cdt, cdn) {
        // 重新计算总额
        frm.trigger('calculate_totals');
    },

    // 当移除订单行时触发
    orders_remove: function(frm, cdt, cdn) {
        // 重新计算总额
        frm.trigger('calculate_totals');
    },

    // 销售订单字段变更事件
    sales_order: function(frm, cdt, cdn) {
        // 获取当前行对象
        let row = locals[cdt][cdn];
        if (row.sales_order) {
            // 调用服务器端方法获取销售订单的净总额
            frappe.call({
                method: 'frappe.client.get_value',
                args: {
                    doctype: 'Sales Order',
                    filters: { name: row.sales_order },
                    fieldname: 'base_net_total'  // 获取净总额字段
                },
                callback: function(r) {
                    if (r.message) {
                        // 设置当前行的销售金额为销售订单的净总额
                        frappe.model.set_value(cdt, cdn, 'sales_amount', r.message.base_net_total);
                        // 重新计算总额
                        frm.trigger('calculate_totals');
                    }
                }
            });
        }
    },

    // 采购订单字段变更事件
    purchase_order: function(frm, cdt, cdn) {
        // 获取当前行对象
        let row = locals[cdt][cdn];
        if (row.purchase_order) {
            // 调用服务器端方法获取采购订单的净总额
            frappe.call({
                method: 'frappe.client.get_value',
                args: {
                    doctype: 'Purchase Order',
                    filters: { name: row.purchase_order },
                    fieldname: 'base_net_total'  // 获取净总额字段
                },
                callback: function(r) {
                    if (r.message) {
                        // 设置当前行的采购成本为采购订单的净总额
                        frappe.model.set_value(cdt, cdn, 'purchase_cost', r.message.base_net_total);
                        // 重新计算总额
                        frm.trigger('calculate_totals');
                    }
                }
            });
        }
    },

    // 快递费用字段变更事件
    shipping_fee: function(frm, cdt, cdn) {
        // 重新计算总额
        frm.trigger('calculate_totals');
    }
});
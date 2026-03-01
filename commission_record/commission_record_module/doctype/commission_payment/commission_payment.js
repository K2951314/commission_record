frappe.ui.form.on('Commission Payment', {
    setup: function(frm) {
        // 设置联系人字段的过滤器
        frm.set_query('contact', function() {
            return {
                query: 'commission_record.commission_record_module.doctype.commission_payment.commission_payment.get_contacts_with_unpaid_commission'
            };
        });
    },

    refresh: function(frm) {
        // 设置状态指示器
        if (frm.doc.__islocal) {
            frm.set_indicator(__("尚未保存"), "orange");
        } else if (frm.doc.docstatus === 0) {
            frm.set_indicator(__("草稿"), "blue");
        } else if (frm.doc.docstatus === 1) {
            frm.set_indicator(__("已提交"), "green");
        } else if (frm.doc.docstatus === 2) {
            frm.set_indicator(__("已取消"), "red");
        }

        // 仅在必要时调用 auto_allocate_payment
        if (frm.doc.docstatus === 0 && frm.doc.contact && frm.doc.payment_amount > 0 && !frm.doc.__unsaved) {
            // 使用标志避免重复调用
            if (!frm.auto_allocated) {
                frm.auto_allocated = true;
                frm.trigger('auto_allocate_payment');
            }
        }

        // 根据文档状态设置按钮
        frm.page.clear_actions();
        
        if (frm.doc.docstatus === 0) {
            frm.page.set_primary_action(__('提交'), function() {
                frm.savesubmit();
            }).addClass('btn-primary');
        } else if (frm.doc.docstatus === 1) {
            frm.page.set_secondary_action(__('取消'), function() {
                frm.savecancel();
            }).addClass('btn-default');
        }
    },

    payment_amount: function(frm) {
        frm.auto_allocated = false; // 重置标志
        frm.trigger('auto_allocate_payment');
    },

    payment_date: function(frm) {
        // 支付日期变更不需要触发自动分配
    },

    contact: function(frm) {
        frm.auto_allocated = false; // 重置标志
        frm.trigger('auto_allocate_payment');
    },

    auto_allocate_payment: function(frm) {
        // 避免不必要的调用
        if (!frm.doc.contact || !frm.doc.payment_amount || frm.doc.payment_amount <= 0 || frm.doc.docstatus !== 0) {
            return;
        }

        frappe.call({
            method: 'commission_record.commission_record_module.doctype.commission_payment.commission_payment.get_unpaid_commission_records',
            args: {
                contact: frm.doc.contact,
                payment_amount: frm.doc.payment_amount
            },
            callback: function(r) {
                if (r.message) {
                    frm.clear_table('allocations');
                    r.message.forEach(function(record) {
                        let row = frm.add_child('allocations');
                        row.commission_record = record.name;
                        row.commission_amount = record.commission_amount;
                        row.allocated_amount = record.allocated_amount;
                        row.remaining_amount = record.remaining_amount;
                    });
                    frm.refresh_field('allocations');
                    
                    // 计算总分配金额和剩余金额
                    let total_allocated = 0;
                    frm.doc.allocations.forEach(function(row) {
                        total_allocated += flt(row.allocated_amount);
                    });
                    frm.set_value('total_allocated_amount', total_allocated);
                    frm.set_value('remaining_amount', flt(frm.doc.payment_amount) - total_allocated);
                }
            }
        });
    }
});

frappe.ui.form.on('Commission Payment Allocation', {
    allocations_add: function(frm) {
        // 当添加新行时，重新计算总额
        frm.trigger('update_totals');
    },
    
    allocations_remove: function(frm) {
        // 当删除行时，重新计算总额
        frm.trigger('update_totals');
    },
    
    allocated_amount: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        row.remaining_amount = flt(row.commission_amount) - flt(row.allocated_amount);
        frm.refresh_field('allocations');
        
        // 调用更新总额方法
        frm.trigger('update_totals');
    },
    
    update_totals: function(frm) {
        // 重新计算总分配金额和剩余金额
        let total_allocated = 0;
        (frm.doc.allocations || []).forEach(function(row) {
            total_allocated += flt(row.allocated_amount);
        });
        frm.set_value('total_allocated_amount', total_allocated);
        frm.set_value('remaining_amount', flt(frm.doc.payment_amount) - total_allocated);
    }
});
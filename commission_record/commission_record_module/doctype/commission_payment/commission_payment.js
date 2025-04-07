
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
        frm.trigger('auto_allocate_payment');

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

    payment_amount: function(frm) {
        frm.trigger('auto_allocate_payment');
    },

    payment_date: function(frm) {
        frm.trigger('auto_allocate_payment');
    },

    contact: function(frm) {
        frm.trigger('auto_allocate_payment');
    },

    auto_allocate_payment: function(frm) {
        if (!frm.doc.contact || !frm.doc.payment_amount || frm.doc.payment_amount <= 0) {
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
    allocated_amount: function(frm, cdt, cdn) {
        let row = locals[cdt][cdn];
        row.remaining_amount = flt(row.commission_amount) - flt(row.allocated_amount);
        frm.refresh_field('allocations');
        
        // 重新计算总分配金额和剩余金额
        let total_allocated = 0;
        frm.doc.allocations.forEach(function(row) {
            total_allocated += flt(row.allocated_amount);
        });
        frm.set_value('total_allocated_amount', total_allocated);
        frm.set_value('remaining_amount', flt(frm.doc.payment_amount) - total_allocated);
    }
});
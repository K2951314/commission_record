zen'mezenme
frappe.ui.form.on('Commission Payment', {
    refresh: function(frm) {
        frm.toggle_display(['total_allocated_amount', 'remaining_amount'], true);
    },

    payment_amount: function(frm) {
        if (frm.doc.payment_amount > 0 && frm.doc.contact) {
            // 当输入支付金额且已选择联系人时，自动加载未支付记录
            load_unpaid_records(frm);
        }
        calculate_allocated_amount(frm);
    },

    contact: function(frm) {
        if (frm.doc.payment_amount > 0 && frm.doc.contact) {
            // 当选择联系人且已输入支付金额时，自动加载未支付记录
            load_unpaid_records(frm);
        }
    }
});

frappe.ui.form.on('Commission Payment Allocation', {
    allocations_add: function(frm, cdt, cdn) {
        calculate_allocated_amount(frm);
    },

    allocations_remove: function(frm, cdt, cdn) {
        calculate_allocated_amount(frm);
    },

    allocated_amount: function(frm, cdt, cdn) {
        calculate_allocated_amount(frm);
    }
});

function load_unpaid_records(frm) {
    frappe.call({
        method: 'commission_record.commission_record_module.doctype.commission_payment.commission_payment.get_unpaid_records',
        args: {
            contact: frm.doc.contact
        },
        callback: function(r) {
            if (r.message && r.message.length) {
                frm.clear_table('allocations');
                let remaining_payment = flt(frm.doc.payment_amount);
                
                r.message.forEach(record => {
                    if (remaining_payment > 0) {
                        // 获取该记录的实际可分配金额
                        let available_amount = flt(record.remaining_commission);
                        if (available_amount > 0) {
                            let allocation_amount = Math.min(remaining_payment, available_amount);
                            frm.add_child('allocations', {
                                commission_record: record.name,
                                commission_amount: record.commission_amount,
                                allocated_amount: allocation_amount
                            });
                            remaining_payment -= allocation_amount;
                        }
                    }
                });
                
                frm.refresh_field('allocations');
                calculate_allocated_amount(frm);
            }
        }
    });
}

function calculate_allocated_amount(frm) {
    let total_allocated = 0;
    if (frm.doc.allocations) {
        frm.doc.allocations.forEach(function(row) {
            total_allocated += flt(row.allocated_amount);
        });
    }
    
    frm.set_value('total_allocated_amount', total_allocated);
    frm.set_value('remaining_amount', flt(frm.doc.payment_amount) - total_allocated);
    
    frm.toggle_display(['total_allocated_amount', 'remaining_amount'], true);
    frm.refresh_fields(['total_allocated_amount', 'remaining_amount']);
}
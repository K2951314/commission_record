frappe.provide('commission_record.workspace');

frappe.pages['commission-workspace'].on_page_load = function (wrapper) {
    commission_record.workspace.page = new commission_record.workspace.CommissionWorkspace(wrapper);
};

commission_record.workspace.CommissionWorkspace = class CommissionWorkspace {
    constructor(wrapper) {
        this.wrapper = wrapper;
        this.page = frappe.ui.make_app_page({
            parent: wrapper,
            title: __('Commission Workspace'),
            single_column: true,
        });

        this.state = {
            name: null,
            orders: [],
            docstatus: 0,
        };

        this.render();
        this.bind_events();
        this.add_row();
        this.refresh_list();
    }

    render() {
        this.page.main.html(`
            <div class="commission-workspace" style="display:grid;grid-template-columns:1fr 1.4fr;gap:16px;">
                <section class="card" style="border:1px solid #ddd;border-radius:8px;padding:12px;">
                    <h4>${__('记录列表')}</h4>
                    <div style="display:flex;gap:8px;margin-bottom:8px;">
                        <input type="text" class="form-control" id="cw-search-contact" placeholder="${__('联系人')}">
                        <button class="btn btn-default" id="cw-refresh">${__('刷新')}</button>
                    </div>
                    <div id="cw-list" style="max-height:520px;overflow:auto;"></div>
                </section>

                <section class="card" style="border:1px solid #ddd;border-radius:8px;padding:12px;">
                    <h4>${__('编辑区')}</h4>
                    <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;">
                        <div>
                            <label>${__('联系人')}</label>
                            <input type="text" class="form-control" id="cw-contact" />
                        </div>
                        <div>
                            <label>${__('分子')}</label>
                            <input type="number" class="form-control" id="cw-numerator" value="1" min="1" />
                        </div>
                        <div>
                            <label>${__('分母')}</label>
                            <input type="number" class="form-control" id="cw-denominator" value="2" min="1" />
                        </div>
                    </div>

                    <div style="margin-top:10px;font-size:13px;">
                        <span>${__('分成比例')}：</span><strong id="cw-percentage">50%</strong>
                        <span style="margin-left:12px;">${__('分成金额')}：</span><strong id="cw-amount">0.00</strong>
                    </div>

                    <hr>
                    <div style="display:flex;justify-content:space-between;align-items:center;">
                        <h5 style="margin:0;">${__('订单行')}</h5>
                        <button class="btn btn-default btn-sm" id="cw-add-row">${__('新增行')}</button>
                    </div>
                    <table class="table table-bordered" style="margin-top:8px;">
                        <thead>
                            <tr>
                                <th>${__('销售金额')}</th>
                                <th>${__('采购成本')}</th>
                                <th>${__('快递费')}</th>
                                <th style="width:70px;">${__('操作')}</th>
                            </tr>
                        </thead>
                        <tbody id="cw-orders"></tbody>
                    </table>

                    <div style="display:flex;gap:8px;">
                        <button class="btn btn-default" id="cw-new">${__('新建')}</button>
                        <button class="btn btn-primary" id="cw-save">${__('保存草稿')}</button>
                        <button class="btn btn-warning" id="cw-submit">${__('保存并提交')}</button>
                        <button class="btn btn-danger" id="cw-cancel" disabled>${__('取消已提交')}</button>
                    </div>
                </section>
            </div>
        `);

        this.$search = this.page.main.find('#cw-search-contact');
        this.$list = this.page.main.find('#cw-list');
        this.$contact = this.page.main.find('#cw-contact');
        this.$numerator = this.page.main.find('#cw-numerator');
        this.$denominator = this.page.main.find('#cw-denominator');
        this.$orders = this.page.main.find('#cw-orders');
        this.$percentage = this.page.main.find('#cw-percentage');
        this.$amount = this.page.main.find('#cw-amount');
        this.$save = this.page.main.find('#cw-save');
        this.$submit = this.page.main.find('#cw-submit');
        this.$cancel = this.page.main.find('#cw-cancel');
    }

    bind_events() {
        this.page.main.on('click', '#cw-refresh', () => this.refresh_list());
        this.page.main.on('click', '#cw-new', () => this.reset_editor());
        this.page.main.on('click', '#cw-add-row', () => this.add_row());
        this.page.main.on('click', '#cw-save', () => this.save('save'));
        this.page.main.on('click', '#cw-submit', () => this.save('submit'));
        this.page.main.on('click', '#cw-cancel', () => this.save('cancel'));

        this.page.main.on('input', '#cw-numerator,#cw-denominator,.cw-sales,.cw-purchase,.cw-shipping', () => {
            this.recompute_preview();
        });

        this.page.main.on('click', '.cw-remove-row', (e) => {
            $(e.currentTarget).closest('tr').remove();
            this.recompute_preview();
        });

        this.page.main.on('click', '.cw-open', (e) => {
            const name = $(e.currentTarget).data('name');
            this.load_record(name);
        });
    }

    update_action_state() {
        const is_submitted = cint(this.state.docstatus || 0) === 1;
        this.$save.prop('disabled', is_submitted);
        this.$submit.prop('disabled', is_submitted);
        this.$cancel.prop('disabled', !is_submitted);
    }

    add_row(line = {}) {
        const row = $(`
            <tr>
                <td><input type="number" class="form-control cw-sales" value="${flt(line.sales_amount || 0)}"></td>
                <td><input type="number" class="form-control cw-purchase" value="${flt(line.purchase_cost || 0)}"></td>
                <td><input type="number" class="form-control cw-shipping" value="${flt(line.shipping_fee || 0)}"></td>
                <td><button class="btn btn-xs btn-danger cw-remove-row">${__('删')}</button></td>
            </tr>
        `);
        this.$orders.append(row);
        this.recompute_preview();
    }

    collect_orders() {
        const rows = [];
        this.$orders.find('tr').each((_, tr) => {
            const $tr = $(tr);
            rows.push({
                sales_amount: flt($tr.find('.cw-sales').val() || 0),
                purchase_cost: flt($tr.find('.cw-purchase').val() || 0),
                shipping_fee: flt($tr.find('.cw-shipping').val() || 0),
            });
        });
        return rows;
    }

    recompute_preview() {
        frappe.call({
            method: 'commission_record.api.web.preview_calculation',
            args: {
                lines: this.collect_orders(),
                numerator: cint(this.$numerator.val() || 0),
                denominator: cint(this.$denominator.val() || 0),
            },
            callback: (r) => {
                if (!r.message) {
                    return;
                }
                const d = r.message;
                this.$percentage.text(`${flt(d.commission_percentage, 4)}%`);
                this.$amount.text(format_currency(d.commission_amount));
            },
            error: () => {
                this.$percentage.text('0%');
                this.$amount.text('0.00');
            },
        });
    }

    refresh_list() {
        frappe.call({
            method: 'commission_record.api.web.list_commission_records',
            args: {
                filters: {
                    contact: this.$search.val() || null,
                },
                page_len: 100,
            },
            callback: (r) => {
                const rows = r.message || [];
                const esc = (value) => {
                    if (frappe.utils && frappe.utils.escape_html) {
                        return frappe.utils.escape_html(value || '');
                    }
                    return value || '';
                };
                if (!rows.length) {
                    this.$list.html(`<div class="text-muted">${__('暂无记录')}</div>`);
                    return;
                }

                const html = rows.map((row) => `
                    <div style="padding:8px;border-bottom:1px solid #eee;display:flex;justify-content:space-between;align-items:center;">
                        <div>
                            <div><strong>${esc(row.name)}</strong></div>
                            <div class="text-muted" style="font-size:12px;">${esc(row.contact || '')} / ${row.docstatus}</div>
                        </div>
                        <button class="btn btn-xs btn-default cw-open" data-name="${esc(row.name)}">${__('打开')}</button>
                    </div>
                `).join('');

                this.$list.html(html);
            },
        });
    }

    load_record(name) {
        frappe.call({
            method: 'commission_record.api.web.get_commission_record',
            args: { name },
            callback: (r) => {
                const doc = r.message;
                if (!doc) return;

                this.state.name = doc.name;
                this.state.docstatus = cint(doc.docstatus || 0);
                this.$contact.val(doc.contact || '');
                this.$numerator.val(doc.commission_ratio_numerator || 1);
                this.$denominator.val(doc.commission_ratio_denominator || 2);
                this.$orders.empty();

                (doc.orders || []).forEach((row) => this.add_row(row));
                if (!(doc.orders || []).length) {
                    this.add_row();
                }

                this.recompute_preview();
                this.update_action_state();
            },
        });
    }

    reset_editor() {
        this.state.name = null;
        this.state.docstatus = 0;
        this.$contact.val('');
        this.$numerator.val(1);
        this.$denominator.val(2);
        this.$orders.empty();
        this.add_row();
        this.update_action_state();
    }

    save(action) {
        const payload = {
            name: this.state.name,
            contact: this.$contact.val(),
            commission_ratio_numerator: cint(this.$numerator.val() || 0),
            commission_ratio_denominator: cint(this.$denominator.val() || 0),
            orders: this.collect_orders(),
            action,
        };

        frappe.call({
            method: 'commission_record.api.web.save_commission_record',
            args: { payload },
            freeze: true,
            freeze_message: __('保存中...'),
            callback: (r) => {
                if (!r.message) return;
                this.state.name = r.message.name;
                this.state.docstatus = cint(r.message.docstatus || 0);
                frappe.show_alert({ message: __('保存成功: {0}', [r.message.name]), indicator: 'green' });
                this.refresh_list();
                this.update_action_state();
            },
        });
    }
};

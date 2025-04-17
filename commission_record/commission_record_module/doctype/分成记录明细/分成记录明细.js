// 分成记录明细前端脚本
// 功能：处理字段间的实时交互和计算
frappe.provide("frappe.ui.form");

console.debug("分成记录明细脚本初始化开始");

// ================== 核心计算函数 ==================
function calculateCommission(frm, cdt, cdn) {//frm:当前表单对象, cdt:子表文档类型, cdn:子表行名称
    try {
        if (!frm || !cdt || !cdn) {//检查参数是否存在
            console.warn("无效参数", {frm, cdt, cdn});
            return Promise.resolve(false);
        }

        const row = frappe.get_doc(cdt, cdn);//使用Frappe框架的API获取子表行数据
        if (!row) {
            console.warn("行数据不存在");
            return Promise.resolve(false);
        }

        console.debug("计算触发", {//记录计算开始时的调试信息
            sales: row.sales_amount,
            percent: row.commission_percentage,
            docname: row.name
        });

        // 验证必要字段
        if (flt(row.sales_amount) <= 0 || flt(row.commission_percentage) <= 0) {
            console.log("无效的金额或比例");
            return Promise.resolve(false);
        }

        // 执行计算
        const amount = flt(row.sales_amount * row.commission_percentage / 100, 2);
        console.log("计算结果:", amount);

        // 更新字段
        return frappe.model.set_value(cdt, cdn, "commission_amount", amount)
            .then(() => {
                console.debug("更新成功");
                frm.refresh_fields();
                return true;
            })
            .catch(e => {
                console.error("更新失败:", e);
                return false;
            });

    } catch (e) {
        console.error("计算异常:", e);
        return Promise.resolve(false);
    }
}

// ================== 主表监听 ==================
frappe.ui.form.on("分成记录明细", {
    refresh(frm) {
        console.log("表单初始化完成", frm.doc.name);
    },
    commission_percentage(frm, cdt, cdn) {
        console.log("分成比例修改事件");
        calculateCommission(frm, cdt, cdn);// 调用计算函数
    },
    sales_amount(frm, cdt, cdn) {
        console.log("销售金额修改事件");
        calculateCommission(frm, cdt, cdn);
    }
});

// ================== 子表监听 ==================
// 请替换为实际的主表Doctype名称
frappe.ui.form.on("分成记录", {
    items_add(frm, cdt, cdn) {
        const row = frappe.get_doc(cdt, cdn);
        if (row.doctype === "分成记录明细") {
            console.log("新明细行添加", row.name);
            setupRowListeners(frm, cdt, cdn);
            calculateCommission(frm, cdt, cdn);
        }
    }
});

// ================== 初始化检查 ==================
if (cur_frm) {
    console.log("当前表单类型:", cur_frm.doctype);
    if (cur_frm.doctype === "分成记录明细") {
        console.log("直接表单模式初始化");
    } else {
        console.log("子表模式初始化");
    }
}

console.debug("分成记录明细脚本初始化完成");

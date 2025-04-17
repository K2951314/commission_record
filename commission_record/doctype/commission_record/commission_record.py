
from frappe.model.document import Document

class CommissionRecord(Document):
    def validate(self):
        # 基本验证逻辑
        if not self.commission_name:
            frappe.throw("请填写分成记录名称")
        
        if self.amount <= 0:
            frappe.throw("金额必须大于0")

    def before_save(self):
        # 保存前的处理逻辑
        pass

    def after_insert(self):
        # 插入后的处理逻辑
        pass
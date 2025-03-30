app_name = "commission_record"
app_title = "分成记录"
app_publisher = "舍满取半"
app_description = "用于记录额外的分成"
app_email = "qdsmqb@163.com"
app_license = "MIT"
required_apps = ["erpnext"]

# 文档事件
doc_events = {
    "Contact": {
        "validate": "commission_record.commission_record.doctype.分成记录.分成记录.validate_contact"
    }
}

# 自定义字段
fixtures = [
    {
        "dt": "Custom Field",
        "filters": [
            [
                "name",
                "in",
                [
                    "Contact-total_commission",
                    "Contact-remaining_commission"
                ]
            ]
        ]
    }
]

# 安装前执行
before_install = "commission_record.setup.before_install"

# 安装后执行
after_install = "commission_record.setup.after_install"

# 报表
get_report_data = {
    "分成统计表": "commission_record.commission_record.report.分成统计表.分成统计表.execute"
}
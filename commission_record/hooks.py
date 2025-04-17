# -*- coding: utf-8 -*-
# 应用基本信息配置
app_name = "commission_record"  # 应用内部名称(必须与目录名一致)
app_title = "分成记录"  # 应用显示名称
app_publisher = "舍满取半"  # 发布者名称
app_description = "用于记录额外的分成"  # 应用功能描述
app_email = "qdsmqb@163.com"  # 联系邮箱
app_license = "MIT"  # 开源许可证类型
required_apps = ["erpnext"]  # 依赖的应用(必须安装才能使用本应用)


# 翻译配置
# 指定翻译文件路径和目标语言
translations = [
    {
        "source_file": "translations/zh.csv",  # 翻译文件路径(相对应用根目录)
        "target_language": "zh"  # 目标语言代码(中文)
    }
]

# 文档事件处理
# 定义文档生命周期事件的处理函数
doc_events = {
    "Contact": {  # 文档类型(联系人)
        "validate": "commission_record.commission_record.doctype.分成记录.分成记录.validate_contact"  # 验证时调用的函数路径
        # 格式: "事件类型": "模块路径.函数名"
    }
}

# 自定义字段配置
# 指定要安装的自定义字段
fixtures = [
    {
        "dt": "Custom Field",  # 文档类型(自定义字段)
        "filters": [  # 过滤条件
            [
                "name",  # 字段名
                "in",  # 操作符(包含)
                [  # 字段名列表
                    "Contact-total_commission",  # 联系人-总分成金额字段
                    "Contact-remaining_commission"  # 联系人-剩余分成金额字段
                ]
            ]
        ]
    }
]

# 安装前钩子
# 应用安装前执行的Python函数
before_install = "commission_record.setup.before_install"  # 函数路径

# 安装后钩子
# 应用安装后执行的Python函数
after_install = "commission_record.setup.after_install"  # 函数路径

# 报表配置
# 定义报表数据获取函数
get_report_data = {
    "分成统计表": "commission_record.commission_record.report.分成统计表.分成统计表.execute"  # 报表名: 执行函数路径
    # 格式: "报表名称": "模块路径.函数名"
}

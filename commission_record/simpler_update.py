#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
简单直接地更新联系人表单中的分成字段位置
用法: bench --site erpnext execute commission_record.simpler_update.execute
"""

import frappe

def execute():
    """使用最简单的方法更新字段位置"""
    try:
        # 直接使用SQL更新字段位置
        print("开始更新字段位置...")
        
        # 查询当前设置
        current = frappe.db.sql("""
            SELECT name, fieldname, insert_after 
            FROM `tabCustom Field` 
            WHERE dt='Contact' AND (fieldname='total_commission' OR fieldname='remaining_commission')
        """, as_dict=1)
        
        print("当前设置:")
        for c in current:
            print(f"  - {c.fieldname}: 插入在 {c.insert_after} 之后")
        
        # 更新分成总额字段
        frappe.db.sql("""
            UPDATE `tabCustom Field` 
            SET insert_after='address'
            WHERE dt='Contact' AND fieldname='total_commission'
        """)
        
        # 更新剩余分成字段
        frappe.db.sql("""
            UPDATE `tabCustom Field` 
            SET insert_after='total_commission'
            WHERE dt='Contact' AND fieldname='remaining_commission'
        """)
        
        # 确保提交更改
        frappe.db.commit()
        
        # 查询更新后的设置
        updated = frappe.db.sql("""
            SELECT name, fieldname, insert_after 
            FROM `tabCustom Field` 
            WHERE dt='Contact' AND (fieldname='total_commission' OR fieldname='remaining_commission')
        """, as_dict=1)
        
        print("\n更新后设置:")
        for u in updated:
            print(f"  - {u.fieldname}: 插入在 {u.insert_after} 之后")
            
        # 刷新缓存
        frappe.clear_cache(doctype="Contact")
        print("\n成功更新字段位置并刷新缓存")
        print("请刷新页面以查看更改效果")
        
    except Exception as e:
        print(f"更新字段位置时出错: {str(e)}")
        
    # 导出修改后的fixtures
    try:
        # 尝试导出fixtures (可能需要开发者模式)
        frappe.db.sql("""
            UPDATE `tabSingles`
            SET value=1
            WHERE doctype='System Settings' AND field='developer_mode'
        """)
        frappe.db.commit()
        
        # 重新导出fixtures
        from frappe.commands.utils import export_fixtures
        export_fixtures('commission_record')
        
        print("已成功导出fixtures")
    except Exception as e:
        print(f"导出fixtures时出错: {str(e)}")
        print("请手动运行: bench export-fixtures") 
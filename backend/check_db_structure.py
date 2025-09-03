"""
检查数据库表结构脚本
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.database import Base

def check_database_structure():
    """检查数据库表结构"""
    print("=== 数据库表结构 ===\n")
    
    if not Base.metadata.tables:
        print("没有找到数据库表！")
        return
    
    for table_name, table in Base.metadata.tables.items():
        print(f"📋 表名: {table_name}")
        print(f"   描述: {table.comment or '无描述'}")
        print("   字段:")
        
        for column in table.columns:
            nullable = "可空" if column.nullable else "非空"
            primary = " (主键)" if column.primary_key else ""
            foreign = ""
            if column.foreign_keys:
                fk_info = list(column.foreign_keys)[0]
                foreign = f" (外键 -> {fk_info.column.table.name}.{fk_info.column.name})"
            
            print(f"     - {column.name}: {column.type} ({nullable}){primary}{foreign}")
            if column.comment:
                print(f"       注释: {column.comment}")
        
        # 显示索引信息
        if table.indexes:
            print("   索引:")
            for index in table.indexes:
                columns = [col.name for col in index.columns]
                unique = "唯一索引" if index.unique else "普通索引"
                print(f"     - {index.name}: {columns} ({unique})")
        
        print()

if __name__ == "__main__":
    try:
        check_database_structure()
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()

#!/usr/bin/env python3
"""
简单的数据库结构检查脚本
"""
import sqlite3
import os

def check_database():
    """检查SQLite数据库结构"""
    db_path = "test.db"
    
    if not os.path.exists(db_path):
        print(f"数据库文件 {db_path} 不存在")
        return
    
    print(f"=== 数据库文件: {db_path} ===")
    print(f"文件大小: {os.path.getsize(db_path)} 字节\n")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 获取所有表名
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        if not tables:
            print("数据库中没有表")
            return
        
        print(f"发现 {len(tables)} 个表:")
        for (table_name,) in tables:
            print(f"  - {table_name}")
        print()
        
        # 详细检查每个表的结构
        for (table_name,) in tables:
            print(f"📋 表: {table_name}")
            
            # 获取表结构
            cursor.execute(f"PRAGMA table_info({table_name});")
            columns = cursor.fetchall()
            
            if columns:
                print("   字段:")
                for col_info in columns:
                    cid, name, data_type, not_null, default_value, pk = col_info
                    nullable = "非空" if not_null else "可空"
                    primary = " (主键)" if pk else ""
                    default = f" 默认值:{default_value}" if default_value is not None else ""
                    print(f"     - {name}: {data_type} ({nullable}){primary}{default}")
            
            # 获取表中的记录数
            cursor.execute(f"SELECT COUNT(*) FROM {table_name};")
            count = cursor.fetchone()[0]
            print(f"   记录数: {count}")
            
            # 如果有数据，显示前几条记录
            if count > 0:
                cursor.execute(f"SELECT * FROM {table_name} LIMIT 3;")
                rows = cursor.fetchall()
                print("   示例数据:")
                for i, row in enumerate(rows, 1):
                    print(f"     记录{i}: {row}")
            
            print()
        
        conn.close()
        
    except Exception as e:
        print(f"检查数据库时出错: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_database()

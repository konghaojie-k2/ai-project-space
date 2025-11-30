#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库性能优化脚本
添加关键索引以提升权限查询性能
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.append(str(Path(__file__).parent.parent))

from app.core.database import get_db_session
from sqlalchemy import text

async def create_performance_indexes():
    """创建性能优化索引"""

    index_statements = [
        # 1. 项目成员表复合索引 - 优化权限检查查询
        """
        CREATE INDEX IF NOT EXISTS idx_project_members_user_project
        ON public.project_members(user_id, project_id, is_active, role);
        """,

        # 2. 项目成员表项目查询索引
        """
        CREATE INDEX IF NOT EXISTS idx_project_members_project_active
        ON public.project_members(project_id, is_active) WHERE is_active = true;
        """,

        # 3. profiles表活跃用户索引 - 优化用户查询
        """
        CREATE INDEX IF NOT EXISTS idx_profiles_active_users
        ON public.profiles(id, is_active, system_role) WHERE is_active = true;
        """,

        # 4. projects表创建者和公开状态索引 - 优化项目访问查询
        """
        CREATE INDEX IF NOT EXISTS idx_projects_creator_public
        ON public.projects(created_by, is_public, is_deleted);
        """,

        # 5. chat_sessions表用户会话索引 - 优化聊天记录查询
        """
        CREATE INDEX IF NOT EXISTS idx_chat_sessions_user_project
        ON public.chat_sessions(user_id, project_id, created_at);
        """,

        # 6. files表用户项目文件索引 - 优化文件查询
        """
        CREATE INDEX IF NOT EXISTS idx_files_user_project_created
        ON public.files(uploaded_by, project_id, created_at);
        """,

        # 7. chat_messages表会话时间索引 - 优化消息查询
        """
        CREATE INDEX IF NOT EXISTS idx_chat_messages_session_time
        ON public.chat_messages(session_id, created_at);
        """,

        # 8. 审计日志表用户时间索引 - 优化审计查询
        """
        CREATE INDEX IF NOT EXISTS idx_audit_logs_user_time
        ON public.audit_logs(performed_by, created_at);
        """,

        # 9. 项目邀请表索引 - 优化邀请查询
        """
        CREATE INDEX IF NOT EXISTS idx_project_invitations_email_status
        ON public.project_invitations(email, status);
        """,

        # 10. 文件标签索引 - 优化标签搜索
        """
        CREATE INDEX IF NOT EXISTS idx_file_tags_name
        ON public.file_tags(name);
        """
    ]

    async with get_db_session() as session:
        try:
            print("开始创建性能优化索引...")

            for i, statement in enumerate(index_statements, 1):
                print(f"执行索引 {i}/10: {statement.strip().split('idx')[1].split(' ')[0] if 'idx' in statement else f'索引{i}'}")
                await session.execute(text(statement))
                await session.commit()
                print(f"✓ 索引 {i} 创建成功")

            print("\n✅ 所有性能优化索引创建完成!")

        except Exception as e:
            print(f"❌ 创建索引时出错: {str(e)}")
            await session.rollback()
            raise

async def create_materialized_views():
    """创建权限物化视图"""

    view_statements = [
        # 1. 用户项目权限物化视图
        """
        DROP MATERIALIZED VIEW IF EXISTS public.user_project_permissions;
        """,
        """
        CREATE MATERIALIZED VIEW public.user_project_permissions AS
        SELECT
            pm.user_id,
            pm.project_id,
            pm.role,
            p.created_by = pm.user_id as is_owner,
            p.is_public,
            pm.is_active,
            p.created_by as project_creator
        FROM public.project_members pm
        JOIN public.projects p ON pm.project_id = p.id
        WHERE pm.is_active = true
        UNION ALL
        SELECT
            p.created_by as user_id,
            p.id as project_id,
            'owner' as role,
            true as is_owner,
            p.is_public,
            true as is_active,
            p.created_by as project_creator
        FROM public.projects p
        WHERE NOT EXISTS (
            SELECT 1 FROM public.project_members pm
            WHERE pm.project_id = p.id AND pm.user_id = p.created_by
        );
        """,

        # 2. 为物化视图创建索引
        """
        CREATE INDEX IF NOT EXISTS idx_user_project_permissions_user
        ON public.user_project_permissions(user_id, project_id, is_active);
        """,

        # 3. 创建刷新权限缓存的函数
        """
        CREATE OR REPLACE FUNCTION public.refresh_user_permissions()
        RETURNS void AS $$
        BEGIN
            REFRESH MATERIALIZED VIEW CONCURRENTLY public.user_project_permissions;
        END;
        $$ LANGUAGE plpgsql;
        """
    ]

    async with get_db_session() as session:
        try:
            print("\n开始创建权限物化视图...")

            for i, statement in enumerate(view_statements, 1):
                print(f"执行视图操作 {i}/3")
                await session.execute(text(statement))
                await session.commit()
                print(f"✓ 视图操作 {i} 完成成功")

            print("\n✅ 权限物化视图创建完成!")

        except Exception as e:
            print(f"❌ 创建物化视图时出错: {str(e)}")
            await session.rollback()
            raise

async def analyze_query_performance():
    """分析查询性能并生成报告"""

    analysis_queries = [
        # 分析慢查询
        """
        SELECT
            query,
            calls,
            total_time,
            mean_time,
            rows
        FROM pg_stat_statements
        WHERE query LIKE '%public.%'
        ORDER BY mean_time DESC
        LIMIT 10;
        """,

        # 分析索引使用情况
        """
        SELECT
            schemaname,
            tablename,
            indexname,
            idx_scan,
            idx_tup_read,
            idx_tup_fetch
        FROM pg_stat_user_indexes
        ORDER BY idx_scan DESC;
        """,

        # 分析表大小
        """
        SELECT
            schemaname,
            tablename,
            pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
        FROM pg_tables
        WHERE schemaname = 'public'
        ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
        """
    ]

    async with get_db_session() as session:
        try:
            print("\n📊 生成性能分析报告...")

            for i, query in enumerate(analysis_queries, 1):
                result = await session.execute(text(query))
                print(f"\n--- 分析报告 {i} ---")
                for row in result:
                    print(f"  {row}")

        except Exception as e:
            print(f"⚠️  生成分析报告时出错: {str(e)}")

async def main():
    """主函数"""
    try:
        print("🚀 开始数据库性能优化...")

        # 1. 创建性能优化索引
        await create_performance_indexes()

        # 2. 创建物化视图
        await create_materialized_views()

        # 3. 分析性能
        await analyze_query_performance()

        print("\n🎉 数据库性能优化完成!")
        print("\n建议立即重启应用服务以使优化生效。")

    except Exception as e:
        print(f"\n💥 优化过程中出错: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
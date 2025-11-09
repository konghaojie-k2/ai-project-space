-- ========================================
-- AI项目管理系统 - Supabase数据库Schema
-- ========================================

-- 启用必要的扩展
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
-- 注意：vector扩展已移除，因为使用外部RAG服务，不再需要本地向量存储

-- ========================================
-- 用户档案表 (扩展Supabase auth.users)
-- ========================================
CREATE TABLE public.profiles (
    id uuid references auth.users not null primary key,
    username text unique,
    full_name text,
    avatar_url text,
    bio text,
    phone text,
    department text,
    position text,
    is_superuser boolean default false,
    created_at timestamp with time zone default timezone('utc'::text, now()) not null,
    updated_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- ========================================
-- 项目表
-- ========================================
CREATE TABLE public.projects (
    id uuid default uuid_generate_v4() not null primary key,
    name text not null,
    description text,
    stage text not null default '售前',
    status text not null default 'active',
    created_by uuid references public.profiles not null,
    created_at timestamp with time zone default timezone('utc'::text, now()) not null,
    updated_at timestamp with time zone default timezone('utc'::text, now()) not null,

    -- 检查约束：项目阶段
    constraint projects_stage_check
        check (stage in ('售前', '业务调研', '数据理解', '数据探索', '工程开发', '实施部署')),

    -- 检查约束：项目状态
    constraint projects_status_check
        check (status in ('active', 'archived', 'completed', 'on_hold'))
);

-- ========================================
-- 项目成员表 (多对多关系)
-- ========================================
CREATE TABLE public.project_members (
    project_id uuid references public.projects on delete cascade not null,
    user_id uuid references public.profiles on delete cascade not null,
    role text not null,
    joined_at timestamp with time zone default timezone('utc'::text, now()) not null,

    primary key (project_id, user_id),

    -- 检查约束：用户角色
    constraint project_members_role_check
        check (role in ('owner', 'admin', 'member', 'viewer'))
);

-- ========================================
-- 文件表
-- ========================================
CREATE TABLE public.files (
    id uuid default uuid_generate_v4() not null primary key,
    original_name text not null,
    stored_name text not null,
    file_path text not null,
    file_size bigint not null,
    file_type text not null,
    file_extension text,
    mime_type text,
    project_id uuid references public.projects on delete cascade,
    uploaded_by uuid references public.profiles not null,
    access_level text not null default 'all_users',
    is_public boolean default false,
    description text,
    tags jsonb default '[]'::jsonb,
    metadata jsonb default '{}'::jsonb,
    created_at timestamp with time zone default timezone('utc'::text, now()) not null,
    updated_at timestamp with time zone default timezone('utc'::text, now()) not null,

    -- 检查约束：访问级别
    constraint files_access_level_check
        check (access_level in ('all_users', 'project_members', 'admins_only', 'owner_only'))
);

-- ========================================
-- 注意：document_embeddings表已移除
-- 向量存储和RAG功能已迁移到外部RAG服务
-- 使用 rag_document_mapping 表来映射本地文件和外部RAG文档
-- ========================================

-- ========================================
-- 聊天会话表
-- ========================================
CREATE TABLE public.chat_sessions (
    id uuid default uuid_generate_v4() not null primary key,
    project_id uuid references public.projects on delete cascade,
    user_id uuid references public.profiles on delete cascade not null,
    title text,
    created_at timestamp with time zone default timezone('utc'::text, now()) not null,
    updated_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- ========================================
-- 聊天消息表
-- ========================================
CREATE TABLE public.chat_messages (
    id uuid default uuid_generate_v4() not null primary key,
    session_id uuid references public.chat_sessions on delete cascade not null,
    role text not null,
    content text not null,
    metadata jsonb default '{}'::jsonb,
    created_at timestamp with time zone default timezone('utc'::text, now()) not null,

    -- 检查约束：消息角色
    constraint chat_messages_role_check
        check (role in ('user', 'assistant', 'system'))
);

-- ========================================
-- 创建更新的触发器函数
-- ========================================
CREATE OR REPLACE FUNCTION public.handle_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = timezone('utc'::text, now());
    RETURN NEW;
END;
$$ language 'plpgsql';

-- 为需要的表添加更新时间戳触发器
CREATE TRIGGER handle_profiles_updated_at
    BEFORE UPDATE ON public.profiles
    FOR EACH ROW EXECUTE FUNCTION public.handle_updated_at();

CREATE TRIGGER handle_projects_updated_at
    BEFORE UPDATE ON public.projects
    FOR EACH ROW EXECUTE FUNCTION public.handle_updated_at();

CREATE TRIGGER handle_files_updated_at
    BEFORE UPDATE ON public.files
    FOR EACH ROW EXECUTE FUNCTION public.handle_updated_at();

CREATE TRIGGER handle_chat_sessions_updated_at
    BEFORE UPDATE ON public.chat_sessions
    FOR EACH ROW EXECUTE FUNCTION public.handle_updated_at();

-- ========================================
-- 创建有用的视图
-- ========================================

-- 项目详情视图 (包含创建者信息和成员数量)
CREATE OR REPLACE VIEW public.project_details AS
SELECT
    p.*,
    creator.username as creator_username,
    creator.full_name as creator_full_name,
    COALESCE(member_counts.member_count, 0) as member_count
FROM public.projects p
LEFT JOIN public.profiles creator ON p.created_by = creator.id
LEFT JOIN (
    SELECT project_id, COUNT(*) as member_count
    FROM public.project_members
    GROUP BY project_id
) member_counts ON p.id = member_counts.project_id;

-- 用户项目视图 (用户可以访问的项目)
CREATE OR REPLACE VIEW public.user_projects AS
SELECT DISTINCT
    p.*,
    pm.role as user_role,
    CASE
        WHEN p.created_by = pm.user_id THEN true
        ELSE false
    END as is_owner
FROM public.projects p
INNER JOIN public.project_members pm ON p.id = pm.project_id
WHERE pm.user_id = auth.uid()

UNION

SELECT
    p.*,
    'owner' as user_role,
    true as is_owner
FROM public.projects p
WHERE p.created_by = auth.uid();

-- ========================================
-- 注意：枚举类型已移除
-- 表定义中使用CHECK约束而不是枚举类型，更灵活且易于修改
-- ========================================

-- ========================================
-- 注释
-- ========================================

COMMENT ON TABLE public.profiles IS '用户档案信息表，扩展Supabase auth.users';
COMMENT ON TABLE public.projects IS '项目管理表，包含项目基本信息和阶段';
COMMENT ON TABLE public.project_members IS '项目成员关系表，定义用户在项目中的角色';
COMMENT ON TABLE public.files IS '文件信息表，存储文件元数据和权限';
COMMENT ON TABLE public.chat_sessions IS '聊天会话表';
COMMENT ON TABLE public.chat_messages IS '聊天消息表';

COMMENT ON COLUMN public.projects.stage IS '项目当前阶段：售前、业务调研、数据理解、数据探索、工程开发、实施部署';
COMMENT ON COLUMN public.project_members.role IS '用户在项目中的角色：owner(所有者)、admin(管理员)、member(成员)、viewer(访客)';
COMMENT ON COLUMN public.files.access_level IS '文件访问级别：all_users(所有用户)、project_members(项目成员)、admins_only(仅管理员)、owner_only(仅所有者)';
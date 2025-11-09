-- ========================================
-- AI项目管理系统 - 权限模型增强
-- ========================================

-- 注意：扩展已在001_initial_schema.sql中启用，此处不需要重复启用
-- uuid-ossp扩展已在001中启用
-- vector扩展已移除（不再需要本地向量存储）

-- ========================================
-- 增强profiles表 - 添加系统级角色
-- ========================================

-- 添加系统级角色字段
ALTER TABLE public.profiles
ADD COLUMN IF NOT EXISTS system_role text DEFAULT 'user',
ADD COLUMN IF NOT EXISTS is_active boolean DEFAULT true,
ADD COLUMN IF NOT EXISTS email_verified boolean DEFAULT false,
ADD COLUMN IF NOT EXISTS last_sign_in_at timestamp with time zone,
ADD COLUMN IF NOT EXISTS preferences jsonb DEFAULT '{}'::jsonb;

-- 添加系统角色约束
ALTER TABLE public.profiles
ADD CONSTRAINT profiles_system_role_check
CHECK (system_role IN ('super_admin', 'admin', 'manager', 'member', 'user'));

-- 添加索引
CREATE INDEX IF NOT EXISTS profiles_system_role_idx ON public.profiles(system_role);
CREATE INDEX IF NOT EXISTS profiles_is_active_idx ON public.profiles(is_active);

-- ========================================
-- 增强projects表 - 添加权限控制字段
-- ========================================

-- 添加项目权限控制字段
ALTER TABLE public.projects
ADD COLUMN IF NOT EXISTS is_public boolean DEFAULT false,
ADD COLUMN IF NOT EXISTS allow_file_upload boolean DEFAULT true,
ADD COLUMN IF NOT EXISTS allow_ai_chat boolean DEFAULT true,
ADD COLUMN IF NOT EXISTS default_member_role text DEFAULT 'viewer',
ADD COLUMN IF NOT EXISTS settings jsonb DEFAULT '{}'::jsonb;

-- 添加默认成员角色约束
ALTER TABLE public.projects
ADD CONSTRAINT projects_default_member_role_check
CHECK (default_member_role IN ('admin', 'member', 'viewer'));

-- 添加索引
CREATE INDEX IF NOT EXISTS projects_is_public_idx ON public.projects(is_public);
CREATE INDEX IF NOT EXISTS projects_allow_file_upload_idx ON public.projects(allow_file_upload);
CREATE INDEX IF NOT EXISTS projects_allow_ai_chat_idx ON public.projects(allow_ai_chat);

-- ========================================
-- 创建项目权限视图 - 简化权限查询
-- ========================================

-- 创建用户可访问项目视图
CREATE OR REPLACE VIEW public.user_accessible_projects AS
SELECT
    p.*,
    -- 用户在项目中的角色
    COALESCE(pm.role,
        CASE
            WHEN p.created_by = auth.uid() THEN 'owner'
            WHEN p.is_public THEN 'viewer'
            ELSE NULL
        END
    ) as user_role,
    -- 权限级别
    CASE
        WHEN p.created_by = auth.uid() THEN 'full'
        WHEN pm.role IN ('owner', 'admin') THEN 'admin'
        WHEN pm.role = 'member' THEN 'member'
        WHEN pm.role = 'viewer' OR p.is_public THEN 'viewer'
        ELSE 'none'
    END as permission_level
FROM public.projects p
LEFT JOIN public.project_members pm ON p.id = pm.project_id AND pm.user_id = auth.uid()
WHERE
    p.created_by = auth.uid() OR
    pm.user_id = auth.uid() OR
    p.is_public;

-- ========================================
-- 增强project_members表 - 添加权限细节
-- ========================================

-- 添加成员权限细节字段
ALTER TABLE public.project_members
ADD COLUMN IF NOT EXISTS invited_by uuid references public.profiles,
ADD COLUMN IF NOT EXISTS permissions jsonb DEFAULT '{}'::jsonb,
ADD COLUMN IF NOT EXISTS is_active boolean DEFAULT true;

-- 添加索引
CREATE INDEX IF NOT EXISTS project_members_invited_by_idx ON public.project_members(invited_by);
CREATE INDEX IF NOT EXISTS project_members_is_active_idx ON public.project_members(is_active);

-- ========================================
-- 创建权限继承函数
-- ========================================

-- 获取用户在项目中的有效权限
CREATE OR REPLACE FUNCTION public.get_effective_project_permissions(
    project_uuid uuid,
    user_uuid uuid
)
RETURNS jsonb AS $$
DECLARE
    user_role text;
    is_creator boolean;
    is_public boolean;
    base_permissions jsonb;
BEGIN
    -- 检查是否为项目创建者
    SELECT created_by, is_public INTO is_creator, is_public
    FROM public.projects
    WHERE id = project_uuid;

    -- 如果是项目创建者，返回所有权限
    IF is_creator = user_uuid THEN
        RETURN '{
            "read": true,
            "write": true,
            "delete": true,
            "manage_members": true,
            "manage_files": true,
            "manage_settings": true
        }'::jsonb;
    END IF;

    -- 获取用户在项目中的角色
    SELECT role INTO user_role
    FROM public.project_members
    WHERE project_id = project_uuid AND user_id = user_uuid AND is_active = true;

    -- 基于角色返回权限
    CASE user_role
        WHEN 'admin' THEN
            RETURN '{
                "read": true,
                "write": true,
                "delete": true,
                "manage_members": true,
                "manage_files": true,
                "manage_settings": false
            }'::jsonb;
        WHEN 'member' THEN
            RETURN '{
                "read": true,
                "write": true,
                "delete": false,
                "manage_members": false,
                "manage_files": true,
                "manage_settings": false
            }'::jsonb;
        WHEN 'viewer' THEN
            RETURN '{
                "read": true,
                "write": false,
                "delete": false,
                "manage_members": false,
                "manage_files": false,
                "manage_settings": false
            }'::jsonb;
        ELSE
            -- 如果不是项目成员，检查是否为公开项目
            IF is_public THEN
                RETURN '{
                    "read": true,
                    "write": false,
                    "delete": false,
                    "manage_members": false,
                    "manage_files": false,
                    "manage_settings": false
                }'::jsonb;
            ELSE
                RETURN '{
                    "read": false,
                    "write": false,
                    "delete": false,
                    "manage_members": false,
                    "manage_files": false,
                    "manage_settings": false
                }'::jsonb;
            END IF;
    END CASE;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- 检查用户是否有特定项目权限
CREATE OR REPLACE FUNCTION public.has_project_permission(
    project_uuid uuid,
    user_uuid uuid,
    required_permission text
)
RETURNS boolean AS $$
DECLARE
    permissions jsonb;
BEGIN
    permissions := public.get_effective_project_permissions(project_uuid, user_uuid);
    RETURN COALESCE((permissions ->> required_permission)::boolean, false);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ========================================
-- 创建用户权限汇总视图
-- ========================================

-- 用户权限汇总视图
CREATE OR REPLACE VIEW public.user_permission_summary AS
SELECT
    auth.uid() as user_id,
    p.system_role,
    p.is_superuser,
    p.is_active,
    -- 项目权限统计
    (SELECT COUNT(*) FROM public.projects WHERE created_by = auth.uid()) as owned_projects_count,
    (SELECT COUNT(*) FROM public.project_members WHERE user_id = auth.uid() AND is_active = true) as member_projects_count,
    -- 系统权限
    CASE
        WHEN p.is_superuser THEN 'system_admin'
        WHEN p.system_role IN ('super_admin', 'admin') THEN 'admin'
        WHEN p.system_role = 'manager' THEN 'manager'
        ELSE 'user'
    END as overall_permission_level,
    updated_at
FROM public.profiles p
WHERE p.id = auth.uid();

-- ========================================
-- 增强RLS策略 - 使用新的权限函数
-- ========================================

-- 更新项目查看策略 - 使用权限视图
DROP POLICY IF EXISTS "用户可以查看可访问的项目" ON public.projects;
CREATE POLICY "用户可以查看可访问的项目" ON public.projects
    FOR SELECT USING (
        created_by = auth.uid() OR
        is_public = true OR
        EXISTS (
            SELECT 1 FROM public.project_members
            WHERE project_id = projects.id AND user_id = auth.uid() AND is_active = true
        )
    );

-- 更新项目更新策略 - 使用新的权限检查
DROP POLICY IF EXISTS "项目所有者和管理员可以更新项目" ON public.projects;
CREATE POLICY "项目所有者和管理员可以更新项目" ON public.projects
    FOR UPDATE USING (
        created_by = auth.uid() OR
        public.has_project_permission(id, auth.uid(), 'manage_settings') = true
    );

-- 更新项目成员添加策略
DROP POLICY IF EXISTS "项目所有者和管理员可以添加成员" ON public.project_members;
CREATE POLICY "项目所有者和管理员可以添加成员" ON public.project_members
    FOR INSERT WITH CHECK (
        public.has_project_permission(project_id, auth.uid(), 'manage_members') = true
    );

-- 更新项目成员更新策略
DROP POLICY IF EXISTS "项目所有者可以更新成员角色" ON public.project_members;
CREATE POLICY "项目所有者和管理员可以更新成员角色" ON public.project_members
    FOR UPDATE USING (
        public.has_project_permission(project_id, auth.uid(), 'manage_members') = true
    );

-- 更新项目成员删除策略
DROP POLICY IF EXISTS "项目所有者和管理员可以移除成员" ON public.project_members;
CREATE POLICY "项目所有者和管理员可以移除成员" ON public.project_members
    FOR DELETE USING (
        user_id != auth.uid() AND
        public.has_project_permission(project_id, auth.uid(), 'manage_members') = true
    );

-- ========================================
-- 创建审计日志表
-- ========================================

-- 权限变更审计日志
CREATE TABLE IF NOT EXISTS public.permission_audit_log (
    id uuid default uuid_generate_v4() not null primary key,
    action text not null, -- 'grant', 'revoke', 'update_role'
    entity_type text not null, -- 'project', 'system'
    entity_id uuid,
    target_user_id uuid references public.profiles,
    performed_by uuid references public.profiles not null,
    old_values jsonb,
    new_values jsonb,
    created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- 添加约束
ALTER TABLE public.permission_audit_log
ADD CONSTRAINT permission_audit_log_action_check
CHECK (action IN ('grant', 'revoke', 'update_role', 'create', 'delete'));

ALTER TABLE public.permission_audit_log
ADD CONSTRAINT permission_audit_log_entity_type_check
CHECK (entity_type IN ('project', 'system', 'file', 'member'));

-- 添加索引
CREATE INDEX IF NOT EXISTS permission_audit_log_entity_idx ON public.permission_audit_log(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS permission_audit_log_target_user_idx ON public.permission_audit_log(target_user_id);
CREATE INDEX IF NOT EXISTS permission_audit_log_performed_by_idx ON public.permission_audit_log(performed_by);
CREATE INDEX IF NOT EXISTS permission_audit_log_created_at_idx ON public.permission_audit_log(created_at);

-- 启用RLS
ALTER TABLE public.permission_audit_log ENABLE ROW LEVEL SECURITY;

-- 审计日志权限策略
CREATE POLICY "用户可以查看相关的审计日志" ON public.permission_audit_log
    FOR SELECT USING (
        target_user_id = auth.uid() OR
        performed_by = auth.uid() OR
        public.is_superuser(auth.uid())
    );

-- ========================================
-- 创建审计触发器
-- ========================================

-- 记录项目成员变更的审计函数
CREATE OR REPLACE FUNCTION public.audit_project_member_change()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        INSERT INTO public.permission_audit_log (
            action, entity_type, entity_id, target_user_id, performed_by, new_values
        ) VALUES (
            'grant', 'project', NEW.project_id, NEW.user_id, auth.uid(),
            jsonb_build_object('role', NEW.role, 'is_active', NEW.is_active)
        );
        RETURN NEW;
    ELSIF TG_OP = 'UPDATE' THEN
        IF OLD.role IS DISTINCT FROM NEW.role OR OLD.is_active IS DISTINCT FROM NEW.is_active THEN
            INSERT INTO public.permission_audit_log (
                action, entity_type, entity_id, target_user_id, performed_by,
                old_values, new_values
            ) VALUES (
                'update_role', 'project', NEW.project_id, NEW.user_id, auth.uid(),
                jsonb_build_object('role', OLD.role, 'is_active', OLD.is_active),
                jsonb_build_object('role', NEW.role, 'is_active', NEW.is_active)
            );
        END IF;
        RETURN NEW;
    ELSIF TG_OP = 'DELETE' THEN
        INSERT INTO public.permission_audit_log (
            action, entity_type, entity_id, target_user_id, performed_by, old_values
        ) VALUES (
            'revoke', 'project', OLD.project_id, OLD.user_id, auth.uid(),
            jsonb_build_object('role', OLD.role, 'is_active', OLD.is_active)
        );
        RETURN OLD;
    END IF;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- 创建触发器
DROP TRIGGER IF EXISTS project_member_audit_trigger ON public.project_members;
CREATE TRIGGER project_member_audit_trigger
    AFTER INSERT OR UPDATE OR DELETE ON public.project_members
    FOR EACH ROW EXECUTE FUNCTION public.audit_project_member_change();

-- ========================================
-- 添加注释
-- ========================================

COMMENT ON TABLE public.permission_audit_log IS '权限变更审计日志表，记录所有权限相关的操作';
COMMENT ON FUNCTION public.get_effective_project_permissions IS '获取用户在项目中的有效权限';
COMMENT ON FUNCTION public.has_project_permission IS '检查用户是否有特定项目权限';
COMMENT ON VIEW public.user_accessible_projects IS '用户可访问的项目视图，包含用户角色和权限级别';
COMMENT ON VIEW public.user_permission_summary IS '用户权限汇总视图，提供整体权限概览';

-- ========================================
-- 数据迁移脚本 - 更新现有数据
-- ========================================

-- 为现有profiles设置默认系统角色
UPDATE public.profiles
SET system_role = CASE
    WHEN is_superuser = true THEN 'admin'
    ELSE 'user'
END
WHERE system_role IS NULL OR system_role = 'user';

-- 为现有项目设置默认值
UPDATE public.projects
SET
    is_public = COALESCE(is_public, false),
    allow_file_upload = COALESCE(allow_file_upload, true),
    allow_ai_chat = COALESCE(allow_ai_chat, true),
    default_member_role = COALESCE(default_member_role, 'viewer')
WHERE
    is_public IS NULL OR
    allow_file_upload IS NULL OR
    allow_ai_chat IS NULL OR
    default_member_role IS NULL;

-- 为现有项目成员设置默认值
UPDATE public.project_members
SET
    is_active = COALESCE(is_active, true),
    permissions = COALESCE(permissions, '{}'::jsonb)
WHERE
    is_active IS NULL OR
    permissions IS NULL;
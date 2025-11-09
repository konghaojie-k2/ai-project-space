-- ========================================
-- AI项目管理系统 - Row Level Security (RLS) 策略
-- ========================================

-- 启用行级安全
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.project_members ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.files ENABLE ROW LEVEL SECURITY;
-- 注意：document_embeddings表已移除，RLS策略不再需要
ALTER TABLE public.chat_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.chat_messages ENABLE ROW LEVEL SECURITY;

-- ========================================
-- 用户档案表权限策略
-- ========================================

-- 用户可以查看自己的档案
CREATE POLICY "用户可以查看自己的档案" ON public.profiles
    FOR SELECT USING (auth.uid() = id);

-- 用户可以更新自己的档案
CREATE POLICY "用户可以更新自己的档案" ON public.profiles
    FOR UPDATE USING (auth.uid() = id);

-- 用户可以插入自己的档案 (通常通过注册触发器)
CREATE POLICY "用户可以创建自己的档案" ON public.profiles
    FOR INSERT WITH CHECK (auth.uid() = id);

-- 管理员可以查看所有档案
-- 注意：避免递归查询，使用JWT中的app_metadata或创建一个辅助函数
-- 先创建一个辅助函数来检查是否为超级管理员（避免递归）
CREATE OR REPLACE FUNCTION public.is_superuser(user_uuid uuid)
RETURNS BOOLEAN AS $$
BEGIN
    -- 使用SECURITY DEFINER绕过RLS，直接查询auth.users表
    RETURN EXISTS (
        SELECT 1 FROM auth.users
        WHERE id = user_uuid
        AND (raw_app_meta_data->>'is_superuser')::boolean = true
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- 管理员可以查看所有档案
CREATE POLICY "管理员可以查看所有档案" ON public.profiles
    FOR SELECT USING (
        -- 使用辅助函数检查是否为超级管理员（避免递归）
        public.is_superuser(auth.uid())
    );

-- ========================================
-- 项目表权限策略
-- ========================================

-- 用户可以查看自己创建的项目或参与的项目
CREATE POLICY "用户可以查看可访问的项目" ON public.projects
    FOR SELECT USING (
        created_by = auth.uid() OR
        EXISTS (
            SELECT 1 FROM public.project_members
            WHERE project_id = projects.id AND user_id = auth.uid()
        )
    );

-- 用户可以创建项目
CREATE POLICY "用户可以创建项目" ON public.projects
    FOR INSERT WITH CHECK (created_by = auth.uid());

-- 项目所有者和管理员可以更新项目
CREATE POLICY "项目所有者和管理员可以更新项目" ON public.projects
    FOR UPDATE USING (
        created_by = auth.uid() OR
        EXISTS (
            SELECT 1 FROM public.project_members
            WHERE project_id = projects.id
            AND user_id = auth.uid()
            AND role IN ('owner', 'admin')
        )
    );

-- 项目所有者可以删除项目
CREATE POLICY "项目所有者可以删除项目" ON public.projects
    FOR DELETE USING (created_by = auth.uid());

-- ========================================
-- 项目成员表权限策略
-- ========================================

-- 用户可以查看自己参与的项目成员信息
CREATE POLICY "用户可以查看项目成员信息" ON public.project_members
    FOR SELECT USING (
        user_id = auth.uid() OR
        EXISTS (
            SELECT 1 FROM public.projects
            WHERE id = project_members.project_id
            AND created_by = auth.uid()
        ) OR
        EXISTS (
            SELECT 1 FROM public.project_members pm2
            WHERE pm2.project_id = project_members.project_id
            AND pm2.user_id = auth.uid()
        )
    );

-- 项目所有者和管理员可以添加项目成员
CREATE POLICY "项目所有者和管理员可以添加成员" ON public.project_members
    FOR INSERT WITH CHECK (
        EXISTS (
            SELECT 1 FROM public.projects
            WHERE id = project_members.project_id
            AND created_by = auth.uid()
        ) OR
        EXISTS (
            SELECT 1 FROM public.project_members pm
            WHERE pm.project_id = project_members.project_id
            AND pm.user_id = auth.uid()
            AND pm.role IN ('owner', 'admin')
        )
    );

-- 项目所有者可以更新成员角色
CREATE POLICY "项目所有者可以更新成员角色" ON public.project_members
    FOR UPDATE USING (
        EXISTS (
            SELECT 1 FROM public.projects
            WHERE id = project_members.project_id
            AND created_by = auth.uid()
        )
    );

-- 项目所有者和管理员可以移除成员 (不能移除自己)
CREATE POLICY "项目所有者和管理员可以移除成员" ON public.project_members
    FOR DELETE USING (
        user_id != auth.uid() AND (
            EXISTS (
                SELECT 1 FROM public.projects
                WHERE id = project_members.project_id
                AND created_by = auth.uid()
            ) OR
            EXISTS (
                SELECT 1 FROM public.project_members pm
                WHERE pm.project_id = project_members.project_id
                AND pm.user_id = auth.uid()
                AND pm.role IN ('owner', 'admin')
            )
        )
    );

-- ========================================
-- 文件表权限策略
-- ========================================

-- 基于access_level的文件访问控制
CREATE POLICY "基于访问级别的文件查看" ON public.files
    FOR SELECT USING (
        uploaded_by = auth.uid() OR
        access_level = 'all_users' OR
        (access_level = 'project_members' AND
         EXISTS (
             SELECT 1 FROM public.project_members
             WHERE project_id = files.project_id
             AND user_id = auth.uid()
         )) OR
        (access_level = 'admins_only' AND
         EXISTS (
             SELECT 1 FROM public.profiles
             WHERE id = auth.uid() AND is_superuser = true
         )) OR
        (access_level = 'owner_only' AND
         (files.project_id IS NULL OR
          EXISTS (
              SELECT 1 FROM public.projects
              WHERE id = files.project_id
              AND created_by = auth.uid()
          )))
    );

-- 用户可以上传文件到有权限的项目
CREATE POLICY "用户可以上传文件" ON public.files
    FOR INSERT WITH CHECK (
        uploaded_by = auth.uid() AND (
            files.project_id IS NULL OR
            EXISTS (
                SELECT 1 FROM public.project_members
                WHERE project_id = files.project_id
                AND user_id = auth.uid()
                AND role IN ('owner', 'admin', 'member')
            ) OR
            EXISTS (
                SELECT 1 FROM public.projects
                WHERE id = files.project_id
                AND created_by = auth.uid()
            )
        )
    );

-- 文件上传者和管理员可以更新文件信息
CREATE POLICY "文件上传者可以更新文件" ON public.files
    FOR UPDATE USING (
        uploaded_by = auth.uid() OR
        (files.project_id IS NOT NULL AND
         EXISTS (
             SELECT 1 FROM public.projects
             WHERE id = files.project_id
             AND created_by = auth.uid()
         )) OR
        EXISTS (
            SELECT 1 FROM public.profiles
            WHERE id = auth.uid() AND is_superuser = true
        )
    );

-- 文件上传者和项目所有者可以删除文件
CREATE POLICY "文件上传者可以删除文件" ON public.files
    FOR DELETE USING (
        uploaded_by = auth.uid() OR
        (files.project_id IS NOT NULL AND
         EXISTS (
             SELECT 1 FROM public.projects
             WHERE id = files.project_id
             AND created_by = auth.uid()
         ))
    );

-- ========================================
-- 注意：document_embeddings表的RLS策略已移除
-- 向量存储和RAG功能已迁移到外部RAG服务
-- ========================================

-- ========================================
-- 聊天会话表权限策略
-- ========================================

-- 用户可以查看自己的聊天会话
CREATE POLICY "用户可以查看自己的聊天会话" ON public.chat_sessions
    FOR SELECT USING (user_id = auth.uid());

-- 用户可以创建自己的聊天会话
CREATE POLICY "用户可以创建聊天会话" ON public.chat_sessions
    FOR INSERT WITH CHECK (
        user_id = auth.uid() AND (
            project_id IS NULL OR
            EXISTS (
                SELECT 1 FROM public.project_members
                WHERE project_id = chat_sessions.project_id
                AND user_id = auth.uid()
            ) OR
            EXISTS (
                SELECT 1 FROM public.projects
                WHERE id = chat_sessions.project_id
                AND created_by = auth.uid()
            )
        )
    );

-- 用户可以更新自己的聊天会话
CREATE POLICY "用户可以更新自己的聊天会话" ON public.chat_sessions
    FOR UPDATE USING (user_id = auth.uid());

-- 用户可以删除自己的聊天会话
CREATE POLICY "用户可以删除自己的聊天会话" ON public.chat_sessions
    FOR DELETE USING (user_id = auth.uid());

-- ========================================
-- 聊天消息表权限策略
-- ========================================

-- 用户可以查看自己参与会话的消息
CREATE POLICY "用户可以查看会话消息" ON public.chat_messages
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM public.chat_sessions cs
            WHERE cs.id = chat_messages.session_id
            AND cs.user_id = auth.uid()
        )
    );

-- 用户可以在自己的会话中创建消息
CREATE POLICY "用户可以在会话中创建消息" ON public.chat_messages
    FOR INSERT WITH CHECK (
        EXISTS (
            SELECT 1 FROM public.chat_sessions cs
            WHERE cs.id = chat_messages.session_id
            AND cs.user_id = auth.uid()
        )
    );

-- 用户可以更新自己在会话中的消息
CREATE POLICY "用户可以更新自己的消息" ON public.chat_messages
    FOR UPDATE USING (
        EXISTS (
            SELECT 1 FROM public.chat_sessions cs
            WHERE cs.id = chat_messages.session_id
            AND cs.user_id = auth.uid()
        )
    );

-- 用户可以删除自己在会话中的消息
CREATE POLICY "用户可以删除自己的消息" ON public.chat_messages
    FOR DELETE USING (
        EXISTS (
            SELECT 1 FROM public.chat_sessions cs
            WHERE cs.id = chat_messages.session_id
            AND cs.user_id = auth.uid()
        )
    );

-- ========================================
-- 创建触发器：用户注册时自动创建profile
-- ========================================

CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO public.profiles (id, username, full_name)
    VALUES (
        NEW.id,
        COALESCE(NEW.raw_user_meta_data->>'username', NEW.email::text),
        COALESCE(NEW.raw_user_meta_data->>'full_name', NEW.raw_user_meta_data->>'name')
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- 创建触发器
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

-- ========================================
-- 创建权限检查函数
-- ========================================

-- 检查用户是否为项目成员
CREATE OR REPLACE FUNCTION public.is_project_member(project_uuid uuid, user_uuid uuid)
RETURNS BOOLEAN AS $$
BEGIN
    RETURN EXISTS (
        SELECT 1 FROM public.project_members
        WHERE project_id = project_uuid
        AND user_id = user_uuid
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- 检查用户在项目中的角色
CREATE OR REPLACE FUNCTION public.get_project_role(project_uuid uuid, user_uuid uuid)
RETURNS TEXT AS $$
BEGIN
    RETURN (
        SELECT role FROM public.project_members
        WHERE project_id = project_uuid
        AND user_id = user_uuid
        LIMIT 1
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- 检查用户是否有文件访问权限
CREATE OR REPLACE FUNCTION public.has_file_access(file_uuid uuid, user_uuid uuid)
RETURNS BOOLEAN AS $$
BEGIN
    RETURN EXISTS (
        SELECT 1 FROM public.files f
        WHERE f.id = file_uuid
        AND (
            f.uploaded_by = user_uuid OR
            f.access_level = 'all_users' OR
            (f.access_level = 'project_members' AND
             public.is_project_member(f.project_id, user_uuid)) OR
            (f.access_level = 'admins_only' AND
             public.is_superuser(user_uuid))
        )
    );
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ========================================
-- 性能优化索引
-- ========================================

-- 为RLS策略创建必要的索引
CREATE INDEX IF NOT EXISTS profiles_id_idx ON public.profiles(id);
CREATE INDEX IF NOT EXISTS projects_created_by_idx ON public.projects(created_by);
CREATE INDEX IF NOT EXISTS project_members_user_id_idx ON public.project_members(user_id);
CREATE INDEX IF NOT EXISTS project_members_project_id_idx ON public.project_members(project_id);
CREATE INDEX IF NOT EXISTS files_uploaded_by_idx ON public.files(uploaded_by);
CREATE INDEX IF NOT EXISTS files_project_id_idx ON public.files(project_id);
CREATE INDEX IF NOT EXISTS files_access_level_idx ON public.files(access_level);
CREATE INDEX IF NOT EXISTS chat_sessions_user_id_idx ON public.chat_sessions(user_id);
CREATE INDEX IF NOT EXISTS chat_messages_session_id_idx ON public.chat_messages(session_id);

-- 复合索引用于常见查询
CREATE INDEX IF NOT EXISTS project_members_composite_idx ON public.project_members(project_id, user_id, role);
CREATE INDEX IF NOT EXISTS files_project_access_idx ON public.files(project_id, access_level);

-- ========================================
-- 注释
-- ========================================

-- 注意：PostgreSQL不支持对POLICY添加COMMENT，已移除相关注释
COMMENT ON FUNCTION public.handle_new_user() IS '新用户注册时自动创建对应的profile记录';
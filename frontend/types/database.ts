/**
 * Supabase数据库类型定义
 *
 * 这个文件定义了Supabase数据库的TypeScript类型
 * 与后端的数据库schema保持一致
 */

export type Json =
  | string
  | number
  | boolean
  | null
  | { [key: string]: Json | undefined }
  | Json[]

export interface Database {
  public: {
    Tables: {
      profiles: {
        Row: {
          id: string
          username: string | null
          full_name: string | null
          avatar_url: string | null
          bio: string | null
          phone: string | null
          department: string | null
          position: string | null
          is_superuser: boolean
          created_at: string
          updated_at: string
        }
        Insert: {
          id?: string
          username?: string | null
          full_name?: string | null
          avatar_url?: string | null
          bio?: string | null
          phone?: string | null
          department?: string | null
          position?: string | null
          is_superuser?: boolean
          created_at?: string
          updated_at?: string
        }
        Update: {
          id?: string
          username?: string | null
          full_name?: string | null
          avatar_url?: string | null
          bio?: string | null
          phone?: string | null
          department?: string | null
          position?: string | null
          is_superuser?: boolean
          updated_at?: string
        }
      }
      projects: {
        Row: {
          id: string
          name: string
          description: string | null
          stage: '售前' | '业务调研' | '数据理解' | '数据探索' | '工程开发' | '实施部署'
          status: 'active' | 'archived' | 'completed' | 'on_hold'
          created_by: string
          created_at: string
          updated_at: string
        }
        Insert: {
          id?: string
          name: string
          description?: string | null
          stage?: '售前' | '业务调研' | '数据理解' | '数据探索' | '工程开发' | '实施部署'
          status?: 'active' | 'archived' | 'completed' | 'on_hold'
          created_by: string
          created_at?: string
          updated_at?: string
        }
        Update: {
          id?: string
          name?: string
          description?: string | null
          stage?: '售前' | '业务调研' | '数据理解' | '数据探索' | '工程开发' | '实施部署'
          status?: 'active' | 'archived' | 'completed' | 'on_hold'
          updated_at?: string
        }
      }
      project_members: {
        Row: {
          project_id: string
          user_id: string
          role: 'owner' | 'admin' | 'member' | 'viewer'
          joined_at: string
        }
        Insert: {
          project_id: string
          user_id: string
          role: 'owner' | 'admin' | 'member' | 'viewer'
          joined_at?: string
        }
        Update: {
          project_id?: string
          user_id?: string
          role?: 'owner' | 'admin' | 'member' | 'viewer'
        }
      }
      files: {
        Row: {
          id: string
          original_name: string
          stored_name: string
          file_path: string
          file_size: number
          file_type: string
          file_extension: string | null
          mime_type: string | null
          project_id: string | null
          uploaded_by: string
          access_level: 'all_users' | 'project_members' | 'admins_only' | 'owner_only'
          is_public: boolean
          description: string | null
          tags: Json
          metadata: Json
          created_at: string
          updated_at: string
        }
        Insert: {
          id?: string
          original_name: string
          stored_name: string
          file_path: string
          file_size: number
          file_type: string
          file_extension?: string | null
          mime_type?: string | null
          project_id?: string | null
          uploaded_by: string
          access_level?: 'all_users' | 'project_members' | 'admins_only' | 'owner_only'
          is_public?: boolean
          description?: string | null
          tags?: Json
          metadata?: Json
          created_at?: string
          updated_at?: string
        }
        Update: {
          id?: string
          original_name?: string
          stored_name?: string
          file_path?: string
          file_size?: number
          file_type?: string
          file_extension?: string | null
          mime_type?: string | null
          project_id?: string | null
          access_level?: 'all_users' | 'project_members' | 'admins_only' | 'owner_only'
          is_public?: boolean
          description?: string | null
          tags?: Json
          metadata?: Json
          updated_at?: string
        }
      }
      document_embeddings: {
        Row: {
          id: string
          file_id: string
          chunk_index: number
          content: string
          embedding: number[] // Vector type
          metadata: Json
          created_at: string
        }
        Insert: {
          id?: string
          file_id: string
          chunk_index?: number
          content: string
          embedding: number[]
          metadata?: Json
          created_at?: string
        }
        Update: {
          id?: string
          file_id?: string
          chunk_index?: number
          content?: string
          embedding?: number[]
          metadata?: Json
        }
      }
      chat_sessions: {
        Row: {
          id: string
          project_id: string | null
          user_id: string
          title: string | null
          created_at: string
          updated_at: string
        }
        Insert: {
          id?: string
          project_id?: string | null
          user_id: string
          title?: string | null
          created_at?: string
          updated_at?: string
        }
        Update: {
          id?: string
          project_id?: string | null
          title?: string | null
          updated_at?: string
        }
      }
      chat_messages: {
        Row: {
          id: string
          session_id: string
          role: 'user' | 'assistant' | 'system'
          content: string
          metadata: Json
          created_at: string
        }
        Insert: {
          id?: string
          session_id: string
          role: 'user' | 'assistant' | 'system'
          content: string
          metadata?: Json
          created_at?: string
        }
        Update: {
          id?: string
          session_id?: string
          role?: 'user' | 'assistant' | 'system'
          content?: string
          metadata?: Json
        }
      }
    }
    Views: {
      project_details: {
        Row: {
          id: string
          name: string
          description: string | null
          stage: '售前' | '业务调研' | '数据理解' | '数据探索' | '工程开发' | '实施部署'
          status: 'active' | 'archived' | 'completed' | 'on_hold'
          created_by: string
          created_at: string
          updated_at: string
          creator_username: string | null
          creator_full_name: string | null
          member_count: number
        }
      }
      user_projects: {
        Row: {
          id: string
          name: string
          description: string | null
          stage: '售前' | '业务调研' | '数据理解' | '数据探索' | '工程开发' | '实施部署'
          status: 'active' | 'archived' | 'completed' | 'on_hold'
          created_by: string
          created_at: string
          updated_at: string
          user_role: 'owner' | 'admin' | 'member' | 'viewer'
          is_owner: boolean
        }
      }
    }
    Functions: {
      search_similar_documents: {
        Args: {
          query_embedding: number[]
          similarity_threshold?: number
          match_count?: number
          project_id?: string
        }
        Returns: {
          id: string
          file_id: string
          chunk_index: number
          content: string
          metadata: Json
          created_at: string
          similarity?: number
        }[]
      }
    }
  }
}

// 扩展的便利类型
export type Profile = Database['public']['Tables']['profiles']['Row']
export type ProfileInsert = Database['public']['Tables']['profiles']['Insert']
export type ProfileUpdate = Database['public']['Tables']['profiles']['Update']

export type Project = Database['public']['Tables']['projects']['Row']
export type ProjectInsert = Database['public']['Tables']['projects']['Insert']
export type ProjectUpdate = Database['public']['Tables']['projects']['Update']

export type ProjectMember = Database['public']['Tables']['project_members']['Row']
export type ProjectMemberInsert = Database['public']['Tables']['project_members']['Insert']
export type ProjectMemberUpdate = Database['public']['Tables']['project_members']['Update']

export type File = Database['public']['Tables']['files']['Row']
export type FileInsert = Database['public']['Tables']['files']['Insert']
export type FileUpdate = Database['public']['Tables']['files']['Update']

export type DocumentEmbedding = Database['public']['Tables']['document_embeddings']['Row']
export type DocumentEmbeddingInsert = Database['public']['Tables']['document_embeddings']['Insert']
export type DocumentEmbeddingUpdate = Database['public']['Tables']['document_embeddings']['Update']

export type ChatSession = Database['public']['Tables']['chat_sessions']['Row']
export type ChatSessionInsert = Database['public']['Tables']['chat_sessions']['Insert']
export type ChatSessionUpdate = Database['public']['Tables']['chat_sessions']['Update']

export type ChatMessage = Database['public']['Tables']['chat_messages']['Row']
export type ChatMessageInsert = Database['public']['Tables']['chat_messages']['Insert']
export type ChatMessageUpdate = Database['public']['Tables']['chat_messages']['Update']

export type ProjectDetail = Database['public']['Views']['project_details']['Row']
export type UserProject = Database['public']['Views']['user_projects']['Row']

// 枚举类型
export type ProjectStage = '售前' | '业务调研' | '数据理解' | '数据探索' | '工程开发' | '实施部署'
export type ProjectStatus = 'active' | 'archived' | 'completed' | 'on_hold'
export type ProjectRole = 'owner' | 'admin' | 'member' | 'viewer'
export type FileAccessLevel = 'all_users' | 'project_members' | 'admins_only' | 'owner_only'
export type MessageRole = 'user' | 'assistant' | 'system'

// 搜索结果类型
export type SimilarDocument = Database['public']['Functions']['search_similar_documents']['Returns'][0]

// 复杂的关联查询类型
export interface ProjectWithMembers extends Project {
  members: (ProjectMember & {
    user: Pick<Profile, 'id' | 'username' | 'full_name' | 'avatar_url'>
  })[]
  creator: Pick<Profile, 'id' | 'username' | 'full_name' | 'avatar_url'>
  files_count?: number
  member_count?: number
}

export interface FileWithProject extends File {
  project?: Pick<Project, 'id' | 'name'>
  uploader: Pick<Profile, 'id' | 'username' | 'full_name' | 'avatar_url'>
}

export interface ChatSessionWithMessages extends ChatSession {
  messages: ChatMessage[]
  project?: Pick<Project, 'id' | 'name'>
}

// API响应类型
export interface ApiResponse<T = any> {
  data?: T
  error?: string
  message?: string
}

export interface PaginatedResponse<T> extends ApiResponse<T[]> {
  count: number
  page: number
  pageSize: number
  hasNext: boolean
  hasPrevious: boolean
}

// 认证相关类型
export interface AuthUser {
  id: string
  email?: string
  user_metadata?: Record<string, any>
  app_metadata?: Record<string, any>
}

export interface AuthSession {
  access_token: string
  refresh_token: string
  expires_in: number
  expires_at?: number
  user: AuthUser
}

// 表单类型
export interface LoginForm {
  email: string
  password: string
}

export interface RegisterForm {
  email: string
  password: string
  confirmPassword: string
  username?: string
  fullName?: string
}

export interface ProfileForm {
  username?: string
  full_name?: string
  bio?: string
  phone?: string
  department?: string
  position?: string
}

export interface ProjectForm {
  name: string
  description?: string
  stage: ProjectStage
}

// 错误类型
export interface SupabaseError {
  message: string
  details?: string
  hint?: string
  code?: string
}
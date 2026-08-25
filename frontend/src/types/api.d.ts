// 后端API响应类型定义

declare namespace API {
  // ==================== 会话相关 ====================

  /** 会话信息（后端返回格式） */
  interface Session {
    session_id: string
    session_name: string
    created_at: string
    updated_at: string
    user_id: string
    message_count: number
    last_message_at: string | null
  }

  /** 会话列表响应 */
  interface SessionListResponse {
    sessions: Session[]
  }

  /** 创建会话响应 */
  interface SessionCreateResponse {
    session_id: string
    session_name: string
    status: string
    message: string
  }

  // ==================== 消息相关 ====================

  /** 消息项（后端返回格式） */
  interface Message {
    role: 'user' | 'assistant' | 'system'
    content: string
    timestamp: string
    metadata?: Record<string, any>
  }

  /** 消息列表响应 */
  interface MessageListResponse {
    messages: Message[]
  }

  // ==================== 聊天相关 ====================

  /** 聊天请求 */
  interface ChatRequest {
    message: string
    web_search?: boolean
    attachments?: string[]
  }

  /** SSE事件类型 */
  interface SSEEvent {
    kind: 'THINK' | 'ANSWER' | 'PROCESS' | 'REFERENCE' | 'QUESTION'
    text?: string
    data?: any
  }

  /** 前端聊天项（用于渲染） */
  interface ChatItem {
    id: string
    role: 'user' | 'assistant' | 'system'
    content: string
    thinking?: string
    process?: string
    timestamp?: string
    isStreaming?: boolean
    references?: Reference[]
    recommendedQuestions?: string[]
  }

  /** 历史消息项（后端返回格式） */
  interface MessageItem {
    message_id: string
    session_id: string
    user_question: string
    model_answer: string
    think?: string | null
    process?: string | null
    documents?: string | null
    created_at: string
  }

  // ==================== 用户相关 ====================

  /** 登录响应 */
  interface LoginResponse {
    access_token: string
    token_type: string
  }

  /** 注册响应 */
  interface RegisterResponse {
    message: string
  }

  /** 用户信息 */
  interface UserInfo {
    user_id: number
    username: string
  }

  // ==================== 通用类型 ====================

  interface Reference {
    id: string
    title: string
    content: string
    url?: string
  }

  interface Result<T = any> {
    success: boolean
    data?: T
    error?: string
    message?: string
  }
}

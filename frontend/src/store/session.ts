import { proxy } from 'valtio'

/** 会话状态管理 */
interface SessionState {
  /** 会话列表 */
  list: API.Session[]
  /** 当前激活的会话ID */
  currentSessionId: string | null
  /** 当前会话的消息列表 */
  currentMessages: API.ChatItem[]
  /** 是否正在加载会话列表 */
  loading: boolean
  /** 是否正在加载消息 */
  messagesLoading: boolean
  /** 是否启用网络搜索 */
  useWeb: boolean
  /** 是否开启深度思考 */
  deepThink: boolean
}

const state = proxy<SessionState>({
  list: [],
  currentSessionId: null,
  currentMessages: [],
  loading: false,
  messagesLoading: false,
  useWeb: false,
  deepThink: true,
})

const actions = {
  /** 设置会话列表 */
  setList(list: API.Session[]) {
    state.list = list
  },

  /** 添加会话到列表 */
  addSession(session: API.Session) {
    state.list.unshift(session)
  },

  /** 删除会话 */
  removeSession(sessionId: string) {
    state.list = state.list.filter((s) => s.session_id !== sessionId)
    if (state.currentSessionId === sessionId) {
      state.currentSessionId = null
      state.currentMessages = []
    }
  },

  /** 设置当前会话 */
  setCurrentSession(sessionId: string) {
    state.currentSessionId = sessionId
    state.currentMessages = []
  },

  /** 设置当前会话的消息列表 */
  setMessages(messages: API.ChatItem[]) {
    state.currentMessages = messages
  },

  /** 添加消息到当前会话 */
  addMessage(message: API.ChatItem) {
    state.currentMessages.push(message)
  },

  /** 更新最后一条消息（用于流式更新） */
  updateLastMessage(content: string) {
    if (state.currentMessages.length > 0) {
      const lastMessage = state.currentMessages[state.currentMessages.length - 1]
      lastMessage.content = content
    }
  },

  /** 更新最后一条消息的思考内容 */
  updateLastThinking(thinking: string) {
    if (state.currentMessages.length > 0) {
      const lastMessage = state.currentMessages[state.currentMessages.length - 1]
      lastMessage.thinking = thinking
    }
  },

  /** 更新最后一条消息的处理过程 */
  updateLastProcess(process: string) {
    if (state.currentMessages.length > 0) {
      const lastMessage = state.currentMessages[state.currentMessages.length - 1]
      lastMessage.process = process
    }
  },

  /** 更新最后一条消息的参考来源 */
  updateLastReferences(references: API.Reference[]) {
    if (state.currentMessages.length > 0) {
      const lastMessage = state.currentMessages[state.currentMessages.length - 1]
      lastMessage.references = references
    }
  },

  /** 完成最后一条消息的流式传输 */
  finishLastMessageStreaming() {
    if (state.currentMessages.length > 0) {
      const lastMessage = state.currentMessages[state.currentMessages.length - 1]
      if (lastMessage.isStreaming) {
        lastMessage.isStreaming = false
      }
    }
  },

  /** 移除最后一条消息（发送失败时） */
  removeLastMessage() {
    if (state.currentMessages.length > 0) {
      state.currentMessages.pop()
    }
  },

  /** 清空当前会话 */
  clearCurrent() {
    state.currentSessionId = null
    state.currentMessages = []
  },

  /** 设置加载状态 */
  setLoading(loading: boolean) {
    state.loading = loading
  },

  /** 设置消息加载状态 */
  setMessagesLoading(loading: boolean) {
    state.messagesLoading = loading
  },

  /** 切换网络搜索 */
  toggleUseWeb() {
    state.useWeb = !state.useWeb
  },

  /** 切换深度思考 */
  toggleDeepThink() {
    state.deepThink = !state.deepThink
  },
}

export const sessionState = state
export const sessionActions = actions

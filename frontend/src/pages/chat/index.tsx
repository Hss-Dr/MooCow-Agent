import { useEffect, useRef, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { message, Spin, Button, FloatButton } from 'antd'
import { useRequest } from 'ahooks'
import { useSnapshot } from 'valtio'
import { VerticalAlignBottomOutlined } from '@ant-design/icons'
import * as api from '@/api'
import { sessionState, sessionActions } from '@/store/session'
import ComSender from '@/components/sender'
import SafeMarkdown from '@/components/safe-markdown'
import ThinkingBlock from '@/components/thinking-block'
import { ThinkingOrb } from 'thinking-orbs'
import styles from './index.module.scss'

// 生成唯一ID
function generateId() {
  return `${Date.now()}_${Math.random().toString(36).substring(2, 9)}`
}

// 滚动到底部
function scrollToBottom(smooth = true) {
  setTimeout(() => {
    window.scrollTo({
      top: document.documentElement.scrollHeight,
      behavior: smooth ? 'smooth' : 'auto',
    })
  }, 100)
}

// 参考来源块：点击胶囊展开该文档的检索片段
function SourcesBlock({ references }: { references: API.Reference[] }) {
  const [activeIdx, setActiveIdx] = useState<number | null>(null)

  return (
    <div className={styles.sourcesWrap}>
      <div className={styles.sources}>
        <span className={styles.sourcesLabel}>📎 参考来源</span>
        {references.map((ref, idx) => (
          <span
            key={ref.id || idx}
            className={`${styles.sourceChip} ${
              activeIdx === idx ? styles.sourceChipActive : ''
            }`}
            title={ref.title}
            onClick={() => setActiveIdx(activeIdx === idx ? null : idx)}
          >
            {ref.title}
          </span>
        ))}
      </div>
      {activeIdx !== null && references[activeIdx] && (
        <div className={styles.sourceDetail}>
          <div className={styles.sourceDetailTitle}>
            {references[activeIdx].title}
          </div>
          <div className={styles.sourceDetailContent}>
            {references[activeIdx].content || '（该来源没有可展示的片段内容）'}
          </div>
        </div>
      )}
    </div>
  )
}

export default function Chat() {
  const { id: sessionId } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { currentMessages, messagesLoading, deepThink } = useSnapshot(sessionState)
  const [isSending, setIsSending] = useState(false)
  const [showScrollButton, setShowScrollButton] = useState(false)
  const abortControllerRef = useRef<AbortController | null>(null)

  // 监听滚动，显示/隐藏滚动到底部按钮
  useEffect(() => {
    const handleScroll = () => {
      const scrollTop = window.pageYOffset || document.documentElement.scrollTop
      const scrollHeight = document.documentElement.scrollHeight
      const clientHeight = window.innerHeight
      setShowScrollButton(scrollHeight - scrollTop - clientHeight > 200)
    }

    window.addEventListener('scroll', handleScroll)
    return () => window.removeEventListener('scroll', handleScroll)
  }, [])

  // 加载会话消息
  const { run: loadMessages } = useRequest(
    async (sid: string) => {
      if (!sid) return

      sessionActions.setMessagesLoading(true)

      try {
        const response = await api.session.detail({ session_id: sid })

        // 转换为ChatItem格式
        const chatItems: API.ChatItem[] = []

        response.data.forEach((item: API.MessageItem) => {
          // 添加用户消息
          if (item.user_question) {
            chatItems.push({
              id: generateId(),
              role: 'user',
              content: item.user_question,
              timestamp: item.created_at,
            })
          }

          // 添加助手消息（恢复思考与处理过程、参考来源）
          if (item.model_answer) {
            let references: API.Reference[] | undefined
            if (item.documents) {
              try {
                references = JSON.parse(item.documents)
              } catch (e) {
                references = undefined
              }
            }

            chatItems.push({
              id: generateId(),
              role: 'assistant',
              content: item.model_answer,
              thinking: item.think || undefined,
              process: item.process || undefined,
              references,
              timestamp: item.created_at,
            })
          }
        })

        sessionActions.setMessages(chatItems)
        scrollToBottom(false)
      } catch (error: any) {
        if (error.response?.status === 404) {
          message.error('会话不存在或无权访问')
          navigate('/')
        } else {
          message.error('加载消息失败')
        }
      } finally {
        sessionActions.setMessagesLoading(false)
      }
    },
    {
      manual: true,
    },
  )

  // 初始化会话
  useEffect(() => {
    if (sessionId) {
      sessionActions.setCurrentSession(sessionId)
      loadMessages(sessionId)
    }
  }, [sessionId, loadMessages])

  // 发送消息
  const handleSend = async (content: string, files?: string[]) => {
    if (!sessionId || !content.trim()) return

    setIsSending(true)

    // 添加用户消息
    const userMessage: API.ChatItem = {
      id: generateId(),
      role: 'user',
      content: content.trim(),
      timestamp: new Date().toISOString(),
    }
    sessionActions.addMessage(userMessage)
    scrollToBottom()

    // 添加助手消息占位符
    const assistantMessage: API.ChatItem = {
      id: generateId(),
      role: 'assistant',
      content: '',
      isStreaming: true,
    }
    sessionActions.addMessage(assistantMessage)

    try {
      abortControllerRef.current = new AbortController()

      const response = await api.session.chat(
        {
          id: sessionId,
          message: content.trim(),
          attachments: files,
          deep_think: deepThink,
        },
        {
          signal: abortControllerRef.current.signal,
        },
      )

      const reader = response.data.getReader()
      const decoder = new TextDecoder()
      let fullContent = ''
      let fullThinking = ''
      let fullProcess = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        const chunk = decoder.decode(value, { stream: true })
        const lines = chunk.split('\n')

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const dataStr = line.slice(6)
              const data = JSON.parse(dataStr)
              const content = data.content

              if (content?.kind === 'ANSWER' && content?.text) {
                fullContent += content.text
                sessionActions.updateLastMessage(fullContent)
                scrollToBottom()
              } else if (content?.kind === 'THINKING' && content?.text) {
                fullThinking += content.text
                sessionActions.updateLastThinking(fullThinking)
              } else if (content?.kind === 'PROCESS' && content?.text) {
                fullProcess += content.text
                sessionActions.updateLastProcess(fullProcess)
              } else if (content?.kind === 'REFERENCE' && content?.text) {
                // 参考来源（JSON 数组，单次事件）
                try {
                  const refs = JSON.parse(content.text)
                  sessionActions.updateLastReferences(refs)
                } catch (e) {
                  // 忽略解析错误
                }
              }
            } catch (e) {
              // 忽略解析错误
            }
          }
        }
      }

      // 标记流式传输完成
      sessionActions.finishLastMessageStreaming()
    } catch (error: any) {
      if (error.name === 'AbortError') {
        message.info('已停止生成')
      } else if (error.response?.status === 404) {
        message.error('会话不存在或无权访问')
        navigate('/')
      } else {
        message.error('发送失败: ' + (error.response?.data?.detail || error.message))
      }

      // 移除失败的助手消息
      sessionActions.removeLastMessage()
    } finally {
      setIsSending(false)
      abortControllerRef.current = null
    }
  }

  // 停止生成
  const handleStop = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
      setIsSending(false)
      sessionActions.finishLastMessageStreaming()
      message.info('已停止生成')
    }
  }

  // 重新生成
  const handleRegenerate = () => {
    // 获取最后一个用户消息
    const messages = sessionState.currentMessages
    let lastUserMessage: API.ChatItem | null = null

    for (let i = messages.length - 1; i >= 0; i--) {
      if (messages[i].role === 'user') {
        lastUserMessage = messages[i]
        break
      }
    }

    if (lastUserMessage) {
      // 删除最后一个助手消息
      sessionActions.removeLastMessage()
      // 重新发送
      handleSend(lastUserMessage.content)
    }
  }

  // 删除消息对
  const handleDeleteMessage = (messageId: string) => {
    // TODO: 实现删除消息逻辑
    message.info('删除功能开发中')
  }

  // 格式化时间
  const formatTime = (timestamp?: string) => {
    if (!timestamp) return ''
    const date = new Date(timestamp)
    return date.toLocaleTimeString('zh-CN', {
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  return (
    <div className={styles.container}>
      <div className={styles.messages}>
        <div className={styles.messagesInner}>
          {messagesLoading ? (
            <div className={styles.loading}>
              <Spin size="large" tip="加载消息中..." />
            </div>
          ) : currentMessages.length === 0 ? (
            <div className={styles.empty}>
              <div className={styles.emptyLogo}>
                <ThinkingOrb state="solving" size={64} theme="dark" />
              </div>
              <p className={styles.emptyTitle}>你好，我是新能源汽车智能助手</p>
              <p className={styles.emptySub}>懂技术、会导航、能联网搜索，随时为你服务</p>
            </div>
          ) : (
            currentMessages.map((msg) => (
            <div
              key={msg.id}
              className={`${styles.message} ${
                msg.role === 'user' ? styles.user : styles.assistant
              }`}
            >
              {msg.role === 'assistant' && (
                <div className={styles.avatarOrb}>
                  <span className={styles.orbScaled}>
                    <ThinkingOrb
                      state={msg.isStreaming ? 'working' : 'solving'}
                      size={64}
                      theme="dark"
                    />
                  </span>
                </div>
              )}
              <div className={styles.messageContent}>
                <div className={styles.messageText}>
                  {msg.role === 'user' ? (
                    msg.content
                  ) : (
                    <>
                      <ThinkingBlock
                        thinking={msg.thinking}
                        process={msg.process}
                        isStreaming={msg.isStreaming}
                      />
                      {msg.content ? (
                        <SafeMarkdown content={msg.content} />
                      ) : (
                        <span className={styles.typingCursor} />
                      )}
                      {msg.references && msg.references.length > 0 && (
                        <SourcesBlock references={msg.references} />
                      )}
                    </>
                  )}
                </div>
                {msg.role !== 'user' && msg.timestamp && (
                  <div className={styles.messageTime}>
                    {formatTime(msg.timestamp)}
                  </div>
                )}
                {msg.role === 'assistant' && !msg.isStreaming && (
                  <div className={styles.messageActions}>
                    <Button
                      size="small"
                      type="text"
                      onClick={() => {
                        navigator.clipboard.writeText(msg.content)
                        message.success('已复制')
                      }}
                    >
                      复制
                    </Button>
                    <Button
                      size="small"
                      type="text"
                      onClick={handleRegenerate}
                    >
                      重新生成
                    </Button>
                  </div>
                )}
              </div>
            </div>
          ))
        )}
        </div>
      </div>

      <div className={styles.sender}>
        <div className={styles.senderInner}>
          <ComSender
            onSend={handleSend}
            onStop={handleStop}
            disabled={messagesLoading}
            loading={isSending}
          />
        </div>
      </div>

      {showScrollButton && (
        <FloatButton
          icon={<VerticalAlignBottomOutlined />}
          tooltip="滚动到底部"
          onClick={() => scrollToBottom()}
        />
      )}
    </div>
  )
}

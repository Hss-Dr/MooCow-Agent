import {
  Button,
  List,
  Popconfirm,
  Spin,
  message,
  Input,
  Modal,
} from 'antd'
import {
  PlusOutlined,
  DeleteOutlined,
  MessageOutlined,
  EditOutlined,
} from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { useSnapshot } from 'valtio'
import { useState } from 'react'
import { useRequest } from 'ahooks'
import * as api from '@/api'
import { sessionState, sessionActions } from '@/store/session'
import styles from './index.module.scss'

export default function SessionList() {
  const navigate = useNavigate()
  const { list, currentSessionId, loading } = useSnapshot(sessionState)
  const [renameModalVisible, setRenameModalVisible] = useState(false)
  const [renamingSession, setRenamingSession] = useState<API.Session | null>(null)
  const [newSessionName, setNewSessionName] = useState('')

  // 加载会话列表
  const { run: loadSessions } = useRequest(
    async () => {
      sessionActions.setLoading(true)
      try {
        const response = await api.session.list({}, { repeatKey: 'session-list' })
        sessionActions.setList(response.data.sessions)
      } catch (error: any) {
        message.error('加载会话列表失败')
      } finally {
        sessionActions.setLoading(false)
      }
    },
    {
      manual: false,
    },
  )

  // 创建新会话
  const { run: createSession, loading: creating } = useRequest(
    async () => {
      try {
        const response = await api.session.create({
          session_name: '新对话',
        })
        const newSession: API.Session = {
          session_id: response.data.session_id,
          session_name: response.data.session_name,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
          user_id: '',
          message_count: 0,
          last_message_at: null,
        }
        sessionActions.addSession(newSession)
        navigate(`/chat/${response.data.session_id}`)
        message.success('创建会话成功')
      } catch (error: any) {
        message.error(error.response?.data?.detail || '创建会话失败')
      }
    },
    {
      manual: true,
    },
  )

  // 删除会话
  const { run: deleteSession } = useRequest(
    async (sessionId: string) => {
      try {
        await api.session.remove(sessionId)
        sessionActions.removeSession(sessionId)
        message.success('删除成功')

        // 如果删除的是当前会话，跳转到首页
        if (sessionId === currentSessionId) {
          navigate('/')
        }
      } catch (error: any) {
        message.error(error.response?.data?.detail || '删除失败')
      }
    },
    {
      manual: true,
    },
  )

  // 重命名会话
  const { run: renameSession, loading: renaming } = useRequest(
    async (sessionId: string, sessionName: string) => {
      try {
        await api.session.rename(sessionId, { session_name: sessionName })

        // 更新本地状态
        const updatedList = list.map((s) =>
          s.session_id === sessionId ? { ...s, session_name: sessionName } : s
        )
        sessionActions.setList(updatedList)

        message.success('重命名成功')
        setRenameModalVisible(false)
        setRenamingSession(null)
        setNewSessionName('')
      } catch (error: any) {
        message.error(error.response?.data?.detail || '重命名失败')
      }
    },
    {
      manual: true,
    },
  )

  // 打开重命名对话框
  const handleRename = (session: API.Session) => {
    setRenamingSession(session)
    setNewSessionName(session.session_name)
    setRenameModalVisible(true)
  }

  // 确认重命名
  const handleConfirmRename = () => {
    if (!renamingSession || !newSessionName.trim()) {
      message.warning('请输入会话名称')
      return
    }
    renameSession(renamingSession.session_id, newSessionName.trim())
  }

  // 选择会话
  const handleSelectSession = (sessionId: string) => {
    navigate(`/chat/${sessionId}`)
  }

  // 按天分组标签（今天 / 昨天 / N天前 / 具体日期）
  const dayLabel = (timestamp: string | null) => {
    if (!timestamp) return '更早'
    const date = new Date(timestamp)
    const now = new Date()
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate())
    const thatDay = new Date(date.getFullYear(), date.getMonth(), date.getDate())
    const days = Math.floor((today.getTime() - thatDay.getTime()) / 86400000)

    if (days <= 0) return '今天'
    if (days === 1) return '昨天'
    if (days < 7) return `${days}天前`
    return date.toLocaleDateString('zh-CN')
  }

  // 会话按天分组（列表已按时间倒序）
  const groupedSessions: { label: string; sessions: API.Session[] }[] = []
  for (const s of list) {
    const label = dayLabel(s.last_message_at)
    const lastGroup = groupedSessions[groupedSessions.length - 1]
    if (lastGroup && lastGroup.label === label) {
      lastGroup.sessions.push(s)
    } else {
      groupedSessions.push({ label, sessions: [s] })
    }
  }

  return (
    <div className={styles.sessionList}>
      <div className={styles.header}>
        <h3 className={styles.title}>对话列表</h3>
        <Button
          className={styles.newChatBtn}
          icon={<PlusOutlined />}
          onClick={createSession}
          loading={creating}
          size="small"
        >
          新建对话
        </Button>
      </div>

      {loading ? (
        <div className={styles.loading}>
          <Spin />
        </div>
      ) : list.length === 0 ? (
        <div className={styles.empty}>
          <MessageOutlined style={{ fontSize: 48, color: '#ccc' }} />
          <p>暂无对话</p>
        </div>
      ) : (
        <List
          dataSource={groupedSessions}
          renderItem={(group) => (
            <div key={group.label}>
              <div className={styles.dayGroup}>{group.label}</div>
              {group.sessions.map((session) => (
                <div
                  key={session.session_id}
                  className={`${styles.item} ${
                    currentSessionId === session.session_id ? styles.active : ''
                  }`}
                  onClick={() => handleSelectSession(session.session_id)}
                >
                  <div className={styles.itemContent}>
                    <div className={styles.itemTitle}>
                      {session.session_name || '未命名对话'}
                    </div>
                  </div>
                  <div className={styles.actions}>
                    <Button
                      type="text"
                      size="small"
                      icon={<EditOutlined />}
                      className={styles.actionBtn}
                      onClick={(e) => {
                        e.stopPropagation()
                        handleRename(session)
                      }}
                      title="重命名"
                    />
                    <Popconfirm
                      title="确定删除此对话吗？"
                      onConfirm={(e) => {
                        e?.stopPropagation()
                        deleteSession(session.session_id)
                      }}
                      okText="删除"
                      cancelText="取消"
                    >
                      <Button
                        type="text"
                        size="small"
                        danger
                        icon={<DeleteOutlined />}
                        className={styles.actionBtn}
                        onClick={(e) => e.stopPropagation()}
                        title="删除"
                      />
                    </Popconfirm>
                  </div>
                </div>
              ))}
            </div>
          )}
        />
      )}

      {/* 重命名对话框 */}
      <Modal
        title="重命名对话"
        open={renameModalVisible}
        onOk={handleConfirmRename}
        onCancel={() => {
          setRenameModalVisible(false)
          setRenamingSession(null)
          setNewSessionName('')
        }}
        okText="确定"
        cancelText="取消"
        confirmLoading={renaming}
      >
        <Input
          placeholder="请输入会话名称"
          value={newSessionName}
          onChange={(e) => setNewSessionName(e.target.value)}
          onPressEnter={handleConfirmRename}
          maxLength={50}
          showCount
        />
      </Modal>
    </div>
  )
}

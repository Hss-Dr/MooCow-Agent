import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Spin, message } from 'antd'
import { ThunderboltOutlined } from '@ant-design/icons'
import { useRequest } from 'ahooks'
import * as api from '@/api'
import { sessionActions } from '@/store/session'
import styles from './index.module.scss'

export default function Index() {
  const navigate = useNavigate()

  // 自动创建新会话并跳转
  const { loading } = useRequest(
    async () => {
      try {
        // 先加载会话列表
        const listResponse = await api.session.list({}, { repeatKey: 'index-init' })
        const sessions = listResponse.data.sessions

        sessionActions.setList(sessions)

        // 如果有会话，跳转到最近的会话
        if (sessions.length > 0) {
          const latestSession = sessions[0]
          navigate(`/chat/${latestSession.session_id}`)
          return
        }

        // 否则创建新会话
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
      } catch (error: any) {
        message.error('初始化失败: ' + (error.response?.data?.detail || error.message))
      }
    },
    {
      manual: false,
    },
  )

  return (
    <div className={styles.container}>
      <div className={styles.logo}>
        <ThunderboltOutlined />
      </div>
      <p className={styles.title}>新能源汽车智能助手</p>
      <p className={styles.sub}>正在初始化会话...</p>
      <Spin size="large" className={styles.spin} />
    </div>
  )
}

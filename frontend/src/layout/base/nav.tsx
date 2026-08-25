import { Avatar, Dropdown, Menu } from 'antd'
import { useSnapshot } from 'valtio'
import { useNavigate, useLocation } from 'react-router-dom'
import {
  MessageOutlined,
  FolderOutlined,
  ThunderboltOutlined,
  LogoutOutlined,
  UserOutlined,
} from '@ant-design/icons'
import SessionList from '@/components/session-list'
import { userState, userActions } from '@/store/user'
import * as authApi from '@/api/auth'
import './nav.scss'

export function Nav() {
  const user = useSnapshot(userState)
  const navigate = useNavigate()
  const location = useLocation()
  const avatarText = user.username ? user.username[0].toUpperCase() : 'U'

  // 判断当前路由
  const currentPath = location.pathname
  const selectedKey = currentPath.startsWith('/repository') ? 'repository' : 'chat'
  // 会话列表只在 /chat 路径挂载（'/' 过渡页由 Index 自己拉列表，避免两个同 URL 请求被防重复插件互杀）
  const showSessions = currentPath.startsWith('/chat')

  const menuItems = [
    {
      key: 'chat',
      icon: <MessageOutlined />,
      label: '对话',
      onClick: () => navigate('/'),
    },
    {
      key: 'repository',
      icon: <FolderOutlined />,
      label: '文档管理',
      onClick: () => navigate('/repository'),
    },
  ]

  const handleLogout = async () => {
    try {
      await authApi.logout()
    } catch (error) {
      // 忽略登出API错误
    } finally {
      userActions.logout()
      navigate('/login')
    }
  }

  const userMenuItems = [
    {
      key: 'logout',
      label: '退出登录',
      icon: <LogoutOutlined />,
      onClick: handleLogout,
    },
  ]

  return (
    <div className="base-layout-nav">
      {/* 顶部品牌 Logo（原顶栏移入） */}
      <div className="base-layout-nav__logo">
        <div className="logo-icon">
          <ThunderboltOutlined />
        </div>
        <span className="logo-name">VoltPilot</span>
      </div>

      {/* 顶部导航菜单 */}
      <div className="base-layout-nav__menu">
        <Menu
          mode="vertical"
          selectedKeys={[selectedKey]}
          items={menuItems}
          style={{ border: 'none' }}
        />
      </div>

      {/* 会话列表（仅在 /chat 路径显示） */}
      {showSessions && (
        <div className="base-layout-nav__sessions">
          <SessionList />
        </div>
      )}

      {/* 底部用户信息（含退出登录） */}
      <Dropdown
        menu={{ items: userMenuItems }}
        placement="topRight"
        trigger={['click']}
      >
        <div className="base-layout-nav__user">
          {/* 未上传头像时的中性占位：灰色底 + 用户名首字母 / 人形图标 */}
          <Avatar
            size={32}
            style={{ background: '#3a3d44', color: '#a6a8ad' }}
          >
            {user.username ? avatarText : <UserOutlined />}
          </Avatar>
          <span className="username">{user.username || '用户'}</span>
        </div>
      </Dropdown>
    </div>
  )
}

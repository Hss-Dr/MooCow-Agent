import { Button, Form, Input, Tabs, message } from 'antd'
import { ThunderboltOutlined } from '@ant-design/icons'
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import * as authApi from '@/api/auth'
import { userActions } from '@/store/user'
import styles from './index.module.scss'

type LoginForm = {
  username: string
  password: string
}

type RegisterForm = {
  username: string
  password: string
  confirmPassword: string
}

export default function Login() {
  const navigate = useNavigate()
  const [activeTab, setActiveTab] = useState<'login' | 'register'>('login')
  const [loginForm] = Form.useForm<LoginForm>()
  const [registerForm] = Form.useForm<RegisterForm>()
  const [loading, setLoading] = useState(false)

  const handleLogin = async (values: LoginForm) => {
    setLoading(true)
    try {
      const response = await authApi.login({
        username: values.username,
        password: values.password,
      })

      // 保存token和用户名
      userActions.setToken(response.data.access_token)
      userActions.setUsername(values.username)

      message.success('登录成功')
      navigate('/')
    } catch (error: any) {
      message.error(error.response?.data?.detail || '登录失败')
    } finally {
      setLoading(false)
    }
  }

  const handleRegister = async (values: RegisterForm) => {
    if (values.password !== values.confirmPassword) {
      message.error('两次输入的密码不一致')
      return
    }

    setLoading(true)
    try {
      // 1. 注册
      await authApi.register({
        username: values.username,
        password: values.password,
      })

      // 2. 自动登录
      const loginResponse = await authApi.login({
        username: values.username,
        password: values.password,
      })

      // 3. 保存token和用户名
      userActions.setToken(loginResponse.data.access_token)
      userActions.setUsername(values.username)

      message.success('注册成功')
      navigate('/')
    } catch (error: any) {
      message.error(error.response?.data?.detail || '注册失败')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className={styles.container}>
      <div className={styles.card}>
        <div className={styles.header}>
          <div className={styles.logo}>
            <ThunderboltOutlined />
          </div>
          <h1>新能源汽车智能助手</h1>
          <p>懂技术 · 会导航 · 能联网搜索</p>
        </div>

        <Tabs
          activeKey={activeTab}
          onChange={(key) => setActiveTab(key as 'login' | 'register')}
          centered
          items={[
            {
              key: 'login',
              label: '登录',
              children: (
                <Form
                  form={loginForm}
                  onFinish={handleLogin}
                  layout="vertical"
                  autoComplete="off"
                >
                  <Form.Item
                    label="用户名"
                    name="username"
                    rules={[{ required: true, message: '请输入用户名' }]}
                  >
                    <Input placeholder="请输入用户名" size="large" />
                  </Form.Item>

                  <Form.Item
                    label="密码"
                    name="password"
                    rules={[{ required: true, message: '请输入密码' }]}
                  >
                    <Input.Password placeholder="请输入密码" size="large" />
                  </Form.Item>

                  <Form.Item>
                    <Button
                      type="primary"
                      htmlType="submit"
                      size="large"
                      block
                      loading={loading}
                    >
                      登录
                    </Button>
                  </Form.Item>
                </Form>
              ),
            },
            {
              key: 'register',
              label: '注册',
              children: (
                <Form
                  form={registerForm}
                  onFinish={handleRegister}
                  layout="vertical"
                  autoComplete="off"
                >
                  <Form.Item
                    label="用户名"
                    name="username"
                    rules={[
                      { required: true, message: '请输入用户名' },
                      { min: 3, message: '用户名至少3个字符' },
                      { max: 20, message: '用户名最多20个字符' },
                    ]}
                  >
                    <Input placeholder="请输入用户名" size="large" />
                  </Form.Item>

                  <Form.Item
                    label="密码"
                    name="password"
                    rules={[
                      { required: true, message: '请输入密码' },
                      { min: 6, message: '密码至少6个字符' },
                    ]}
                  >
                    <Input.Password placeholder="请输入密码" size="large" />
                  </Form.Item>

                  <Form.Item
                    label="确认密码"
                    name="confirmPassword"
                    rules={[{ required: true, message: '请确认密码' }]}
                  >
                    <Input.Password placeholder="请再次输入密码" size="large" />
                  </Form.Item>

                  <Form.Item>
                    <Button
                      type="primary"
                      htmlType="submit"
                      size="large"
                      block
                      loading={loading}
                    >
                      注册
                    </Button>
                  </Form.Item>
                </Form>
              ),
            },
          ]}
        />
      </div>
    </div>
  )
}

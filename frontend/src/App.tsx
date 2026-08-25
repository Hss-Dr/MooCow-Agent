import { Router } from '@/router'
import { App as AntdApp, ConfigProvider, Spin, theme } from 'antd'
import zhCN from 'antd/es/locale/zh_CN'
import { useCallback, useRef, useState } from 'react'
function App() {
  return (
    <ConfigProvider
      locale={zhCN}
      theme={{
        cssVar: true,
        algorithm: theme.darkAlgorithm,
        token: {
          colorPrimary: '#4d6bfe',
          colorInfo: '#4d6bfe',
          colorText: '#ececec',
          colorTextSecondary: '#a6a8ad',
          colorBgBase: '#000000',
          colorBgContainer: '#2b2e33',
          colorBgLayout: '#000000',
          colorBgElevated: '#2b2e33',
          colorBorder: '#34373c',
          colorBorderSecondary: '#2a2c31',
          borderRadius: 8,
          fontSize: 14,
          fontFamily:
            "-apple-system, BlinkMacSystemFont, 'SF Pro Text', Inter, 'PingFang SC', 'Microsoft YaHei', sans-serif",
          controlHeight: 36,
        },
        components: {
          Button: {
            primaryShadow: 'none',
            fontWeight: 500,
          },
          Input: {
            activeShadow: '0 0 0 3px rgba(255, 255, 255, 0.06)',
            colorBgContainer: '#2b2e33',
          },
          Menu: {
            itemSelectedBg: '#32353b',
            itemSelectedColor: '#ececec',
            itemBorderRadius: 8,
            darkItemBg: '#000000',
          },
          FloatButton: {
            colorPrimary: '#32353b',
            colorText: '#a6a8ad',
          },
          Spin: {
            colorPrimary: '#a6a8ad',
          },
          Message: {
            contentBg: '#2b2e33',
            colorText: '#ececec',
          },
          Tabs: {
            colorBgContainer: 'transparent',
            itemSelectedColor: '#ececec',
            inkBarColor: '#ececec',
          },
          Form: {
            labelColor: '#a6a8ad',
          },
          Upload: {
            colorBgContainer: '#2b2e33',
          },
          Card: {
            colorBgContainer: '#2b2e33',
          },
          Modal: {
            contentBg: '#2b2e33',
            headerBg: '#2b2e33',
          },
          Table: {
            colorBgContainer: '#2b2e33',
            headerBg: '#32353b',
            rowHoverBg: '#32353b',
            borderColor: '#34373c',
          },
        },
      }}
    >
      <AntdApp>
        <Router />
        <MountApi />
      </AntdApp>
    </ConfigProvider>
  )
}

function MountApi() {
  window.$app = AntdApp.useApp()

  const [loading, setLoading] = useState(false)
  const [loadingText, setLoadingText] = useState('')
  const loadingCount = useRef(0)
  window.$showLoading = useCallback(({ title }: { title?: string } = {}) => {
    loadingCount.current++
    setLoading(true)
    setLoadingText(title ?? '')
  }, [])
  window.$hideLoading = useCallback(() => {
    loadingCount.current--
    setTimeout(() => {
      if (loadingCount.current <= 0) {
        setLoading(false)
        setLoadingText('')
      }
    }, 100)
  }, [])

  return (
    <>
      <Spin
        spinning={loading}
        tip={loadingText}
        fullscreen
        style={{
          zIndex: 9999999,
        }}
      ></Spin>
    </>
  )
}

export default App

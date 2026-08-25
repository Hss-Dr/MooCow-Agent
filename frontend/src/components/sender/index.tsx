import * as api from '@/api'
import IconFile from '@/assets/component/file.svg'
import IconSend from '@/components/icons/IconSend'
import { BorderBeam } from 'border-beam'
import { sessionActions, sessionState } from '@/store/session'
import {
  BulbOutlined,
  GlobalOutlined,
  LoadingOutlined,
} from '@ant-design/icons'
import { Button, Input, Space, Upload, UploadFile } from 'antd'
import classNames from 'classnames'
import { PropsWithChildren, useMemo, useState } from 'react'
import { useSnapshot } from 'valtio'
import './index.scss'

const IconFile2 = (
  <svg
    className="com-sender__file-icon"
    xmlns="http://www.w3.org/2000/svg"
    width="24"
    height="24"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
    aria-hidden="true"
  >
    <path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"></path>
    <path d="M14 2v4a2 2 0 0 0 2 2h4"></path>
    <path d="M10 9H8"></path>
    <path d="M16 13H8"></path>
    <path d="M16 17H8"></path>
  </svg>
)

export default function ComSender(
  props: PropsWithChildren<{
    className?: string
    loading?: boolean
    disabled?: boolean
    onSend?: (value: string, files?: string[]) => void | Promise<void>
    onStop?: () => void
    onContract?: () => void
  }>,
) {
  const { className, onSend, onStop, onContract, loading, disabled, ...rest } = props
  const [value, setValue] = useState('')
  const [fileList, setFileList] = useState<
    (UploadFile & {
      loading?: boolean
    })[]
  >([])

  const uploading = useMemo(() => {
    return fileList.some((file) => file.loading)
  }, [fileList])

  const session = useSnapshot(sessionState)

  const handleClickUpload = () => {
    // 上传功能可用
  }

  async function send() {
    if (uploading) {
      window.$app.message.info('正在上传中，请耐心等待')
      return
    }
    if (loading || disabled) return
    if (!value) return
    await onSend?.(
      value,
      fileList.filter((item) => item.url).map((item) => item.url!),
    )
    setValue('')
    setFileList([])
  }

  // 输入卡片主体（流式生成时用 BorderBeam 包裹加流动光束）
  const mainCard = (
    <div className="com-sender__main">
      <Input.TextArea
        value={value}
        onChange={(e) => setValue(e.target.value)}
        placeholder="按 Enter 发送，Shift + Enter 换行"
        autoSize={{ minRows: 2, maxRows: 6 }}
        autoFocus
        onPressEnter={(e) => {
          if (!e.shiftKey) {
            e.preventDefault()
            send()
          }
        }}
      />

      <div className="com-sender__actions">
        <Space className="com-sender__actions-left" size={12}>
          {
            <Upload
              accept=".doc, .docx, .pdf, application/msword, application/pdf"
              showUploadList={false}
              beforeUpload={(file) => {
                upload(file)
                return false
              }}
            >
              <Button
                variant="text"
                color="default"
                onClick={handleClickUpload}
              >
                {uploading ? <LoadingOutlined /> : <img src={IconFile} />}
                附件
              </Button>
            </Upload>
          }

          <Button
            className={session.deepThink ? 'com-sender__toggle-active' : ''}
            color="default"
            variant="outlined"
            icon={<BulbOutlined />}
            onClick={() => sessionActions.toggleDeepThink()}
            disabled={loading}
            title={session.deepThink ? '已开启深度思考' : '已关闭深度思考'}
          >
            深度思考
          </Button>

          <Button
            className={session.useWeb ? 'com-sender__toggle-active' : ''}
            color="default"
            variant="outlined"
            icon={<GlobalOutlined />}
            onClick={() => sessionActions.toggleUseWeb()}
          >
            网络搜索
          </Button>
        </Space>

        <Space className="com-sender__actions-right" size={12}>
          {loading ? (
            // 生成中：发送键变为停止键（Kimi 风格）
            <Button
              className="btn-stop"
              onClick={onStop}
              title="停止生成"
            >
              <span className="btn-stop__square" />
            </Button>
          ) : (
            <Button
              className="btn-send"
              color="primary"
              variant="filled"
              onClick={send}
              disabled={!value && !fileList.length}
              icon={<IconSend />}
            ></Button>
          )}
        </Space>
      </div>
    </div>
  )

  async function upload(
    file: UploadFile & {
      loading?: boolean
    },
  ) {
    if (fileList.length >= 10) {
      window.$app.message.error('最多只能上传 10 个附件')
      return
    }

    file.loading = true

    if (file.type?.startsWith('image/')) {
      file.preview = URL.createObjectURL(file as any)
    }

    setFileList((prev) => [...prev, file])

    try {
      const { data } = await api.session.upload({ files: file as any })
      file.url = data.url

      window.$app.message.success(`${file.name} 上传成功，文档正在解析中...`)
    } catch (error) {
      window.$app.message.error(`${file.name} 上传失败`)
    } finally {
      file.loading = false
      setFileList((prev) => [...prev])
    }
  }

  return (
    <div className={classNames('com-sender', className)} {...rest}>
      {fileList.length ? (
        <div className="com-sender__files">
          {fileList.map((file) => (
            <div key={file.uid} className="com-sender__file">
              {file.type?.startsWith('image/') ? (
                <img className="com-sender__file-image" src={file.preview} />
              ) : (
                <>
                  {IconFile2}
                  <div className="com-sender__file-name" title={file.name}>
                    {file.name}
                  </div>
                </>
              )}
            </div>
          ))}
        </div>
      ) : null}

      {loading ? (
        <BorderBeam size="sm" colorVariant="mono" theme="dark">
          {mainCard}
        </BorderBeam>
      ) : (
        mainCard
      )}

      {/* <div className="com-sender__footer">
        <Space></Space>
      </div> */}
    </div>
  )
}

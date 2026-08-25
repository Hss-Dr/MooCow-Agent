import * as api from '@/api'
import IconUpload from '@/assets/repository/upload.svg'
import { Upload, UploadFile, UploadProps } from 'antd'
import { forwardRef, useImperativeHandle, useState } from 'react'
import styles from './upload.module.scss'

export type RepositoryUploadRef = {
  submit: () => Promise<void>
}

export default forwardRef(function RepositoryUpload(
  props: UploadProps,
  ref?: React.Ref<RepositoryUploadRef>,
) {
  const { ...otherProps } = props

  const [fileList, setFileList] = useState<UploadFile[]>([])

  useImperativeHandle(ref, () => {
    return {
      submit: async () => {
        let hasError = false

        for (const file of fileList) {
          if (file.status === 'done') continue

          setFileList((prev) =>
            prev.map((item) => {
              if (item.uid === file.uid) {
                return {
                  ...item,
                  status: 'uploading',
                }
              }
              return item
            }),
          )
          try {
            // 检查文件大小
            if ((file.size ?? 0) > 5 * 1024 * 1024) {
              throw new Error('文件大小不能超过5M')
            }

            await api.session.upload({ files: file.originFileObj as File })

            setFileList((prev) =>
              prev.map((item) => {
                if (item.uid === file.uid) {
                  return {
                    ...item,
                    status: 'done',
                    url: '#',
                  }
                }
                return item
              }),
            )
          } catch (error: any) {
            window.$app.message.error(error?.message || '上传失败')
            hasError = true
            setFileList((prev) =>
              prev.map((item) => {
                if (item.uid === file.uid) {
                  return {
                    ...item,
                    status: 'error',
                    response: error?.message,
                  }
                }
                return item
              }),
            )
          }
        }

        if (hasError) {
          throw new Error('Upload failed')
        } else {
          window.$app.message.success('上传已完成')
        }
      },
    }
  })

  return (
    <div className={styles['repository-upload']}>
      <Upload.Dragger
        {...otherProps}
        showUploadList={false}
        maxCount={10}
        fileList={fileList}
        onChange={(info) => setFileList(info.fileList)}
      >
        <img src={IconUpload} />
        <p
          className="ant-upload-text"
          style={{
            color: '#666',
          }}
        >
          Drag file here or{' '}
          <span style={{ color: '#4d6bfe' }}>click to upload</span>
        </p>
      </Upload.Dragger>

      <p className={styles['repository-upload__desc']}>
        Supports single or bulk file upload. Files must not exceed 5M each,with
        a maximum of 10 files.
      </p>

      <Upload
        fileList={fileList}
        onChange={(info) => setFileList(info.fileList)}
      />
    </div>
  )
})

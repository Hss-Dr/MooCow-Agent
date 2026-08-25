import { useState } from 'react'
import { DownOutlined, RightOutlined, ThunderboltOutlined } from '@ant-design/icons'
import { ThinkingOrb } from 'thinking-orbs'
import styles from './index.module.scss'

interface ThinkingBlockProps {
  thinking?: string
  process?: string
  isStreaming?: boolean
}

/** 折叠思考文本中的连续换行（2+ 个 \n → 1 个 \n），让推理内容紧凑显示 */
function collapseThinking(text: string): string {
  return text.replace(/\n{2,}/g, '\n')
}

export default function ThinkingBlock({ thinking, process, isStreaming }: ThinkingBlockProps) {
  const [expanded, setExpanded] = useState(false)

  const hasContent = thinking || process

  if (!hasContent) return null

  const label = isStreaming ? '思考中...' : '已深度思考'

  return (
    <div className={`${styles.thinkingBlock} ${expanded ? styles.expanded : ''}`}>
      <div
        className={styles.header}
        onClick={() => setExpanded(!expanded)}
      >
        <ThunderboltOutlined className={styles.icon} />
        {isStreaming && (
          <span className={styles.spinner}>
            <ThinkingOrb state="working" size={20} theme="dark" />
          </span>
        )}
        <span className={styles.label}>{label}</span>
        {expanded ? (
          <DownOutlined className={styles.arrow} />
        ) : (
          <RightOutlined className={styles.arrow} />
        )}
      </div>
      {expanded && (
        <div className={styles.content}>
          {thinking && (
            <div className={styles.thinkingSection}>
              <div className={styles.text}>{collapseThinking(thinking)}</div>
            </div>
          )}
          {process && (
            <div
              className={styles.processSection}
              dangerouslySetInnerHTML={{ __html: process }}
            />
          )}
        </div>
      )}
    </div>
  )
}

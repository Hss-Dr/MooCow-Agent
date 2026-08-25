/**
 * 安全的 Markdown 渲染组件
 *
 * 功能：
 * - 使用 react-markdown 渲染 Markdown
 * - 集成 DOMPurify 防止 XSS 攻击
 * - 支持代码高亮
 * - 支持数学公式（LaTeX）
 * - 支持 GitHub Flavored Markdown
 */

import ReactMarkdown from 'react-markdown'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism'
import remarkGfm from 'remark-gfm'
import remarkMath from 'remark-math'
import rehypeKatex from 'rehype-katex'
import rehypeRaw from 'rehype-raw'
import DOMPurify from 'dompurify'
import { useMemo } from 'react'
import 'katex/dist/katex.min.css'
import './index.scss'

interface SafeMarkdownProps {
  content: string
  className?: string
}

/**
 * 折叠连续空行（3+ 个 \n → 1 个空行），让模型输出的冗余换行不撑开间距。
 * 代码块（``` 围栏）内的换行原样保留。
 */
function collapseBlankLines(text: string): string {
  const lines = text.split('\n')
  const out: string[] = []
  let inFence = false
  let blankCount = 0

  for (const line of lines) {
    if (/^\s*```/.test(line)) {
      inFence = !inFence
      out.push(line)
      blankCount = 0
      continue
    }
    if (inFence) {
      out.push(line)
      continue
    }
    if (line.trim() === '') {
      blankCount++
      if (blankCount <= 1) out.push('') // 最多保留一个空行
    } else {
      blankCount = 0
      out.push(line)
    }
  }
  return out.join('\n')
}

export function SafeMarkdown({ content, className }: SafeMarkdownProps) {
  // 清理 HTML，防止 XSS（先折叠冗余空行）
  const sanitizedContent = useMemo(() => {
    return DOMPurify.sanitize(collapseBlankLines(content), {
      ALLOWED_TAGS: [
        'p', 'br', 'strong', 'em', 'u', 's', 'code', 'pre',
        'a', 'ul', 'ol', 'li', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
        'blockquote', 'hr', 'table', 'thead', 'tbody', 'tr', 'th', 'td',
        'img', 'span', 'div', 'sup', 'sub'
      ],
      ALLOWED_ATTR: ['href', 'target', 'rel', 'src', 'alt', 'title', 'class', 'id']
    })
  }, [content])

  return (
    <div className={`safe-markdown ${className || ''}`}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm, remarkMath]}
        rehypePlugins={[rehypeKatex, rehypeRaw]}
        components={{
          // 代码块高亮
          code({ node, inline, className, children, ...props }) {
            const match = /language-(\w+)/.exec(className || '')
            return !inline && match ? (
              <SyntaxHighlighter
                {...props}
                style={vscDarkPlus}
                language={match[1]}
                PreTag="div"
                customStyle={{
                  margin: 0,
                  borderRadius: '6px',
                  fontSize: '14px'
                }}
              >
                {String(children).replace(/\n$/, '')}
              </SyntaxHighlighter>
            ) : (
              <code className={className} {...props}>
                {children}
              </code>
            )
          },
          // 链接在新标签页打开
          a({ node, children, href, ...props }) {
            return (
              <a
                href={href}
                target="_blank"
                rel="noopener noreferrer"
                {...props}
              >
                {children}
              </a>
            )
          },
          // 表格样式
          table({ node, children, ...props }) {
            return (
              <div className="table-wrapper">
                <table {...props}>{children}</table>
              </div>
            )
          }
        }}
      >
        {sanitizedContent}
      </ReactMarkdown>
    </div>
  )
}

export default SafeMarkdown

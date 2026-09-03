/**
 * Markdown 渲染组件
 * 用于聊天消息中的 Markdown 内容渲染
 * 紧凑排版，适合对话场景
 */
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

interface MarkdownRendererProps {
  content: string
}

const styles = {
  p: {
    margin: 0,
    marginBottom: '4px',
    lineHeight: 1.4,
  },
  h1: {
    fontSize: 16,
    margin: '6px 0 2px',
    fontWeight: 600,
    lineHeight: 1.3,
  },
  h2: {
    fontSize: 15,
    margin: '4px 0 2px',
    fontWeight: 600,
    lineHeight: 1.3,
  },
  h3: {
    fontSize: 14,
    margin: '4px 0 2px',
    fontWeight: 600,
    lineHeight: 1.3,
  },
  h4: {
    fontSize: 13,
    margin: '4px 0 2px',
    fontWeight: 600,
    lineHeight: 1.3,
  },
  ul: {
    paddingLeft: 16,
    margin: '2px 0',
  },
  ol: {
    paddingLeft: 16,
    margin: '2px 0',
  },
  li: {
    margin: 0,
    padding: '1px 0',
    lineHeight: 1.4,
  },
  codeInline: {
    background: '#f0f0f0',
    padding: '0 3px',
    borderRadius: 3,
    fontSize: 12,
    fontFamily: 'monospace',
  },
  codeBlock: {
    background: '#282c34',
    color: '#abb2bf',
    padding: '10px 12px',
    borderRadius: 6,
    overflowX: 'auto' as const,
    fontSize: 13,
    margin: '6px 0',
    fontFamily: 'Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace',
    lineHeight: 1.5,
    border: '1px solid #3e4451',
  },
  blockquote: {
    borderLeft: '2px solid #1890ff',
    paddingLeft: 8,
    margin: '4px 0',
    color: '#666',
    background: '#fafafa',
    padding: '2px 8px',
    borderRadius: 3,
  },
  table: {
    borderCollapse: 'collapse' as const,
    width: '100%',
    fontSize: 12,
    margin: '4px 0',
  },
  th: {
    border: '1px solid #e8e8e8',
    padding: '2px 6px',
    background: '#fafafa',
    fontWeight: 500,
  },
  td: {
    border: '1px solid #e8e8e8',
    padding: '2px 6px',
  },
  hr: {
    border: 'none',
    borderTop: '1px solid #e8e8e8',
    margin: '4px 0',
  },
}

function MarkdownRenderer({ content }: MarkdownRendererProps) {
  return (
    <div className="markdown-content" style={{ fontSize: 14, lineHeight: 1.4 }}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          p: ({ children }) => <p style={styles.p}>{children}</p>,
          h1: ({ children }) => <h1 style={styles.h1}>{children}</h1>,
          h2: ({ children }) => <h2 style={styles.h2}>{children}</h2>,
          h3: ({ children }) => <h3 style={styles.h3}>{children}</h3>,
          h4: ({ children }) => <h4 style={styles.h4}>{children}</h4>,
          ul: ({ children }) => <ul style={styles.ul}>{children}</ul>,
          ol: ({ children }) => <ol style={styles.ol}>{children}</ol>,
          li: ({ children }) => <li style={styles.li}>{children}</li>,
          code: ({ className, children, ...props }) => {
            const match = /language-(\w+)/.exec(className || '')
            const isInline = !match && !String(children).includes('\n')

            if (isInline) {
              return (
                <code style={styles.codeInline} {...props}>
                  {children}
                </code>
              )
            }

            return (
              <pre style={styles.codeBlock}>
                <code className={className} {...props}>
                  {children}
                </code>
              </pre>
            )
          },
          blockquote: ({ children }) => (
            <blockquote style={styles.blockquote}>{children}</blockquote>
          ),
          a: ({ href, children }) => (
            <a href={href} target="_blank" rel="noopener noreferrer" style={{ color: '#1890ff' }}>
              {children}
            </a>
          ),
          table: ({ children }) => (
            <div style={{ overflowX: 'auto', margin: '4px 0' }}>
              <table style={styles.table}>{children}</table>
            </div>
          ),
          th: ({ children }) => <th style={styles.th}>{children}</th>,
          td: ({ children }) => <td style={styles.td}>{children}</td>,
          hr: () => <hr style={styles.hr} />,
          strong: ({ children }) => <strong style={{ fontWeight: 600 }}>{children}</strong>,
          em: ({ children }) => <em style={{ fontStyle: 'italic' }}>{children}</em>,
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  )
}

export default MarkdownRenderer

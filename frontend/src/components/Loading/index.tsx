/**
 * 通用加载状态组件
 * 支持多种加载样式
 */
import { Spin, Typography } from '@douyinfe/semi-ui'
import './Loading.css'

const { Text } = Typography

interface LoadingProps {
  size?: 'small' | 'medium' | 'large'
  text?: string
  fullScreen?: boolean
  delay?: number
}

function Loading({ size = 'medium', text, fullScreen = false }: LoadingProps) {
  // Semi Spin 组件的 size 类型是 'small' | 'middle' | 'large'
  const spinSize = size === 'medium' ? 'middle' : size

  const content = (
    <div className={`loading-container loading-${size}`}>
      <Spin size={spinSize} />
      {text && <Text type="tertiary" style={{ marginTop: 12 }}>{text}</Text>}
    </div>
  )

  if (fullScreen) {
    return <div className="loading-fullscreen">{content}</div>
  }

  return content
}

export default Loading

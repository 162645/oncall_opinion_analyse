/**
 * 通用空状态组件
 * 支持多种预设场景和自定义
 */
import { Button, Typography } from '@douyinfe/semi-ui'
import {
  IconInbox,
  IconSearch,
  IconFile,
  IconAlertCircle,
  IconWifi,
} from '@douyinfe/semi-icons'
import './EmptyState.css'

const { Text, Title } = Typography

type EmptyType = 'default' | 'search' | 'data' | 'error' | 'network' | 'custom'

interface EmptyStateProps {
  type?: EmptyType
  title?: string
  description?: string
  icon?: React.ReactNode
  action?: {
    text: string
    onClick: () => void
  }
  size?: 'small' | 'default' | 'large'
}

const presetConfig: Record<EmptyType, { icon: React.ReactNode; title: string; description: string }> = {
  default: {
    icon: <IconInbox size="extra-large" />,
    title: '暂无数据',
    description: '这里还没有任何内容',
  },
  search: {
    icon: <IconSearch size="extra-large" />,
    title: '未找到结果',
    description: '尝试调整搜索条件或关键词',
  },
  data: {
    icon: <IconFile size="extra-large" />,
    title: '暂无数据',
    description: '开始添加数据来查看内容',
  },
  error: {
    icon: <IconAlertCircle size="extra-large" />,
    title: '出错了',
    description: '抱歉，出现了一些问题',
  },
  network: {
    icon: <IconWifi size="extra-large" />,
    title: '网络异常',
    description: '请检查网络连接后重试',
  },
  custom: {
    icon: <IconInbox size="extra-large" />,
    title: '',
    description: '',
  },
}

function EmptyState({
  type = 'default',
  title,
  description,
  icon,
  action,
  size = 'default',
}: EmptyStateProps) {
  const config = presetConfig[type]

  return (
    <div className={`empty-state-container empty-state-${size}`}>
      <div className="empty-state-icon">
        {icon || config.icon}
      </div>

      {(title || config.title) && (
        <Title heading={5} style={{ marginTop: 16, marginBottom: 8 }}>
          {title || config.title}
        </Title>
      )}

      {(description || config.description) && (
        <Text type="tertiary" style={{ textAlign: 'center', maxWidth: 300 }}>
          {description || config.description}
        </Text>
      )}

      {action && (
        <Button
          type="primary"
          theme="solid"
          onClick={action.onClick}
          style={{ marginTop: 24 }}
        >
          {action.text}
        </Button>
      )}
    </div>
  )
}

export default EmptyState

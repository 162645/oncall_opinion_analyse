/**
 * 查询进度组件
 * 显示数据加载进度、已用时间、预计剩余时间
 * 支持中断操作
 */
import { useState, useEffect, useRef } from 'react'
import {
  Card,
  Typography,
  Button,
  Space,
  Progress,
  Tag,
  Spin,
} from '@douyinfe/semi-ui'
import {
  IconStop,
  IconRefresh,
  IconTickCircle,
  IconCrossCircleStroked,
} from '@douyinfe/semi-icons'

const { Text, Title } = Typography

export interface QueryProgressProps {
  // 查询状态
  status: 'idle' | 'connecting' | 'querying' | 'processing' | 'success' | 'error' | 'cancelled'

  // 进度百分比 (0-100)
  progress?: number

  // 当前步骤描述
  currentStep?: string

  // 总步骤数
  totalSteps?: number

  // 当前步骤索引
  currentStepIndex?: number

  // 错误信息
  errorMessage?: string

  // 中断回调
  onCancel?: () => void

  // 重试回调
  onRetry?: () => void

  // 开始时间
  startTime?: Date | null
}

// 步骤配置
const QUERY_STEPS = [
  { key: 'connecting', label: '连接数据库', estimatedSeconds: 2 },
  { key: 'validating', label: '验证参数', estimatedSeconds: 1 },
  { key: 'querying', label: '执行查询', estimatedSeconds: 10 },
  { key: 'processing', label: '处理数据', estimatedSeconds: 5 },
  { key: 'rendering', label: '渲染图表', estimatedSeconds: 2 },
]

function QueryProgress({
  status,
  progress = 0,
  currentStep = '',
  totalSteps = 5,
  currentStepIndex = 0,
  errorMessage = '',
  onCancel,
  onRetry,
  startTime,
}: QueryProgressProps) {
  const [elapsedTime, setElapsedTime] = useState(0)
  const [estimatedRemaining, setEstimatedRemaining] = useState(0)
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)

  // 计时器
  useEffect(() => {
    if (status === 'idle' || status === 'success' || status === 'error' || status === 'cancelled') {
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
        intervalRef.current = null
      }
      return
    }

    intervalRef.current = setInterval(() => {
      if (startTime) {
        const elapsed = Math.floor((Date.now() - startTime.getTime()) / 1000)
        setElapsedTime(elapsed)

        // 估算剩余时间
        if (progress > 0 && progress < 100) {
          const estimatedTotal = Math.floor(elapsed / (progress / 100))
          setEstimatedRemaining(Math.max(0, estimatedTotal - elapsed))
        }
      }
    }, 1000)

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
      }
    }
  }, [status, startTime, progress])

  // 格式化时间
  const formatTime = (seconds: number): string => {
    if (seconds < 60) {
      return `${seconds}秒`
    }
    const minutes = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${minutes}分${secs}秒`
  }

  // 获取状态配置
  const getStatusConfig = () => {
    switch (status) {
      case 'idle':
        return { color: 'grey' as const, text: '等待开始', icon: null }
      case 'connecting':
        return { color: 'blue' as const, text: '连接中...', icon: null }
      case 'querying':
        return { color: 'blue' as const, text: '查询中...', icon: null }
      case 'processing':
        return { color: 'blue' as const, text: '处理中...', icon: null }
      case 'success':
        return { color: 'green' as const, text: '完成', icon: <IconTickCircle style={{ color: 'var(--semi-color-success)' }} /> }
      case 'error':
        return { color: 'red' as const, text: '失败', icon: <IconCrossCircleStroked style={{ color: 'var(--semi-color-danger)' }} /> }
      case 'cancelled':
        return { color: 'orange' as const, text: '已取消', icon: <IconStop style={{ color: 'var(--semi-color-warning)' }} /> }
      default:
        return { color: 'grey' as const, text: '未知', icon: null }
    }
  }

  // 如果是空闲状态，不显示
  if (status === 'idle') {
    return null
  }

  const config = getStatusConfig()
  const isActive = status === 'connecting' || status === 'querying' || status === 'processing'

  return (
    <Card className="query-progress-card" style={{ marginBottom: 16, height: 'auto', minHeight: 0 }}>
      <div className="progress-header">
        <Space>
          {config.icon}
          <Title heading={6}>查询进度</Title>
          <Tag color={config.color}>{config.text}</Tag>
        </Space>
        {isActive && onCancel && (
          <Button
            type="danger"
            size="small"
            icon={<IconStop />}
            onClick={onCancel}
          >
            中断查询
          </Button>
        )}
        {status === 'error' && onRetry && (
          <Button
            type="primary"
            size="small"
            icon={<IconRefresh />}
            onClick={onRetry}
          >
            重试
          </Button>
        )}
      </div>

      {/* 进度条 */}
      <div className="progress-bar-container">
        <Progress
          percent={progress}
          stroke={config.color === 'red' ? 'var(--semi-color-danger)' : undefined}
          showInfo
          style={{ marginBottom: 8 }}
        />
      </div>

      {/* 当前步骤 */}
      {currentStep && (
        <div className="current-step">
          <Text type="tertiary">当前步骤: </Text>
          <Text strong>{currentStep}</Text>
          {totalSteps > 1 && (
            <Text type="tertiary"> ({currentStepIndex + 1}/{totalSteps})</Text>
          )}
        </div>
      )}

      {/* 时间信息 */}
      <div className="time-info">
        <Space spacing="loose">
          {elapsedTime > 0 && (
            <div className="time-item">
              <Text type="tertiary" size="small">已用时间</Text>
              <Text strong style={{ display: 'block' }}>{formatTime(elapsedTime)}</Text>
            </div>
          )}
          {isActive && estimatedRemaining > 0 && (
            <div className="time-item">
              <Text type="tertiary" size="small">预计剩余</Text>
              <Text strong style={{ display: 'block' }}>{formatTime(estimatedRemaining)}</Text>
            </div>
          )}
          {!isActive && elapsedTime > 0 && (
            <div className="time-item">
              <Text type="tertiary" size="small">总耗时</Text>
              <Text strong style={{ display: 'block' }}>{formatTime(elapsedTime)}</Text>
            </div>
          )}
        </Space>
      </div>

      {/* 错误信息 */}
      {status === 'error' && errorMessage && (
        <div className="error-message" style={{ marginTop: 12 }}>
          <Text type="danger">{errorMessage}</Text>
        </div>
      )}

      {/* 步骤列表 */}
      {isActive && totalSteps > 1 && (
        <div className="steps-list query-progress-steps" style={{ marginTop: 16 }}>
          {QUERY_STEPS.map((step, index) => {
            const isCompleted = index < currentStepIndex
            const isCurrent = index === currentStepIndex
            return (
              <div
                key={step.key}
                className={`step-item ${isCompleted ? 'completed' : ''} ${isCurrent ? 'current' : ''}`}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  padding: '4px 0',
                  opacity: isCompleted || isCurrent ? 1 : 0.5,
                }}
              >
                <Tag
                  size="small"
                  color={isCompleted ? 'green' : isCurrent ? 'blue' : 'grey'}
                    style={{ marginRight: 8, width: 24, minWidth: 24, justifyContent: 'center', padding: 0 }}
                >
                  {isCompleted ? '✓' : index + 1}
                </Tag>
                <Text>{step.label}</Text>
                {isCurrent && <Spin size="small" style={{ marginLeft: 8 }} />}
              </div>
            )
          })}
        </div>
      )}
    </Card>
  )
}

export default QueryProgress

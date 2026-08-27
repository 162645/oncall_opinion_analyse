import { useState, useEffect } from 'react'
import { Collapse, Typography, Space, Spin, Tag, Timeline, Button } from '@douyinfe/semi-ui'
import {
  IconBulb,
  IconChevronDown,
  IconChevronUp,
  IconCopy,
  IconTickCircle,
} from '@douyinfe/semi-icons'
import './ThinkingDisplay.css'

const { Text } = Typography

export interface ThinkingStep {
  id: string
  content: string
  type?: 'reasoning' | 'analysis' | 'decision' | 'observation' | 'action'
  timestamp?: string
  duration_ms?: number
}

interface ThinkingDisplayProps {
  steps: ThinkingStep[]
  isThinking?: boolean
  title?: string
  collapsible?: boolean
  defaultExpanded?: boolean
  showTimeline?: boolean
  onStepClick?: (step: ThinkingStep) => void
}

const getStepTypeConfig = (type?: ThinkingStep['type']) => {
  switch (type) {
    case 'reasoning':
      return { color: 'blue' as const, label: '推理', icon: '💭' }
    case 'analysis':
      return { color: 'purple' as const, label: '分析', icon: '🔍' }
    case 'decision':
      return { color: 'green' as const, label: '决策', icon: '✅' }
    case 'observation':
      return { color: 'cyan' as const, label: '观察', icon: '👁' }
    case 'action':
      return { color: 'orange' as const, label: '行动', icon: '⚡' }
    default:
      return { color: 'grey' as const, label: '思考', icon: '🧠' }
  }
}

const formatTimestamp = (timestamp?: string) => {
  if (!timestamp) return ''
  const date = new Date(timestamp)
  return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

const formatDuration = (ms?: number) => {
  if (!ms) return ''
  if (ms < 1000) return `${ms}ms`
  return `${(ms / 1000).toFixed(2)}s`
}

export function ThinkingDisplay({
  steps,
  isThinking = false,
  title = '思考过程',
  collapsible = true,
  defaultExpanded = false,
  showTimeline = true,
  onStepClick,
}: ThinkingDisplayProps) {
  const [expandedSteps, setExpandedSteps] = useState<Set<string>>(new Set())
  const [copied, setCopied] = useState<string | null>(null)

  useEffect(() => {
    // 自动展开最新的步骤
    if (steps.length > 0 && isThinking) {
      const lastStep = steps[steps.length - 1]
      if (lastStep && lastStep.id) {
        setExpandedSteps(prev => new Set([...prev, lastStep.id]))
      }
    }
  }, [steps, isThinking])

  if (!steps || steps.length === 0) {
    if (isThinking) {
      return (
        <div className="thinking-display thinking-active">
          <div className="thinking-header">
            <Space>
              <Spin size="small" />
              <IconBulb style={{ color: 'var(--semi-color-primary)' }} />
              <Text strong>{title}</Text>
            </Space>
          </div>
          <div className="thinking-placeholder">
            <Text type="tertiary">正在思考中...</Text>
          </div>
        </div>
      )
    }
    return null
  }

  const toggleStep = (stepId: string) => {
    setExpandedSteps(prev => {
      const next = new Set(prev)
      if (next.has(stepId)) {
        next.delete(stepId)
      } else {
        next.add(stepId)
      }
      return next
    })
  }

  const copyAllSteps = async () => {
    const text = steps.map(s => s.content).join('\n\n')
    await navigator.clipboard.writeText(text)
    setCopied('all')
    setTimeout(() => setCopied(null), 2000)
  }

  const copyStep = async (step: ThinkingStep) => {
    await navigator.clipboard.writeText(step.content)
    setCopied(step.id)
    setTimeout(() => setCopied(null), 2000)
  }

  const totalDuration = steps.reduce((sum, s) => sum + (s.duration_ms || 0), 0)

  const headerContent = (
    <Space className="thinking-header-content">
      <IconBulb style={{ color: 'var(--semi-color-primary)' }} />
      <Text strong>{title}</Text>
      <Tag size="small">{steps.length} 步</Tag>
      {isThinking && (
        <Tag color="blue" size="small">
          <Spin size="small" /> 进行中
        </Tag>
      )}
      {totalDuration > 0 && (
        <Text type="tertiary" size="small">
          总耗时: {formatDuration(totalDuration)}
        </Text>
      )}
    </Space>
  )

  const renderTimelineMode = () => (
    <Timeline className="thinking-timeline">
      {steps.map((step, index) => {
        const config = getStepTypeConfig(step.type)
        const isExpanded = expandedSteps.has(step.id)
        const isLastStep = index === steps.length - 1

        return (
          <Timeline.Item
            key={step.id}
            color={config.color}
            dot={
              <span className="timeline-dot">
                {isLastStep && isThinking ? <Spin size="small" /> : config.icon}
              </span>
            }
          >
            <div
              className={`thinking-step ${isExpanded ? 'expanded' : ''} ${onStepClick ? 'clickable' : ''}`}
              onClick={() => onStepClick?.(step)}
            >
              <div className="thinking-step-header">
                <Space>
                  <Tag size="small" color={config.color}>{config.label}</Tag>
                  {step.timestamp && (
                    <Text type="tertiary" size="small">{formatTimestamp(step.timestamp)}</Text>
                  )}
                  {step.duration_ms && (
                    <Text type="tertiary" size="small">⏱ {formatDuration(step.duration_ms)}</Text>
                  )}
                </Space>
                <Space>
                  <Button
                    size="small"
                    icon={copied === step.id ? <IconTickCircle /> : <IconCopy />}
                    onClick={(e) => {
                      e.stopPropagation()
                      copyStep(step)
                    }}
                  >
                    {copied === step.id ? '已复制' : '复制'}
                  </Button>
                  <Button
                    size="small"
                    icon={isExpanded ? <IconChevronUp /> : <IconChevronDown />}
                    onClick={(e) => {
                      e.stopPropagation()
                      toggleStep(step.id)
                    }}
                  />
                </Space>
              </div>

              <div className="thinking-step-content">
                <Text>{step.content}</Text>
              </div>
            </div>
          </Timeline.Item>
        )
      })}
    </Timeline>
  )

  const renderSimpleMode = () => (
    <div className="thinking-steps-simple">
      {steps.map((step, index) => {
        const config = getStepTypeConfig(step.type)
        const isLastStep = index === steps.length - 1

        return (
          <div key={step.id} className="thinking-step-simple">
            <div className="thinking-step-simple-header">
              <Space>
                <span className="step-icon">
                  {isLastStep && isThinking ? <Spin size="small" /> : config.icon}
                </span>
                <Tag size="small" color={config.color}>{config.label}</Tag>
              </Space>
              {step.duration_ms && (
                <Text type="tertiary" size="small">{formatDuration(step.duration_ms)}</Text>
              )}
            </div>
            <div className="thinking-step-simple-content">
              <Text>{step.content}</Text>
            </div>
          </div>
        )
      })}
    </div>
  )

  const content = (
    <div className="thinking-content">
      <div className="thinking-actions">
        <Button
          size="small"
          icon={copied === 'all' ? <IconTickCircle /> : <IconCopy />}
          onClick={copyAllSteps}
        >
          {copied === 'all' ? '已复制全部' : '复制全部'}
        </Button>
      </div>

      {showTimeline ? renderTimelineMode() : renderSimpleMode()}

      {isThinking && (
        <div className="thinking-indicator">
          <Spin size="small" />
          <Text type="tertiary" size="small">思考中...</Text>
        </div>
      )}
    </div>
  )

  if (!collapsible) {
    return (
      <div className={`thinking-display ${isThinking ? 'thinking-active' : ''}`}>
        {headerContent}
        {content}
      </div>
    )
  }

  return (
    <div className={`thinking-display ${isThinking ? 'thinking-active' : ''}`}>
      <Collapse accordion defaultActiveKey={defaultExpanded ? 'thinking' : undefined}>
        <Collapse.Panel itemKey="thinking" header={headerContent}>
          {content}
        </Collapse.Panel>
      </Collapse>
    </div>
  )
}

export default ThinkingDisplay

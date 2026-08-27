/**
 * 增强版思考过程展示组件
 * 支持长时间思考（10+ 分钟）和详细的时间消耗分解
 */
import { useState, useEffect, useMemo } from 'react'
import {
  Collapse,
  Typography,
  Space,
  Spin,
  Tag,
  Timeline,
  Button,
  Progress,
  Tooltip,
  Tabs,
  TabPane,
} from '@douyinfe/semi-ui'
import {
  IconBulb,
  IconChevronDown,
  IconChevronUp,
  IconCopy,
  IconTickCircle,
  IconClock,
  IconStar,
} from '@douyinfe/semi-icons'
import './ThinkingDisplayEnhanced.css'

const { Text } = Typography

export interface ThinkingStepEnhanced {
  id: string
  content: string
  type?: 'reasoning' | 'analysis' | 'decision' | 'observation' | 'action' | 'search' | 'calculation'
  timestamp?: string
  duration_ms?: number
  tokens_used?: number
  subSteps?: ThinkingStepEnhanced[]
}

interface TimeBreakdown {
  category: string
  duration_ms: number
  percentage: number
  color: string
  icon: React.ReactNode
  description: string
}

interface ThinkingDisplayEnhancedProps {
  steps: ThinkingStepEnhanced[]
  isThinking?: boolean
  title?: string
  collapsible?: boolean
  defaultExpanded?: boolean
  showTimeBreakdown?: boolean
  totalDuration?: number
  startTime?: Date
  onStepClick?: (step: ThinkingStepEnhanced) => void
}

const getStepTypeConfig = (type?: ThinkingStepEnhanced['type']) => {
  switch (type) {
    case 'reasoning':
      return { color: 'blue' as const, label: '推理', icon: '💭', description: '逻辑推理和假设验证' }
    case 'analysis':
      return { color: 'purple' as const, label: '分析', icon: '🔍', description: '数据分析和模式识别' }
    case 'decision':
      return { color: 'green' as const, label: '决策', icon: '✅', description: '做出判断和选择' }
    case 'observation':
      return { color: 'cyan' as const, label: '观察', icon: '👁', description: '收集信息和观察现象' }
    case 'action':
      return { color: 'orange' as const, label: '行动', icon: '⚡', description: '执行操作和调用工具' }
    case 'search':
      return { color: 'teal' as const, label: '检索', icon: '🔎', description: '搜索知识和文档' }
    case 'calculation':
      return { color: 'pink' as const, label: '计算', icon: '🧮', description: '数值计算和统计' }
    default:
      return { color: 'grey' as const, label: '思考', icon: '🧠', description: '通用思考过程' }
  }
}

const formatDuration = (ms?: number): string => {
  if (!ms) return '0ms'
  if (ms < 1000) return `${ms}ms`
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`
  const minutes = Math.floor(ms / 60000)
  const seconds = Math.round((ms % 60000) / 1000)
  return `${minutes}m ${seconds}s`
}

const formatDurationDetailed = (ms: number): { value: string; unit: string } => {
  if (ms < 1000) return { value: `${ms}`, unit: 'ms' }
  if (ms < 60000) return { value: (ms / 1000).toFixed(2), unit: '秒' }
  if (ms < 3600000) {
    const minutes = Math.floor(ms / 60000)
    const seconds = Math.round((ms % 60000) / 1000)
    return { value: `${minutes}分${seconds}秒`, unit: '' }
  }
  const hours = Math.floor(ms / 3600000)
  const minutes = Math.round((ms % 3600000) / 60000)
  return { value: `${hours}小时${minutes}分`, unit: '' }
}

function ThinkingDisplayEnhanced({
  steps,
  isThinking = false,
  title = '思考过程',
  collapsible = true,
  defaultExpanded = false,
  showTimeBreakdown = true,
  totalDuration,
  startTime,
  onStepClick,
}: ThinkingDisplayEnhancedProps) {
  const [expandedSteps, setExpandedSteps] = useState<Set<string>>(new Set())
  const [copied, setCopied] = useState<string | null>(null)
  const [elapsedTime, setElapsedTime] = useState(0)
  const [activeTab, setActiveTab] = useState<string>('timeline')

  // 计算总时长
  const calculatedTotalDuration = useMemo(() => {
    if (totalDuration) return totalDuration
    return steps.reduce((sum, s) => sum + (s.duration_ms || 0), 0)
  }, [steps, totalDuration])

  // 实时计时
  useEffect(() => {
    if (isThinking && startTime) {
      const interval = setInterval(() => {
        setElapsedTime(Date.now() - startTime.getTime())
      }, 100)
      return () => clearInterval(interval)
    }
  }, [isThinking, startTime])

  // 时间分解
  const timeBreakdown: TimeBreakdown[] = useMemo(() => {
    const categoryTimes: Record<string, number> = {}

    steps.forEach(step => {
      const config = getStepTypeConfig(step.type)
      const category = config.label
      categoryTimes[category] = (categoryTimes[category] || 0) + (step.duration_ms || 0)
    })

    const total = Object.values(categoryTimes).reduce((a, b) => a + b, 0)

    return Object.entries(categoryTimes)
      .map(([category, duration]) => {
        const config = Object.values(getStepTypeConfig).find(c => c.label === category) || getStepTypeConfig()
        return {
          category,
          duration_ms: duration,
          percentage: total > 0 ? (duration / total) * 100 : 0,
          color: config.color,
          icon: config.icon,
          description: config.description,
        }
      })
      .sort((a, b) => b.duration_ms - a.duration_ms)
  }, [steps])

  // Token 统计
  const tokenStats = useMemo(() => {
    const total = steps.reduce((sum, s) => sum + (s.tokens_used || 0), 0)
    return {
      total,
      average: steps.length > 0 ? Math.round(total / steps.length) : 0,
    }
  }, [steps])

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
    const text = steps.map(s => `[${getStepTypeConfig(s.type).label}] ${s.content}`).join('\n\n')
    await navigator.clipboard.writeText(text)
    setCopied('all')
    setTimeout(() => setCopied(null), 2000)
  }

  const copyStep = async (step: ThinkingStepEnhanced) => {
    await navigator.clipboard.writeText(step.content)
    setCopied(step.id)
    setTimeout(() => setCopied(null), 2000)
  }

  // 渲染时间分解视图
  const renderTimeBreakdown = () => (
    <div className="time-breakdown">
      <div className="breakdown-header">
        <Space>
          <IconClock style={{ color: 'var(--semi-color-primary)' }} />
          <Text strong>时间消耗分解</Text>
        </Space>
        <Text type="tertiary">
          总耗时: {formatDuration(calculatedTotalDuration)}
        </Text>
      </div>

      {/* 总览进度条 */}
      <div className="breakdown-overview">
        <div className="progress-bar-container">
          {timeBreakdown.map((item, index) => (
            <div
              key={index}
              className="progress-bar-segment"
              style={{
                width: `${item.percentage}%`,
                backgroundColor: `var(--semi-color-${item.color})`,
              }}
            />
          ))}
        </div>
        <div className="progress-legend">
          {timeBreakdown.slice(0, 4).map((item, index) => (
            <Space key={index} style={{ marginRight: 16 }}>
              <div
                className="legend-dot"
                style={{ backgroundColor: `var(--semi-color-${item.color})` }}
              />
              <Text type="tertiary" size="small">{item.category}</Text>
            </Space>
          ))}
        </div>
      </div>

      {/* 详细列表 */}
      <div className="breakdown-list">
        {timeBreakdown.map((item, index) => (
          <div key={index} className="breakdown-item">
            <div className="breakdown-item-header">
              <Space>
                <span className="breakdown-icon">{item.icon}</span>
                <Text strong>{item.category}</Text>
                <Tooltip content={item.description}>
                  <Text type="tertiary" size="small" style={{ cursor: 'help' }}>
                    (?)
                  </Text>
                </Tooltip>
              </Space>
              <Space>
                <Text strong>{formatDuration(item.duration_ms)}</Text>
                <Tag size="small">{item.percentage.toFixed(1)}%</Tag>
              </Space>
            </div>
            <Progress
              percent={item.percentage}
              showInfo={false}
              stroke={`var(--semi-color-${item.color})`}
              size="small"
            />
          </div>
        ))}
      </div>

      {/* Token 统计 */}
      {tokenStats.total > 0 && (
        <div className="token-stats">
          <Space>
            <IconStar style={{ color: 'var(--semi-color-warning)' }} />
            <Text type="tertiary">Token 消耗:</Text>
            <Text strong>{tokenStats.total.toLocaleString()}</Text>
            <Text type="tertiary">|</Text>
            <Text type="tertiary">平均每步: {tokenStats.average}</Text>
          </Space>
        </div>
      )}
    </div>
  )

  // 渲染时间线视图
  const renderTimeline = () => (
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
                  {step.duration_ms && (
                    <Text type="tertiary" size="small">
                      ⏱ {formatDuration(step.duration_ms)}
                    </Text>
                  )}
                  {step.tokens_used && (
                    <Tag size="small" color="grey">{step.tokens_used} tokens</Tag>
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

              {/* 子步骤 */}
              {step.subSteps && step.subSteps.length > 0 && (
                <div className="sub-steps">
                  {step.subSteps.map((subStep, subIndex) => {
                    const subConfig = getStepTypeConfig(subStep.type)
                    return (
                      <div key={subStep.id || subIndex} className="sub-step">
                        <Space>
                          <span>{subConfig.icon}</span>
                          <Tag size="small" color={subConfig.color}>{subConfig.label}</Tag>
                          <Text size="small">{subStep.content}</Text>
                        </Space>
                      </div>
                    )
                  })}
                </div>
              )}
            </div>
          </Timeline.Item>
        )
      })}
    </Timeline>
  )

  // 实时计时显示
  const renderElapsedTime = () => {
    if (!isThinking || !startTime) return null

    const displayTime = elapsedTime || 0
    const duration = formatDurationDetailed(displayTime)

    return (
      <div className="elapsed-time-display">
        <Spin size="small" />
        <Text type="tertiary">已思考</Text>
        <Text strong style={{ fontSize: 18, color: 'var(--semi-color-primary)' }}>
          {duration.value}
        </Text>
        <Text type="tertiary">{duration.unit}</Text>
      </div>
    )
  }

  if (!steps || steps.length === 0) {
    if (isThinking) {
      return (
        <div className="thinking-display-enhanced thinking-active">
          <div className="thinking-header">
            <Space>
              <Spin size="small" />
              <IconBulb style={{ color: 'var(--semi-color-primary)' }} />
              <Text strong>{title}</Text>
            </Space>
            {renderElapsedTime()}
          </div>
          <div className="thinking-placeholder">
            <div className="thinking-animation">
              <div className="pulse-ring" />
              <IconBulb size="large" style={{ color: 'var(--semi-color-primary)' }} />
            </div>
            <Text type="tertiary">正在进行深度思考...</Text>
            <Text type="tertiary" size="small">这可能需要几分钟时间，请耐心等待</Text>
          </div>
        </div>
      )
    }
    return null
  }

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
      <Text type="tertiary" size="small">
        总耗时: {formatDuration(calculatedTotalDuration)}
      </Text>
    </Space>
  )

  const content = (
    <div className="thinking-content-enhanced">
      {/* 实时计时 */}
      {renderElapsedTime()}

      {/* 操作按钮 */}
      <div className="thinking-actions">
        <Space>
          <Button
            size="small"
            icon={copied === 'all' ? <IconTickCircle /> : <IconCopy />}
            onClick={copyAllSteps}
          >
            {copied === 'all' ? '已复制全部' : '复制全部'}
          </Button>
        </Space>
      </div>

      {/* 标签页切换 */}
      {showTimeBreakdown && timeBreakdown.length > 1 ? (
        <Tabs
          activeKey={activeTab}
          onChange={setActiveTab}
          type="line"
          size="small"
        >
          <TabPane tab="时间线" itemKey="timeline">
            {renderTimeline()}
          </TabPane>
          <TabPane tab="时间分解" itemKey="breakdown">
            {renderTimeBreakdown()}
          </TabPane>
        </Tabs>
      ) : (
        renderTimeline()
      )}

      {/* 思考中指示器 */}
      {isThinking && (
        <div className="thinking-indicator">
          <Spin size="small" />
          <Text type="tertiary" size="small">思考中...</Text>
          {renderElapsedTime()}
        </div>
      )}
    </div>
  )

  if (!collapsible) {
    return (
      <div className={`thinking-display-enhanced ${isThinking ? 'thinking-active' : ''}`}>
        {headerContent}
        {content}
      </div>
    )
  }

  return (
    <div className={`thinking-display-enhanced ${isThinking ? 'thinking-active' : ''}`}>
      <Collapse accordion defaultActiveKey={defaultExpanded ? 'thinking' : undefined}>
        <Collapse.Panel itemKey="thinking" header={headerContent}>
          {content}
        </Collapse.Panel>
      </Collapse>
    </div>
  )
}

export default ThinkingDisplayEnhanced

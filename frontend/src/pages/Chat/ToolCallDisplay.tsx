import { Collapse, Tag, Typography, Space, Spin, Tooltip, Badge } from '@douyinfe/semi-ui'
import {
  IconTickCircle,
  IconCrossCircleStroked,
  IconLoading,
  IconBolt,
  IconInfoCircle,
} from '@douyinfe/semi-icons'
import './ToolCallDisplay.css'

const { Text } = Typography

export interface ToolCall {
  id: string
  name: string
  description?: string
  parameters: Record<string, any>
  status: 'pending' | 'running' | 'success' | 'error'
  result?: any
  duration_ms?: number
  error?: string
  timestamp?: string
}

interface ToolCallDisplayProps {
  toolCalls: ToolCall[]
  title?: string
  collapsible?: boolean
  defaultExpanded?: boolean
}

const getStatusConfig = (status: ToolCall['status']) => {
  switch (status) {
    case 'pending':
      return { color: 'grey' as const, icon: <IconInfoCircle />, text: '等待中' }
    case 'running':
      return { color: 'blue' as const, icon: <IconLoading />, text: '执行中' }
    case 'success':
      return { color: 'green' as const, icon: <IconTickCircle />, text: '成功' }
    case 'error':
      return { color: 'red' as const, icon: <IconCrossCircleStroked />, text: '失败' }
    default:
      return { color: 'grey' as const, icon: <IconInfoCircle />, text: status }
  }
}

const formatDuration = (ms?: number) => {
  if (!ms) return ''
  if (ms < 1000) return `${ms}ms`
  return `${(ms / 1000).toFixed(2)}s`
}

const formatParameterValue = (value: any): string => {
  if (value === null || value === undefined) return 'null'
  if (typeof value === 'string') return value.length > 50 ? value.substring(0, 50) + '...' : value
  if (typeof value === 'object') return JSON.stringify(value, null, 2)
  return String(value)
}

const renderParameters = (parameters: Record<string, any>) => {
  if (!parameters || Object.keys(parameters).length === 0) {
    return <Text type="tertiary">无参数</Text>
  }

  return (
    <div className="tool-params">
      {Object.entries(parameters).map(([key, value]) => (
        <div key={key} className="tool-param-item">
          <Text strong className="tool-param-key">{key}:</Text>
          <pre className="tool-param-value">{formatParameterValue(value)}</pre>
        </div>
      ))}
    </div>
  )
}

const renderResult = (result: any, status: ToolCall['status']) => {
  if (!result) return null

  if (status === 'error') {
    return (
      <div className="tool-result tool-result-error">
        <Text type="danger">错误信息:</Text>
        <pre className="tool-result-content">{typeof result === 'string' ? result : JSON.stringify(result, null, 2)}</pre>
      </div>
    )
  }

  // 处理不同类型的结果
  if (typeof result === 'object') {
    // 检查是否是数据表格
    if (result.data && Array.isArray(result.data)) {
      return (
        <div className="tool-result tool-result-data">
          <Text type="success">返回 {result.data.length} 条数据</Text>
          <pre className="tool-result-content">{JSON.stringify(result.data.slice(0, 5), null, 2)}</pre>
          {result.data.length > 5 && (
            <Text type="tertiary" size="small">... 还有 {result.data.length - 5} 条</Text>
          )}
        </div>
      )
    }

    // 检查是否是统计结果
    if (result.statistics || result.stats) {
      const stats = result.statistics || result.stats
      return (
        <div className="tool-result tool-result-stats">
          <Text type="success">统计结果:</Text>
          <div className="stats-grid">
            {Object.entries(stats).map(([key, value]) => (
              <div key={key} className="stats-item">
                <Text type="tertiary" size="small">{key}</Text>
                <Text strong>{typeof value === 'number' ? value.toLocaleString() : String(value)}</Text>
              </div>
            ))}
          </div>
        </div>
      )
    }

    // 默认 JSON 展示
    return (
      <div className="tool-result">
        <pre className="tool-result-content">{JSON.stringify(result, null, 2)}</pre>
      </div>
    )
  }

  return (
    <div className="tool-result">
      <pre className="tool-result-content">{String(result)}</pre>
    </div>
  )
}

export function ToolCallDisplay({
  toolCalls,
  title = '工具调用',
  collapsible = true,
  defaultExpanded = false,
}: ToolCallDisplayProps) {
  if (!toolCalls || toolCalls.length === 0) {
    return null
  }

  // 统计信息
  const successCount = toolCalls.filter(t => t.status === 'success').length
  const errorCount = toolCalls.filter(t => t.status === 'error').length
  const runningCount = toolCalls.filter(t => t.status === 'running').length
  const totalDuration = toolCalls.reduce((sum, t) => sum + (t.duration_ms || 0), 0)

  const headerContent = (
    <Space className="tool-call-header">
      <IconBolt style={{ color: 'var(--semi-color-primary)' }} />
      <Text strong>{title}</Text>
      <Badge count={toolCalls.length} type="primary" />
      {runningCount > 0 && (
        <Tag color="blue" size="small">
          <Spin size="small" /> {runningCount} 执行中
        </Tag>
      )}
      {successCount > 0 && (
        <Tag color="green" size="small">{successCount} 成功</Tag>
      )}
      {errorCount > 0 && (
        <Tag color="red" size="small">{errorCount} 失败</Tag>
      )}
      {totalDuration > 0 && (
        <Text type="tertiary" size="small">
          总耗时: {formatDuration(totalDuration)}
        </Text>
      )}
    </Space>
  )

  const content = (
    <div className="tool-calls-list">
      {toolCalls.map((call, index) => {
        const config = getStatusConfig(call.status)

        return (
          <div key={call.id || index} className={`tool-call-item tool-call-${call.status}`}>
            <div className="tool-call-item-header">
              <Space>
                <span className="tool-status-icon">{config.icon}</span>
                <Text strong>{call.name}</Text>
                <Tag size="small" color={config.color}>{config.text}</Tag>
                {call.duration_ms && (
                  <Tooltip content="执行耗时">
                    <Text type="tertiary" size="small">⏱ {formatDuration(call.duration_ms)}</Text>
                  </Tooltip>
                )}
              </Space>
            </div>

            {call.description && (
              <div className="tool-call-description">
                <Text type="tertiary" size="small">{call.description}</Text>
              </div>
            )}

            <Collapse accordion defaultActiveKey={defaultExpanded ? 'params' : undefined}>
              <Collapse.Panel itemKey="params" header="参数">
                {renderParameters(call.parameters)}
              </Collapse.Panel>

              {(call.result || call.error) && (
                <Collapse.Panel
                  itemKey="result"
                  header={call.status === 'error' ? '错误信息' : '执行结果'}
                >
                  {renderResult(call.error || call.result, call.status)}
                </Collapse.Panel>
              )}
            </Collapse>
          </div>
        )
      })}
    </div>
  )

  if (!collapsible) {
    return (
      <div className="tool-call-display">
        {headerContent}
        {content}
      </div>
    )
  }

  return (
    <div className="tool-call-display">
      <Collapse accordion defaultActiveKey={defaultExpanded ? 'tools' : undefined}>
        <Collapse.Panel itemKey="tools" header={headerContent}>
          {content}
        </Collapse.Panel>
      </Collapse>
    </div>
  )
}

export default ToolCallDisplay

import { useState, useRef, useEffect, useCallback } from 'react'
import {
  Input,
  Button,
  Space,
  Typography,
  Select,
  Tag,
  Empty,
  Spin,
  List,
  Modal,
  Toast,
  Tooltip,
  Dropdown,
  Table,
  Card,
  Descriptions,
} from '@douyinfe/semi-ui'
import {
  IconSend,
  IconHistory,
  IconClear,
  IconPlus,
  IconDelete,
  IconCommentStroked,
  IconStop,
  IconClock,
  IconLink,
} from '@douyinfe/semi-icons'
import type { BasicSelectValue } from '@douyinfe/semi-ui/lib/es/select'
import ReactECharts from 'echarts-for-react'
import type { EChartsOption } from 'echarts'
import { ToolCallDisplay, type ToolCall } from './ToolCallDisplay'
import ThinkingDisplayEnhanced, { type ThinkingStepEnhanced } from './ThinkingDisplayEnhanced'
import MarkdownRenderer from '../../components/MarkdownRenderer'
import ThinkingProgress from './ThinkingProgress'
import './Chat.css'
import type { EvidenceItem } from '../../api/chat'

const { Title, Text } = Typography

// 网络可视化展示组件
function NetworkVizDisplay({ type, data, region }: { type: string; data: any; region: string }) {
  if (!data) return null

  // 末端节点分析 - 支持数组和字典格式
  if (type === 'trace_terminal_analysis') {
    const terminals = Array.isArray(data) ? data : (data.terminals || [])
    if (terminals.length === 0) return null
    const columns = [
      { title: '末端节点', dataIndex: 'terminal', render: (t: string) => <Text style={{ fontFamily: 'monospace', fontSize: 11 }}>{t}</Text> },
      { title: '路径数', dataIndex: 'trace_count', width: 80, render: (c: number) => <Tag color="blue">{c?.toLocaleString()}</Tag> },
      { title: 'Prefix24数', dataIndex: 'prefix24_count', width: 90 },
    ]
    return (
      <Card style={{ marginTop: 8 }}>
        <Text type="tertiary" size="small">末端节点分析 - 共 {terminals.length} 个</Text>
        <Table dataSource={terminals.slice(0, 10)} columns={columns} pagination={false} size="small" rowKey="terminal" />
      </Card>
    )
  }

  // 路径分析
  if (type === 'trace_path_analysis' && data?.paths) {
    const columns = [
      { title: '路径', dataIndex: 'path', render: (t: string) => <Text style={{ fontFamily: 'monospace', fontSize: 11 }}>{t?.slice(0, 50)}...</Text> },
      { title: '路径数', dataIndex: 'occurrence_count', width: 80, render: (c: number) => <Tag color="blue">{c?.toLocaleString()}</Tag> },
    ]
    return (
      <Card style={{ marginTop: 8 }}>
        <Text type="tertiary" size="small">路径分析 - 共 {data.paths.length} 条</Text>
        <Table dataSource={data.paths.slice(0, 10)} columns={columns} pagination={false} size="small" rowKey="path" />
      </Card>
    )
  }

  // 地区概览
  if (type === 'region_overview') {
    const pingStats = data.ping_stats || {}
    const traceStats = data.trace_stats || []
    return (
      <Card style={{ marginTop: 8 }}>
        <Descriptions>
          <Descriptions.Item itemKey="平均 RTT">{pingStats.mean_rtt?.toFixed(2)} ms</Descriptions.Item>
          <Descriptions.Item itemKey="中位数 RTT">{pingStats.median_rtt?.toFixed(2)} ms</Descriptions.Item>
          <Descriptions.Item itemKey="样本数">{pingStats.total_samples?.toLocaleString()}</Descriptions.Item>
        </Descriptions>
        {traceStats.length > 0 && (
          <div style={{ marginTop: 12 }}>
            <Text type="tertiary" size="small">Top 路径</Text>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4, marginTop: 4 }}>
              {traceStats.slice(0, 5).map((item: any, idx: number) => (
                <Tag key={idx} color="cyan" size="small">{item.path?.slice(0, 20)}... ({item.occurrence_count})</Tag>
              ))}
            </div>
          </div>
        )}
        <div style={{ marginTop: 12 }}>
          <Button size="small" icon={<IconLink />} onClick={() => window.open(`/visualization?region=${region}`, '_blank')}>
            查看完整可视化
          </Button>
        </div>
      </Card>
    )
  }

  // Ping 统计
  if (type === 'ping_overall') {
    const percentiles = data.percentiles || {}
    return (
      <Card style={{ marginTop: 8 }}>
        <Descriptions>
          <Descriptions.Item itemKey="平均 RTT">{data.mean_rtt?.toFixed(2)} ms</Descriptions.Item>
          <Descriptions.Item itemKey="中位数 RTT">{data.median_rtt?.toFixed(2)} ms</Descriptions.Item>
          <Descriptions.Item itemKey="P90">{percentiles.p90?.toFixed(2)} ms</Descriptions.Item>
          <Descriptions.Item itemKey="P95">{percentiles.p95?.toFixed(2)} ms</Descriptions.Item>
          <Descriptions.Item itemKey="样本数">{data.total_samples?.toLocaleString()}</Descriptions.Item>
        </Descriptions>
      </Card>
    )
  }

  // 默认：显示数据类型
  return null
}

// ECharts 图表颜色
function getChartColor(index: number): string {
  const colors = ['#5B8FF9', '#5AD8A6', '#F6BD16', '#E86452', '#6DC8EC', '#945FB9', '#FF9D4D', '#61DDAA', '#73C0DE', '#3BA272']
  return colors[index % colors.length]
}

// ECharts 交互式图表组件
function EChartsDisplay({ chartData, height = 350 }: { chartData: ChartData; height?: number }) {
  if (!chartData) return null

  // 如果有 base64 图片，显示图片
  if (chartData.base64) {
    return (
      <div className="chart-image" style={{ marginTop: 12 }}>
        <img
          src={`data:image/png;base64,${chartData.base64}`}
          alt={chartData.title || 'Chart'}
          style={{
            maxWidth: '100%',
            borderRadius: 8,
            border: '1px solid var(--semi-color-border)',
            boxShadow: '0 2px 8px rgba(0,0,0,0.08)',
          }}
        />
      </div>
    )
  }

  // 如果有 xAxis 和 series，使用 ECharts 渲染
  if (chartData.x_axis && chartData.series) {
    const option: EChartsOption = {
      title: {
        text: chartData.title || '',
        left: 'center',
        textStyle: { fontSize: 14, fontWeight: 'bold' },
      },
      tooltip: {
        trigger: 'axis',
        confine: true,
      },
      legend: {
        bottom: 5,
        type: 'scroll',
      },
      grid: {
        left: '3%',
        right: '4%',
        bottom: '15%',
        top: '12%',
        containLabel: true,
      },
      xAxis: {
        type: 'category',
        data: chartData.x_axis,
        axisLabel: {
          rotate: chartData.x_axis.length > 8 ? 35 : 0,
          interval: 'auto',
          fontSize: 10,
        },
      },
      yAxis: {
        type: 'value',
        name: chartData.y_axis_name || '',
      },
      series: chartData.series.map((s, i) => ({
        name: s.name,
        type: chartData.chart_type === 'line' ? 'line' : 'bar',
        smooth: true,
        data: s.data,
        itemStyle: { color: getChartColor(i) },
        areaStyle: chartData.chart_type === 'line' ? { opacity: 0.1 } : undefined,
        barMaxWidth: 50,
      })),
    }

    return (
      <Card style={{ marginTop: 12 }} bodyStyle={{ padding: 12 }}>
        <ReactECharts option={option} style={{ height }} notMerge={true} />
        {chartData.summary && (
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginTop: 8 }}>
            {chartData.summary.data_points && <Tag color="blue">数据点: {chartData.summary.data_points}</Tag>}
            {chartData.summary.time_range && <Tag color="green">{chartData.summary.time_range}</Tag>}
          </div>
        )}
      </Card>
    )
  }

  return null
}

const API_BASE = import.meta.env.VITE_API_BASE || ''

interface ChartData {
  charts?: ChartData[]
  base64?: string
  html?: string
  title?: string
  description?: string
  summary?: {
    data_points: number
    time_range: string
    metric: string
    chart_type: string
    lowest_asgeo?: string
    lowest_rtt?: number
  }
  // 结构化网络可视化数据
  structured?: {
    type: string  // trace_terminal_analysis, trace_path_analysis, ping_trend, etc.
    data: any
    region: string
  }
  // 图表数据
  chart_type?: string
  x_axis?: string[]
  y_axis_name?: string
  series?: Array<{
    name: string
    data: (number | null)[]
  }>
}

interface TraceStep {
  step_id: number
  step_type: string
  agent_name: string
  action: string
  reasoning?: string
  duration_ms: number
  status: string
  tool_name?: string
  tool_parameters?: Record<string, any>
  tool_result?: any
  tool_result_summary?: string
  thinking_content?: string
  thinking_type?: 'reasoning' | 'analysis' | 'decision' | 'observation' | 'action'
  tokens_used?: number
  tokens?: {
    prompt_tokens: number
    completion_tokens: number
    total_tokens: number
  }
}

interface Message {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp: string
  trace?: TraceStep[]
  confidence?: number
  mode?: string
  chartData?: ChartData
  provider?: string
  model?: string
  toolCalls?: ToolCall[]
  thinkingSteps?: ThinkingStepEnhanced[]
  isThinking?: boolean
  totalDuration?: number
  tokenUsage?: {
    prompt_tokens: number
    completion_tokens: number
    total_tokens: number
  }
  verdict?: 'PASS' | 'PARTIAL' | 'ABSTAIN'
  evidence?: EvidenceItem[]
}

function EvidenceLedger({ verdict, evidence }: { verdict?: Message['verdict']; evidence?: EvidenceItem[] }) {
  if (!evidence?.length && !verdict) return null
  const color = verdict === 'PASS' ? 'green' : verdict === 'PARTIAL' ? 'orange' : 'red'
  const label = verdict === 'PASS' ? '证据完整' : verdict === 'PARTIAL' ? '证据部分可用' : '证据不足，已拒答'
  return (
    <Card className="evidence-ledger" style={{ marginTop: 12, padding: 12 }}>
      <Space align="center" style={{ marginBottom: 8 }}>
        <Text strong>证据校验</Text>
        <Tag color={color}>{label}</Tag>
        <Text type="tertiary" size="small">{evidence?.filter(item => item.status === 'observed').length || 0}/{evidence?.length || 0} 条查询有效</Text>
      </Space>
      <List
        dataSource={evidence || []}
        size="small"
        renderItem={(item) => (
          <List.Item>
            <Space>
              <Tag size="small" color={item.status === 'observed' ? 'green' : 'red'}>{item.status === 'observed' ? '已观测' : '不可用'}</Tag>
            <Text style={{ fontFamily: 'monospace' }}>{item.evidence_id}</Text>
            <Text>{item.query_id}</Text>
            {item.error && <Text type="danger" title={item.error}>{item.error.slice(0, 80)}</Text>}
            </Space>
          </List.Item>
        )}
      />
    </Card>
  )
}

interface SessionInfo {
  session_id: string
  title: string
  created_at: string
  updated_at: string
  message_count: number
  mode: string
}

interface ModelInfo {
  id: string
  name: string
  max_tokens: number
  tier: string
}

interface Provider {
  name: string
  display_name: string
  models: ModelInfo[]
}

const modes = [
  { value: 'sequential', label: '顺序执行', desc: 'Agent 按顺序依次执行', icon: '📝' },
  { value: 'parallel', label: '并行执行', desc: '所有 Agent 同时并行执行', icon: '⚡' },
  { value: 'hierarchical', label: '层级执行', desc: '按层级顺序执行', icon: '📊' },
  { value: 'debate', label: '辩论模式', desc: '多 Agent 辩论后选出最佳方案', icon: '🗣️' },
]

const quickQueries = [
  { label: '🔍 诊断延迟问题', query: '帮我分析最近24小时的延迟问题' },
  { label: '📊 数据趋势分析', query: '展示最近的流量变化趋势' },
  { label: '🐛 错误日志分析', query: '分析最近的错误日志' },
  { label: '📈 性能报告', query: '生成最近的性能报告' },
]

function Chat() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [selectedMode, setSelectedMode] = useState('sequential')
  const [sessionId, setSessionId] = useState(() => `session-${Date.now()}`)
  const [sessions, setSessions] = useState<SessionInfo[]>([])
  const [sessionsLoading, setSessionsLoading] = useState(false)
  const [showHistory, setShowHistory] = useState(true)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const abortControllerRef = useRef<AbortController | null>(null)

  // 思考进度状态
  const [thinkingStartTime, setThinkingStartTime] = useState<Date | null>(null)
  const [thinkingProgress, setThinkingProgress] = useState<string>('')

  // 模型选择状态
  const [providers, setProviders] = useState<Provider[]>([])
  const [selectedProvider, setSelectedProvider] = useState<string>('')
  const [selectedModel, setSelectedModel] = useState<string>('')
  const [availableModels, setAvailableModels] = useState<ModelInfo[]>([])

  // 高级设置
  const advancedSettings = {
    maxThinkingTime: 600, // 最大思考时间（秒）
    showDetailedProgress: true,
    enableLongThinking: true,
  }

  // 加载可用模型
  const loadProviders = async () => {
    const cacheKey = 'oncall_llm_providers'
    try {
      const cached = sessionStorage.getItem(cacheKey)
      if (cached) {
        const parsed = JSON.parse(cached)
        if (parsed?.expiresAt > Date.now() && Array.isArray(parsed.providers)) {
          applyProviders(parsed.providers)
          return
        }
      }
    } catch (_) {
      // 缓存损坏时继续请求服务端
    }
    try {
      const controller = new AbortController()
      const timeout = window.setTimeout(() => controller.abort(), 8000)
      const response = await fetch(`${API_BASE}/api/llm/providers`, { signal: controller.signal })
      window.clearTimeout(timeout)
      const data = await response.json()
      if (data.success && data.providers) {
        applyProviders(data.providers)
        sessionStorage.setItem(cacheKey, JSON.stringify({ providers: data.providers, expiresAt: Date.now() + 5 * 60 * 1000 }))
      }
    } catch (error) {
      console.error('Failed to load providers:', error)
      Toast.error({ content: '加载模型列表失败', duration: 3 })
    }
  }

  const applyProviders = (nextProviders: Provider[]) => {
    setProviders(nextProviders)
    if (nextProviders.length > 0) {
      const firstProvider = nextProviders[0]
      setSelectedProvider(firstProvider.name)
      setAvailableModels(firstProvider.models)
      if (firstProvider.models.length > 0) setSelectedModel(firstProvider.models[0].id)
    }
  }

  // 处理提供商变更
  const handleProviderChange = (value: BasicSelectValue | undefined) => {
    const providerName = String(value || '')
    setSelectedProvider(providerName)
    const provider = providers.find(p => p.name === providerName)
    if (provider && provider.models.length > 0) {
      setAvailableModels(provider.models)
      setSelectedModel(provider.models[0].id)
    }
  }

  // 处理模型变更
  const handleModelChange = (value: BasicSelectValue | undefined) => {
    setSelectedModel(String(value || ''))
  }

  // 加载会话列表
  const loadSessions = async () => {
    setSessionsLoading(true)
    try {
      const response = await fetch(`${API_BASE}/api/chat/sessions`)
      const data = await response.json()
      if (data.success) {
        setSessions(data.sessions)
      }
    } catch (error) {
      console.error('Failed to load sessions:', error)
    } finally {
      setSessionsLoading(false)
    }
  }

  // 加载会话消息
  const loadSessionMessages = async (sid: string) => {
    try {
      const response = await fetch(`/api/chat/sessions/${sid}`)
      const data = await response.json()
      if (data.success && data.session) {
        const historyMessages: Message[] = (data.session.messages || []).map((msg: any, index: number) => ({
          id: `msg-${index}`,
          role: msg.role,
          content: msg.content,
          timestamp: msg.timestamp,
          trace: msg.metadata?.trace || [],
          confidence: msg.metadata?.confidence,
          chartData: msg.metadata?.chart_data,
          verdict: msg.metadata?.verdict,
          evidence: msg.metadata?.evidence || msg.metadata?.chart_data?.evidence,
        }))
        setMessages(historyMessages)
        setSelectedMode(data.session.mode || 'sequential')
      }
    } catch (error) {
      console.error('Failed to load session messages:', error)
      Toast.error({ content: '加载会话消息失败', duration: 3 })
    }
  }

  // 切换会话
  const switchSession = async (sid: string) => {
    setSessionId(sid)
    await loadSessionMessages(sid)
  }

  // 新建对话
  const newSession = () => {
    const newSid = `session-${Date.now()}`
    setSessionId(newSid)
    setMessages([])
    setSelectedMode('sequential')
    setThinkingStartTime(null)
    setThinkingProgress('')
  }

  // 删除会话
  const deleteSession = async (sid: string, e: React.MouseEvent) => {
    e.stopPropagation()
    Modal.confirm({
      title: '确认删除',
      content: '确定要删除这个对话吗？删除后无法恢复。',
      okText: '删除',
      cancelText: '取消',
      okButtonProps: { type: 'danger' },
      onOk: async () => {
        try {
          await fetch(`/api/chat/sessions/${sid}`, { method: 'DELETE' })
          Toast.success({ content: '对话已删除', duration: 3 })
          loadSessions()
          if (sid === sessionId) {
            newSession()
          }
        } catch (error) {
          Toast.error({ content: '删除失败', duration: 3 })
        }
      },
    })
  }

  // 停止思考
  const stopThinking = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
      abortControllerRef.current = null
      setLoading(false)
      setThinkingStartTime(null)
      Toast.warning({ content: '已停止思考', duration: 3 })
    }
  }, [])

  useEffect(() => {
    loadSessions()
    loadProviders()
  }, [])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // 发送消息
  const sendMessage = async () => {
    if (!input.trim() || loading) return

    // 检查输入长度
    if (input.length > 10000) {
      Toast.warning({ content: '输入内容过长，请缩短后重试', duration: 3 })
      return
    }

    const userMessage: Message = {
      id: `msg-${Date.now()}`,
      role: 'user',
      content: input,
      timestamp: new Date().toISOString(),
    }

    setMessages((prev) => [...prev, userMessage])
    setInput('')
    setLoading(true)
    setThinkingStartTime(new Date())
    setThinkingProgress('准备开始思考...')

    // 创建 AbortController 用于取消请求
    abortControllerRef.current = new AbortController()

    try {
      const response = await fetch(`${API_BASE}/api/chat/send`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: sessionId,
          message: input,
          mode: selectedMode,
          provider: selectedProvider || undefined,
          model: selectedModel || undefined,
          enable_long_thinking: advancedSettings.enableLongThinking,
          max_thinking_time: advancedSettings.maxThinkingTime,
        }),
        signal: abortControllerRef.current.signal,
      })
      const data = await response.json()

      if (data.success) {
        const trace = data.trace || []

        // 提取工具调用
        const toolCalls: ToolCall[] = trace
          .filter((step: TraceStep) => step.tool_name || step.step_type === 'tool_call')
          .map((step: TraceStep, index: number) => ({
            id: `tool-${step.step_id || index}`,
            name: step.tool_name || step.agent_name,
            description: step.action,
            parameters: step.tool_parameters || {},
            status: step.status === 'success' ? 'success' : step.status === 'error' ? 'error' : 'success',
            result: step.tool_result,
            duration_ms: step.duration_ms,
          }))

        // 提取思考步骤 - 包含所有 trace 步骤，更详细的信息
        const thinkingSteps: ThinkingStepEnhanced[] = trace.map((step: TraceStep, index: number) => {
          // 根据 step_type 确定 type
          let stepType: ThinkingStepEnhanced['type'] = 'reasoning'
          if (step.step_type === 'database') stepType = 'action'
          else if (step.step_type === 'analysis') stepType = 'analysis'
          else if (step.step_type === 'retrieval') stepType = 'search'
          else if (step.step_type === 'llm') stepType = 'reasoning'
          else if (step.step_type === 'router') stepType = 'decision'
          else if (step.step_type === 'tool') stepType = 'action'

          // 构建更详细的内容
          let content = step.reasoning || step.action || ''

          // 添加工具参数信息
          if (step.tool_parameters) {
            const params = step.tool_parameters
            const paramStr = Object.entries(params)
              .map(([k, v]) => `${k}=${v}`)
              .join(', ')
            content += `\n参数: ${paramStr}`
          }

          // 添加执行结果摘要
          if (step.tool_result_summary) {
            content += `\n结果: ${step.tool_result_summary}`
          }

          // 添加 agent 名称作为前缀
          if (step.agent_name) {
            content = `[${step.agent_name}] ${content}`
          }

          return {
            id: `thinking-${step.step_id || index}`,
            content,
            type: stepType,
            timestamp: new Date().toISOString(),
            duration_ms: step.duration_ms,
            tokens_used: step.tokens?.total_tokens || 0,
          }
        })

        // 计算总时长
        const totalDuration = trace.reduce((sum: number, step: TraceStep) => sum + (step.duration_ms || 0), 0)

        const assistantMessage: Message = {
          id: `msg-${Date.now()}`,
          role: 'assistant',
          content: data.message,
          timestamp: new Date().toISOString(),
          trace: data.trace,
          confidence: data.confidence,
          mode: data.mode,
          chartData: data.chart_data,
          verdict: data.verdict,
          evidence: data.evidence,
          provider: data.provider,
          model: data.model,
          toolCalls,
          thinkingSteps,
          totalDuration: data.total_duration_ms || totalDuration,
          tokenUsage: data.token_usage,
        }
        setMessages((prev) => [...prev, assistantMessage])
        loadSessions()
      } else {
        Toast.error({ content: data.error || '请求失败', duration: 3 })
      }
    } catch (error: any) {
      if (error.name === 'AbortError') {
        console.log('Request aborted')
      } else {
        console.error('Failed to send message:', error)
        Toast.error({ content: '发送消息失败，请检查网络连接', duration: 3 })
      }
    } finally {
      setLoading(false)
      setThinkingStartTime(null)
      setThinkingProgress('')
      abortControllerRef.current = null
    }
  }

  // 清空消息
  const clearMessages = () => {
    Modal.confirm({
      title: '确认清空',
      content: '确定要清空当前对话吗？清空后无法恢复。',
      okText: '清空',
      cancelText: '取消',
      okButtonProps: { type: 'danger' },
      onOk: () => {
        setMessages([])
        newSession()
      },
    })
  }

  // 快速查询
  const handleQuickQuery = (query: string) => {
    setInput(query)
  }

  // 格式化时长
  const formatDuration = (ms: number) => {
    if (ms < 1000) return `${ms}ms`
    if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`
    const minutes = Math.floor(ms / 60000)
    const seconds = Math.round((ms % 60000) / 1000)
    return `${minutes}m ${seconds}s`
  }

  // 格式化时间
  const formatTime = (dateStr: string) => {
    const date = new Date(dateStr)
    const now = new Date()
    const diff = now.getTime() - date.getTime()
    const days = Math.floor(diff / (1000 * 60 * 60 * 24))

    if (days === 0) {
      return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
    } else if (days === 1) {
      return '昨天'
    } else if (days < 7) {
      return `${days}天前`
    } else {
      return date.toLocaleDateString('zh-CN', { month: '2-digit', day: '2-digit' })
    }
  }

  // 渲染思考进度
  const renderThinkingProgress = () => {
    if (!loading || !thinkingStartTime) return null

    return (
      <div className="message message-assistant thinking-progress-message">
        <ThinkingProgress
          startTime={thinkingStartTime}
          isThinking={loading}
          thinkingContent={thinkingProgress}
        />
        <Space style={{ marginTop: 12 }}>
          <Button
            type="danger"
            size="small"
            icon={<IconStop />}
            onClick={stopThinking}
          >
            停止思考
          </Button>
        </Space>
      </div>
    )
  }

  return (
    <div className="chat-page">
      {/* 头部 */}
      <div className="chat-header">
        <Title heading={4} style={{ margin: 0 }}>智能诊断助手</Title>
        <Space>
          <Button
            icon={<IconHistory />}
            onClick={() => setShowHistory(!showHistory)}
            size="small"
          >
            {showHistory ? '隐藏' : '历史'}
          </Button>

          {/* 模型选择 */}
          <Select
            value={selectedProvider}
            onChange={handleProviderChange}
            style={{ width: 100 }}
            placeholder="提供商"
            disabled={loading}
            size="small"
          >
            {providers.map((p) => (
              <Select.Option key={p.name} value={p.name}>
                {p.display_name}
              </Select.Option>
            ))}
          </Select>

          <Select
            value={selectedModel}
            onChange={handleModelChange}
            style={{ width: 130 }}
            placeholder="模型"
            disabled={loading}
            size="small"
          >
            {availableModels.map((m) => (
              <Select.Option key={m.id} value={m.id}>
                <Tooltip content={`最大 ${m.max_tokens} tokens`}>
                  <span>{m.name}</span>
                </Tooltip>
              </Select.Option>
            ))}
          </Select>

          {/* 执行模式 */}
          <Dropdown
            trigger="click"
            position="bottomRight"
            render={
              <Dropdown.Menu>
                {modes.map((mode) => (
                  <Dropdown.Item
                    key={mode.value}
                    onClick={() => setSelectedMode(mode.value)}
                    active={selectedMode === mode.value}
                  >
                    <Space>
                      <span>{mode.icon}</span>
                      <div>
                        <Text strong>{mode.label}</Text>
                        <br />
                        <Text type="tertiary" size="small">{mode.desc}</Text>
                      </div>
                    </Space>
                  </Dropdown.Item>
                ))}
              </Dropdown.Menu>
            }
          >
            <Button disabled={loading} size="small">
              {modes.find((m) => m.value === selectedMode)?.icon} {modes.find((m) => m.value === selectedMode)?.label}
            </Button>
          </Dropdown>

          <Button icon={<IconClear />} onClick={clearMessages} disabled={loading} size="small">
            清空
          </Button>
        </Space>
      </div>

      {/* 当前配置信息 */}
      <div className="mode-info">
        <Tag color="blue" size="small">
          {modes.find((m) => m.value === selectedMode)?.icon} {modes.find((m) => m.value === selectedMode)?.label}
        </Tag>
        {selectedModel && (
          <Tag color="green" size="small" style={{ marginLeft: 8 }}>
            {availableModels.find(m => m.id === selectedModel)?.name || selectedModel}
          </Tag>
        )}
        {advancedSettings.enableLongThinking && (
          <Tag color="purple" size="small" style={{ marginLeft: 8 }}>
            <IconClock /> 深度思考
          </Tag>
        )}
      </div>

      <div className="chat-layout">
        {/* 左侧历史会话列表 */}
        {showHistory && (
          <div className="history-sidebar">
            <div className="history-header">
              <Text strong>对话历史</Text>
              <Button
                size="small"
                icon={<IconPlus />}
                onClick={newSession}
              >
                新建
              </Button>
            </div>
            <div className="history-list">
              {sessionsLoading ? (
                <div style={{ padding: 20, textAlign: 'center' }}>
                  <Spin size="small" />
                </div>
              ) : sessions.length === 0 ? (
                <Empty
                  description="暂无对话"
                  style={{ padding: 20 }}
                >
                  <Button size="small" onClick={newSession}>开始对话</Button>
                </Empty>
              ) : (
                <List
                  dataSource={sessions}
                  renderItem={(session) => (
                    <List.Item
                      className={`history-item ${session.session_id === sessionId ? 'active' : ''}`}
                      onClick={() => !loading && switchSession(session.session_id)}
                    >
                      <div className="history-item-content">
                        <div className="history-item-title">
                          <IconCommentStroked style={{ marginRight: 6 }} />
                          <Text ellipsis style={{ flex: 1 }}>
                            {session.title}
                          </Text>
                        </div>
                        <div className="history-item-meta">
                          <Text type="tertiary" size="small">
                            {formatTime(session.updated_at)}
                          </Text>
                          <Text type="tertiary" size="small">
                            {session.message_count}条
                          </Text>
                        </div>
                      </div>
                      <Button
                        size="small"
                        icon={<IconDelete />}
                        type="tertiary"
                        onClick={(e) => deleteSession(session.session_id, e)}
                        disabled={loading}
                      />
                    </List.Item>
                  )}
                />
              )}
            </div>
          </div>
        )}

        {/* 右侧聊天区域 */}
        <div className="chat-container">
          <div className="messages-area">
            {messages.length === 0 ? (
              <div className="empty-state">
                <Empty
                  title="开始智能对话"
                  description="输入问题，AI 助手为您提供诊断和分析"
                />
                {/* 快速查询 */}
                <div className="quick-queries-section">
                  <Text type="tertiary" size="small" style={{ marginBottom: 8, display: 'block' }}>
                    快速开始
                  </Text>
                  <Space wrap>
                    {quickQueries.map((q) => (
                      <Button
                        key={q.query}
                        size="small"
                        theme="light"
                        onClick={() => handleQuickQuery(q.query)}
                      >
                        {q.label}
                      </Button>
                    ))}
                  </Space>
                </div>
              </div>
            ) : (
              messages.map((msg) => (
                <div key={msg.id} className={`message message-${msg.role}`}>
                  <div className="message-header">
                    <Space>
                      <Text strong>{msg.role === 'user' ? '👤 您' : '🤖 助手'}</Text>
                      {msg.provider && msg.model && (
                        <Tag size="small" color="cyan">{msg.model}</Tag>
                      )}
                      {msg.totalDuration !== undefined && (
                        <Tag size="small" color="purple">
                          <IconClock /> {formatDuration(msg.totalDuration)}
                        </Tag>
                      )}
                      {msg.tokenUsage && (
                        <Tooltip content={`输入: ${msg.tokenUsage.prompt_tokens || 0} tokens | 输出: ${msg.tokenUsage.completion_tokens || 0} tokens`}>
                          <Tag size="small" color={msg.tokenUsage.total_tokens > 0 ? "green" : "grey"}>
                            🔤 {msg.tokenUsage.total_tokens || 0} tokens
                          </Tag>
                        </Tooltip>
                      )}
                    </Space>
                    <Text type="tertiary" size="small">
                      {new Date(msg.timestamp).toLocaleTimeString()}
                    </Text>
                  </div>
                  <div className="message-content">
                    <MarkdownRenderer content={msg.content} />
                  </div>

                  {/* 图表展示区域 */}
                  {msg.chartData && (
                    <div className="chart-section">
                      <EChartsDisplay chartData={msg.chartData.charts?.[0] || msg.chartData} />
                      {/* 结构化网络可视化数据 - 数据表格 */}
                      {msg.chartData.structured && (
                        <div className="structured-viz-section" style={{ marginTop: 8 }}>
                          <NetworkVizDisplay
                            type={msg.chartData.structured.type}
                            data={msg.chartData.structured.data}
                            region={msg.chartData.structured.region}
                          />
                        </div>
                      )}
                      {msg.chartData.summary && (
                        <div className="chart-summary" style={{ marginTop: 12 }}>
                          <Space wrap>
                            <Tag color="blue">数据点: {msg.chartData.summary.data_points}</Tag>
                            <Tag color="green">时间范围: {msg.chartData.summary.time_range}</Tag>
                            <Tag color="purple">图表类型: {msg.chartData.summary.chart_type}</Tag>
                          </Space>
                        </div>
                      )}
                    </div>
                  )}

                  <EvidenceLedger verdict={msg.verdict} evidence={msg.evidence} />

                  {/* 思考过程展示 */}
                  {msg.thinkingSteps && msg.thinkingSteps.length > 0 && (
                    <ThinkingDisplayEnhanced
                      steps={msg.thinkingSteps}
                      isThinking={msg.isThinking}
                      title="思考过程"
                      defaultExpanded={true}
                      showTimeBreakdown={true}
                      totalDuration={msg.totalDuration}
                    />
                  )}

                  {/* 工具调用展示 */}
                  {msg.toolCalls && msg.toolCalls.length > 0 && (
                    <ToolCallDisplay
                      toolCalls={msg.toolCalls}
                      title="工具调用"
                      defaultExpanded={false}
                    />
                  )}

                  {/* 置信度 */}
                  {msg.confidence && (
                    <div className="confidence">
                      <Space>
                        <Text type="success">✓ 置信度: {(msg.confidence * 100).toFixed(0)}%</Text>
                      </Space>
                    </div>
                  )}
                </div>
              ))
            )}

            {/* 思考进度 */}
            {renderThinkingProgress()}

            <div ref={messagesEndRef} />
          </div>

          {/* 输入区域 - 固定在底部 */}
          <div className="input-area">
            <Input
              placeholder="输入您的问题... (如：分析最近24小时的延迟问题)"
              value={input}
              onChange={setInput}
              onKeyPress={(e) => e.key === 'Enter' && !loading && sendMessage()}
              style={{ flex: 1 }}
              size="large"
              disabled={loading}
              maxLength={10000}
              showClear
            />
            <Button
              type="primary"
              theme="solid"
              size="large"
              onClick={sendMessage}
              loading={loading}
              disabled={!input.trim() || loading}
            >
              <IconSend /> 发送
            </Button>
          </div>

          {/* 底部提示 */}
          <div className="input-footer">
            <Text type="tertiary" size="small">
              {providers.find(p => p.name === selectedProvider)?.display_name} / {availableModels.find(m => m.id === selectedModel)?.name}
              {' · '}
              {modes.find(m => m.value === selectedMode)?.label}
              {advancedSettings.enableLongThinking && ' · 深度思考'}
            </Text>
          </div>
        </div>
      </div>
    </div>
  )
}

export default Chat

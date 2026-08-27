/**
 * Chat API 客户端
 * 智能对话、可视化相关接口
 */
import axios from 'axios'

const API_BASE = import.meta.env.VITE_API_BASE || ''

const api = axios.create({
  baseURL: API_BASE,
  timeout: 60000, // 对话可能较慢
  headers: {
    'Content-Type': 'application/json',
  },
})

// ============ 类型定义 ============

export interface ChatMessage {
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp?: string
}

export interface TraceStep {
  step_id: number
  step_type: string
  agent_name: string
  action: string
  reasoning?: string
  duration_ms: number
  status: string
}

export interface SkillRecommendation {
  recommended: boolean
  reason: string
  suggested_name: string
  suggested_description: string
}

export interface ChatResponse {
  success: boolean
  session_id: string
  message: string
  trace?: TraceStep[]
  chart_data?: {
    base64: string
    title: string
    description: string
  }
  confidence?: number
  mode: string
  skill_recommendation?: SkillRecommendation
}

export interface SessionInfo {
  session_id: string
  created_at: string
  message_count: number
  mode: string
}

export interface AgentMode {
  id: string
  name: string
  description: string
  recommended_for: string[]
}

export interface VisualizeResponse {
  success: boolean
  chart_base64?: string
  chart_html?: string
  title: string
  description: string
  error?: string
}

// ============ API 方法 ============

/**
 * 发送对话消息
 */
export async function sendMessage(params: {
  session_id?: string
  message: string
  mode?: 'sequential' | 'parallel' | 'hierarchical' | 'debate'
  context?: Record<string, any>
}): Promise<ChatResponse> {
  const response = await api.post('/api/chat/send', params)
  return response.data
}

/**
 * 获取会话列表
 */
export async function listSessions(): Promise<{
  success: boolean
  sessions: SessionInfo[]
}> {
  const response = await api.get('/api/chat/sessions')
  return response.data
}

/**
 * 获取会话详情
 */
export async function getSession(sessionId: string): Promise<{
  success: boolean
  session: {
    session_id: string
    messages: ChatMessage[]
    mode: string
  }
}> {
  const response = await api.get(`/api/chat/sessions/${sessionId}`)
  return response.data
}

/**
 * 删除会话
 */
export async function deleteSession(sessionId: string): Promise<{ success: boolean }> {
  const response = await api.delete(`/api/chat/sessions/${sessionId}`)
  return response.data
}

/**
 * 获取可用模式
 */
export async function getModes(): Promise<{
  success: boolean
  modes: AgentMode[]
}> {
  const response = await api.get('/api/chat/modes')
  return response.data
}

/**
 * 生成可视化图表
 */
export async function visualize(params: {
  query: string
  output_format?: 'base64' | 'html'
}): Promise<VisualizeResponse> {
  const response = await api.post('/api/chat/visualize', params)
  return response.data
}

/**
 * 高级可视化
 */
export async function advancedVisualize(params: {
  query: string
  output_format?: string
}): Promise<VisualizeResponse & {
  metrics?: string[]
  chart_type?: string
}> {
  const response = await api.post('/api/chat/visualize/advanced', params)
  return response.data
}

/**
 * 获取可视化示例
 */
export async function getVisualizeExamples(): Promise<{
  success: boolean
  simple_examples: Array<{ query: string; description: string }>
  complex_examples: Array<{ query: string; description: string; type: string }>
  supported_metrics: Array<{ id: string; name: string; unit: string }>
  supported_chart_types: Array<{ id: string; name: string; usage: string }>
}> {
  const response = await api.get('/api/chat/visualize/examples')
  return response.data
}

export default {
  sendMessage,
  listSessions,
  getSession,
  deleteSession,
  getModes,
  visualize,
  advancedVisualize,
  getVisualizeExamples,
}

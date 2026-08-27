/**
 * Agent API 客户端
 */
import axios from 'axios'

const API_BASE = import.meta.env.VITE_API_BASE || ''

const api = axios.create({
  baseURL: API_BASE,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// ============ 类型定义 ============

export interface Agent {
  id: string
  name: string
  type: string
  description: string
  enabled: boolean
  capabilities: string[]
  config: Record<string, any>
}

export interface Tool {
  id: string
  name: string
  description: string
  type: string
  config: Record<string, any>
}

export interface AgentStatus {
  agent_id: string
  status: 'idle' | 'running' | 'error'
  current_task?: string
  last_execution?: string
  metrics: {
    total_executions: number
    success_rate: number
    avg_duration_ms: number
  }
}

// ============ API 方法 ============

/**
 * 获取 Agent 列表
 */
export async function listAgents(): Promise<{
  success: boolean
  agents: Agent[]
}> {
  const response = await api.get('/api/agent/list')
  return response.data
}

/**
 * 获取 Agent 详情
 */
export async function getAgent(agentId: string): Promise<{
  success: boolean
  agent?: Agent
}> {
  const response = await api.get(`/api/agent/${agentId}`)
  return response.data
}

/**
 * 切换 Agent 状态
 */
export async function toggleAgent(agentId: string, enabled: boolean): Promise<{
  success: boolean
  agent?: Agent
}> {
  const response = await api.post(`/api/agent/${agentId}/toggle`, { enabled })
  return response.data
}

/**
 * 获取工具列表
 */
export async function listTools(): Promise<{
  success: boolean
  tools: Tool[]
}> {
  const response = await api.get('/api/agent/tools/list')
  return response.data
}

/**
 * 获取 Agent 状态
 */
export async function getAgentStatus(): Promise<{
  success: boolean
  agents: AgentStatus[]
}> {
  const response = await api.get('/api/agent/status')
  return response.data
}

/**
 * 获取模式推荐
 */
export async function getModeRecommendation(query: string): Promise<{
  success: boolean
  recommended_mode: string
  reason: string
}> {
  const response = await api.get('/api/agent/modes/recommend', {
    params: { query },
  })
  return response.data
}

export default {
  listAgents,
  getAgent,
  toggleAgent,
  listTools,
  getAgentStatus,
  getModeRecommendation,
}

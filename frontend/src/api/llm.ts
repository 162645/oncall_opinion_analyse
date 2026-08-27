/**
 * LLM Gateway API 客户端
 */
import axios from 'axios'

const API_BASE = import.meta.env.VITE_API_BASE || ''

const api = axios.create({
  baseURL: API_BASE,
  timeout: 60000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// ============ 类型定义 ============

export interface Provider {
  id: string
  name: string
  models: string[]
  available: boolean
}

export interface GenerateResponse {
  success: boolean
  content: string
  model: string
  provider: string
  usage?: {
    prompt_tokens: number
    completion_tokens: number
    total_tokens: number
  }
  latency_ms: number
}

export interface CostInfo {
  provider: string
  model: string
  total_tokens: number
  total_cost: number
}

// ============ API 方法 ============

/**
 * 生成文本
 */
export async function generate(params: {
  prompt: string
  provider?: string
  model?: string
  temperature?: number
  max_tokens?: number
}): Promise<GenerateResponse> {
  const response = await api.post('/api/llm/generate', params)
  return response.data
}

/**
 * 智能生成 (自动选择最优模型)
 */
export async function smartGenerate(params: {
  prompt: string
  task_type?: 'diagnosis' | 'analysis' | 'code' | 'chat'
}): Promise<GenerateResponse> {
  const response = await api.post('/api/llm/smart-generate', params)
  return response.data
}

/**
 * 带降级的生成
 */
export async function generateWithFallback(params: {
  prompt: string
  primary?: string
  fallback?: string
}): Promise<GenerateResponse> {
  const response = await api.post('/api/llm/generate-with-fallback', params)
  return response.data
}

/**
 * 获取可用提供商
 */
export async function getProviders(): Promise<{
  success: boolean
  providers: Provider[]
}> {
  const response = await api.get('/api/llm/providers')
  return response.data
}

/**
 * 获取成本统计
 */
export async function getCosts(): Promise<{
  success: boolean
  costs: CostInfo[]
  total_cost: number
}> {
  const response = await api.get('/api/llm/costs')
  return response.data
}

/**
 * 重置成本统计
 */
export async function resetCosts(): Promise<{ success: boolean }> {
  const response = await api.post('/api/llm/costs/reset')
  return response.data
}

export default {
  generate,
  smartGenerate,
  generateWithFallback,
  getProviders,
  getCosts,
  resetCosts,
}

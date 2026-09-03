/**
 * Skill API 客户端
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

export interface Skill {
  id: string
  name: string
  description: string
  category: string
  tags: string[]
  scope: 'personal' | 'team' | 'system'
  owner: string
  trigger: {
    keywords: string[]
    intent?: string
  }
  workflow: {
    step_type: string
    name: string
    config: Record<string, any>
  }[]
  parameters: {
    name: string
    type: string
    description: string
    required: boolean
    default?: any
    options?: string[]
  }[]
  usage_count: number
  success_count: number
  rating: number
  quality_score: number
  status: string
  created_at: string
  updated_at: string
}

export interface SkillListResponse {
  success: boolean
  total: number
  page: number
  page_size: number
  skills: Skill[]
}

export interface SkillResponse {
  success: boolean
  skill?: Skill
  error?: string
}

export interface ExecutionResponse {
  success: boolean
  execution_id: string
  skill_id: string
  result?: string
  steps_executed: any[]
  duration_ms: number
  error?: string
}

export interface SearchResult {
  skill: Skill
  score: number
  match_reason: string
}

export interface SkillRecommendation {
  recommended: boolean
  reason: string
  suggested_name?: string
  suggested_description?: string
  suggested_workflow?: any[]
  suggested_trigger?: any
  suggested_params?: any[]
  confidence?: number
}

/**
 * 获取 Skill 列表
 */
export async function listSkills(params?: {
  scope?: string
  category?: string
  status?: string
  min_rating?: number
  sort_by?: string
  page?: number
  page_size?: number
}): Promise<SkillListResponse> {
  const response = await api.get('/api/skills/', { params })
  return response.data
}

/**
 * 获取单个 Skill
 */
export async function getSkill(skillId: string): Promise<SkillResponse> {
  const response = await api.get(`/api/skills/${skillId}`)
  return response.data
}

/**
 * 创建 Skill
 */
export async function createSkill(data: {
  name: string
  description: string
  workflow: any[]
  trigger?: any
  parameters?: any[]
  tags?: string[]
  category?: string
  scope?: string
  team_id?: string
}): Promise<SkillResponse> {
  const response = await api.post('/api/skills/', data)
  return response.data
}

/**
 * 更新 Skill
 */
export async function updateSkill(
  skillId: string,
  data: Partial<{
    name: string
    description: string
    workflow: any[]
    trigger: any
    parameters: any[]
    tags: string[]
    status: string
  }>
): Promise<SkillResponse> {
  const response = await api.put(`/api/skills/${skillId}`, data)
  return response.data
}

/**
 * 删除 Skill
 */
export async function deleteSkill(skillId: string): Promise<{ success: boolean }> {
  const response = await api.delete(`/api/skills/${skillId}`)
  return response.data
}

/**
 * 搜索 Skill
 */
export async function searchSkills(query: string, topK = 10): Promise<{
  success: boolean
  query: string
  results: SearchResult[]
}> {
  const response = await api.post('/api/skills/search', { query, top_k: topK })
  return response.data
}

/**
 * 执行 Skill
 */
export async function executeSkill(
  skillId: string,
  params: Record<string, any>,
  context?: Record<string, any>
): Promise<ExecutionResponse> {
  const response = await api.post(`/api/skills/${skillId}/execute`, { params, context })
  return response.data
}

/**
 * 评价 Skill
 */
export async function rateSkill(
  skillId: string,
  score: number,
  comment?: string
): Promise<{ success: boolean }> {
  const response = await api.post(`/api/skills/${skillId}/rate`, { score, comment })
  return response.data
}

/**
 * 克隆 Skill
 */
export async function cloneSkill(skillId: string): Promise<SkillResponse> {
  const response = await api.post(`/api/skills/${skillId}/clone`)
  return response.data
}

/**
 * 分析流程 (判断是否推荐保存为 Skill)
 */
export async function analyzeFlow(flowData: {
  session_id: string
  query: string
  intent: string
  steps: any[]
  success: boolean
  duration_ms: number
  user_feedback?: number
}): Promise<{
  success: boolean
  recommendation: SkillRecommendation
}> {
  const response = await api.post('/api/skills/analyze-flow', flowData)
  return response.data
}

/**
 * 获取统计信息
 */
export async function getSkillStats(): Promise<{
  success: boolean
  stats: {
    total: number
    by_scope: Record<string, number>
    by_category: Record<string, number>
    by_status: Record<string, number>
    total_executions: number
    avg_rating: number
  }
}> {
  const response = await api.get('/api/skills/stats/overview')
  return response.data
}

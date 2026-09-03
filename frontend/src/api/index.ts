/**
 * API 客户端统一导出
 */
import axios from 'axios'

const API_BASE = import.meta.env.VITE_API_BASE || ''

// 创建 axios 实例
export const api = axios.create({
  baseURL: API_BASE,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// 请求拦截器
api.interceptors.request.use(
  (config) => {
    // 可以在这里添加认证 token
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// 响应拦截器
api.interceptors.response.use(
  (response) => {
    return response
  },
  (error) => {
    // 统一错误处理
    console.error('API Error:', error.response?.data || error.message)
    return Promise.reject(error)
  }
)

// 导出各模块 API (使用命名空间避免冲突)
export * as knowledgeApi from './knowledge'
export * as chatApi from './chat'
export * as agentApi from './agent'
export * as skillApi from './skill'
export * as llmApi from './llm'

// 同时导出具体函数和类型供直接使用
export {
  uploadDocument,
  batchUpload,
  listDocuments,
  getDocument,
  deleteDocument,
  searchKnowledge,
  getStats,
  type Document,
  type SearchResult as KnowledgeSearchResult,
  type UploadResponse,
  type SearchResponse,
} from './knowledge'

export {
  sendMessage,
  getSession,
  listSessions,
  deleteSession,
  visualize,
  type ChatMessage,
  type TraceStep,
  type ChatResponse,
  type SessionInfo,
} from './chat'

export {
  listAgents,
  getAgent,
  toggleAgent,
  listTools,
  getAgentStatus,
  getModeRecommendation,
  type Agent,
  type Tool,
  type AgentStatus,
} from './agent'

export {
  listSkills,
  getSkill,
  createSkill,
  updateSkill,
  deleteSkill,
  executeSkill,
  getSkillStats,
  type Skill,
} from './skill'

export {
  getProviders,
  type Provider,
} from './llm'

// 默认导出
export default {
  api,
}

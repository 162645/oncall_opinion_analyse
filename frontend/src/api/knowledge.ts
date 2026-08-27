/**
 * 知识库 API 客户端
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

export interface Document {
  id: string
  title: string
  content: string
  doc_type: string
  file_path: string
  file_size: number
  status: string
  metadata: Record<string, any>
  created_at: string
  updated_at: string
}

export interface SearchResult {
  doc_id: string
  content: string
  score: number
  metadata: Record<string, any>
}

export interface UploadResponse {
  success: boolean
  document?: Document
  error?: string
}

export interface SearchResponse {
  success: boolean
  results: SearchResult[]
  total: number
}

// ============ API 方法 ============

/**
 * 上传文档
 */
export async function uploadDocument(file: File, metadata?: Record<string, any>): Promise<UploadResponse> {
  const formData = new FormData()
  formData.append('file', file)
  if (metadata) {
    formData.append('metadata', JSON.stringify(metadata))
  }

  const response = await api.post('/api/knowledge/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  })
  return response.data
}

/**
 * 批量上传文档
 */
export async function batchUpload(files: File[]): Promise<{ success: boolean; documents?: Document[] }> {
  const formData = new FormData()
  files.forEach(file => formData.append('files', file))

  const response = await api.post('/api/knowledge/batch', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  })
  return response.data
}

/**
 * 获取文档列表
 */
export async function listDocuments(params?: {
  doc_type?: string
  status?: string
  page?: number
  page_size?: number
}): Promise<{ success: boolean; documents: Document[]; total: number }> {
  const response = await api.get('/api/knowledge/documents', { params })
  return response.data
}

/**
 * 获取文档详情
 */
export async function getDocument(docId: string): Promise<{ success: boolean; document?: Document }> {
  const response = await api.get(`/api/knowledge/documents/${docId}`)
  return response.data
}

/**
 * 删除文档
 */
export async function deleteDocument(docId: string): Promise<{ success: boolean }> {
  const response = await api.delete(`/api/knowledge/documents/${docId}`)
  return response.data
}

/**
 * 搜索知识库
 */
export async function searchKnowledge(params: {
  query: string
  top_k?: number
  filters?: Record<string, any>
}): Promise<SearchResponse> {
  const response = await api.post('/api/knowledge/search', params)
  return response.data
}

/**
 * 获取统计信息
 */
export async function getStats(): Promise<{
  success: boolean
  stats: {
    total_documents: number
    total_size: number
    by_type: Record<string, number>
  }
}> {
  const response = await api.get('/api/knowledge/stats')
  return response.data
}

export default {
  uploadDocument,
  batchUpload,
  listDocuments,
  getDocument,
  deleteDocument,
  searchKnowledge,
  getStats,
}

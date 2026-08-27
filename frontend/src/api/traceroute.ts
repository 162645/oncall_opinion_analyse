/**
 * Traceroute API 服务
 * 提供 Traceroute 深度分析相关的 API 调用
 */
import axios from 'axios'

// 从 localStorage 获取 API 地址
const getApiBase = (): string => {
  try {
    const config = localStorage.getItem('app_config')
    if (config) {
      return JSON.parse(config).apiBaseUrl || ''
    }
  } catch (e) {
    // ignore
  }
  return ''
}

// 请求参数类型
export interface TerminalAnalysisParams {
  region: string
  start_time?: string
  end_time?: string
  terminal_type: 'as' | 'asgeo'
  top_n?: number
  include_paths?: boolean
  terminal_filter?: string  // 新增：末端节点模糊搜索
}

export interface TerminalListParams {
  region: string
  terminal_type?: 'as' | 'asgeo'
  search?: string  // 模糊搜索关键词
  limit?: number
}

export interface ASPathAnalysisParams {
  region: string
  start_time?: string
  end_time?: string
  path_type?: 'as' | 'asgeo'
  terminal_as?: string  // 限定末端 AS
  terminal_asgeo?: string  // 限定末端 ASGeo
  top_n?: number
}

export interface TerminalPrefix24Params {
  region: string
  terminal: string
  terminal_type?: 'as' | 'asgeo'
  start_time?: string
  end_time?: string
  top_n?: number
}

export interface PingTraceCorrelationParams {
  region: string
  prefix24: string
  recent_hours?: number
  start_time?: string
  end_time?: string
}

// 响应类型
export interface TerminalNode {
  terminal: string
  trace_count: number
  path_count: number  // 独立路径数
  prefix24_count: number
  data_center_count: number
  avg_hop_count: number
  sample_paths: Array<{ path: string; count: number }>
}

export interface TerminalAnalysisResponse {
  success: boolean
  region: string
  terminal_type: string
  data_source: 'full' | 'quarter' | 'unknown'
  sampling_rate: number
  terminals: TerminalNode[]
  total_traces: number
  unique_terminals: number
}

export interface Prefix24Detail {
  prefix24: string
  trace_count: number
  unique_ips: number
  sample_as_path: string
  sample_asgeo_path: string
  ping_stats: {
    sample_count: number
    mean_rtt: number
    median_rtt: number
    p90_rtt: number
    p95_rtt: number
    p99_rtt: number
    min_rtt: number
    max_rtt: number
  }
}

export interface TerminalPrefix24Response {
  success: boolean
  region: string
  terminal: string
  terminal_type: string
  prefix24s: Prefix24Detail[]
  total_prefixes: number
}

export interface PathInfo {
  as_path: string
  asgeo_path: string
  ip_path: string
  count: number
  avg_hop_count: number
  reached_count: number
}

export interface PingTraceCorrelationResponse {
  success: boolean
  prefix24: string
  trace_data: {
    sample_type: 'quarter' | 'full'
    sampling_rate: number
    paths: PathInfo[]
    total_traces: number
  }
  ping_data: {
    sample_type: 'full'
    sampling_rate: number
    stats: {
      sample_count: number
      mean_rtt: number
      median_rtt: number
      std_rtt: number
      p50_rtt: number
      p90_rtt: number
      p95_rtt: number
      p99_rtt: number
      min_rtt: number
      max_rtt: number
      unique_ips: number
    }
  }
  correlation: {
    asn: number | null
    as_name: string | null
    geo_country: string | null
  }
}

export interface DataSourceInfo {
  success: boolean
  region: string
  data_source: 'full' | 'quarter' | 'unknown'
  table_name: string
  sampling_rate: number
  record_count: number
  description: string
}

// 末端节点列表项
export interface TerminalListItem {
  terminal: string
  trace_count: number
  prefix24_count: number
  data_center_count: number
}

export interface TerminalListResponse {
  success: boolean
  region: string
  terminal_type: string
  terminals: TerminalListItem[]
  total: number
}

// 路径分析结果
export interface PathAnalysisItem {
  path: string
  occurrence_count: number
  avg_hop_count: number
  prefix24_count: number
  data_center_count: number
}

// 路径搜索列表项
export interface PathListItem {
  path: string
  trace_count: number
}

export interface PathListParams {
  region: string
  path_type?: 'as' | 'asgeo'
  search?: string
  limit?: number
}

export interface PathListResponse {
  success: boolean
  region: string
  path_type: string
  paths: PathListItem[]
}

export interface TerminalDistributionItem {
  terminal: string
  trace_count: number
}

export interface ASPathAnalysisResponse {
  success: boolean
  region: string
  path_type: string
  paths: PathAnalysisItem[]
  total_traces: number
  unique_paths: number
  avg_hop_count: number
  total_reached: number
  terminal_distribution: TerminalDistributionItem[]
  filters: {
    terminal_as: string | null
    terminal_asgeo: string | null
  }
}

// ===== 路径详情相关类型 =====

export interface PathDetailParams {
  region: string
  path: string
  path_type?: 'as' | 'asgeo'
  start_time?: string
  end_time?: string
  top_n?: number
}

export interface PathTerminalItem {
  terminal: string
  trace_count: number
  prefix24_count: number
  avg_hop_count: number
}

export interface PathPrefix24Item {
  prefix24: string
  trace_count: number
  unique_ips: number
  sample_terminal: string
}

export interface PathDataCenterItem {
  data_center: string
  count: number
}

export interface PathDetailResponse {
  success: boolean
  region: string
  path: string
  path_type: string
  terminals: PathTerminalItem[]
  prefix24s: PathPrefix24Item[]
  data_centers: PathDataCenterItem[]
  total_traces: number
  unique_terminals: number
  unique_prefix24s: number
  avg_hop_count: number
}

// ===== 路径 Ping 时序分析相关类型 =====

export interface PathPingTrendParams {
  region: string
  path: string
  path_type?: 'as' | 'asgeo'
  interval?: 'minute' | 'hour' | 'day'
  start_time?: string
  end_time?: string
  percentiles?: number[]
  // 筛选参数
  asn?: number
  asgeo?: string
  isp?: string
  data_center?: string
  // 极端值过滤
  outlier_filter_min?: number
  outlier_filter_max?: number
}

export interface TimeSeriesItem {
  time: string
  sample_count: number
  mean_rtt: number
  median_rtt: number
  min_rtt: number
  max_rtt: number
  std_rtt: number
  percentiles: Record<string, number>
}

export interface PathPingTrendSummary {
  total_samples: number
  mean_rtt: number
  median_rtt: number
  min_rtt: number
  max_rtt: number
  std_rtt: number
  percentiles: Record<string, number>
}

export interface PathPingTrendResponse {
  success: boolean
  region: string
  path: string
  path_type: string
  interval: string
  time_series: TimeSeriesItem[]
  prefix24_count: number
  prefix24s: string[]
  summary: PathPingTrendSummary
}

// ===== 路径筛选选项相关类型 =====

export interface PathFilterOptionsParams {
  region: string
  path: string
  path_type?: 'as' | 'asgeo'
  start_time?: string
  end_time?: string
}

export interface PathFilterOptionsResponse {
  success: boolean
  region: string
  as_options: Array<{ asn: number; as_name: string; sample_count: number }>
  asgeo_options: Array<{ asgeo: string; sample_count: number }>
  isp_options: Array<{ isp: string; sample_count: number }>
  data_center_options: Array<{ data_center: string; sample_count: number }>
  prefix24_options: Array<{ prefix24: string; sample_count: number }>
}

// API 服务
export const tracerouteApi = {
  /**
   * 获取末端节点分析
   */
  async getTerminalAnalysis(params: TerminalAnalysisParams): Promise<TerminalAnalysisResponse> {
    const apiBase = getApiBase()
    const response = await axios.post(`${apiBase}/api/clickhouse/trace/terminal-analysis`, params)
    return response.data
  },

  /**
   * 获取末端节点的所有 Prefix24
   */
  async getTerminalPrefix24s(params: TerminalPrefix24Params): Promise<TerminalPrefix24Response> {
    const apiBase = getApiBase()
    const response = await axios.get(`${apiBase}/api/clickhouse/trace/terminal/${encodeURIComponent(params.terminal)}/prefix24s`, {
      params: {
        region: params.region,
        terminal_type: params.terminal_type,
        start_time: params.start_time,
        end_time: params.end_time,
        top_n: params.top_n,
      },
    })
    return response.data
  },

  /**
   * 获取 Ping-Trace 关联数据
   */
  async getPingTraceCorrelation(params: PingTraceCorrelationParams): Promise<PingTraceCorrelationResponse> {
    const apiBase = getApiBase()
    const response = await axios.post(`${apiBase}/api/clickhouse/trace/ping-correlation`, params)
    return response.data
  },

  /**
   * 获取数据源信息
   */
  async getDataSourceInfo(region: string): Promise<DataSourceInfo> {
    const apiBase = getApiBase()
    const response = await axios.get(`${apiBase}/api/clickhouse/trace/data-source`, {
      params: { region },
    })
    return response.data
  },

  /**
   * 获取末端节点列表（支持模糊搜索）
   */
  async getTerminalList(params: TerminalListParams): Promise<TerminalListResponse> {
    const apiBase = getApiBase()
    const response = await axios.post(`${apiBase}/api/clickhouse/trace/terminals/list`, params)
    return response.data
  },

  /**
   * AS/ASGeo 路径分析（支持末端节点过滤）
   */
  async getASPathAnalysis(params: ASPathAnalysisParams): Promise<ASPathAnalysisResponse> {
    const apiBase = getApiBase()
    const response = await axios.post(`${apiBase}/api/clickhouse/trace/paths/analysis`, params)
    return response.data
  },

  /**
   * 搜索路径列表（用于下拉搜索）
   */
  async getPathList(params: PathListParams): Promise<PathListResponse> {
    const apiBase = getApiBase()
    const response = await axios.post(`${apiBase}/api/clickhouse/trace/paths/list`, params)
    return response.data
  },

  /**
   * 获取路径详情（关联的末端节点和 prefix24）
   */
  async getPathDetail(params: PathDetailParams): Promise<PathDetailResponse> {
    const apiBase = getApiBase()
    const response = await axios.post(`${apiBase}/api/clickhouse/trace/path/detail`, params)
    return response.data
  },

  /**
   * 获取路径关联的 Ping 时序数据
   */
  async getPathPingTrend(params: PathPingTrendParams): Promise<PathPingTrendResponse> {
    const apiBase = getApiBase()
    const response = await axios.post(`${apiBase}/api/clickhouse/trace/path/ping-trend`, params)
    return response.data
  },

  /**
   * 获取路径筛选选项
   */
  async getPathFilterOptions(params: PathFilterOptionsParams): Promise<PathFilterOptionsResponse> {
    const apiBase = getApiBase()
    const response = await axios.post(`${apiBase}/api/clickhouse/trace/path/filter-options`, params)
    return response.data
  },
}

export default tracerouteApi

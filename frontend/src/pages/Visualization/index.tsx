/**
 * 可视化页面
 * 清晰分离 Ping 数据分析和 Traceroute 路径分析
 */
import { useState, useEffect, useCallback, useRef } from 'react'
import {
  Card,
  Typography,
  Button,
  Space,
  Tabs,
  TabPane,
  Toast,
  Empty,
  Banner,
  Select,
  Tag,
  Row,
  Col,
  RadioGroup,
  Radio,
  DatePicker,
  Collapse,
  Slider,
  Checkbox,
  CheckboxGroup,
  Spin,
  Table,
  Input,
  Divider,
} from '@douyinfe/semi-ui'
import {
  IconServer,
  IconFilter,
  IconRefresh,
  IconLink,
  IconActivity,
  IconSearch,
  IconLineChartStroked,
  IconHome,
} from '@douyinfe/semi-icons'
import axios from 'axios'

import ChartDisplay, { type ChartData } from './components/ChartDisplay'
import PercentileRangeChart from './components/PercentileRangeChart'
import DataTable from './DataTable'
import QueryProgress from './QueryProgress'
import RegionOverview from './components/RegionOverview'
import tracerouteApi from '../../api/traceroute'
import './Visualization.css'

const { Title, Text } = Typography

// 从 localStorage 获取 API 地址
const getApiBase = () => {
  try {
    const config = localStorage.getItem('app_config')
    if (config) {
      return JSON.parse(config).apiBaseUrl || ''
    }
  } catch (e) {}
  return ''
}

// 分析维度选项 - 用于显示标签
const DIMENSION_LABELS: Record<string, string> = {
  overall: '整体统计',
  time_trend: '时间趋势',
  asn: '按 AS 分析',
  asgeo: '按 AS+Geo 分析',
  country: '按国家分析',
  data_center: '按数据中心分析',
  prefix24: '按 IP 前缀分析',
}

// 可选统计指标 - 基础统计
const BASIC_STATISTICS_OPTIONS = [
  { label: '平均值 (Mean)', value: 'mean' },
  { label: '中位数 (Median)', value: 'median' },
  { label: '标准差 (Std)', value: 'std' },
  { label: '方差 (Variance)', value: 'variance' },
  { label: '最小值 (Min)', value: 'min' },
  { label: '最大值 (Max)', value: 'max' },
]

// 可选统计指标 - 高级统计
const ADVANCED_STATISTICS_OPTIONS = [
  { label: '变异系数 (CV)', value: 'cv' },
  { label: '四分位距 (IQR)', value: 'iqr' },
  { label: '偏度 (Skewness)', value: 'skewness' },
  { label: '峰度 (Kurtosis)', value: 'kurtosis' },
]

// 可选统计指标 - 分位数
const PERCENTILE_OPTIONS = [
  { label: 'P10', value: 'p10' },
  { label: 'P25', value: 'p25' },
  { label: 'P50', value: 'p50' },
  { label: 'P75', value: 'p75' },
  { label: 'P90', value: 'p90' },
  { label: 'P95', value: 'p95' },
  { label: 'P99', value: 'p99' },
]

// 分位数范围可视化配置
interface PercentileRangeConfig {
  enabled: boolean           // 是否启用分位数范围模式
  minPercentile: number      // 最小分位数 (0-99)
  maxPercentile: number      // 最大分位数 (1-100)
  step: number               // 步长，控制绘制多少条线 (如 step=1 表示每1个百分点一条线)
  chartType: 'line' | 'area' // 图表类型：折线图或面积图
}

// 运营商选项 (ISP)
// 数据库连接状态
type DbStatus = 'connected' | 'disconnected' | 'testing' | 'unknown'

// 元数据选项类型
interface AsOption { asn: number; as_name: string; sample_count: number; display: string }
interface AsgeoOption { asgeo: string; sample_count: number }
interface DataCenterOption { data_center: string; sample_count: number }
interface Prefix24Option { prefix24: string; sample_count: number; unique_ips: number }
interface IspOption { isp: string; sample_count: number }  // 运营商选项

// Ping 筛选状态
interface PingFilterState {
  region: string
  startTime: Date | null
  endTime: Date | null
  chartType: 'auto' | 'bar' | 'line'
  interval: 'minute' | 'hour' | 'day'
  selectedStats: string[]  // 用户选择的统计指标
  outlierFilterEnabled: boolean
  outlierFilterMin: number
  outlierFilterMax: number
  // 高级筛选 - 支持搜索下拉，选择后自动过滤该维度的数据
  asn: number | null
  asgeo: string | null
  country: string | null
  dataCenter: string | null
  prefix24: string | null
  isp: string | null  // 运营商筛选（从数据库动态获取）
  // 分位数范围可视化
  percentileRange: PercentileRangeConfig
}

const defaultPingFilter: PingFilterState = {
  region: '',
  startTime: null,
  endTime: null,
  chartType: 'auto',
  interval: 'hour',
  selectedStats: ['mean', 'median', 'p50', 'p95'],
  outlierFilterEnabled: false,
  outlierFilterMin: 5,
  outlierFilterMax: 95,
  asn: null,
  asgeo: null,
  country: null,
  dataCenter: null,
  prefix24: null,
  isp: null,
  percentileRange: {
    enabled: false,
    minPercentile: 5,
    maxPercentile: 95,
    step: 5,  // 默认每5个百分点一条线
    chartType: 'line',
  },
}

// Traceroute 筛选状态
interface TracerouteFilterState {
  region: string
  startTime: Date | null
  endTime: Date | null
  dataCenter: string | null  // 数据中心筛选
  traceType: 'quarter' | 'full'  // traceroute 类型：1/4抽样 或 全量
}

const defaultTracerouteFilter: TracerouteFilterState = {
  region: '',
  startTime: null,
  endTime: null,
  dataCenter: null,
  traceType: 'quarter',
}

function Visualization() {
  const [regions, setRegions] = useState<string[]>([])
  const [regionsLoading, setRegionsLoading] = useState(true)
  const [dbStatus, setDbStatus] = useState<DbStatus>('unknown')
  const [activeTab, setActiveTab] = useState<string>('ping')

  // Traceroute 数据中心选项
  const [tracerouteDcOptions, setTracerouteDcOptions] = useState<string[]>([])
  const [tracerouteDcLoading, setTracerouteDcLoading] = useState(false)

  // Ping 分析状态
  const [pingFilter, setPingFilter] = useState<PingFilterState>(defaultPingFilter)
  const [queryLoading, setQueryLoading] = useState(false)
  const [queryResult, setQueryResult] = useState<any>(null)
  const [chartData, setChartData] = useState<ChartData | null>(null)
  const [percentileRangeData, setPercentileRangeData] = useState<ChartData | null>(null)  // 分位数范围图表数据
  const [percentileRangeLoading, setPercentileRangeLoading] = useState(false)
  const [queryProgress, setQueryProgress] = useState(0)
  const [queryStep, setQueryStep] = useState('')
  const [queryStepIndex, setQueryStepIndex] = useState(0)
  const [queryStartTime, setQueryStartTime] = useState<Date | null>(null)
  const [showFilters, setShowFilters] = useState(true)
  const [chartViewMode, setChartViewMode] = useState<'trend' | 'percentile'>('trend')  // 图表视图模式切换

  // Traceroute 分析状态 - 独立地区选择
  const [tracerouteFilter, setTracerouteFilter] = useState<TracerouteFilterState>(defaultTracerouteFilter)

  // Traceroute 分析子状态
  const [traceSubTab, setTraceSubTab] = useState<string>('terminals')
  const [traceTerminalType, setTraceTerminalType] = useState<'as' | 'asgeo'>('asgeo')
  const [traceTerminalSearch, setTraceTerminalSearch] = useState<string>('')
  const [traceTerminalData, setTraceTerminalData] = useState<any>(null)
  const [traceTerminalLoading, setTraceTerminalLoading] = useState(false)

  const [tracePathType, setTracePathType] = useState<'as' | 'asgeo'>('as')
  const [tracePathFilter, setTracePathFilter] = useState<string>('')
  const [tracePathData, setTracePathData] = useState<any>(null)
  const [tracePathLoading, setTracePathLoading] = useState(false)

  const [traceDetailPath, setTraceDetailPath] = useState<string>('')
  const [traceDetailType, setTraceDetailType] = useState<'as' | 'asgeo'>('as')
  const [traceDetailData, setTraceDetailData] = useState<any>(null)
  const [traceDetailLoading, setTraceDetailLoading] = useState(false)

  const [tracePingPath, setTracePingPath] = useState<string>('')
  const [tracePingType, setTracePingType] = useState<'as' | 'asgeo'>('as')
  const [tracePingInterval, setTracePingInterval] = useState<'minute' | 'hour' | 'day'>('hour')
  const [tracePingData, setTracePingData] = useState<any>(null)
  const [tracePingLoading, setTracePingLoading] = useState(false)
  const [traceAnalysisStarted, setTraceAnalysisStarted] = useState(false)  // 是否点击了开始分析

  // 路径 Ping 筛选状态
  const [tracePingFilter, setTracePingFilter] = useState<{
    asn: number | null
    asgeo: string | null
    isp: string | null
    data_center: string | null
    outlierFilterEnabled: boolean
    outlierFilterMin: number
    outlierFilterMax: number
    selectedStats: string[]
    percentileRangeEnabled: boolean
    percentileRangeMin: number
    percentileRangeMax: number
    percentileRangeStep: number
    chartType: 'auto' | 'line' | 'bar'
  }>({
    asn: null,
    asgeo: null,
    isp: null,
    data_center: null,
    outlierFilterEnabled: false,
    outlierFilterMin: 5,
    outlierFilterMax: 95,
    selectedStats: ['mean', 'median', 'p95'],
    percentileRangeEnabled: false,
    percentileRangeMin: 50,
    percentileRangeMax: 99,
    percentileRangeStep: 5,
    chartType: 'auto',
  })

  // 路径 Ping 筛选选项（动态获取，只包含该路径有的）
  const [tracePingFilterOptions, setTracePingFilterOptions] = useState<{
    asOptions: Array<{ asn: number; as_name: string; sample_count: number }>
    asgeoOptions: Array<{ asgeo: string; sample_count: number }>
    ispOptions: Array<{ isp: string; sample_count: number }>
    dataCenterOptions: Array<{ data_center: string; sample_count: number }>
    prefix24Options: Array<{ prefix24: string; sample_count: number }>
  }>({ asOptions: [], asgeoOptions: [], ispOptions: [], dataCenterOptions: [], prefix24Options: [] })
  const [tracePingFilterOptionsLoading, setTracePingFilterOptionsLoading] = useState(false)

  // 路径搜索下拉选项
  const [tracePathOptions, setTracePathOptions] = useState<any[]>([])
  const [tracePathOptionsLoading, setTracePathOptionsLoading] = useState(false)

  // 元数据搜索状态
  const [asOptions, setAsOptions] = useState<AsOption[]>([])
  const [asOptionsLoading, setAsOptionsLoading] = useState(false)
  const [asgeoOptions, setAsgeoOptions] = useState<AsgeoOption[]>([])
  const [asgeoOptionsLoading, setAsgeoOptionsLoading] = useState(false)
  const [dcOptions, setDcOptions] = useState<DataCenterOption[]>([])
  const [dcOptionsLoading, setDcOptionsLoading] = useState(false)
  const [prefix24Options, setPrefix24Options] = useState<Prefix24Option[]>([])
  const [prefix24OptionsLoading, setPrefix24OptionsLoading] = useState(false)
  const [ispOptions, setIspOptions] = useState<IspOption[]>([])
  const [ispOptionsLoading, setIspOptionsLoading] = useState(false)

  const abortControllerRef = useRef<AbortController | null>(null)
  const apiBase = getApiBase()

  // 加载地区列表
  const loadRegions = useCallback(async (force = false) => {
    const cacheKey = 'oncall_clickhouse_regions'
    if (!force) {
      try {
        const cached = sessionStorage.getItem(cacheKey)
        const parsed = cached ? JSON.parse(cached) : null
        if (parsed?.expiresAt > Date.now() && Array.isArray(parsed.regions)) {
          setRegions(parsed.regions)
          setDbStatus('connected')
          setRegionsLoading(false)
          return
        }
      } catch (_) {
        // 缓存损坏时回退到服务端请求
      }
    }
    setRegionsLoading(true)
    setDbStatus('testing')
    // 页面首次打开时后端/ClickHouse 可能仍在启动，短暂失败不应立即显示“未连接”。
    // 采用指数退避重试，手动刷新仍可通过 force=true 立即重新探测。
    let lastError: unknown = null
    for (let attempt = 0; attempt < 3; attempt += 1) {
      try {
        const response = await axios.get(`${apiBase}/api/clickhouse/regions`, { timeout: 8000 })
        if (response.data.success) {
          const nextRegions = response.data.regions.map((r: any) => r.name || r)
          setRegions(nextRegions)
          sessionStorage.setItem(cacheKey, JSON.stringify({ regions: nextRegions, expiresAt: Date.now() + 5 * 60 * 1000 }))
          setDbStatus('connected')
          setRegionsLoading(false)
          return
        }
        lastError = new Error(response.data.message || 'ClickHouse 返回失败')
      } catch (error) {
        lastError = error
      }
      if (attempt < 2) await new Promise(resolve => setTimeout(resolve, 500 * (attempt + 1)))
    }
    console.warn('ClickHouse connection failed after retries', lastError)
    setDbStatus('disconnected')
    setRegions([])
    setRegionsLoading(false)
  }, [apiBase])

  useEffect(() => {
    loadRegions()
  }, [loadRegions])

  // 从 URL 读取 region 参数并设置到 tracerouteFilter
  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const regionFromUrl = params.get('region')
    if (regionFromUrl) {
      setTracerouteFilter(prev => ({ ...prev, region: regionFromUrl }))
    }
  }, [])

  // ===== 元数据搜索函数 =====

  // 搜索 AS
  const searchAs = useCallback(async (search: string) => {
    if (!pingFilter.region) return
    setAsOptionsLoading(true)
    try {
      const response = await axios.get(`${apiBase}/api/clickhouse/metadata/asns`, {
        params: { region: pingFilter.region, search: search || undefined, limit: 50 }
      })
      setAsOptions(response.data.asns || [])
    } catch (error) {
      console.error('Failed to search AS:', error)
    } finally {
      setAsOptionsLoading(false)
    }
  }, [pingFilter.region, apiBase])

  // 搜索 ASGeo
  const searchAsgeo = useCallback(async (search: string) => {
    if (!pingFilter.region) return
    setAsgeoOptionsLoading(true)
    try {
      const response = await axios.get(`${apiBase}/api/clickhouse/metadata/asgeos`, {
        params: { region: pingFilter.region, search: search || undefined, limit: 50 }
      })
      setAsgeoOptions(response.data.asgeos || [])
    } catch (error) {
      console.error('Failed to search ASGeo:', error)
    } finally {
      setAsgeoOptionsLoading(false)
    }
  }, [pingFilter.region, apiBase])

  // 搜索数据中心
  const searchDataCenter = useCallback(async (search: string) => {
    if (!pingFilter.region) return
    setDcOptionsLoading(true)
    try {
      const response = await axios.get(`${apiBase}/api/clickhouse/metadata/data-centers`, {
        params: { region: pingFilter.region, search: search || undefined, limit: 50 }
      })
      setDcOptions(response.data.data_centers || [])
    } catch (error) {
      console.error('Failed to search data centers:', error)
    } finally {
      setDcOptionsLoading(false)
    }
  }, [pingFilter.region, apiBase])

  // 搜索 Prefix24
  const searchPrefix24 = useCallback(async (search: string) => {
    if (!pingFilter.region) return
    setPrefix24OptionsLoading(true)
    try {
      const response = await axios.get(`${apiBase}/api/clickhouse/metadata/prefix24s`, {
        params: { region: pingFilter.region, search: search || undefined, limit: 50 }
      })
      setPrefix24Options(response.data.prefix24s || [])
    } catch (error) {
      console.error('Failed to search prefix24s:', error)
    } finally {
      setPrefix24OptionsLoading(false)
    }
  }, [pingFilter.region, apiBase])

  // 搜索运营商 (ISP)
  const searchIsp = useCallback(async (search: string) => {
    if (!pingFilter.region) return
    setIspOptionsLoading(true)
    try {
      const response = await axios.get(`${apiBase}/api/clickhouse/metadata/isps`, {
        params: { region: pingFilter.region, search: search || undefined, limit: 50 }
      })
      setIspOptions(response.data.isps || [])
    } catch (error) {
      console.error('Failed to search ISPs:', error)
    } finally {
      setIspOptionsLoading(false)
    }
  }, [pingFilter.region, apiBase])

  // ===== Traceroute 数据中心选项 =====

  // 加载 Traceroute 数据中心选项
  const loadTracerouteDcOptions = useCallback(async () => {
    if (!tracerouteFilter.region) return
    setTracerouteDcLoading(true)
    try {
      const response = await axios.get(`${apiBase}/api/clickhouse/traceroute/data-centers`, {
        params: { region: tracerouteFilter.region }
      })
      setTracerouteDcOptions(response.data.data_centers || [])
    } catch (error) {
      console.error('Failed to load traceroute data centers:', error)
    } finally {
      setTracerouteDcLoading(false)
    }
  }, [tracerouteFilter.region, apiBase])

  // 地区变化时加载数据中心选项
  useEffect(() => {
    if (tracerouteFilter.region) {
      loadTracerouteDcOptions()
    }
  }, [tracerouteFilter.region, loadTracerouteDcOptions])

  // ===== Traceroute 数据加载函数 =====

  // 加载末端节点数据
  const loadTraceTerminals = useCallback(async () => {
    if (!tracerouteFilter.region) return
    setTraceTerminalLoading(true)
    try {
      const params: any = {
        region: tracerouteFilter.region,
        terminal_type: traceTerminalType,
        top_n: 50,
        include_paths: true,
        trace_type: tracerouteFilter.traceType,
      }
      if (tracerouteFilter.startTime) params.start_time = tracerouteFilter.startTime.toISOString()
      if (tracerouteFilter.endTime) params.end_time = tracerouteFilter.endTime.toISOString()
      if (traceTerminalSearch) params.terminal_filter = traceTerminalSearch
      if (tracerouteFilter.dataCenter) params.data_center = tracerouteFilter.dataCenter

      const data = await tracerouteApi.getTerminalAnalysis(params)
      setTraceTerminalData(data)
    } catch (error: any) {
      console.error('Failed to load terminals:', error)
      Toast.error({ content: '加载末端节点失败', duration: 3 })
    } finally {
      setTraceTerminalLoading(false)
    }
  }, [tracerouteFilter.region, tracerouteFilter.startTime, tracerouteFilter.endTime, tracerouteFilter.dataCenter, tracerouteFilter.traceType, traceTerminalType, traceTerminalSearch])

  // 加载路径数据
  const loadTracePaths = useCallback(async () => {
    if (!tracerouteFilter.region) return
    setTracePathLoading(true)
    try {
      const params: any = {
        region: tracerouteFilter.region,
        path_type: tracePathType,
        top_n: 100,
        trace_type: tracerouteFilter.traceType,
      }
      if (tracerouteFilter.startTime) params.start_time = tracerouteFilter.startTime.toISOString()
      if (tracerouteFilter.endTime) params.end_time = tracerouteFilter.endTime.toISOString()
      if (tracePathFilter) {
        if (tracePathType === 'as') params.terminal_as = tracePathFilter
        else params.terminal_asgeo = tracePathFilter
      }
      if (tracerouteFilter.dataCenter) params.data_center = tracerouteFilter.dataCenter

      const data = await tracerouteApi.getASPathAnalysis(params)
      setTracePathData(data)
    } catch (error: any) {
      console.error('Failed to load paths:', error)
      Toast.error({ content: '加载路径数据失败', duration: 3 })
    } finally {
      setTracePathLoading(false)
    }
  }, [tracerouteFilter.region, tracerouteFilter.startTime, tracerouteFilter.endTime, tracerouteFilter.dataCenter, tracerouteFilter.traceType, tracePathType, tracePathFilter])

  // 加载路径详情
  const loadTraceDetail = useCallback(async (pathOverride?: string, typeOverride?: 'as' | 'asgeo') => {
    const pathToUse = pathOverride || traceDetailPath.trim()
    const typeToUse = typeOverride || traceDetailType
    if (!tracerouteFilter.region || !pathToUse) return
    setTraceDetailLoading(true)
    try {
      const params: any = {
        region: tracerouteFilter.region,
        path: pathToUse,
        path_type: typeToUse,
        top_n: 100,
      }
      if (tracerouteFilter.startTime) params.start_time = tracerouteFilter.startTime.toISOString()
      if (tracerouteFilter.endTime) params.end_time = tracerouteFilter.endTime.toISOString()

      const data = await tracerouteApi.getPathDetail(params)
      setTraceDetailData(data)
    } catch (error: any) {
      console.error('Failed to load path detail:', error)
      Toast.error({ content: '加载路径详情失败', duration: 3 })
      setTraceDetailData(null)
    } finally {
      setTraceDetailLoading(false)
    }
  }, [tracerouteFilter.region, tracerouteFilter.startTime, tracerouteFilter.endTime, traceDetailPath, traceDetailType])

  // 加载路径 Ping 筛选选项
  const loadTracePingFilterOptions = useCallback(async (pathOverride?: string, pathTypeOverride?: 'as' | 'asgeo') => {
    const pathToUse = pathOverride || tracePingPath.trim()
    const pathTypeToUse = pathTypeOverride || tracePingType
    console.log('=== loadTracePingFilterOptions ===')
    console.log('region:', tracerouteFilter.region)
    console.log('pathToUse:', pathToUse)
    console.log('pathTypeToUse:', pathTypeToUse)
    if (!tracerouteFilter.region || !pathToUse) {
      console.log('Early return: missing region or path')
      return
    }
    setTracePingFilterOptionsLoading(true)
    try {
      const params: any = {
        region: tracerouteFilter.region,
        path: pathToUse,
        path_type: pathTypeToUse,
      }
      if (tracerouteFilter.startTime) params.start_time = tracerouteFilter.startTime.toISOString()
      if (tracerouteFilter.endTime) params.end_time = tracerouteFilter.endTime.toISOString()

      console.log('Calling API with params:', params)
      const data = await tracerouteApi.getPathFilterOptions(params)
      console.log('API response:', data)
      setTracePingFilterOptions({
        asOptions: data.as_options || [],
        asgeoOptions: data.asgeo_options || [],
        ispOptions: data.isp_options || [],
        dataCenterOptions: data.data_center_options || [],
        prefix24Options: data.prefix24_options || [],
      })
    } catch (error: any) {
      console.error('Failed to load filter options:', error)
    } finally {
      setTracePingFilterOptionsLoading(false)
    }
  }, [tracerouteFilter.region, tracerouteFilter.startTime, tracerouteFilter.endTime, tracePingPath, tracePingType])

  // 加载 Ping 时序
  const loadTracePing = useCallback(async () => {
    if (!tracerouteFilter.region || !tracePingPath.trim()) return
    setTracePingLoading(true)
    try {
      // 生成分位数列表
      let percentiles: number[]
      if (tracePingFilter.percentileRangeEnabled) {
        percentiles = []
        for (let p = tracePingFilter.percentileRangeMin; p <= tracePingFilter.percentileRangeMax; p += tracePingFilter.percentileRangeStep) {
          percentiles.push(p)
        }
      } else {
        percentiles = [50, 90, 95, 99]
      }

      const params: any = {
        region: tracerouteFilter.region,
        path: tracePingPath.trim(),
        path_type: tracePingType,
        interval: tracePingInterval,
        percentiles,
      }
      if (tracerouteFilter.startTime) params.start_time = tracerouteFilter.startTime.toISOString()
      if (tracerouteFilter.endTime) params.end_time = tracerouteFilter.endTime.toISOString()

      // 添加筛选参数
      if (tracePingFilter.asn) params.asn = tracePingFilter.asn
      if (tracePingFilter.asgeo) params.asgeo = tracePingFilter.asgeo
      if (tracePingFilter.isp) params.isp = tracePingFilter.isp
      if (tracePingFilter.data_center) params.data_center = tracePingFilter.data_center

      // 极端值过滤
      if (tracePingFilter.outlierFilterEnabled) {
        params.outlier_filter_min = tracePingFilter.outlierFilterMin
        params.outlier_filter_max = tracePingFilter.outlierFilterMax
      }

      const data = await tracerouteApi.getPathPingTrend(params)
      setTracePingData(data)
    } catch (error: any) {
      console.error('Failed to load ping trend:', error)
      Toast.error({ content: '加载 Ping 时序失败', duration: 3 })
      setTracePingData(null)
    } finally {
      setTracePingLoading(false)
    }
  }, [tracerouteFilter.region, tracerouteFilter.startTime, tracerouteFilter.endTime, tracePingPath, tracePingType, tracePingInterval, tracePingFilter])

  // 搜索路径（用于下拉框）
  const searchTracePaths = useCallback(async (search: string, pathType: 'as' | 'asgeo') => {
    console.log('[searchTracePaths] called with:', { search, pathType, region: tracerouteFilter.region })
    if (!tracerouteFilter.region) {
      console.log('[searchTracePaths] No region selected, returning')
      return
    }
    setTracePathOptionsLoading(true)
    try {
      const params = {
        region: tracerouteFilter.region,
        path_type: pathType,
        search: search || undefined,
        limit: 50,
      }
      console.log('[searchTracePaths] Calling API with params:', params)
      const data = await tracerouteApi.getPathList(params)
      console.log('[searchTracePaths] API response:', data)
      setTracePathOptions(data.paths || [])
    } catch (error) {
      console.error('[searchTracePaths] Failed to search paths:', error)
    } finally {
      setTracePathOptionsLoading(false)
    }
  }, [tracerouteFilter.region])

  // 地区变化时加载初始元数据
  useEffect(() => {
    if (pingFilter.region) {
      searchAs('')
      searchAsgeo('')
      searchDataCenter('')
      searchPrefix24('')
      searchIsp('')
    }
  }, [pingFilter.region, searchAs, searchAsgeo, searchDataCenter, searchPrefix24, searchIsp])

  // 执行 Ping 查询
  const executePingQuery = useCallback(async () => {
    if (!pingFilter.region) {
      Toast.warning({ content: '请先选择地区', duration: 3 })
      return
    }

    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
    }
    abortControllerRef.current = new AbortController()

    setQueryLoading(true)
    setQueryResult(null)
    setChartData(null)
    setQueryStartTime(new Date())
    setQueryProgress(0)
    setQueryStepIndex(0)

    try {
      setQueryStep('连接数据库')
      setQueryProgress(10)
      setQueryStepIndex(0)
      await new Promise(resolve => setTimeout(resolve, 200))

      setQueryStep('验证查询参数')
      setQueryProgress(20)
      setQueryStepIndex(1)

      // 分析维度逻辑：
      // 默认就是时间趋势 (time_trend)
      // 高级筛选用于过滤特定 AS/国家/等的数据
      const analysisDimension = 'time_trend'

      const params: any = {
        region: pingFilter.region,
        analysis_dimension: analysisDimension,
        interval: pingFilter.interval,
        // 从 selectedStats 中提取分位数用于后端计算
        percentiles: pingFilter.selectedStats
          .filter(s => s.startsWith('p') && !isNaN(parseInt(s.substring(1))))
          .map(s => parseInt(s.substring(1)))
          .sort((a, b) => a - b),
        top_n: 100,
      }

      // 时间范围
      if (pingFilter.startTime) {
        params.start_time = pingFilter.startTime.toISOString()
      }
      if (pingFilter.endTime) {
        params.end_time = pingFilter.endTime.toISOString()
      }

      // 极端值过滤
      if (pingFilter.outlierFilterEnabled) {
        params.outlier_filter_min = pingFilter.outlierFilterMin
        params.outlier_filter_max = pingFilter.outlierFilterMax
      }

      // 高级筛选条件
      if (pingFilter.asn) {
        params.asn = pingFilter.asn
      }
      if (pingFilter.asgeo) {
        params.asgeo = pingFilter.asgeo
      }
      if (pingFilter.country) {
        params.country = pingFilter.country
      }
      if (pingFilter.dataCenter) {
        params.data_center = pingFilter.dataCenter
      }
      if (pingFilter.prefix24) {
        params.prefix24 = pingFilter.prefix24
      }
      if (pingFilter.isp) {
        params.isp = pingFilter.isp
      }

      setQueryStep('执行数据查询')
      setQueryProgress(40)
      setQueryStepIndex(2)

      const response = await axios.post(`${apiBase}/api/clickhouse/ping/analyze`, params, {
        timeout: 60000,
        signal: abortControllerRef.current.signal,
      })

      setQueryStep('处理分析结果')
      setQueryProgress(70)
      setQueryStepIndex(3)

      if (response.data.success) {
        setQueryResult(response.data)

        setQueryStep('生成可视化图表')
        setQueryProgress(90)
        setQueryStepIndex(4)

        const transformedData = transformToChartData(response.data, pingFilter)
        if (transformedData) {
          setChartData(transformedData)
          setQueryProgress(100)
          // 清理可能残留的旧提示，并保留明确的自动关闭兜底，避免 Toast 因页面切换/重复查询常驻。
          Toast.destroyAll()
          const successToastId = Toast.success({ content: '查询成功', duration: 3 })
          window.setTimeout(() => Toast.close(successToastId), 3600)
        } else {
          Toast.error({ content: '数据转换失败，无法生成图表', duration: 3 })
        }

        // 如果启用了分位数范围可视化，额外查询分位数数据
        if (pingFilter.percentileRange.enabled) {
          setPercentileRangeLoading(true)
          try {
            const percentileParams = { ...params }
            // 生成分位数列表
            const percentiles: number[] = []
            for (let p = pingFilter.percentileRange.minPercentile; p <= pingFilter.percentileRange.maxPercentile; p += pingFilter.percentileRange.step) {
              percentiles.push(p)
            }
            percentileParams.percentiles = percentiles
            percentileParams.percentile_range_mode = true  // 标记这是分位数范围查询
            // 确保使用 time_trend 维度
            percentileParams.analysis_dimension = 'time_trend'

            console.log('Sending percentile range query with params:', {
              region: percentileParams.region,
              dimension: percentileParams.analysis_dimension,
              percentiles: percentileParams.percentiles,
              percentilesCount: percentiles.length,
              interval: percentileParams.interval
            })

            const percentileResponse = await axios.post(`${apiBase}/api/clickhouse/ping/analyze`, percentileParams, {
              timeout: 120000,  // 分位数查询可能较慢
              signal: abortControllerRef.current.signal,
            })

            console.log('Percentile range response:', percentileResponse.data)
            console.log('Response statistics type:', typeof percentileResponse.data.statistics, Array.isArray(percentileResponse.data.statistics))
            if (Array.isArray(percentileResponse.data.statistics) && percentileResponse.data.statistics.length > 0) {
              console.log('First item keys:', Object.keys(percentileResponse.data.statistics[0]))
              console.log('First item percentiles:', percentileResponse.data.statistics[0].percentiles)
            }

            if (percentileResponse.data.success) {
              const percentileChartData = transformPercentileRangeData(percentileResponse.data, pingFilter)
              console.log('Transformed percentile chart data:', percentileChartData)
              if (percentileChartData) {
                setPercentileRangeData(percentileChartData)
              } else {
                Toast.warning({ content: '分位数数据转换失败，请检查后端返回格式', duration: 3 })
              }
            } else {
              console.error('Percentile query returned failure:', percentileResponse.data)
              Toast.warning({ content: '分位数范围查询失败: ' + (percentileResponse.data.error || '未知错误'), duration: 3 })
            }
          } catch (pErr: any) {
            console.error('Percentile range query failed:', pErr)
            Toast.warning({ content: '分位数范围数据查询失败: ' + (pErr.message || '网络错误'), duration: 3 })
          } finally {
            setPercentileRangeLoading(false)
          }
        } else {
          setPercentileRangeData(null)
        }
      } else {
        Toast.error({ content: response.data.error || '查询失败', duration: 3 })
      }
    } catch (err: any) {
      if (err.name !== 'AbortError' && err.code !== 'ERR_CANCELED') {
        Toast.error({ content: err.response?.data?.detail || err.message || '查询失败', duration: 3 })
      }
    } finally {
      setQueryLoading(false)
    }
  }, [pingFilter, apiBase])

  // 取消查询
  const cancelQuery = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
      setQueryLoading(false)
      Toast.info({ content: '查询已取消', duration: 3 })
    }
  }, [])

  // 数据转换为图表数据
  const transformToChartData = (result: any, filters: PingFilterState): ChartData | null => {
    const statistics = result.statistics || result
    // 维度从后端响应获取，默认 time_trend
    const dimension = result.dimension || 'time_trend'

    if (!statistics) {
      console.error('transformToChartData: No statistics data')
      return null
    }

    // 确保有选中的统计指标
    const selectedStats = filters.selectedStats?.length > 0
      ? filters.selectedStats
      : ['mean', 'median', 'p95']

    // 统一的指标处理函数
    const getStatValue = (item: any, stat: string): number | null => {
      switch (stat) {
        case 'mean': return item.mean_rtt ?? null
        case 'median': return item.median_rtt ?? null
        case 'std': return item.std_rtt ?? null
        case 'variance': return item.var_rtt ?? null
        case 'min': return item.min_rtt ?? null
        case 'max': return item.max_rtt ?? null
        case 'cv': return item.coefficient_of_variation != null ? item.coefficient_of_variation * 100 : null
        case 'iqr': return item.iqr ?? null
        case 'skewness': return item.skewness ?? null
        case 'kurtosis': return item.kurtosis ?? null
        default:
          if (stat.startsWith('p') && !isNaN(parseInt(stat.substring(1)))) {
            const p = stat.substring(1)
            return item.percentiles?.[`p${p}`] ?? null
          }
          return null
      }
    }

    const getStatLabel = (stat: string): string => {
      const labels: Record<string, string> = {
        mean: '均值', median: '中位数', std: '标准差', variance: '方差',
        min: '最小值', max: '最大值', cv: '变异系数(%)', iqr: 'IQR',
        skewness: '偏度', kurtosis: '峰度',
      }
      if (stat.startsWith('p')) return stat.toUpperCase()
      return labels[stat] || stat
    }

    // 时间趋势分析
    if (dimension === 'time_trend' && Array.isArray(statistics)) {
      const chartType = filters.chartType === 'auto' ? 'line' : filters.chartType as 'bar' | 'line'

      // 柱状图：显示聚合后的统计指标值
      if (chartType === 'bar') {
        // 计算整个时间段内的聚合统计
        const aggregatedStats: { [key: string]: number | null } = {}

        // 收集所有值
        const allValues: number[] = []
        statistics.forEach((item: any) => {
          if (item.mean_rtt !== null && item.mean_rtt !== undefined) {
            allValues.push(item.mean_rtt)
          }
        })

        if (allValues.length > 0) {
          // 计算聚合统计
          const sum = allValues.reduce((a, b) => a + b, 0)
          const mean = sum / allValues.length
          const sorted = [...allValues].sort((a, b) => a - b)
          const median = sorted[Math.floor(sorted.length / 2)]
          const min = sorted[0]
          const max = sorted[sorted.length - 1]

          // 计算标准差
          const squaredDiffs = allValues.map(v => Math.pow(v - mean, 2))
          const avgSquaredDiff = squaredDiffs.reduce((a, b) => a + b, 0) / squaredDiffs.length
          const std = Math.sqrt(avgSquaredDiff)

          aggregatedStats['mean'] = mean
          aggregatedStats['median'] = median
          aggregatedStats['min'] = min
          aggregatedStats['max'] = max
          aggregatedStats['std'] = std
        }

        // 从用户选择的指标中获取值
        const xAxisLabels: string[] = []
        const dataValues: (number | null)[] = []

        selectedStats.forEach(stat => {
          if (stat === 'mean' || stat === 'median' || stat === 'min' || stat === 'max' || stat === 'std') {
            xAxisLabels.push(getStatLabel(stat))
            dataValues.push(aggregatedStats[stat] ?? null)
          } else if (stat.startsWith('p')) {
            // 从统计数据中提取分位数
            const p = parseInt(stat.substring(1))
            const pValues: number[] = []
            statistics.forEach((item: any) => {
              const val = item.percentiles?.[`p${p}`] ?? item[`p${p}_rtt`]
              if (val !== null && val !== undefined) pValues.push(val)
            })
            if (pValues.length > 0) {
              const sorted = [...pValues].sort((a, b) => a - b)
              const pVal = sorted[Math.floor(sorted.length * p / 100)]
              xAxisLabels.push(getStatLabel(stat))
              dataValues.push(pVal)
            }
          }
        })

        if (xAxisLabels.length === 0) {
          xAxisLabels.push('均值', '中位数', '最小值', '最大值')
          dataValues.push(
            aggregatedStats['mean'] ?? null,
            aggregatedStats['median'] ?? null,
            aggregatedStats['min'] ?? null,
            aggregatedStats['max'] ?? null
          )
        }

        return {
          title: `时间趋势聚合统计 (${filters.region})${filters.asn ? ` - AS${filters.asn}` : ''}${filters.asgeo ? ` - ${filters.asgeo}` : ''}`,
          chartType: 'bar',
          data: {
            xAxis: xAxisLabels,
            series: [{ name: 'RTT (ms)', data: dataValues }],
            yAxisName: 'RTT (ms)',
          },
          summary: {
            totalRecords: statistics.length,
            timeRange: statistics.length > 0 ?
              `${statistics[0].time_bucket?.substring(0, 16) || ''} ~ ${statistics[statistics.length - 1].time_bucket?.substring(0, 16) || ''}` : '',
          },
        }
      }

      // 折线图：显示时间序列
      const series: { name: string; data: (number | null)[] }[] = []

      selectedStats.forEach(stat => {
        const data = statistics.map((item: any) => getStatValue(item, stat))
        if (data.some(v => v !== null)) {
          series.push({ name: getStatLabel(stat), data })
        }
      })

      if (series.length === 0) {
        series.push({ name: '均值', data: statistics.map((item: any) => item.mean_rtt ?? null) })
      }

      return {
        title: `时间趋势分析 (${filters.region})${filters.asn ? ` - AS${filters.asn}` : ''}${filters.asgeo ? ` - ${filters.asgeo}` : ''}`,
        chartType: 'line',
        data: {
          xAxis: statistics.map((item: any) => {
            const time = item.time || item.time_bucket
            return time ? time.substring(0, 16) : ''
          }),
          series,
          yAxisName: 'RTT (ms)',
        },
      }
    }

    // 分组统计（ASN, ASGeo, Country, DataCenter 等）
    if (Array.isArray(statistics) && statistics.length > 0) {
      const firstItem = statistics[0]
      const labelKey = firstItem.asn !== undefined ? 'asn' :
        firstItem.asgeo !== undefined ? 'asgeo' :
        firstItem.country !== undefined ? 'country' :
        firstItem.data_center !== undefined ? 'data_center' :
        firstItem.prefix24 !== undefined ? 'prefix24' : 'name'

      const chartType = filters.chartType === 'auto' ? 'bar' : filters.chartType as 'bar' | 'line' | 'pie'
      const series: { name: string; data: (number | null)[] }[] = []

      selectedStats.forEach(stat => {
        const data = statistics.slice(0, 30).map((item: any) => getStatValue(item, stat))
        if (data.some(v => v !== null)) {
          series.push({ name: getStatLabel(stat), data })
        }
      })

      if (series.length === 0) {
        series.push({ name: '均值', data: statistics.slice(0, 30).map((item: any) => item.mean_rtt ?? null) })
      }

      return {
        title: `${DIMENSION_LABELS[dimension] || dimension} 分析 (${filters.region})`,
        chartType,
        data: {
          xAxis: statistics.slice(0, 30).map((item: any) => {
            const label = item[labelKey] || item.name || 'Unknown'
            return String(label).substring(0, 15)
          }),
          series,
          yAxisName: 'RTT (ms)',
        },
        summary: {
          totalRecords: statistics.length,
        },
      }
    }

    // 整体统计 - 用柱状图显示
    if (statistics.total_samples !== undefined) {
      const xAxisLabels: string[] = []
      const dataValues: (number | null)[] = []

      selectedStats.forEach(stat => {
        xAxisLabels.push(getStatLabel(stat))
        dataValues.push(getStatValue(statistics, stat))
      })

      if (xAxisLabels.length === 0) {
        xAxisLabels.push('均值', '中位数', 'P95')
        dataValues.push(
          statistics.mean_rtt ?? null,
          statistics.median_rtt ?? null,
          statistics.percentiles?.p95 ?? null
        )
      }

      return {
        title: `整体统计分析 (${filters.region})`,
        chartType: 'bar',
        data: {
          xAxis: xAxisLabels,
          series: [{ name: 'RTT (ms)', data: dataValues }],
          yAxisName: 'RTT (ms)',
        },
        summary: {
          totalRecords: statistics.total_samples,
        },
      }
    }

    console.error('transformToChartData: No matching condition', {
      isArray: Array.isArray(statistics),
      length: Array.isArray(statistics) ? statistics.length : 'N/A',
      hasTotalSamples: statistics?.total_samples !== undefined
    })
    return null
  }

  // 分位数范围数据转换 - 用于绘制多条分位数曲线
  const transformPercentileRangeData = (result: any, filters: PingFilterState): ChartData | null => {
    console.log('transformPercentileRangeData input:', { result, filters })

    // 尝试多种数据结构
    let statistics = result.statistics || result.data || result

    // 如果 statistics 是对象且有 time_trend 或其他属性，尝试提取数组
    if (!Array.isArray(statistics) && typeof statistics === 'object') {
      // 可能的结构: { time_trend: [...], dimension: 'time_trend' }
      if (statistics.time_trend) {
        statistics = statistics.time_trend
      } else if (statistics.data) {
        statistics = statistics.data
      } else if (statistics.statistics) {
        statistics = statistics.statistics
      }
    }

    console.log('Extracted statistics:', statistics, 'isArray:', Array.isArray(statistics))

    if (!Array.isArray(statistics) || statistics.length === 0) {
      console.error('transformPercentileRangeData: Invalid data - statistics is not an array or is empty', {
        statistics,
        resultKeys: Object.keys(result),
        resultType: typeof result
      })
      return null
    }

    const { minPercentile, maxPercentile, step } = filters.percentileRange

    // 生成分位数列表
    const percentiles: number[] = []
    for (let p = minPercentile; p <= maxPercentile; p += step) {
      percentiles.push(p)
    }

    console.log('Generated percentiles:', percentiles, 'from', minPercentile, 'to', maxPercentile, 'step', step)

    // 检查第一个数据项的结构
    console.log('First statistics item:', statistics[0])

    // 为每个分位数生成一条曲线
    const series = percentiles.map((p) => {
      const data = statistics.map((item: any) => {
        const value = item.percentiles?.[`p${p}`] ?? null
        return value
      })
      const nonNullCount = data.filter(v => v !== null).length
      console.log(`P${p} series: ${nonNullCount}/${data.length} non-null values`)
      return {
        name: `P${p}`,
        data,
        percentile: p,  // 存储分位数值，用于点击显示
        color: getPercentileColor(p, minPercentile, maxPercentile),
      }
    })

    // 检查是否有有效数据
    const hasValidData = series.some(s => s.data.some(v => v !== null && v !== undefined))
    if (!hasValidData) {
      console.error('transformPercentileRangeData: No valid data points found in any series')
      return null
    }

    return {
      title: `分位数分布图 (P${minPercentile} - P${maxPercentile})`,
      chartType: filters.percentileRange.chartType === 'area' ? 'line' : 'line',
      data: {
        xAxis: statistics.map((item: any) => {
          const time = item.time || item.time_bucket
          return time ? time.substring(0, 16) : ''
        }),
        series,
        yAxisName: 'RTT (ms)',
      },
      summary: {
        totalRecords: statistics.length,
        percentileCount: percentiles.length,
      },
    }
  }

  // 分位数颜色计算 - 使用渐变色
  const getPercentileColor = (p: number, minP: number, maxP: number): string => {
    const ratio = (p - minP) / (maxP - minP || 1)
    // 从蓝色 (低分位数) 到红色 (高分位数) 的渐变
    const r = Math.round(50 + ratio * 200)
    const g = Math.round(100 + (1 - Math.abs(ratio - 0.5) * 2) * 100)
    const b = Math.round(200 - ratio * 150)
    return `rgb(${r}, ${g}, ${b})`
  }

  // 数据库状态指示器
  const renderDbStatus = () => {
    const statusConfig: Record<string, { color: 'green' | 'red' | 'blue' | 'grey', text: string }> = {
      connected: { color: 'green', text: '已连接' },
      disconnected: { color: 'red', text: '未连接' },
      testing: { color: 'blue', text: '测试中...' },
      unknown: { color: 'grey', text: '未知' },
    }
    const config = statusConfig[dbStatus]
    return (
      <Tag color={config.color} size="large">
        <IconServer /> {config.text}
      </Tag>
    )
  }

  // 快捷时间范围 - 实际应用到筛选状态
  const setQuickTimeRange = (hours: number) => {
    const endTime = new Date()
    const startTime = new Date(endTime.getTime() - hours * 60 * 60 * 1000)
    setPingFilter(prev => ({ ...prev, startTime, endTime }))
    Toast.success({ content: `已设置时间范围: 最近 ${hours} 小时`, duration: 3 })
  }

  // Ping 筛选面板 - 精简优化版
  const renderPingFilterPanel = () => (
    <Card style={{ marginBottom: 16 }}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8, width: '100%' }}>
        {/* ===== 基础筛选 ===== */}
        <div style={{ marginBottom: 8 }}>
          <Text type="tertiary" size="small" style={{ display: 'block', marginBottom: 8 }}>📌 基础配置</Text>

          {/* 地区选择 */}
          <div style={{ marginBottom: 12 }}>
            <Text size="small" style={{ display: 'block', marginBottom: 4 }}>地区 <span style={{ color: 'red' }}>*</span></Text>
            <Select
              value={pingFilter.region}
              onChange={(value) => setPingFilter(prev => ({ ...prev, region: String(value || '') }))}
              placeholder="选择地区"
              style={{ width: '100%' }}
              filter
            >
              {regions.map((region) => (
                <Select.Option key={region} value={region}>
                  {region}
                </Select.Option>
              ))}
            </Select>
          </div>

          {/* 时间范围 */}
          <div style={{ marginBottom: 12 }}>
            <Text size="small" style={{ display: 'block', marginBottom: 4 }}>📅 时间范围</Text>
            <DatePicker
              type="dateTimeRange"
              value={pingFilter.startTime && pingFilter.endTime ? [pingFilter.startTime, pingFilter.endTime] : undefined}
              onChange={(dates) => {
                if (Array.isArray(dates) && dates.length === 2 && dates[0] && dates[1]) {
                  setPingFilter(prev => ({
                    ...prev,
                    startTime: dates[0] as Date,
                    endTime: dates[1] as Date,
                  }))
                }
              }}
              style={{ width: '100%' }}
              placeholder="选择时间范围"
            />
            {/* 快捷时间按钮 */}
            <div style={{ marginTop: 8 }}>
              <Text type="tertiary" size="small" style={{ marginRight: 8 }}>快捷:</Text>
              <Space wrap spacing={4}>
                <Button size="small" onClick={() => setQuickTimeRange(1)}>1h</Button>
                <Button size="small" onClick={() => setQuickTimeRange(6)}>6h</Button>
                <Button size="small" onClick={() => setQuickTimeRange(24)}>24h</Button>
                <Button size="small" onClick={() => setQuickTimeRange(72)}>3d</Button>
                <Button size="small" onClick={() => setQuickTimeRange(168)}>7d</Button>
                <Button size="small" type="tertiary" onClick={() => setPingFilter(prev => ({ ...prev, startTime: null, endTime: null }))}>清除</Button>
              </Space>
            </div>
          </div>

          {/* 时间粒度 - 始终显示 */}
          <div style={{ marginBottom: 12 }}>
            <Text size="small" style={{ display: 'block', marginBottom: 4 }}>⏱️ 时间粒度</Text>
            <RadioGroup
              type="button"
              value={pingFilter.interval}
              onChange={(e) => setPingFilter(prev => ({ ...prev, interval: e.target.value }))}
            >
              <Radio value="minute">分钟</Radio>
              <Radio value="hour">小时</Radio>
              <Radio value="day">天</Radio>
            </RadioGroup>
          </div>

          {/* 图表类型 */}
          <div>
            <Text size="small" style={{ display: 'block', marginBottom: 4 }}>📈 图表类型</Text>
            <RadioGroup
              type="button"
              value={pingFilter.chartType}
              onChange={(e) => setPingFilter(prev => ({ ...prev, chartType: e.target.value }))}
            >
              <Radio value="auto">自动</Radio>
              <Radio value="bar">柱状图</Radio>
              <Radio value="line">折线图</Radio>
            </RadioGroup>
          </div>
        </div>

        {/* ===== 统计指标选择 ===== */}
        <div style={{ marginTop: 16, paddingTop: 12, marginBottom: 8, borderTop: '1px solid #eee' }}>
          <Text type="tertiary" size="small" style={{ display: 'block', marginBottom: 8 }}>📈 统计指标 (勾选要在图表中显示的指标)</Text>

          {/* 基础统计 */}
          <div style={{ marginBottom: 8 }}>
            <Text size="small" style={{ display: 'block', marginBottom: 4, color: '#666' }}>基础统计</Text>
            <CheckboxGroup
              value={pingFilter.selectedStats}
              onChange={(values) => setPingFilter(prev => ({ ...prev, selectedStats: values as string[] }))}
            >
              <Row gutter={[8, 4]}>
                {BASIC_STATISTICS_OPTIONS.map((opt) => (
                  <Col span={8} key={opt.value}>
                    <Checkbox value={opt.value}>{opt.label}</Checkbox>
                  </Col>
                ))}
              </Row>
            </CheckboxGroup>
          </div>

          {/* 高级统计 */}
          <div style={{ marginBottom: 8 }}>
            <Text size="small" style={{ display: 'block', marginBottom: 4, color: '#666' }}>高级统计</Text>
            <CheckboxGroup
              value={pingFilter.selectedStats}
              onChange={(values) => setPingFilter(prev => ({ ...prev, selectedStats: values as string[] }))}
            >
              <Row gutter={[8, 4]}>
                {ADVANCED_STATISTICS_OPTIONS.map((opt) => (
                  <Col span={12} key={opt.value}>
                    <Checkbox value={opt.value}>{opt.label}</Checkbox>
                  </Col>
                ))}
              </Row>
            </CheckboxGroup>
          </div>

          {/* 分位数 */}
          <div>
            <Text size="small" style={{ display: 'block', marginBottom: 4, color: '#666' }}>分位数</Text>
            <CheckboxGroup
              value={pingFilter.selectedStats}
              onChange={(values) => setPingFilter(prev => ({ ...prev, selectedStats: values as string[] }))}
            >
              <Row gutter={[8, 4]}>
                {PERCENTILE_OPTIONS.map((opt) => (
                  <Col span={6} key={opt.value}>
                    <Checkbox value={opt.value}>{opt.label}</Checkbox>
                  </Col>
                ))}
              </Row>
            </CheckboxGroup>
          </div>
        </div>

        {/* ===== 分位数分布图 ===== */}
        <div style={{
          marginTop: 16,
          padding: 16,
          borderRadius: 8,
          border: '2px solid #1890ff',
          background: 'linear-gradient(to bottom, #e6f7ff, #ffffff)',
          width: '100%',
          boxSizing: 'border-box'
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
            <div>
              <Title heading={6} style={{ margin: 0, color: '#1890ff' }}>📊 分位数分布图</Title>
              <Text type="tertiary" size="small">在主图表下方单独显示多条分位数曲线（启用后点击"执行查询"查看）</Text>
            </div>
            <RadioGroup
              type="button"
              value={pingFilter.percentileRange.enabled ? 'enabled' : 'disabled'}
              onChange={(e) => setPingFilter(prev => ({
                ...prev,
                percentileRange: { ...prev.percentileRange, enabled: e.target.value === 'enabled' }
              }))}
            >
              <Radio value="disabled">关闭</Radio>
              <Radio value="enabled">启用</Radio>
            </RadioGroup>
          </div>

          {pingFilter.percentileRange.enabled && (
            <div style={{ padding: 16, background: '#fafafa', borderRadius: 8 }}>
              {/* 分位数范围滑块 */}
              <div style={{ marginBottom: 16 }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
                  <Text size="small">分位数范围：</Text>
                  <Tag color="blue" size="large">
                    P{pingFilter.percentileRange.minPercentile} ~ P{pingFilter.percentileRange.maxPercentile}
                  </Tag>
                </div>
                <Slider
                  range
                  value={[pingFilter.percentileRange.minPercentile, pingFilter.percentileRange.maxPercentile]}
                  onChange={(value) => {
                    if (Array.isArray(value) && value.length === 2) {
                      setPingFilter(prev => ({
                        ...prev,
                        percentileRange: {
                          ...prev.percentileRange,
                          minPercentile: value[0] as number,
                          maxPercentile: value[1] as number,
                        }
                      }))
                    }
                  }}
                  min={0}
                  max={100}
                  step={1}
                />
              </div>

              {/* 步长 */}
              <div style={{ marginTop: 12 }}>
                <Text size="small" style={{ display: 'block', marginBottom: 4 }}>曲线间隔</Text>
                <Select
                  value={pingFilter.percentileRange.step}
                  onChange={(value) => setPingFilter(prev => ({
                    ...prev,
                    percentileRange: { ...prev.percentileRange, step: value as number }
                  }))}
                  style={{ width: '100%' }}
                >
                  <Select.Option value={1}>每 1% (最多100条线)</Select.Option>
                  <Select.Option value={2}>每 2% (最多50条线)</Select.Option>
                  <Select.Option value={5}>每 5% (最多20条线)</Select.Option>
                  <Select.Option value={10}>每 10% (最多10条线)</Select.Option>
                </Select>
              </div>

              {/* 预览信息 */}
              <div style={{ marginTop: 12, padding: '8px 12px', background: '#e6f7ff', borderRadius: 4, textAlign: 'center' }}>
                <Text size="small">
                  将绘制 <strong>{Math.max(1, Math.floor((pingFilter.percentileRange.maxPercentile - pingFilter.percentileRange.minPercentile) / pingFilter.percentileRange.step) + 1)}</strong> 条分位数曲线
                  <Text type="tertiary" size="small" style={{ marginLeft: 8 }}>
                    （颜色从蓝色渐变到红色）
                  </Text>
                </Text>
              </div>
            </div>
          )}
        </div>

        {/* ===== 极端值过滤 ===== */}
        <div style={{
          marginTop: 16,
          padding: 16,
          borderRadius: 8,
          border: '2px solid #52c41a',
          background: 'linear-gradient(to bottom, #f6ffed, #ffffff)',
          width: '100%',
          boxSizing: 'border-box'
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
            <div>
              <Title heading={6} style={{ margin: 0, color: '#52c41a' }}>🔧 极端值过滤</Title>
              <Text type="tertiary" size="small">过滤掉极端大或极端小的 RTT 值</Text>
            </div>
            <RadioGroup
              type="button"
              value={pingFilter.outlierFilterEnabled ? 'enabled' : 'disabled'}
              onChange={(e) => setPingFilter(prev => ({ ...prev, outlierFilterEnabled: e.target.value === 'enabled' }))}
            >
              <Radio value="disabled">关闭</Radio>
              <Radio value="enabled">开启</Radio>
            </RadioGroup>
          </div>
          {pingFilter.outlierFilterEnabled && (
            <div style={{ marginTop: 8, padding: 12, background: '#fff', borderRadius: 6, border: '1px solid #b7eb8f' }}>
              <Text type="tertiary" size="small" style={{ display: 'block', marginBottom: 8 }}>
                只分析 P{pingFilter.outlierFilterMin} 到 P{pingFilter.outlierFilterMax} 之间的数据
              </Text>
              <Slider
                range
                value={[pingFilter.outlierFilterMin, pingFilter.outlierFilterMax]}
                onChange={(value) => {
                  if (Array.isArray(value) && value.length === 2) {
                    setPingFilter(prev => ({
                      ...prev,
                      outlierFilterMin: value[0] as number,
                      outlierFilterMax: value[1] as number,
                    }))
                  }
                }}
                min={0}
                max={100}
              />
              <Space wrap style={{ marginTop: 8 }} spacing={4}>
                <Button size="small" onClick={() => setPingFilter(prev => ({ ...prev, outlierFilterMin: 5, outlierFilterMax: 95 }))}>
                  P5-P95
                </Button>
                <Button size="small" onClick={() => setPingFilter(prev => ({ ...prev, outlierFilterMin: 10, outlierFilterMax: 90 }))}>
                  P10-P90
                </Button>
                <Button size="small" onClick={() => setPingFilter(prev => ({ ...prev, outlierFilterMin: 25, outlierFilterMax: 75 }))}>
                  P25-P75
                </Button>
              </Space>
            </div>
          )}
        </div>

        {/* ===== 高级筛选（折叠面板） ===== */}
        <Collapse accordion>
          <Collapse.Panel header="🔍 高级筛选 (AS/ASGeo/数据中心/IP前缀/运营商)" itemKey="advanced">
            <div style={{ width: '100%' }}>
              {/* 运营商筛选 - 从数据库动态获取 */}
              <div style={{ marginBottom: 16, width: '100%' }}>
                <Text size="small" style={{ display: 'block', marginBottom: 4 }}>📡 运营商 (ISP)</Text>
                <Select
                  style={{ width: '100%' }}
                  placeholder="搜索或选择运营商..."
                  filter
                  showClear
                  onSearch={(value) => searchIsp(value)}
                  onFocus={() => {
                    if (ispOptions.length === 0) searchIsp('')
                  }}
                  value={pingFilter.isp || undefined}
                  onChange={(value) => setPingFilter(prev => ({ ...prev, isp: value ? String(value) : null }))}
                  loading={ispOptionsLoading}
                >
                  {ispOptions.map((item) => (
                    <Select.Option key={item.isp} value={item.isp}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <span>{item.isp}</span>
                        <Text type="tertiary" size="small">{item.sample_count?.toLocaleString()}</Text>
                      </div>
                    </Select.Option>
                  ))}
                </Select>
              </div>

              {/* AS 号筛选 */}
              <div style={{ marginBottom: 16, width: '100%' }}>
                <Text size="small" style={{ display: 'block', marginBottom: 4 }}>🌐 AS 号</Text>
                <Select
                  style={{ width: '100%' }}
                  placeholder="搜索或选择 AS..."
                  filter
                  showClear
                  onSearch={(value) => searchAs(value)}
                  value={pingFilter.asn || undefined}
                  onChange={(value) => setPingFilter(prev => ({
                    ...prev,
                    asn: value ? Number(value) : null,
                    asgeo: null  // 选择 AS 时清除 ASGeo
                  }))}
                  loading={asOptionsLoading}
                >
                  {asOptions.map((item) => (
                    <Select.Option key={item.asn} value={item.asn}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <span>AS{item.asn} {item.as_name ? `- ${item.as_name.substring(0, 30)}${item.as_name.length > 30 ? '...' : ''}` : ''}</span>
                        <Text type="tertiary" size="small">{item.sample_count?.toLocaleString()}</Text>
                      </div>
                    </Select.Option>
                  ))}
                </Select>
              </div>

              {/* ASGeo 筛选 */}
              <div style={{ marginBottom: 16, width: '100%' }}>
                <Text size="small" style={{ display: 'block', marginBottom: 4 }}>🗺️ ASGeo (包含 AS + 地理位置信息)</Text>
                <Select
                  style={{ width: '100%' }}
                  placeholder="搜索或选择 ASGeo..."
                  filter
                  showClear
                  onSearch={(value) => searchAsgeo(value)}
                  value={pingFilter.asgeo || undefined}
                  onChange={(value) => setPingFilter(prev => ({
                    ...prev,
                    asgeo: value ? String(value) : null,
                    asn: null  // 选择 ASGeo 时清除 AS
                  }))}
                  loading={asgeoOptionsLoading}
                >
                  {asgeoOptions.map((item) => (
                    <Select.Option key={item.asgeo} value={item.asgeo}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <span>{item.asgeo}</span>
                        <Text type="tertiary" size="small">{item.sample_count?.toLocaleString()}</Text>
                      </div>
                    </Select.Option>
                  ))}
                </Select>
              </div>

              {/* 数据中心筛选 */}
              <div style={{ marginBottom: 16, width: '100%' }}>
                <Text size="small" style={{ display: 'block', marginBottom: 4 }}>🏢 数据中心</Text>
                <Select
                  style={{ width: '100%' }}
                  placeholder="搜索或选择数据中心..."
                  filter
                  showClear
                  onSearch={(value) => searchDataCenter(value)}
                  value={pingFilter.dataCenter || undefined}
                  onChange={(value) => setPingFilter(prev => ({ ...prev, dataCenter: value ? String(value) : null }))}
                  loading={dcOptionsLoading}
                >
                  {dcOptions.map((item) => (
                    <Select.Option key={item.data_center} value={item.data_center}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <span>{item.data_center}</span>
                        <Text type="tertiary" size="small">{item.sample_count?.toLocaleString()}</Text>
                      </div>
                    </Select.Option>
                  ))}
                </Select>
              </div>

              {/* IP 前缀筛选 */}
              <div style={{ width: '100%' }}>
                <Text size="small" style={{ display: 'block', marginBottom: 4 }}>🔢 IP 前缀 (/24)</Text>
                <Select
                  style={{ width: '100%' }}
                  placeholder="搜索或选择前缀..."
                  filter
                  showClear
                  onSearch={(value) => searchPrefix24(value)}
                  value={pingFilter.prefix24 || undefined}
                  onChange={(value) => setPingFilter(prev => ({ ...prev, prefix24: value ? String(value) : null }))}
                  loading={prefix24OptionsLoading}
                >
                  {prefix24Options.map((item) => (
                    <Select.Option key={item.prefix24} value={item.prefix24}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <span>{item.prefix24}.0/24</span>
                        <Text type="tertiary" size="small">{item.sample_count?.toLocaleString()} | {item.unique_ips} IPs</Text>
                      </div>
                    </Select.Option>
                  ))}
                </Select>
              </div>
            </div>
          </Collapse.Panel>
        </Collapse>
      </div>
    </Card>
  )

  return (
    <div className="visualization-page">
      <div className="page-header">
        <Title heading={3}>数据可视化分析</Title>
        <Space>
          {renderDbStatus()}
          <Button icon={<IconRefresh />} onClick={() => loadRegions(true)} loading={regionsLoading}>
            刷新连接
          </Button>
        </Space>
      </div>

      {/* 数据库状态提示 */}
      {dbStatus === 'disconnected' && (
        <Banner
          type="warning"
          icon={<IconServer />}
          title="数据库未连接"
          description={
            <div>
              <p>无法连接到 ClickHouse 数据库，可视化功能将无法使用。</p>
              <p>请前往 <a href="/settings">设置页面</a> 检查数据库配置</p>
            </div>
          }
          style={{ marginBottom: 16 }}
        />
      )}

      <div className="visualization-tabs-wrapper">
        <Tabs activeKey={activeTab} onChange={setActiveTab}>
          {/* ===== Ping 数据分析 ===== */}
          <TabPane tab={<><IconActivity /> Ping 数据分析</>} itemKey="ping">
            <div className="query-layout">
              {/* 左侧筛选面板 */}
              {showFilters && (
                <div className="filter-sider">
                  {renderPingFilterPanel()}
                  <Button
                    type="primary"
                    theme="solid"
                    block
                    size="large"
                    onClick={executePingQuery}
                    loading={queryLoading}
                    disabled={!pingFilter.region || dbStatus !== 'connected'}
                  >
                    执行查询
                  </Button>
                </div>
              )}

              {/* 右侧内容区 */}
              <div className="query-content">
                {/* 工具栏 */}
                <Card className="toolbar-card">
                  <Space style={{ width: '100%', justifyContent: 'space-between' }}>
                    <Space>
                      <Button
                        icon={<IconFilter />}
                        onClick={() => setShowFilters(!showFilters)}
                      >
                        {showFilters ? '隐藏筛选' : '显示筛选'}
                      </Button>
                      {/* 图表视图切换 - 仅当启用分位数时显示 */}
                      {pingFilter.percentileRange.enabled && percentileRangeData && (
                        <RadioGroup
                          type="button"
                          value={chartViewMode}
                          onChange={(e) => setChartViewMode(e.target.value as 'trend' | 'percentile')}
                          style={{ marginLeft: 16 }}
                        >
                          <Radio value="trend">📈 时间趋势图</Radio>
                          <Radio value="percentile">📊 分位数分布图</Radio>
                        </RadioGroup>
                      )}
                    </Space>
                    <Space wrap spacing={4}>
                      {pingFilter.region && <Tag color="blue">{pingFilter.region}</Tag>}
                      <Tag color="green">时间趋势</Tag>
                      {pingFilter.asn && <Tag color="cyan">AS: {pingFilter.asn}</Tag>}
                      {pingFilter.asgeo && <Tag color="teal">ASGeo: {pingFilter.asgeo}</Tag>}
                      {pingFilter.dataCenter && <Tag color="violet">DC: {pingFilter.dataCenter}</Tag>}
                      {pingFilter.prefix24 && <Tag color="purple">前缀: {pingFilter.prefix24}</Tag>}
                      {pingFilter.isp && <Tag color="orange">ISP: {pingFilter.isp}</Tag>}
                      {pingFilter.percentileRange.enabled && (
                        <Tag color="pink">📊 P{pingFilter.percentileRange.minPercentile}-P{pingFilter.percentileRange.maxPercentile}</Tag>
                      )}
                      {pingFilter.selectedStats.length > 0 && (
                        <Tag color="purple">{pingFilter.selectedStats.length} 个指标</Tag>
                      )}
                    </Space>
                  </Space>
                </Card>

                {/* 图表展示 */}
                {queryLoading ? (
                  <QueryProgress
                    status="querying"
                    progress={queryProgress}
                    currentStep={queryStep}
                    totalSteps={5}
                    currentStepIndex={queryStepIndex}
                    onCancel={cancelQuery}
                    startTime={queryStartTime}
                  />
                ) : chartData ? (
                  <div style={{ display: 'flex', flexDirection: 'column', minHeight: 400 }}>
                    {/* 根据视图模式显示不同图表 */}
                    {chartViewMode === 'trend' ? (
                      <div style={{ maxHeight: 500, overflowY: 'auto', border: '1px solid #e8e8e8', borderRadius: 4 }}>
                        <ChartDisplay
                          data={chartData}
                          loading={queryLoading}
                          height={400}
                        />
                      </div>
                    ) : (
                      /* 分位数分布图 */
                      <div style={{ marginTop: 16 }}>
                        <div style={{
                          background: '#e6f7ff',
                          padding: '8px 16px',
                          borderRadius: '8px 8px 0 0',
                          border: '2px solid #1890ff',
                          borderBottom: 'none'
                        }}>
                          <Text style={{ color: '#1890ff', fontWeight: 'bold' }}>
                            📊 分位数分布图 (P{pingFilter.percentileRange.minPercentile} - P{pingFilter.percentileRange.maxPercentile})
                            {percentileRangeLoading && ' - 加载中...'}
                            {!percentileRangeLoading && percentileRangeData && ' - 数据已就绪'}
                            {!percentileRangeLoading && !percentileRangeData && ' - 无数据'}
                          </Text>
                        </div>
                        <PercentileRangeChart
                          data={percentileRangeData}
                          loading={percentileRangeLoading}
                          height={400}
                          chartType={(chartData?.chartType === 'line' || chartData?.chartType === 'bar') ? chartData.chartType : 'line'}
                        />
                        {/* 调试信息 */}
                        {!percentileRangeLoading && !percentileRangeData && (
                          <div style={{ padding: 20, background: '#fff7e6', border: '1px solid #ffd591', borderRadius: '0 0 8px 8px' }}>
                            <Text type="warning">⚠️ 分位数数据未加载，可能原因：</Text>
                            <ul style={{ margin: '8px 0', paddingLeft: 20, color: '#666' }}>
                              <li>查询请求失败 - 请检查控制台 Network 面板</li>
                              <li>后端返回数据格式不正确 - 请查看控制台 Console</li>
                              <li>统计指标中没有选择分位数 - 请确保选择了分位数</li>
                            </ul>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                ) : (
                  <Card className="chart-placeholder">
                    <Empty
                      title={dbStatus === 'connected' ? "选择筛选条件" : "数据库未连接"}
                      description={
                        dbStatus === 'connected'
                          ? "请选择地区和分析维度，然后点击执行查询"
                          : "请先连接数据库"
                      }
                      style={{ padding: 60 }}
                    />
                  </Card>
                )}

                {/* 统计摘要卡片 - 整体分析时显示高级统计 */}
                {queryResult && queryResult.statistics && !Array.isArray(queryResult.statistics) && (
                  <Card style={{ marginTop: 16 }}>
                    <Title heading={6}>高级统计指标</Title>
                    <Row gutter={[16, 16]} style={{ marginTop: 12 }}>
                      <Col span={6}>
                        <div style={{ textAlign: 'center', padding: 12, background: '#f5f5f5', borderRadius: 8 }}>
                          <Text type="tertiary" size="small">变异系数 (CV)</Text>
                          <div style={{ fontSize: 20, fontWeight: 'bold', color: queryResult.statistics.coefficient_of_variation > 1 ? '#e74c3c' : '#27ae60' }}>
                            {((queryResult.statistics.coefficient_of_variation || 0) * 100).toFixed(1)}%
                          </div>
                          <Text type="tertiary" size="small">标准差/均值</Text>
                        </div>
                      </Col>
                      <Col span={6}>
                        <div style={{ textAlign: 'center', padding: 12, background: '#f5f5f5', borderRadius: 8 }}>
                          <Text type="tertiary" size="small">偏度 (Skewness)</Text>
                          <div style={{ fontSize: 20, fontWeight: 'bold' }}>
                            {(queryResult.statistics.skewness || 0).toFixed(3)}
                          </div>
                          <Text type="tertiary" size="small">
                            {Math.abs(queryResult.statistics.skewness || 0) > 1 ? '偏态分布' : '近似对称'}
                          </Text>
                        </div>
                      </Col>
                      <Col span={6}>
                        <div style={{ textAlign: 'center', padding: 12, background: '#f5f5f5', borderRadius: 8 }}>
                          <Text type="tertiary" size="small">峰度 (Kurtosis)</Text>
                          <div style={{ fontSize: 20, fontWeight: 'bold' }}>
                            {(queryResult.statistics.kurtosis || 0).toFixed(3)}
                          </div>
                          <Text type="tertiary" size="small">
                            {(queryResult.statistics.kurtosis || 0) > 3 ? '尖峰分布' : '平峰分布'}
                          </Text>
                        </div>
                      </Col>
                      <Col span={6}>
                        <div style={{ textAlign: 'center', padding: 12, background: '#f5f5f5', borderRadius: 8 }}>
                          <Text type="tertiary" size="small">四分位距 (IQR)</Text>
                          <div style={{ fontSize: 20, fontWeight: 'bold', color: '#3498db' }}>
                            {(queryResult.statistics.iqr || 0).toFixed(2)} ms
                          </div>
                          <Text type="tertiary" size="small">P75 - P25</Text>
                        </div>
                      </Col>
                    </Row>
                    {queryResult.statistics.trimmed_mean && (
                      <div style={{ marginTop: 12, textAlign: 'center' }}>
                        <Tag color="cyan" size="large">
                          截尾均值 (P{queryResult.statistics.trimmed_percentile_range?.min}-P{queryResult.statistics.trimmed_percentile_range?.max}): {queryResult.statistics.trimmed_mean.toFixed(2)} ms
                        </Tag>
                      </div>
                    )}
                  </Card>
                )}

                {/* 数据表格 */}
                {queryResult && (queryResult.statistics || queryResult.paths)?.length > 0 && (
                  <DataTable
                    data={Array.isArray(queryResult.statistics) ? queryResult.statistics : [queryResult.statistics]}
                    title="查询结果详情"
                    loading={queryLoading}
                  />
                )}
              </div>
            </div>
          </TabPane>

          {/* ===== Traceroute 路径分析 ===== */}
          <TabPane tab={<><IconLink /> Traceroute 分析</>} itemKey="traceroute">
            <div className="traceroute-content-scroll">
              {/* 顶部控制栏 */}
              <Card style={{ marginBottom: 16, position: 'sticky', top: 0, zIndex: 10, background: '#fff' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 12 }}>
                  <Space wrap>
                    <Text type="tertiary">地区:</Text>
                    <Select
                      value={tracerouteFilter.region}
                      onChange={(value) => {
                        setTracerouteFilter(prev => ({ ...prev, region: String(value || '') }))
                        setTraceAnalysisStarted(false)
                        setTraceTerminalData(null)
                        setTracePathData(null)
                        setTraceDetailData(null)
                        setTracePingData(null)
                      }}
                      placeholder="选择地区"
                      style={{ width: 180 }}
                      filter
                    >
                      {regions.map((region) => (
                        <Select.Option key={region} value={region}>{region}</Select.Option>
                      ))}
                    </Select>

                    <Text type="tertiary">时间范围:</Text>
                    <DatePicker
                      type="dateTimeRange"
                      value={tracerouteFilter.startTime && tracerouteFilter.endTime ? [tracerouteFilter.startTime, tracerouteFilter.endTime] : undefined}
                      onChange={(dates) => {
                        if (Array.isArray(dates) && dates.length === 2 && dates[0] && dates[1]) {
                          setTracerouteFilter(prev => ({ ...prev, startTime: dates[0] as Date, endTime: dates[1] as Date }))
                        } else {
                          setTracerouteFilter(prev => ({ ...prev, startTime: null, endTime: null }))
                        }
                      }}
                      style={{ width: 320 }}
                      placeholder="可选时间范围"
                    />

                    <Text type="tertiary">数据中心:</Text>
                    <Select
                      value={tracerouteFilter.dataCenter || undefined}
                      onChange={(value) => {
                        setTracerouteFilter(prev => ({ ...prev, dataCenter: value ? String(value) : null }))
                        setTraceAnalysisStarted(false)
                        setTraceTerminalData(null)
                        setTracePathData(null)
                      }}
                      placeholder="全部数据中心"
                      style={{ width: 150 }}
                      showClear
                      loading={tracerouteDcLoading}
                    >
                      {tracerouteDcOptions.map((dc) => (
                        <Select.Option key={dc} value={dc}>{dc}</Select.Option>
                      ))}
                    </Select>

                    <Text type="tertiary">数据类型:</Text>
                    <Select
                      value={tracerouteFilter.traceType}
                      onChange={(value) => {
                        setTracerouteFilter(prev => ({ ...prev, traceType: value as 'quarter' | 'full' }))
                        setTraceAnalysisStarted(false)
                        setTraceTerminalData(null)
                        setTracePathData(null)
                      }}
                      style={{ width: 130 }}
                    >
                      <Select.Option value="quarter">1/4 抽样</Select.Option>
                      <Select.Option value="full">全量数据</Select.Option>
                    </Select>
                  </Space>

                  <Space>
                    {traceAnalysisStarted && (
                      <Button
                        icon={<IconRefresh />}
                        onClick={() => {
                          if (traceSubTab === 'terminals') loadTraceTerminals()
                          else if (traceSubTab === 'paths') loadTracePaths()
                          else if (traceSubTab === 'detail' && traceDetailPath) loadTraceDetail()
                          else if (traceSubTab === 'ping' && tracePingPath) loadTracePing()
                        }}
                      >
                        刷新
                      </Button>
                    )}
                    <Button
                      type="primary"
                      theme="solid"
                      disabled={!tracerouteFilter.region || dbStatus !== 'connected'}
                      onClick={() => {
                        setTraceAnalysisStarted(true)
                        loadTraceTerminals()
                        loadTracePaths()
                      }}
                    >
                      {traceAnalysisStarted ? '重新分析' : '开始分析'}
                    </Button>
                  </Space>
                </div>
              </Card>

              {/* 分析内容区 */}
              {traceAnalysisStarted && tracerouteFilter.region ? (
                <Tabs
                  type="card"
                  activeKey={traceSubTab}
                  onChange={(key) => setTraceSubTab(key)}
                >
                  {/* 末端节点分析 */}
                  <TabPane tab={<><IconServer /> 末端节点</>} itemKey="terminals">
                    <Card style={{ marginBottom: 16 }}>
                      <Space>
                        <Text type="tertiary">类型:</Text>
                        <RadioGroup type="button" value={traceTerminalType} onChange={(e) => setTraceTerminalType(e.target.value)}>
                          <Radio value="asgeo">AS+Geo</Radio>
                          <Radio value="as">AS</Radio>
                        </RadioGroup>
                        <Text type="tertiary">搜索:</Text>
                        <Input placeholder="搜索末端节点..." value={traceTerminalSearch} onChange={(e) => setTraceTerminalSearch(e)} style={{ width: 200 }} onKeyPress={(e) => e.key === 'Enter' && loadTraceTerminals()} />
                        <Button onClick={loadTraceTerminals} loading={traceTerminalLoading}>查询</Button>
                      </Space>
                    </Card>

                    {traceTerminalLoading ? (
                      <Card style={{ padding: 60, textAlign: 'center' }}><Spin size="large" /></Card>
                    ) : traceTerminalData ? (
                      <>
                        <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
                          <Col span={6}><Card className="metric-card"><Text type="tertiary">总路径数</Text><div className="metric-value">{traceTerminalData.total_traces?.toLocaleString()}</div></Card></Col>
                          <Col span={6}><Card className="metric-card"><Text type="tertiary">末端节点</Text><div className="metric-value">{traceTerminalData.unique_terminals}</div></Card></Col>
                        </Row>
                        <Card title={`末端节点列表 (${traceTerminalData.terminals?.length || 0})`}>
                          <Table
                            dataSource={traceTerminalData.terminals || []}
                            columns={[
                              { title: '末端节点', dataIndex: 'terminal', render: (t: string) => <Text strong style={{ fontFamily: 'monospace' }}>{t}</Text> },
                              { title: '路径数', dataIndex: 'trace_count', width: 100, render: (c: number) => <Tag color="blue">{c?.toLocaleString()}</Tag> },
                              { title: '独立路径', dataIndex: 'path_count', width: 90, render: (c: number) => <Tag color="cyan">{c?.toLocaleString()}</Tag> },
                              { title: 'Prefix24数', dataIndex: 'prefix24_count', width: 90 },
                              { title: '操作', width: 100, render: (_: any, record: any) => <Button size="small" onClick={() => { setTracePathFilter(record.terminal); setTraceSubTab('paths') }}>查看路径</Button> },
                            ]}
                            pagination={{ pageSize: 15 }}
                            rowKey="terminal"
                            expandedRowRender={(record) => (
                              <div style={{ padding: '8px 16px' }}>
                                <Text type="tertiary" size="small">关联路径 (Top 20):</Text>
                                <Table
                                  dataSource={record.sample_paths || []}
                                  columns={[
                                    {
                                      title: '路径',
                                      dataIndex: 'path',
                                      render: (path: string) => (
                                        <Text
                                          link
                                          style={{ fontSize: 11, fontFamily: 'monospace' }}
                                          onClick={() => {
                                            setTraceDetailPath(path)
                                            setTraceDetailType(traceTerminalType)
                                            setTraceSubTab('detail')
                                            loadTraceDetail(path, traceTerminalType)
                                          }}
                                        >
                                          {path?.length > 80 ? path.substring(0, 80) + '...' : path}
                                        </Text>
                                      )
                                    },
                                    { title: '数量', dataIndex: 'count', width: 80, render: (c: number) => <Tag size="small">{c?.toLocaleString()}</Tag> },
                                    {
                                      title: '操作',
                                      width: 180,
                                      render: (_: any, rec: any) => (
                                        <Space>
                                          <Button size="small" onClick={() => {
                                            setTraceDetailPath(rec.path)
                                            setTraceDetailType(traceTerminalType)
                                            setTraceSubTab('detail')
                                            loadTraceDetail(rec.path, traceTerminalType)
                                          }}>详情</Button>
                                          <Button size="small" type="primary" onClick={() => {
                                            setTracePingPath(rec.path)
                                            setTracePingType(traceTerminalType)
                                            setTraceSubTab('ping')
                                            loadTracePingFilterOptions(rec.path, traceTerminalType)
                                          }}>Ping分析</Button>
                                        </Space>
                                      )
                                    },
                                  ]}
                                  pagination={false}
                                  size="small"
                                  rowKey="path"
                                />
                              </div>
                            )}
                          />
                        </Card>
                      </>
                    ) : (
                      <Card style={{ padding: 60 }}><Empty description="点击查询加载数据" /></Card>
                    )}
                  </TabPane>

                  {/* 路径分析 */}
                  <TabPane tab={<><IconLink /> 路径分析</>} itemKey="paths">
                    <Card style={{ marginBottom: 16 }}>
                      <Space>
                        <Text type="tertiary">路径类型:</Text>
                        <RadioGroup type="button" value={tracePathType} onChange={(e) => setTracePathType(e.target.value)}>
                          <Radio value="as">AS 路径</Radio>
                          <Radio value="asgeo">ASGeo 路径</Radio>
                        </RadioGroup>
                        <Text type="tertiary">末端筛选:</Text>
                        <Input placeholder="输入末端节点..." value={tracePathFilter} onChange={(e) => setTracePathFilter(e)} style={{ width: 180 }} onKeyPress={(e) => e.key === 'Enter' && loadTracePaths()} />
                        <Button onClick={loadTracePaths} loading={tracePathLoading}>查询</Button>
                        {tracePathFilter && <Tag color="blue" closable onClose={() => { setTracePathFilter(''); loadTracePaths() }}>{tracePathFilter}</Tag>}
                      </Space>
                    </Card>

                    {tracePathLoading ? (
                      <Card style={{ padding: 60, textAlign: 'center' }}><Spin size="large" /></Card>
                    ) : tracePathData ? (
                      <>
                        <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
                          <Col span={6}><Card className="metric-card"><Text type="tertiary">总路径数</Text><div className="metric-value">{tracePathData.total_traces?.toLocaleString()}</div></Card></Col>
                          <Col span={6}><Card className="metric-card"><Text type="tertiary">独立路径</Text><div className="metric-value">{tracePathData.unique_paths}</div></Card></Col>
                        </Row>
                        <Card title="路径列表">
                          <Table
                            dataSource={tracePathData.paths || []}
                            columns={[
                              { title: '路径', dataIndex: 'path', render: (t: string) => <Text style={{ fontSize: 11, fontFamily: 'monospace' }}>{t?.length > 60 ? t.substring(0, 60) + '...' : t}</Text> },
                              { title: '路径数', dataIndex: 'occurrence_count', width: 80, render: (c: number) => <Tag color="blue">{c?.toLocaleString()}</Tag> },
                              { title: '操作', width: 140, render: (_: any, record: any) => (
                                <Space>
                                  <Button size="small" onClick={() => { setTraceDetailPath(record.path); setTraceDetailType(tracePathType); setTraceSubTab('detail'); loadTraceDetail(record.path, tracePathType) }}>详情</Button>
                                  <Button size="small" type="primary" onClick={() => { setTracePingPath(record.path); setTracePingType(tracePathType); setTraceSubTab('ping'); loadTracePingFilterOptions(record.path, tracePathType) }}>Ping</Button>
                                </Space>
                              )},
                            ]}
                            pagination={{ pageSize: 20 }}
                            rowKey="path"
                          />
                        </Card>
                      </>
                    ) : (
                      <Card style={{ padding: 60 }}><Empty description="点击查询加载数据" /></Card>
                    )}
                  </TabPane>

                  {/* 路径详情 */}
                  <TabPane tab={<><IconSearch /> 路径详情</>} itemKey="detail">
                    <Card style={{ marginBottom: 16 }}>
                      <Space>
                        <Text type="tertiary">类型:</Text>
                        <RadioGroup type="button" value={traceDetailType} onChange={(e) => { setTraceDetailType(e.target.value); setTraceDetailPath(''); setTraceDetailData(null) }}>
                          <Radio value="as">AS</Radio>
                          <Radio value="asgeo">ASGeo</Radio>
                        </RadioGroup>
                        <Text type="tertiary">路径:</Text>
                        <Select
                          style={{ width: 400 }}
                          placeholder="搜索并选择路径..."
                          filter
                          showClear
                          onSearch={(value) => searchTracePaths(value, traceDetailType)}
                          value={traceDetailPath || undefined}
                          onChange={(value) => setTraceDetailPath(String(value || ''))}
                          loading={tracePathOptionsLoading}
                        >
                          {tracePathOptions.map((item) => (
                            <Select.Option key={item.path} value={item.path}>
                              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                <Text style={{ fontSize: 11, fontFamily: 'monospace' }}>{item.path?.length > 50 ? item.path.substring(0, 50) + '...' : item.path}</Text>
                                <Text type="tertiary" size="small">{item.trace_count}条</Text>
                              </div>
                            </Select.Option>
                          ))}
                        </Select>
                        <Button type="primary" onClick={() => loadTraceDetail()} loading={traceDetailLoading} disabled={!traceDetailPath}>查询</Button>
                      </Space>
                    </Card>

                    {traceDetailLoading ? (
                      <Card style={{ padding: 60, textAlign: 'center' }}><Spin size="large" /></Card>
                    ) : traceDetailData ? (
                      <>
                        <Card style={{ marginBottom: 16 }}>
                          <Text type="tertiary" size="small">路径</Text>
                          <div style={{ marginTop: 4, marginBottom: 12 }}>
                            <Text strong style={{ fontFamily: 'monospace', fontSize: 12 }}>{traceDetailData.path}</Text>
                          </div>
                          <Row gutter={16}>
                            <Col span={8}><Text type="tertiary" size="small">总路径数</Text><div style={{ fontSize: 18, fontWeight: 'bold' }}>{traceDetailData.total_traces?.toLocaleString()}</div></Col>
                            <Col span={8}><Text type="tertiary" size="small">末端节点</Text><div style={{ fontSize: 18, fontWeight: 'bold' }}>{traceDetailData.unique_terminals}</div></Col>
                            <Col span={8}><Text type="tertiary" size="small">Prefix24数</Text><div style={{ fontSize: 18, fontWeight: 'bold' }}>{traceDetailData.unique_prefix24s}</div></Col>
                          </Row>
                          <Divider margin="12px" />
                          <Button type="primary" icon={<IconLineChartStroked />} onClick={() => { setTracePingPath(traceDetailData.path); setTracePingType(traceDetailType); setTraceSubTab('ping'); loadTracePingFilterOptions(traceDetailData.path, traceDetailType) }} disabled={!traceDetailData.prefix24s?.length}>查看 Ping 时序</Button>
                        </Card>
                        <Tabs type="card">
                          <TabPane tab={<><IconServer /> 末端 ({traceDetailData.terminals?.length || 0})</>} itemKey="terminals">
                            <Table dataSource={traceDetailData.terminals || []} columns={[
                              { title: '末端', dataIndex: 'terminal', render: (t: string) => <Text style={{ fontFamily: 'monospace' }}>{t}</Text> },
                              { title: '路径数', dataIndex: 'trace_count', width: 100, render: (c: number) => <Tag color="blue">{c}</Tag> },
                              { title: 'Prefix24数', dataIndex: 'prefix24_count', width: 100 },
                            ]} pagination={{ pageSize: 10 }} rowKey="terminal" size="small" />
                          </TabPane>
                          <TabPane tab={<><IconLink /> Prefix24 ({traceDetailData.prefix24s?.length || 0})</>} itemKey="prefix24s">
                            <Table dataSource={traceDetailData.prefix24s || []} columns={[
                              { title: 'Prefix24', dataIndex: 'prefix24', render: (t: string) => <Text style={{ fontFamily: 'monospace' }}>{t}</Text> },
                              { title: '路径数', dataIndex: 'trace_count', width: 80 },
                              { title: '独立IP', dataIndex: 'unique_ips', width: 80 },
                            ]} pagination={{ pageSize: 10 }} rowKey="prefix24" size="small" />
                          </TabPane>
                          <TabPane tab={<><IconHome /> 数据中心 ({traceDetailData.data_centers?.length || 0})</>} itemKey="dc">
                            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                              {traceDetailData.data_centers?.map((item: any, idx: number) => (
                                <Tag key={idx} color={idx < 3 ? 'blue' : 'grey'} size="large">{item.data_center} ({item.count})</Tag>
                              ))}
                            </div>
                          </TabPane>
                        </Tabs>
                      </>
                    ) : (
                      <Card style={{ padding: 60 }}><Empty description="输入路径进行查询" /></Card>
                    )}
                  </TabPane>

                  {/* Ping 时序 */}
                  <TabPane tab={<><IconLineChartStroked /> Ping 时序</>} itemKey="ping">
                    {/* 基础配置 */}
                    <Card style={{ marginBottom: 16 }}>
                      <Space wrap>
                        <Text type="tertiary">类型:</Text>
                        <RadioGroup type="button" value={tracePingType} onChange={(e) => { setTracePingType(e.target.value); setTracePingPath(''); setTracePingData(null); setTracePingFilterOptions({ asOptions: [], asgeoOptions: [], ispOptions: [], dataCenterOptions: [], prefix24Options: [] }) }}>
                          <Radio value="as">AS</Radio>
                          <Radio value="asgeo">ASGeo</Radio>
                        </RadioGroup>
                        <Text type="tertiary">路径:</Text>
                        <Select
                          style={{ width: 350 }}
                          placeholder="搜索并选择路径..."
                          filter
                          showClear
                          onSearch={(value) => searchTracePaths(value, tracePingType)}
                          onFocus={() => {
                            // 聚焦时自动加载路径选项
                            if (tracePathOptions.length === 0) {
                              searchTracePaths('', tracePingType)
                            }
                          }}
                          value={tracePingPath || undefined}
                          onChange={(value) => {
                            const newPath = String(value || '')
                            setTracePingPath(newPath)
                            setTracePingData(null)
                            setTracePingFilterOptions({ asOptions: [], asgeoOptions: [], ispOptions: [], dataCenterOptions: [], prefix24Options: [] })
                            if (value) {
                              loadTracePingFilterOptions(newPath)
                            }
                          }}
                          loading={tracePathOptionsLoading}
                        >
                          {tracePathOptions.map((item) => (
                            <Select.Option key={item.path} value={item.path}>
                              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                <Text style={{ fontSize: 11, fontFamily: 'monospace' }}>{item.path?.length > 45 ? item.path.substring(0, 45) + '...' : item.path}</Text>
                                <Text type="tertiary" size="small">{item.trace_count}条</Text>
                              </div>
                            </Select.Option>
                          ))}
                        </Select>
                        <Text type="tertiary">粒度:</Text>
                        <RadioGroup type="button" value={tracePingInterval} onChange={(e) => setTracePingInterval(e.target.value)}>
                          <Radio value="minute">分钟</Radio>
                          <Radio value="hour">小时</Radio>
                          <Radio value="day">天</Radio>
                        </RadioGroup>
                        <Button type="primary" onClick={loadTracePing} loading={tracePingLoading} disabled={!tracePingPath}>分析</Button>
                      </Space>
                    </Card>

                    {/* 高级筛选（有路径时显示） */}
                    {tracePingPath && (
                      <Collapse style={{ marginBottom: 16 }} defaultActiveKey={['filter']}>
                        <Collapse.Panel header={`🔍 筛选 ${tracePingFilterOptionsLoading ? '(加载中...)' : `(此路径关联 ${tracePingFilterOptions.asOptions.length} 个 AS, ${tracePingFilterOptions.asgeoOptions.length} 个 ASGeo, ${tracePingFilterOptions.ispOptions.length} 个运营商)`}`} itemKey="filter">
                          {tracePingFilterOptionsLoading ? (
                            <div style={{ padding: 20, textAlign: 'center' }}><Spin /></div>
                          ) : (
                          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 16 }}>
                            {/* AS 筛选 */}
                            <div style={{ minWidth: 200 }}>
                              <Text size="small" style={{ display: 'block', marginBottom: 4 }}>🌐 AS 号 ({tracePingFilterOptions.asOptions.length})</Text>
                              <Select
                                style={{ width: '100%' }}
                                placeholder="选择 AS..."
                                filter
                                showClear
                                getPopupContainer={() => document.body}
                                value={tracePingFilter.asn || undefined}
                                onChange={(value) => setTracePingFilter(prev => ({ ...prev, asn: value ? Number(value) : null, asgeo: null }))}
                                loading={tracePingFilterOptionsLoading}
                              >
                                {tracePingFilterOptions.asOptions.map((item) => (
                                  <Select.Option key={item.asn} value={item.asn}>
                                    AS{item.asn} {item.as_name?.substring(0, 15)} ({item.sample_count?.toLocaleString()})
                                  </Select.Option>
                                ))}
                              </Select>
                            </div>

                            {/* ASGeo 筛选 */}
                            <div style={{ minWidth: 200 }}>
                              <Text size="small" style={{ display: 'block', marginBottom: 4 }}>🌍 AS+Geo ({tracePingFilterOptions.asgeoOptions.length})</Text>
                              <Select
                                style={{ width: '100%' }}
                                placeholder="选择 ASGeo..."
                                filter
                                showClear
                                getPopupContainer={() => document.body}
                                value={tracePingFilter.asgeo || undefined}
                                onChange={(value) => setTracePingFilter(prev => ({ ...prev, asgeo: value ? String(value) : null, asn: null }))}
                                loading={tracePingFilterOptionsLoading}
                              >
                                {tracePingFilterOptions.asgeoOptions.map((item) => (
                                  <Select.Option key={item.asgeo} value={item.asgeo}>
                                    {item.asgeo} ({item.sample_count?.toLocaleString()})
                                  </Select.Option>
                                ))}
                              </Select>
                            </div>

                            {/* 运营商筛选 */}
                            <div style={{ minWidth: 200 }}>
                              <Text size="small" style={{ display: 'block', marginBottom: 4 }}>📡 运营商</Text>
                              <Select
                                style={{ width: '100%' }}
                                placeholder="选择运营商..."
                                filter
                                showClear
                                getPopupContainer={() => document.body}
                                value={tracePingFilter.isp || undefined}
                                onChange={(value) => setTracePingFilter(prev => ({ ...prev, isp: value ? String(value) : null }))}
                                loading={tracePingFilterOptionsLoading}
                              >
                                {tracePingFilterOptions.ispOptions.map((item) => (
                                  <Select.Option key={item.isp} value={item.isp}>
                                    {item.isp} ({item.sample_count?.toLocaleString()})
                                  </Select.Option>
                                ))}
                              </Select>
                            </div>
                          </div>
                          )}
                        </Collapse.Panel>

                        {/* 统计指标选择 */}
                        <Collapse.Panel header={`📊 统计指标 (${tracePingFilter.selectedStats.length} 个已选)`} itemKey="stats">
                          <Text type="tertiary" size="small" style={{ display: 'block', marginBottom: 8 }}>选择要在图表中显示的统计指标</Text>
                          <div style={{ display: 'flex', gap: 24, flexWrap: 'wrap' }}>
                            <div>
                              <Text size="small" type="tertiary">基础统计</Text>
                              <CheckboxGroup
                                value={tracePingFilter.selectedStats}
                                onChange={(values) => setTracePingFilter(prev => ({ ...prev, selectedStats: values as string[] }))}
                                direction="vertical"
                              >
                                {BASIC_STATISTICS_OPTIONS.map((opt) => (
                                  <Checkbox key={opt.value} value={opt.value}>{opt.label}</Checkbox>
                                ))}
                              </CheckboxGroup>
                            </div>
                            <div>
                              <Text size="small" type="tertiary">分位数</Text>
                              <CheckboxGroup
                                value={tracePingFilter.selectedStats}
                                onChange={(values) => setTracePingFilter(prev => ({ ...prev, selectedStats: values as string[] }))}
                                direction="vertical"
                              >
                                {PERCENTILE_OPTIONS.map((opt) => (
                                  <Checkbox key={opt.value} value={opt.value}>{opt.label}</Checkbox>
                                ))}
                              </CheckboxGroup>
                            </div>
                          </div>
                        </Collapse.Panel>

                        {/* 极端值过滤 */}
                        <Collapse.Panel header="🔧 极端值过滤" itemKey="outlier">
                          <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
                            <RadioGroup
                              type="button"
                              value={tracePingFilter.outlierFilterEnabled ? 'enabled' : 'disabled'}
                              onChange={(e) => setTracePingFilter(prev => ({ ...prev, outlierFilterEnabled: e.target.value === 'enabled' }))}
                            >
                              <Radio value="disabled">关闭</Radio>
                              <Radio value="enabled">开启</Radio>
                            </RadioGroup>
                            {tracePingFilter.outlierFilterEnabled && (
                              <>
                                <Text type="tertiary">P{tracePingFilter.outlierFilterMin} ~ P{tracePingFilter.outlierFilterMax}</Text>
                                <Slider
                                  range
                                  value={[tracePingFilter.outlierFilterMin, tracePingFilter.outlierFilterMax]}
                                  onChange={(value) => {
                                    if (Array.isArray(value) && value.length === 2) {
                                      setTracePingFilter(prev => ({
                                        ...prev,
                                        outlierFilterMin: value[0] as number,
                                        outlierFilterMax: value[1] as number,
                                      }))
                                    }
                                  }}
                                  min={0}
                                  max={100}
                                  style={{ width: 200 }}
                                />
                                <Space spacing={4}>
                                  <Button size="small" onClick={() => setTracePingFilter(prev => ({ ...prev, outlierFilterMin: 5, outlierFilterMax: 95 }))}>P5-P95</Button>
                                  <Button size="small" onClick={() => setTracePingFilter(prev => ({ ...prev, outlierFilterMin: 10, outlierFilterMax: 90 }))}>P10-P90</Button>
                                </Space>
                              </>
                            )}
                          </div>
                        </Collapse.Panel>

                        {/* 分位数分布图 */}
                        <Collapse.Panel header="📊 分位数分布图" itemKey="percentile">
                          <div style={{ marginBottom: 12 }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                              <Text size="small">启用后将在主图表下方显示多条分位数曲线</Text>
                              <RadioGroup
                                type="button"
                                value={tracePingFilter.percentileRangeEnabled ? 'enabled' : 'disabled'}
                                onChange={(e) => setTracePingFilter(prev => ({ ...prev, percentileRangeEnabled: e.target.value === 'enabled' }))}
                              >
                                <Radio value="disabled">关闭</Radio>
                                <Radio value="enabled">启用</Radio>
                              </RadioGroup>
                            </div>
                            {tracePingFilter.percentileRangeEnabled && (
                              <div style={{ padding: 12, background: '#fafafa', borderRadius: 8 }}>
                                <div style={{ marginBottom: 12 }}>
                                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
                                    <Text size="small">分位数范围：</Text>
                                    <Tag color="blue">P{tracePingFilter.percentileRangeMin} ~ P{tracePingFilter.percentileRangeMax}</Tag>
                                  </div>
                                  <Slider
                                    range
                                    value={[tracePingFilter.percentileRangeMin, tracePingFilter.percentileRangeMax]}
                                    onChange={(value) => {
                                      if (Array.isArray(value) && value.length === 2) {
                                        setTracePingFilter(prev => ({
                                          ...prev,
                                          percentileRangeMin: value[0] as number,
                                          percentileRangeMax: value[1] as number,
                                        }))
                                      }
                                    }}
                                    min={0}
                                    max={100}
                                    step={1}
                                  />
                                </div>
                                <div>
                                  <Text size="small" style={{ display: 'block', marginBottom: 4 }}>曲线间隔</Text>
                                  <Select
                                    value={tracePingFilter.percentileRangeStep}
                                    onChange={(value) => setTracePingFilter(prev => ({ ...prev, percentileRangeStep: value as number }))}
                                    style={{ width: '100%' }}
                                  >
                                    <Select.Option value={1}>每 1% (最多100条线)</Select.Option>
                                    <Select.Option value={2}>每 2% (最多50条线)</Select.Option>
                                    <Select.Option value={5}>每 5% (最多20条线)</Select.Option>
                                    <Select.Option value={10}>每 10% (最多10条线)</Select.Option>
                                  </Select>
                                </div>
                                <div style={{ marginTop: 12, padding: '8px 12px', background: '#e6f7ff', borderRadius: 4, textAlign: 'center' }}>
                                  <Text size="small">
                                    将绘制 <strong>{Math.max(1, Math.floor((tracePingFilter.percentileRangeMax - tracePingFilter.percentileRangeMin) / tracePingFilter.percentileRangeStep) + 1)}</strong> 条分位数曲线
                                  </Text>
                                </div>
                              </div>
                            )}
                          </div>
                        </Collapse.Panel>
                      </Collapse>
                    )}

                    {tracePingLoading ? (
                      <Card style={{ padding: 60, textAlign: 'center' }}><Spin size="large" /></Card>
                    ) : tracePingData ? (
                      <>
                        <Banner type="info" icon={<IconServer />} title="路径 Ping 时序分析" description={`关联 ${tracePingData.prefix24_count} 个 Prefix24${tracePingFilter.asn ? ` | 筛选: AS${tracePingFilter.asn}` : ''}${tracePingFilter.isp ? ` | ISP: ${tracePingFilter.isp}` : ''}`} style={{ marginBottom: 16 }} />

                        {/* 分位数分布图模式 */}
                        {tracePingFilter.percentileRangeEnabled && tracePingData.time_series?.length > 0 && (
                          <Card
                            title={`📊 分位数分布图 (P${tracePingFilter.percentileRangeMin} - P${tracePingFilter.percentileRangeMax})`}
                            style={{ marginBottom: 16 }}
                          >
                            <ChartDisplay data={{
                              title: '',
                              chartType: 'line',
                              data: {
                                xAxis: tracePingData.time_series.map((item: any) => item.time?.substring(0, 16)),
                                series: (() => {
                                  // 生成多条分位数曲线
                                  const series: any[] = []
                                  for (let p = tracePingFilter.percentileRangeMin; p <= tracePingFilter.percentileRangeMax; p += tracePingFilter.percentileRangeStep) {
                                    const ratio = (p - tracePingFilter.percentileRangeMin) / (tracePingFilter.percentileRangeMax - tracePingFilter.percentileRangeMin || 1)
                                    const r = Math.round(50 + ratio * 200)
                                    const g = Math.round(100 + (1 - Math.abs(ratio - 0.5) * 2) * 100)
                                    const b = Math.round(200 - ratio * 150)
                                    series.push({
                                      name: `P${p}`,
                                      data: tracePingData.time_series.map((item: any) => item.percentiles?.[`p${p}`]),
                                      itemStyle: { color: `rgb(${r}, ${g}, ${b})` },
                                    })
                                  }
                                  return series
                                })(),
                                yAxisName: 'RTT (ms)',
                              },
                            }} height={400} />
                          </Card>
                        )}

                        {/* 常规图表（未启用分位数分布图时） */}
                        {!tracePingFilter.percentileRangeEnabled && tracePingData.time_series?.length > 0 && (
                          <Card title="RTT 时间趋势" style={{ marginBottom: 16 }}>
                            <ChartDisplay data={{
                              title: '',
                              chartType: tracePingFilter.chartType === 'auto' ? 'line' : tracePingFilter.chartType,
                              data: (() => {
                                console.log('=== CHART DATA V2 ===')
                                console.log('[Chart data] selectedStats:', tracePingFilter.selectedStats);
                                console.log('[Chart data] time_series length:', tracePingData.time_series?.length);
                                console.log('[Chart data] time_series[0]:', tracePingData.time_series?.[0]);
                                return {
                                  xAxis: tracePingData.time_series.map((item: any) => item.time?.substring(0, 16)),
                                  series: tracePingFilter.selectedStats.map((stat) => {
                                    const statMap: Record<string, { name: string; field: string }> = {
                                      mean: { name: '平均 RTT', field: 'mean_rtt' },
                                      median: { name: '中位数', field: 'median_rtt' },
                                      std: { name: '标准差', field: 'std_rtt' },
                                      variance: { name: '方差', field: 'var_rtt' },
                                      min: { name: '最小值', field: 'min_rtt' },
                                      max: { name: '最大值', field: 'max_rtt' },
                                      cv: { name: '变异系数', field: 'coefficient_of_variation' },
                                      iqr: { name: 'IQR', field: 'iqr' },
                                      skewness: { name: '偏度', field: 'skewness' },
                                      kurtosis: { name: '峰度', field: 'kurtosis' },
                                      p10: { name: 'P10', field: 'p10' },
                                      p25: { name: 'P25', field: 'p25' },
                                      p50: { name: 'P50', field: 'p50' },
                                      p75: { name: 'P75', field: 'p75' },
                                      p90: { name: 'P90', field: 'p90' },
                                      p95: { name: 'P95', field: 'p95' },
                                      p99: { name: 'P99', field: 'p99' },
                                    };
                                    const config = statMap[stat];
                                    console.log('[Chart data] stat:', stat, 'config:', config);
                                    if (!config) return { name: stat, data: [] };
                                    // 分位数从 percentiles 对象中取
                                    if (stat.startsWith('p') && !isNaN(parseInt(stat.substring(1)))) {
                                      const percentileData = tracePingData.time_series.map((item: any) => item.percentiles?.[stat]);
                                      console.log('[Chart data] percentile data length:', percentileData.length, 'first value:', percentileData[0]);
                                      return {
                                        name: config.name,
                                        data: percentileData,
                                      };
                                    }
                                    const fieldData = tracePingData.time_series.map((item: any) => item[config.field]);
                                    console.log('[Chart data] field:', config.field, 'data length:', fieldData.length, 'first value:', fieldData[0]);
                                    return {
                                      name: config.name,
                                      data: fieldData,
                                    };
                                  }),
                                  yAxisName: 'RTT (ms)',
                                };
                              })(),
                            }} height={350} />
                          </Card>
                        )}

                        {tracePingData.summary?.total_samples > 0 && (
                          <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
                            <Col span={4}><Card className="metric-card"><Text type="tertiary" size="small">总样本</Text><div style={{ fontSize: 18, fontWeight: 'bold' }}>{tracePingData.summary.total_samples?.toLocaleString()}</div></Card></Col>
                            <Col span={4}><Card className="metric-card"><Text type="tertiary" size="small">平均 RTT</Text><div style={{ fontSize: 18, fontWeight: 'bold' }}>{tracePingData.summary.mean_rtt?.toFixed(2)} ms</div></Card></Col>
                            <Col span={4}><Card className="metric-card"><Text type="tertiary" size="small">中位数</Text><div style={{ fontSize: 18, fontWeight: 'bold' }}>{tracePingData.summary.median_rtt?.toFixed(2)} ms</div></Card></Col>
                            <Col span={4}><Card className="metric-card"><Text type="tertiary" size="small">P90</Text><div style={{ fontSize: 18, fontWeight: 'bold' }}>{tracePingData.summary.percentiles?.p90?.toFixed(2)} ms</div></Card></Col>
                            <Col span={4}><Card className="metric-card"><Text type="tertiary" size="small">P95</Text><div style={{ fontSize: 18, fontWeight: 'bold' }}>{tracePingData.summary.percentiles?.p95?.toFixed(2)} ms</div></Card></Col>
                            <Col span={4}><Card className="metric-card"><Text type="tertiary" size="small">P99</Text><div style={{ fontSize: 18, fontWeight: 'bold' }}>{tracePingData.summary.percentiles?.p99?.toFixed(2)} ms</div></Card></Col>
                          </Row>
                        )}
                      </>
                    ) : (
                      <Card style={{ padding: 60 }}><Empty description="选择路径后点击分析" /></Card>
                    )}
                  </TabPane>
                </Tabs>
              ) : (
                <Card style={{ padding: 80 }}>
                  <Empty
                    title={tracerouteFilter.region ? '点击"开始分析"开始' : "请先选择地区"}
                    description={tracerouteFilter.region ? "选择时间范围（可选），然后点击开始分析按钮" : "选择地区后可以开始 Traceroute 分析"}
                  />
                </Card>
              )}
            </div>
          </TabPane>

          {/* ===== 地区概览 ===== */}
          <TabPane tab={<><IconServer /> 地区概览</>} itemKey="overview">
            <RegionOverview
              regions={regions}
              regionsLoading={regionsLoading}
            />
          </TabPane>
        </Tabs>
      </div>
    </div>
  )
}

export default Visualization

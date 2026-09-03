/**
 * 增强版筛选面板组件
 * 支持多维度筛选：地区、时间、AS、ASGeo、数据中心、国家、路径等
 * 支持自定义分位数配置（0-100）
 */
import { useState, useEffect } from 'react'
import {
  Card,
  Select,
  DatePicker,
  Button,
  Space,
  RadioGroup,
  Radio,
  Input,
  InputNumber,
  Tag,
  Typography,
  Divider,
  Collapse,
  Spin,
  Slider,
  Tooltip,
} from '@douyinfe/semi-ui'
import {
  IconSearch,
  IconRefresh,
  IconFilter,
  IconPlus,
} from '@douyinfe/semi-icons'
import axios from 'axios'
import './FilterPanel.css'

const { Text } = Typography

const API_BASE = import.meta.env.VITE_API_BASE || ''

export interface FilterState {
  // 基础筛选
  region: string
  startTime: Date | null
  endTime: Date | null
  dataType: 'ping' | 'traceroute'
  interval: 'minute' | 'hour' | 'day'

  // Ping 分析维度
  analysisDimension: 'overall' | 'asn' | 'asgeo' | 'country' | 'region' | 'city' | 'data_center' | 'prefix24' | 'time_trend'

  // 图表类型
  chartType: 'auto' | 'bar' | 'line' | 'pie'

  // 多选筛选
  selectedAsns: number[]
  selectedCountries: string[]
  selectedDataCenters: string[]
  selectedPrefix24s: string[]

  // 单选筛选
  asn: number | null
  prefix24: string | null
  dataCenter: string | null
  country: string | null

  // Traceroute 筛选
  targetAsn: number | null
  targetAsgeo: string | null
  pathType: 'ip' | 'as' | 'asgeo' | 'all'
  reachedTarget: boolean | null
  terminalAs: string | null  // 末端 AS 筛选
  terminalAsgeo: string | null  // 末端 ASGeo 筛选

  // 统计配置
  percentiles: number[]  // 如 [50, 90, 95, 99] - 支持0-100任意值
  compareMode: 'none' | 'region' | 'asn' | 'time'

  // 极端值过滤
  outlierFilterEnabled: boolean
  outlierFilterMin: number  // 最小分位数 (0-100)
  outlierFilterMax: number  // 最大分位数 (0-100)
}

interface FilterPanelProps {
  regions: string[]
  onFilterChange: (filters: FilterState) => void
  loading?: boolean
  defaultFilters?: Partial<FilterState>
}

const defaultFilterState: FilterState = {
  region: '',
  startTime: null,
  endTime: null,
  dataType: 'ping',
  interval: 'hour',
  analysisDimension: 'overall',
  chartType: 'auto',
  selectedAsns: [],
  selectedCountries: [],
  selectedDataCenters: [],
  selectedPrefix24s: [],
  asn: null,
  prefix24: null,
  dataCenter: null,
  country: null,
  targetAsn: null,
  targetAsgeo: null,
  pathType: 'as',
  reachedTarget: null,
  terminalAs: null,
  terminalAsgeo: null,
  percentiles: [50, 90, 95, 99],
  compareMode: 'none',
  outlierFilterEnabled: false,
  outlierFilterMin: 5,
  outlierFilterMax: 95,
}

// 分析维度选项
const ANALYSIS_DIMENSION_OPTIONS = [
  { value: 'overall', label: '整体统计', description: '汇总所有数据的统计信息' },
  { value: 'time_trend', label: '时间趋势', description: '按时间粒度分析变化趋势' },
  { value: 'asn', label: '按 AS', description: '按自治系统号分组分析' },
  { value: 'asgeo', label: '按 AS+Geo', description: '按 AS 和地理位置组合分析' },
  { value: 'country', label: '按国家', description: '按国家/地区分组分析' },
  { value: 'data_center', label: '按数据中心', description: '按数据中心分组分析' },
]

// 预设分位数
const PRESET_PERCENTILES = [
  { label: 'P10', value: 10 },
  { label: 'P25', value: 25 },
  { label: 'P50 (中位数)', value: 50 },
  { label: 'P75', value: 75 },
  { label: 'P90', value: 90 },
  { label: 'P95', value: 95 },
  { label: 'P99', value: 99 },
]

// 动态数据选项（从后端加载）
interface DynamicOptions {
  asns: { asn: number; as_name: string; sample_count: number }[]
  countries: { country: string; sample_count: number }[]
  dataCenters: string[]
  timeRange: { min_time: Date | null; max_time: Date | null }
}

// 末端节点选项
interface TerminalOption {
  terminal: string
  trace_count: number
  prefix24_count: number
  reach_rate: number
}

function FilterPanel({
  regions,
  onFilterChange,
  loading = false,
  defaultFilters,
}: FilterPanelProps) {
  const [filters, setFilters] = useState<FilterState>({
    ...defaultFilterState,
    ...defaultFilters,
  })

  // 自定义分位数输入
  const [customPercentile, setCustomPercentile] = useState<number>(50)

  // 动态选项
  const [dynamicOptions, setDynamicOptions] = useState<DynamicOptions>({
    asns: [],
    countries: [],
    dataCenters: [],
    timeRange: { min_time: null, max_time: null },
  })
  const [optionsLoading, setOptionsLoading] = useState(false)

  // 末端节点选项（用于模糊搜索）
  const [terminalOptions, setTerminalOptions] = useState<TerminalOption[]>([])
  const [terminalOptionsLoading, setTerminalOptionsLoading] = useState(false)

  // 当地区变化时，加载动态选项
  useEffect(() => {
    if (filters.region) {
      loadDynamicOptions(filters.region)
    }
  }, [filters.region])

  const loadDynamicOptions = async (region: string) => {
    setOptionsLoading(true)
    try {
      // 并行加载 AS 列表、国家列表、时间范围
      const [asnsRes, countriesRes, timeRangeRes] = await Promise.all([
        axios.get(`${API_BASE}/api/clickhouse/metadata/asns`, { params: { region, limit: 100 } }),
        axios.get(`${API_BASE}/api/clickhouse/metadata/countries`, { params: { region, limit: 50 } }),
        axios.get(`${API_BASE}/api/clickhouse/metadata/time-range`, { params: { region } }),
      ])

      setDynamicOptions({
        asns: asnsRes.data.asns || [],
        countries: countriesRes.data.countries || [],
        dataCenters: [],
        timeRange: {
          min_time: timeRangeRes.data.min_time ? new Date(timeRangeRes.data.min_time) : null,
          max_time: timeRangeRes.data.max_time ? new Date(timeRangeRes.data.max_time) : null,
        },
      })
    } catch (error) {
      console.error('Failed to load dynamic options:', error)
    } finally {
      setOptionsLoading(false)
    }
  }

  // 加载末端节点选项（用于模糊搜索）
  const loadTerminalOptions = async (search: string, terminalType: 'as' | 'asgeo') => {
    if (!filters.region) return

    setTerminalOptionsLoading(true)
    try {
      const response = await axios.post(`${API_BASE}/api/clickhouse/trace/terminals/list`, {
        region: filters.region,
        terminal_type: terminalType,
        search: search || undefined,
        limit: 50,
      })
      setTerminalOptions(response.data.terminals || [])
    } catch (error) {
      console.error('Failed to load terminal options:', error)
    } finally {
      setTerminalOptionsLoading(false)
    }
  }

  // 更新筛选条件 - 立即同步到父组件
  const updateFilter = <K extends keyof FilterState>(key: K, value: FilterState[K]) => {
    const newFilters = { ...filters, [key]: value }
    setFilters(newFilters)
    // 立即同步到父组件
    onFilterChange(newFilters)
  }

  // 添加分位数
  const addPercentile = (value: number) => {
    if (value >= 0 && value <= 100 && !filters.percentiles.includes(value)) {
      const newPercentiles = [...filters.percentiles, value].sort((a, b) => a - b)
      updateFilter('percentiles', newPercentiles)
    }
  }

  // 移除分位数
  const removePercentile = (value: number) => {
    updateFilter('percentiles', filters.percentiles.filter(p => p !== value))
  }

  // 应用筛选
  const applyFilters = () => {
    onFilterChange({ ...filters })
  }

  // 重置筛选
  const resetFilters = () => {
    setFilters(defaultFilterState)
    onFilterChange(defaultFilterState)
  }

  // 设置快捷时间范围
  const setQuickTimeRange = (hours: number) => {
    const endTime = new Date()
    const startTime = new Date(endTime.getTime() - hours * 60 * 60 * 1000)
    setFilters({ ...filters, startTime, endTime })
  }

  // 设置时间范围到数据范围
  const setTimeToDataRange = () => {
    if (dynamicOptions.timeRange.min_time && dynamicOptions.timeRange.max_time) {
      setFilters({
        ...filters,
        startTime: dynamicOptions.timeRange.min_time,
        endTime: dynamicOptions.timeRange.max_time,
      })
    }
  }

  return (
    <Card className="filter-panel">
      <div className="filter-header">
        <Space>
          <IconFilter style={{ color: 'var(--semi-color-primary)' }} />
          <Text strong>筛选条件</Text>
        </Space>
        {optionsLoading && <Spin size="small" />}
      </div>

      <div className="filter-content">
        {/* ===== 基础筛选条件 ===== */}
        <div className="filter-section">
          <Text type="tertiary" size="small" className="section-label">基础筛选</Text>

          {/* 地区选择 */}
          <div className="filter-item">
            <Text className="filter-label">地区 <span className="required">*</span></Text>
            <Select
              value={filters.region}
              onChange={(value) => updateFilter('region', String(value || ''))}
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

          {/* 数据类型 */}
          <div className="filter-item">
            <Text className="filter-label">数据类型</Text>
            <RadioGroup
              type="button"
              value={filters.dataType}
              onChange={(e) => updateFilter('dataType', e.target.value as 'ping' | 'traceroute')}
            >
              <Radio value="ping">Ping</Radio>
              <Radio value="traceroute">Traceroute</Radio>
            </RadioGroup>
          </div>

          {/* 时间范围 */}
          <div className="filter-item">
            <Text className="filter-label">时间范围</Text>
            <Space vertical style={{ width: '100%' }}>
              <DatePicker
                type="dateTimeRange"
                value={filters.startTime && filters.endTime ? [filters.startTime, filters.endTime] : undefined}
                onChange={(dates) => {
                  if (Array.isArray(dates) && dates.length === 2 && dates[0] && dates[1]) {
                    setFilters({
                      ...filters,
                      startTime: dates[0] as Date,
                      endTime: dates[1] as Date,
                    })
                  }
                }}
                style={{ width: '100%' }}
                placeholder="选择时间范围"
              />
              <Space wrap>
                <Button size="small" onClick={() => setQuickTimeRange(1)}>1小时</Button>
                <Button size="small" onClick={() => setQuickTimeRange(24)}>24小时</Button>
                <Button size="small" onClick={() => setQuickTimeRange(168)}>7天</Button>
                <Button size="small" onClick={setTimeToDataRange}>全部数据</Button>
              </Space>
              {dynamicOptions.timeRange.min_time && (
                <Text type="tertiary" size="small">
                  数据范围: {dynamicOptions.timeRange.min_time.toLocaleDateString()} - {dynamicOptions.timeRange.max_time?.toLocaleDateString()}
                </Text>
              )}
            </Space>
          </div>

          {/* 时间粒度 */}
          <div className="filter-item">
            <Text className="filter-label">时间粒度</Text>
            <Select
              value={filters.interval}
              onChange={(value) => updateFilter('interval', value as FilterState['interval'])}
              style={{ width: '100%' }}
            >
              <Select.Option value="minute">按分钟</Select.Option>
              <Select.Option value="hour">按小时</Select.Option>
              <Select.Option value="day">按天</Select.Option>
            </Select>
          </div>
        </div>

        <Divider margin="12px" />

        {/* ===== 分析维度 ===== */}
        <div className="filter-section">
          <Text type="tertiary" size="small" className="section-label">分析维度</Text>

          {filters.dataType === 'ping' && (
            <>
              {/* 分析维度选择 */}
              <div className="filter-item">
                <Text className="filter-label">分析维度</Text>
                <Select
                  value={filters.analysisDimension}
                  onChange={(value) => updateFilter('analysisDimension', value as FilterState['analysisDimension'])}
                  style={{ width: '100%' }}
                >
                  {ANALYSIS_DIMENSION_OPTIONS.map((opt) => (
                    <Select.Option key={opt.value} value={opt.value}>
                      <div>
                        <Text>{opt.label}</Text>
                        <Text type="tertiary" size="small" style={{ marginLeft: 8 }}>
                          {opt.description}
                        </Text>
                      </div>
                    </Select.Option>
                  ))}
                </Select>
              </div>

              {/* 图表类型选择 */}
              <div className="filter-item">
                <Text className="filter-label">图表类型</Text>
                <RadioGroup
                  type="button"
                  value={filters.chartType || 'auto'}
                  onChange={(e) => updateFilter('chartType', e.target.value)}
                >
                  <Radio value="auto">自动</Radio>
                  <Radio value="bar">柱状图</Radio>
                  <Radio value="line">折线图</Radio>
                  <Radio value="pie">饼图</Radio>
                </RadioGroup>
                <Text type="tertiary" size="small" style={{ marginTop: 4, display: 'block' }}>
                  {filters.chartType === 'auto' ? '根据分析维度自动选择最佳图表' : '已手动选择图表类型'}
                </Text>
              </div>

              {/* 分位数选择 */}
              <div className="filter-item">
                <Text className="filter-label">统计分位数</Text>
                <div className="percentile-selector">
                  {/* 已选分位数标签 */}
                  <div className="percentile-tags">
                    {filters.percentiles.map((p) => (
                      <Tag
                        key={p}
                        color="cyan"
                        closable
                        onClose={() => removePercentile(p)}
                      >
                        P{p}
                      </Tag>
                    ))}
                  </div>

                  {/* 预设分位数 */}
                  <div className="percentile-presets">
                    <Text type="tertiary" size="small">快捷选择:</Text>
                    <Space wrap spacing={8}>
                      {PRESET_PERCENTILES.map((opt) => (
                        <Button
                          key={opt.value}
                          size="small"
                          type={filters.percentiles.includes(opt.value) ? 'primary' : 'tertiary'}
                          onClick={() => {
                            if (filters.percentiles.includes(opt.value)) {
                              removePercentile(opt.value)
                            } else {
                              addPercentile(opt.value)
                            }
                          }}
                        >
                          {opt.label}
                        </Button>
                      ))}
                    </Space>
                  </div>

                  {/* 自定义分位数输入 */}
                  <div className="percentile-custom">
                    <Text type="tertiary" size="small">自定义:</Text>
                    <Space>
                      <InputNumber
                        min={0}
                        max={100}
                        value={customPercentile}
                        onChange={(value) => setCustomPercentile(Number(value) || 0)}
                        style={{ width: 80 }}
                        placeholder="0-100"
                      />
                      <Button
                        size="small"
                        icon={<IconPlus />}
                        onClick={() => {
                          addPercentile(customPercentile)
                        }}
                      >
                        添加
                      </Button>
                    </Space>
                    <Slider
                      value={customPercentile}
                      onChange={(value) => setCustomPercentile(value as number)}
                      min={0}
                      max={100}
                      style={{ width: 180, marginTop: 8 }}
                    />
                  </div>
                </div>
              </div>

              {/* 极端值过滤 */}
              <div className="filter-item">
                <Space style={{ marginBottom: 8 }}>
                  <Text className="filter-label">极端值过滤</Text>
                  <RadioGroup
                    type="button"
                    value={filters.outlierFilterEnabled ? 'enabled' : 'disabled'}
                    onChange={(e) => updateFilter('outlierFilterEnabled', e.target.value === 'enabled')}
                  >
                    <Radio value="disabled">关闭</Radio>
                    <Radio value="enabled">开启</Radio>
                  </RadioGroup>
                </Space>
                {filters.outlierFilterEnabled && (
                  <div className="outlier-filter-panel" style={{ padding: 12, backgroundColor: 'var(--semi-color-bg-1)', borderRadius: 6 }}>
                    <Text type="tertiary" size="small" style={{ display: 'block', marginBottom: 8 }}>
                      只分析 P{filters.outlierFilterMin} 到 P{filters.outlierFilterMax} 之间的数据
                    </Text>
                    <Space style={{ width: '100%' }} spacing="loose">
                      <div>
                        <Text size="small">下限分位数:</Text>
                        <InputNumber
                          min={0}
                          max={filters.outlierFilterMax - 1}
                          value={filters.outlierFilterMin}
                          onChange={(value) => updateFilter('outlierFilterMin', Number(value) || 0)}
                          style={{ width: 80, marginLeft: 8 }}
                          suffix="P"
                        />
                      </div>
                      <div>
                        <Text size="small">上限分位数:</Text>
                        <InputNumber
                          min={filters.outlierFilterMin + 1}
                          max={100}
                          value={filters.outlierFilterMax}
                          onChange={(value) => updateFilter('outlierFilterMax', Number(value) || 100)}
                          style={{ width: 80, marginLeft: 8 }}
                          suffix="P"
                        />
                      </div>
                    </Space>
                    <Slider
                      range
                      value={[filters.outlierFilterMin, filters.outlierFilterMax]}
                      onChange={(value) => {
                        if (Array.isArray(value) && value.length === 2) {
                          updateFilter('outlierFilterMin', value[0] as number)
                          updateFilter('outlierFilterMax', value[1] as number)
                        }
                      }}
                      min={0}
                      max={100}
                      style={{ marginTop: 12 }}
                    />
                    <Space wrap style={{ marginTop: 8 }}>
                      <Button size="small" onClick={() => { updateFilter('outlierFilterMin', 5); updateFilter('outlierFilterMax', 95) }}>
                        P5-P95
                      </Button>
                      <Button size="small" onClick={() => { updateFilter('outlierFilterMin', 10); updateFilter('outlierFilterMax', 90) }}>
                        P10-P90
                      </Button>
                      <Button size="small" onClick={() => { updateFilter('outlierFilterMin', 25); updateFilter('outlierFilterMax', 75) }}>
                        P25-P75 (IQR)
                      </Button>
                    </Space>
                  </div>
                )}
              </div>
            </>
          )}

          {/* Traceroute 筛选 */}
          {filters.dataType === 'traceroute' && (
            <>
              {/* 路径类型 */}
              <div className="filter-item">
                <Text className="filter-label">路径类型</Text>
                <RadioGroup
                  type="button"
                  value={filters.pathType}
                  onChange={(e) => updateFilter('pathType', e.target.value)}
                >
                  <Radio value="as">AS 路径</Radio>
                  <Radio value="asgeo">ASGeo 路径</Radio>
                </RadioGroup>
              </div>

              {/* 末端 AS 模糊搜索 */}
              <div className="filter-item">
                <Text className="filter-label">末端 AS（模糊搜索）</Text>
                <Select
                  value={filters.terminalAs ?? undefined}
                  onChange={(value) => updateFilter('terminalAs', value ? String(value) : null)}
                  placeholder="输入 AS 号搜索..."
                  style={{ width: '100%' }}
                  filter
                  remote
                  loading={terminalOptionsLoading}
                  onSearch={(value) => {
                    // 远程搜索末端 AS
                    if (filters.region && value.length >= 1) {
                      loadTerminalOptions(value, 'as')
                    }
                  }}
                >
                  {terminalOptions.map((item) => (
                    <Select.Option key={item.terminal} value={item.terminal}>
                      {item.terminal} ({item.trace_count} 条路径)
                    </Select.Option>
                  ))}
                </Select>
              </div>

              {/* 末端 ASGeo 模糊搜索 */}
              <div className="filter-item">
                <Text className="filter-label">末端 ASGeo（模糊搜索）</Text>
                <Select
                  value={filters.terminalAsgeo ?? undefined}
                  onChange={(value) => updateFilter('terminalAsgeo', value ? String(value) : null)}
                  placeholder="输入 AS 或国家代码搜索..."
                  style={{ width: '100%' }}
                  filter
                  remote
                  loading={terminalOptionsLoading}
                  onSearch={(value) => {
                    if (filters.region && value.length >= 1) {
                      loadTerminalOptions(value, 'asgeo')
                    }
                  }}
                >
                  {terminalOptions.map((item) => (
                    <Select.Option key={item.terminal} value={item.terminal}>
                      {item.terminal} ({item.trace_count} 条路径)
                    </Select.Option>
                  ))}
                </Select>
              </div>

              {/* 是否到达目标 */}
              <div className="filter-item">
                <Text className="filter-label">路径状态</Text>
                <RadioGroup
                  type="button"
                  value={filters.reachedTarget === null ? 'all' : filters.reachedTarget}
                  onChange={(e) => {
                    const val = e.target.value
                    updateFilter('reachedTarget', val === 'all' ? null : val as boolean)
                  }}
                >
                  <Radio value="all">全部</Radio>
                  <Radio value={true}>到达目标</Radio>
                  <Radio value={false}>未到达</Radio>
                </RadioGroup>
              </div>
            </>
          )}
        </div>

        <Divider margin="12px" />

        {/* ===== 高级筛选 ===== */}
        <Collapse accordion>
          <Collapse.Panel header="高级筛选" itemKey="advanced">
            <div className="advanced-filters">
              {/* AS 筛选 */}
              <div className="filter-item">
                <Text className="filter-label">AS 号</Text>
                <Select
                  value={filters.asn ?? undefined}
                  onChange={(value) => updateFilter('asn', value ? Number(value) : null)}
                  placeholder="筛选特定 AS"
                  style={{ width: '100%' }}
                  filter
                >
                  {dynamicOptions.asns.map((item) => (
                    <Select.Option key={item.asn} value={item.asn}>
                      AS{item.asn} - {item.as_name?.substring(0, 30) || 'Unknown'} ({item.sample_count} 样本)
                    </Select.Option>
                  ))}
                </Select>
              </div>

              {/* 国家筛选 */}
              <div className="filter-item">
                <Text className="filter-label">国家</Text>
                <Select
                  value={filters.country ?? undefined}
                  onChange={(value) => updateFilter('country', value ? String(value) : null)}
                  placeholder="筛选特定国家"
                  style={{ width: '100%' }}
                  filter
                >
                  {dynamicOptions.countries.map((item) => (
                    <Select.Option key={item.country} value={item.country}>
                      {item.country} ({item.sample_count} 样本)
                    </Select.Option>
                  ))}
                </Select>
              </div>

              {/* /24 前缀筛选 */}
              <div className="filter-item">
                <Text className="filter-label">/24 前缀</Text>
                <Input
                  placeholder="输入前缀，如 192.168.1"
                  value={filters.prefix24 || ''}
                  onChange={(value) => updateFilter('prefix24', value || null)}
                />
              </div>

              {/* 对比模式 */}
              <div className="filter-item">
                <Text className="filter-label">对比分析</Text>
                <RadioGroup
                  type="button"
                  value={filters.compareMode}
                  onChange={(e) => updateFilter('compareMode', e.target.value)}
                >
                  <Radio value="none">无对比</Radio>
                  <Radio value="region">对比地区</Radio>
                  <Radio value="asn">对比 AS</Radio>
                  <Radio value="time">对比时段</Radio>
                </RadioGroup>
              </div>
            </div>
          </Collapse.Panel>
        </Collapse>

        {/* 操作按钮 */}
        <div className="filter-actions">
          <Space style={{ width: '100%', justifyContent: 'space-between' }}>
            <Button
              icon={<IconRefresh />}
              onClick={resetFilters}
            >
              重置
            </Button>
            <Button
              type="primary"
              theme="solid"
              icon={<IconSearch />}
              onClick={applyFilters}
              loading={loading}
              disabled={!filters.region}
            >
              应用筛选
            </Button>
          </Space>
        </div>

        {/* 当前筛选状态 */}
        {(filters.region || filters.asn || filters.country || filters.prefix24 || filters.percentiles.length > 0 || filters.outlierFilterEnabled || filters.terminalAs || filters.terminalAsgeo || filters.pathType !== 'as') && (
          <div className="active-filters">
            <Text type="tertiary" size="small">当前筛选:</Text>
            <Space wrap style={{ marginTop: 4 }}>
              {filters.region && (
                <Tag color="blue">地区: {filters.region}</Tag>
              )}
              {filters.dataType === 'traceroute' && (
                <Tag color="teal">Traceroute</Tag>
              )}
              {filters.terminalAs && (
                <Tag color="green" closable onClose={() => updateFilter('terminalAs', null)}>
                  末端 AS: {filters.terminalAs}
                </Tag>
              )}
              {filters.terminalAsgeo && (
                <Tag color="cyan" closable onClose={() => updateFilter('terminalAsgeo', null)}>
                  末端 ASGeo: {filters.terminalAsgeo}
                </Tag>
              )}
              {filters.asn && (
                <Tag color="green" closable onClose={() => updateFilter('asn', null)}>
                  AS: {filters.asn}
                </Tag>
              )}
              {filters.country && (
                <Tag color="purple" closable onClose={() => updateFilter('country', null)}>
                  国家: {filters.country}
                </Tag>
              )}
              {filters.prefix24 && (
                <Tag color="orange" closable onClose={() => updateFilter('prefix24', null)}>
                  前缀: {filters.prefix24}
                </Tag>
              )}
              {filters.percentiles.length > 0 && (
                <Tooltip content={`分位数: ${filters.percentiles.map(p => `P${p}`).join(', ')}`}>
                  <Tag color="cyan">
                    分位数: {filters.percentiles.length} 个
                  </Tag>
                </Tooltip>
              )}
              {filters.outlierFilterEnabled && (
                <Tooltip content={`只分析 P${filters.outlierFilterMin} 到 P${filters.outlierFilterMax} 之间的数据`}>
                  <Tag color="red" closable onClose={() => updateFilter('outlierFilterEnabled', false)}>
                    极端值过滤: P{filters.outlierFilterMin}-P{filters.outlierFilterMax}
                  </Tag>
                </Tooltip>
              )}
            </Space>
          </div>
        )}
      </div>
    </Card>
  )
}

export default FilterPanel

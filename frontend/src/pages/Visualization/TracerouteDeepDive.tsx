/**
 * Traceroute 深度分析页面
 * 使用 Tab 切换不同分析模式，而非层层进入
 *
 * 分析模式：
 * 1. 末端节点分析 - 查看所有末端 AS/ASGeo
 * 2. 路径分析 - 查看路径列表（可按末端筛选）
 * 3. 路径详情 - 查看单条路径的关联信息
 * 4. Ping 时序 - 查看路径关联的 Ping 数据
 */
import { useState, useEffect, useCallback, useMemo } from 'react'
import { useSearchParams, useNavigate } from 'react-router-dom'
import {
  Card,
  Typography,
  Button,
  Space,
  Tabs,
  TabPane,
  Toast,
  Tag,
  Row,
  Col,
  Select,
  DatePicker,
  Empty,
  Spin,
  Table,
  RadioGroup,
  Radio,
  Input,
  Banner,
  Collapse,
} from '@douyinfe/semi-ui'
import {
  IconArrowLeft,
  IconRefresh,
  IconServer,
  IconLink,
  IconLineChartStroked,
  IconSearch,
  IconHome,
} from '@douyinfe/semi-icons'
import tracerouteApi, {
  type TerminalNode,
  type TerminalAnalysisResponse,
  type TerminalListItem,
  type ASPathAnalysisResponse,
  type PathDetailResponse,
  type PathPingTrendResponse,
  type PathFilterOptionsResponse,
} from '../../api/traceroute'
import { DataSourceBadge } from './components'
import ChartDisplay from './components/ChartDisplay'
import './Visualization.css'

const { Title, Text } = Typography

function TracerouteDeepDive() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()

  // URL 参数
  const regionFromUrl = searchParams.get('region') || ''

  // 基础状态
  const [selectedRegion, setSelectedRegion] = useState<string>(regionFromUrl)
  const [startTime, setStartTime] = useState<Date | null>(null)
  const [endTime, setEndTime] = useState<Date | null>(null)
  const [regions, setRegions] = useState<string[]>([])
  const [regionsLoading, setRegionsLoading] = useState(false)
  const [activeTab, setActiveTab] = useState<string>('terminals')

  // ===== 末端节点分析状态 =====
  const [terminalType, setTerminalType] = useState<'as' | 'asgeo'>('asgeo')
  const [terminalData, setTerminalData] = useState<TerminalAnalysisResponse | null>(null)
  const [terminalLoading, setTerminalLoading] = useState(false)
  const [terminalSearch, setTerminalSearch] = useState<string>('')
  const [terminalOptions, setTerminalOptions] = useState<TerminalListItem[]>([])
  const [terminalOptionsLoading, setTerminalOptionsLoading] = useState(false)

  // ===== 路径分析状态 =====
  const [pathType, setPathType] = useState<'as' | 'asgeo'>('as')
  const [pathData, setPathData] = useState<ASPathAnalysisResponse | null>(null)
  const [pathLoading, setPathLoading] = useState(false)
  const [pathTerminalFilter, setPathTerminalFilter] = useState<string>('')

  // ===== 路径详情状态 =====
  const [detailPathInput, setDetailPathInput] = useState<string>('')
  const [detailPathType, setDetailPathType] = useState<'as' | 'asgeo'>('as')
  const [pathDetail, setPathDetail] = useState<PathDetailResponse | null>(null)
  const [pathDetailLoading, setPathDetailLoading] = useState(false)

  // ===== Ping 时序状态 =====
  const [pingPathInput, setPingPathInput] = useState<string>('')
  const [pingPathType, setPingPathType] = useState<'as' | 'asgeo'>('as')
  const [pingTrendData, setPingTrendData] = useState<PathPingTrendResponse | null>(null)
  const [pingTrendLoading, setPingTrendLoading] = useState(false)
  const [pingTrendInterval, setPingTrendInterval] = useState<'minute' | 'hour' | 'day'>('hour')

  // ===== Ping 时序筛选状态 =====
  const [pingFilterOptions, setPingFilterOptions] = useState<PathFilterOptionsResponse | null>(null)
  const [pingFilterLoading, setPingFilterLoading] = useState(false)
  const [selectedAsn, setSelectedAsn] = useState<number | null>(null)
  const [selectedAsgeo, setSelectedAsgeo] = useState<string | null>(null)
  const [selectedIsp, setSelectedIsp] = useState<string | null>(null)
  const [selectedDataCenter, setSelectedDataCenter] = useState<string | null>(null)

  // 加载地区列表
  useEffect(() => {
    const loadRegions = async () => {
      setRegionsLoading(true)
      try {
        const apiBase = localStorage.getItem('app_config')
        const baseUrl = apiBase ? JSON.parse(apiBase).apiBaseUrl || '' : ''
        const response = await fetch(`${baseUrl}/api/clickhouse/regions`)
        const data = await response.json()
        if (data.success && data.regions) {
          setRegions(data.regions.map((r: any) => r.name || r))
        }
      } catch (error) {
        console.error('Failed to load regions:', error)
      } finally {
        setRegionsLoading(false)
      }
    }
    loadRegions()
  }, [])

  // ===== 末端节点分析 =====
  const loadTerminalOptions = useCallback(async (search: string) => {
    if (!selectedRegion) return
    setTerminalOptionsLoading(true)
    try {
      const data = await tracerouteApi.getTerminalList({
        region: selectedRegion,
        terminal_type: terminalType,
        search: search || undefined,
        limit: 50,
      })
      setTerminalOptions(data.terminals || [])
    } catch (error) {
      console.error('Failed to load terminal options:', error)
    } finally {
      setTerminalOptionsLoading(false)
    }
  }, [selectedRegion, terminalType])

  const loadTerminalData = useCallback(async () => {
    if (!selectedRegion) return
    setTerminalLoading(true)
    try {
      const params: any = {
        region: selectedRegion,
        terminal_type: terminalType,
        top_n: 50,
        include_paths: true,
      }
      if (startTime) params.start_time = startTime.toISOString()
      if (endTime) params.end_time = endTime.toISOString()
      if (terminalSearch) params.terminal_filter = terminalSearch

      const data = await tracerouteApi.getTerminalAnalysis(params)
      setTerminalData(data)
    } catch (error: any) {
      console.error('Failed to load terminal data:', error)
      Toast.error({ content: error.response?.data?.detail || '加载末端节点数据失败', duration: 3 })
    } finally {
      setTerminalLoading(false)
    }
  }, [selectedRegion, terminalType, startTime, endTime, terminalSearch])

  // ===== 路径分析 =====
  const loadPathData = useCallback(async (terminal?: string) => {
    if (!selectedRegion) return
    setPathLoading(true)
    try {
      const params: any = {
        region: selectedRegion,
        path_type: pathType,
        top_n: 100,
      }
      if (startTime) params.start_time = startTime.toISOString()
      if (endTime) params.end_time = endTime.toISOString()
      if (terminal) {
        if (pathType === 'as') {
          params.terminal_as = terminal
        } else {
          params.terminal_asgeo = terminal
        }
      }

      const data = await tracerouteApi.getASPathAnalysis(params)
      setPathData(data)
    } catch (error: any) {
      console.error('Failed to load path data:', error)
      Toast.error({ content: error.response?.data?.detail || '加载路径数据失败', duration: 3 })
    } finally {
      setPathLoading(false)
    }
  }, [selectedRegion, pathType, startTime, endTime])

  // ===== 路径详情 =====
  const loadPathDetail = useCallback(async () => {
    if (!selectedRegion || !detailPathInput.trim()) {
      Toast.warning({ content: '请输入路径', duration: 3 })
      return
    }
    setPathDetailLoading(true)
    try {
      const params: any = {
        region: selectedRegion,
        path: detailPathInput.trim(),
        path_type: detailPathType,
        top_n: 100,
      }
      if (startTime) params.start_time = startTime.toISOString()
      if (endTime) params.end_time = endTime.toISOString()

      const data = await tracerouteApi.getPathDetail(params)
      setPathDetail(data)
    } catch (error: any) {
      console.error('Failed to load path detail:', error)
      Toast.error({ content: error.response?.data?.detail || '加载路径详情失败', duration: 3 })
      setPathDetail(null)
    } finally {
      setPathDetailLoading(false)
    }
  }, [selectedRegion, detailPathInput, detailPathType, startTime, endTime])

  // 加载 Ping 时序筛选选项 - 必须在 loadPingTrendData 之前定义
  const loadPingFilterOptions = useCallback(async () => {
    if (!selectedRegion || !pingPathInput.trim()) {
      setPingFilterOptions(null)
      return
    }
    setPingFilterLoading(true)
    try {
      const params: any = {
        region: selectedRegion,
        path: pingPathInput.trim(),
        path_type: pingPathType,
      }
      if (startTime) params.start_time = startTime.toISOString()
      if (endTime) params.end_time = endTime.toISOString()

      const data = await tracerouteApi.getPathFilterOptions(params)
      setPingFilterOptions(data)
    } catch (error: any) {
      console.error('Failed to load ping filter options:', error)
      setPingFilterOptions(null)
    } finally {
      setPingFilterLoading(false)
    }
  }, [selectedRegion, pingPathInput, pingPathType, startTime, endTime])

  // ===== Ping 时序 =====
  const loadPingTrendData = useCallback(async () => {
    if (!selectedRegion || !pingPathInput.trim()) {
      Toast.warning({ content: '请输入路径', duration: 3 })
      return
    }
    setPingTrendLoading(true)
    try {
      const params: any = {
        region: selectedRegion,
        path: pingPathInput.trim(),
        path_type: pingPathType,
        interval: pingTrendInterval,
        percentiles: [50, 90, 95, 99],
      }
      if (startTime) params.start_time = startTime.toISOString()
      if (endTime) params.end_time = endTime.toISOString()

      const data = await tracerouteApi.getPathPingTrend(params)
      setPingTrendData(data)

      // 自动加载筛选选项
      loadPingFilterOptions()
    } catch (error: any) {
      console.error('Failed to load ping trend:', error)
      Toast.error({ content: error.response?.data?.detail || '加载 Ping 时序数据失败', duration: 3 })
      setPingTrendData(null)
    } finally {
      setPingTrendLoading(false)
    }
  }, [selectedRegion, pingPathInput, pingPathType, pingTrendInterval, startTime, endTime, loadPingFilterOptions])

  // 初始加载和参数变化时加载数据
  useEffect(() => {
    if (selectedRegion) {
      loadTerminalData()
      loadPathData()
    }
  }, [selectedRegion])

  useEffect(() => {
    if (selectedRegion && activeTab === 'terminals') {
      loadTerminalData()
    }
  }, [terminalType])

  useEffect(() => {
    if (selectedRegion && activeTab === 'paths') {
      loadPathData(pathTerminalFilter || undefined)
    }
  }, [pathType])

  // 路径表格列
  const pathColumns = useMemo(() => [
    {
      title: '路径',
      dataIndex: 'path',
      key: 'path',
      width: 400,
      render: (text: string) => (
        <Text style={{ fontSize: 12, fontFamily: 'monospace' }}>
          {text?.length > 80 ? `${text.substring(0, 80)}...` : text}
        </Text>
      ),
    },
    {
      title: '路径数',
      dataIndex: 'occurrence_count',
      key: 'occurrence_count',
      width: 100,
      render: (count: number) => <Tag color="blue">{count?.toLocaleString()}</Tag>,
    },
    {
      title: '平均跳数',
      dataIndex: 'avg_hop_count',
      key: 'avg_hop_count',
      width: 100,
      render: (val: number) => val?.toFixed(1) || '-',
    },
    {
      title: '到达率',
      dataIndex: 'reach_rate',
      key: 'reach_rate',
      width: 100,
      render: (rate: number) => (
        <Tag color={rate > 0.9 ? 'green' : rate > 0.5 ? 'orange' : 'red'}>
          {(rate * 100).toFixed(1)}%
        </Tag>
      ),
    },
    {
      title: 'Prefix24 数',
      dataIndex: 'prefix24_count',
      key: 'prefix24_count',
      width: 100,
    },
    {
      title: '操作',
      key: 'action',
      width: 200,
      render: (_: any, record: any) => (
        <Space>
          <Button
            size="small"
            onClick={() => {
              setDetailPathInput(record.path)
              setDetailPathType(pathType)
              setActiveTab('detail')
            }}
          >
            查看详情
          </Button>
          <Button
            size="small"
            type="primary"
            onClick={() => {
              setPingPathInput(record.path)
              setPingPathType(pathType)
              setActiveTab('ping')
            }}
          >
            Ping 分析
          </Button>
        </Space>
      ),
    },
  ], [pathType])

  // 末端节点表格列
  const terminalColumns = useMemo(() => [
    {
      title: '末端节点',
      dataIndex: 'terminal',
      key: 'terminal',
      render: (text: string) => (
        <Text strong style={{ fontFamily: 'monospace' }}>{text}</Text>
      ),
    },
    {
      title: '路径数',
      dataIndex: 'trace_count',
      key: 'trace_count',
      width: 100,
      render: (count: number) => <Tag color="blue">{count?.toLocaleString()}</Tag>,
    },
    {
      title: 'Prefix24 数',
      dataIndex: 'prefix24_count',
      key: 'prefix24_count',
      width: 100,
    },
    {
      title: '到达率',
      dataIndex: 'reach_rate',
      key: 'reach_rate',
      width: 100,
      render: (rate: number) => (
        <Tag color={rate > 0.9 ? 'green' : rate > 0.5 ? 'orange' : 'red'}>
          {(rate * 100).toFixed(1)}%
        </Tag>
      ),
    },
    {
      title: '操作',
      key: 'action',
      width: 120,
      render: (_: any, record: TerminalNode) => (
        <Button
          size="small"
          type="primary"
          onClick={() => {
            setPathTerminalFilter(record.terminal)
            setActiveTab('paths')
          }}
        >
          查看路径
        </Button>
      ),
    },
  ], [])

  // 返回主页
  const goBackToMain = () => {
    navigate('/visualization')
  }

  // 刷新当前 Tab
  const handleRefresh = () => {
    switch (activeTab) {
      case 'terminals':
        loadTerminalData()
        break
      case 'paths':
        loadPathData(pathTerminalFilter || undefined)
        break
      case 'detail':
        if (detailPathInput) loadPathDetail()
        break
      case 'ping':
        if (pingPathInput) loadPingTrendData()
        break
    }
  }

  if (!selectedRegion) {
    return (
      <div className="visualization-page">
        <Card style={{ padding: 60 }}>
          <Empty title="请先选择地区" description="请从下方选择地区后再进入深度分析" />
          <div style={{ marginTop: 24 }}>
            <Select
              placeholder="选择地区"
              style={{ width: 300 }}
              loading={regionsLoading}
              filter
              onChange={(value) => setSelectedRegion(String(value))}
            >
              {regions.map((region) => (
                <Select.Option key={region} value={region}>{region}</Select.Option>
              ))}
            </Select>
          </div>
          <div style={{ textAlign: 'center', marginTop: 24 }}>
            <Button type="primary" onClick={goBackToMain}>返回可视化主页</Button>
          </div>
        </Card>
      </div>
    )
  }

  return (
    <div className="visualization-page traceroute-deep-dive">
      {/* 页面头部 - 全局控制 */}
      <Card style={{ marginBottom: 16 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 16 }}>
          <Space>
            <Button icon={<IconArrowLeft />} onClick={goBackToMain}>返回</Button>
            <Title heading={4} style={{ margin: 0 }}>Traceroute 深度分析</Title>
            <Tag color="blue" size="large">{selectedRegion}</Tag>
          </Space>

          <Space wrap>
            {/* 地区选择 */}
            <Select
              value={selectedRegion}
              onChange={(value) => {
                setSelectedRegion(String(value))
                // 切换地区时清空所有数据
                setTerminalData(null)
                setPathData(null)
                setPathDetail(null)
                setPingTrendData(null)
              }}
              style={{ width: 180 }}
              filter
              placeholder="搜索地区"
            >
              {regions.map((region) => (
                <Select.Option key={region} value={region}>{region}</Select.Option>
              ))}
            </Select>

            {/* 时间范围 */}
            <DatePicker
              type="dateTimeRange"
              value={startTime && endTime ? [startTime, endTime] : undefined}
              onChange={(dates) => {
                if (Array.isArray(dates) && dates.length === 2 && dates[0] && dates[1]) {
                  setStartTime(dates[0] as Date)
                  setEndTime(dates[1] as Date)
                } else {
                  setStartTime(null)
                  setEndTime(null)
                }
              }}
              style={{ width: 360 }}
              placeholder="选择时间范围（可选）"
            />

            <Button icon={<IconRefresh />} onClick={handleRefresh}>刷新</Button>
          </Space>
        </div>
      </Card>

      {/* Tab 切换分析模式 */}
      <Tabs
        type="card"
        activeKey={activeTab}
        onChange={(key) => {
          setActiveTab(key)
          // 切换 Tab 时加载对应数据
          if (key === 'terminals' && !terminalData) {
            loadTerminalData()
          } else if (key === 'paths' && !pathData) {
            loadPathData(pathTerminalFilter || undefined)
          }
        }}
      >
        {/* Tab 1: 末端节点分析 */}
        <TabPane
          tab={<><IconServer /> 末端节点分析</>}
          itemKey="terminals"
        >
          <div className="tab-content">
            {/* 筛选栏 */}
            <Card style={{ marginBottom: 16 }}>
              <Space spacing="loose" wrap align="center">
                <div>
                  <Text type="tertiary" size="small" style={{ display: 'block', marginBottom: 4 }}>末端类型</Text>
                  <RadioGroup
                    type="button"
                    value={terminalType}
                    onChange={(e) => setTerminalType(e.target.value as 'as' | 'asgeo')}
                  >
                    <Radio value="asgeo">AS+Geo</Radio>
                    <Radio value="as">AS</Radio>
                  </RadioGroup>
                </div>

                <div>
                  <Text type="tertiary" size="small" style={{ display: 'block', marginBottom: 4 }}>搜索末端节点</Text>
                  <Select
                    style={{ width: 280 }}
                    placeholder="输入 AS 号或国家代码搜索..."
                    filter
                    showClear
                    onSearch={(value) => {
                      setTerminalSearch(value)
                      if (value.length >= 1) loadTerminalOptions(value)
                    }}
                    value={terminalSearch || undefined}
                    onChange={(value) => {
                      setTerminalSearch(String(value || ''))
                      loadTerminalData()
                    }}
                    loading={terminalOptionsLoading}
                  >
                    {terminalOptions.map((item) => (
                      <Select.Option key={item.terminal} value={item.terminal}>
                        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                          <span>{item.terminal}</span>
                          <Text type="tertiary" size="small">{item.trace_count} 条</Text>
                        </div>
                      </Select.Option>
                    ))}
                  </Select>
                </div>
              </Space>
            </Card>

            {/* 统计卡片 */}
            {terminalData && (
              <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
                <Col span={6}>
                  <Card className="metric-card">
                    <Text type="tertiary">总路径数</Text>
                    <div className="metric-value">{terminalData.total_traces?.toLocaleString() || 0}</div>
                  </Card>
                </Col>
                <Col span={6}>
                  <Card className="metric-card">
                    <Text type="tertiary">末端节点数</Text>
                    <div className="metric-value">{terminalData.unique_terminals || 0}</div>
                  </Card>
                </Col>
                <Col span={6}>
                  <Card className="metric-card">
                    <Text type="tertiary">数据源</Text>
                    <div style={{ marginTop: 8 }}>
                      <DataSourceBadge source={terminalData.data_source} />
                    </div>
                  </Card>
                </Col>
                <Col span={6}>
                  <Card className="metric-card">
                    <Text type="tertiary">分析类型</Text>
                    <div className="metric-value">{terminalType === 'asgeo' ? 'AS+Geo' : 'AS'}</div>
                  </Card>
                </Col>
              </Row>
            )}

            {/* 末端节点表格 */}
            <Card title={`末端节点列表 (${terminalData?.terminals?.length || 0})`}>
              <Spin spinning={terminalLoading}>
                <Table
                  dataSource={terminalData?.terminals || []}
                  columns={terminalColumns}
                  pagination={{ pageSize: 15 }}
                  rowKey="terminal"
                  empty={<Empty description="暂无数据" />}
                />
              </Spin>
            </Card>

            {/* 末端节点分布图表 */}
            {terminalData?.terminals && terminalData.terminals.length > 0 && (
              <Card title="末端节点路径分布" style={{ marginTop: 16 }}>
                <ChartDisplay
                  data={{
                    title: '',
                    chartType: 'bar',
                    data: {
                      xAxis: terminalData.terminals.slice(0, 15).map((t) =>
                        t.terminal.length > 15 ? t.terminal.substring(0, 15) + '...' : t.terminal
                      ),
                      series: [
                        { name: '路径数', data: terminalData.terminals.slice(0, 15).map((t) => t.trace_count) },
                        { name: 'Prefix24数', data: terminalData.terminals.slice(0, 15).map((t) => t.prefix24_count) },
                      ],
                      yAxisName: '数量',
                    },
                  }}
                  height={250}
                />
              </Card>
            )}
          </div>
        </TabPane>

        {/* Tab 2: 路径分析 */}
        <TabPane
          tab={<><IconLink /> 路径分析</>}
          itemKey="paths"
        >
          <div className="tab-content">
            {/* 筛选栏 */}
            <Card style={{ marginBottom: 16 }}>
              <Space spacing="loose" wrap align="center">
                <div>
                  <Text type="tertiary" size="small" style={{ display: 'block', marginBottom: 4 }}>路径类型</Text>
                  <RadioGroup
                    type="button"
                    value={pathType}
                    onChange={(e) => setPathType(e.target.value as 'as' | 'asgeo')}
                  >
                    <Radio value="as">AS 路径</Radio>
                    <Radio value="asgeo">ASGeo 路径</Radio>
                  </RadioGroup>
                </div>

                <div>
                  <Text type="tertiary" size="small" style={{ display: 'block', marginBottom: 4 }}>按末端筛选</Text>
                  <Input
                    style={{ width: 250 }}
                    placeholder="输入末端节点过滤..."
                    value={pathTerminalFilter}
                    onChange={(e) => setPathTerminalFilter(e)}
                    onBlur={() => loadPathData(pathTerminalFilter || undefined)}
                    onKeyPress={(e) => e.key === 'Enter' && loadPathData(pathTerminalFilter || undefined)}
                  />
                </div>

                {pathTerminalFilter && (
                  <div>
                    <Text type="tertiary" size="small">当前筛选</Text>
                    <Tag color="blue" size="large" style={{ marginLeft: 8 }}>
                      {pathTerminalFilter}
                      <span
                        style={{ marginLeft: 8, cursor: 'pointer' }}
                        onClick={() => {
                          setPathTerminalFilter('')
                          loadPathData()
                        }}
                      >
                        ×
                      </span>
                    </Tag>
                  </div>
                )}
              </Space>
            </Card>

            {/* 统计卡片 */}
            {pathData && (
              <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
                <Col span={6}>
                  <Card className="metric-card">
                    <Text type="tertiary">总路径数</Text>
                    <div className="metric-value">{pathData.total_traces?.toLocaleString()}</div>
                  </Card>
                </Col>
                <Col span={6}>
                  <Card className="metric-card">
                    <Text type="tertiary">独立路径</Text>
                    <div className="metric-value">{pathData.unique_paths?.toLocaleString()}</div>
                  </Card>
                </Col>
                <Col span={6}>
                  <Card className="metric-card">
                    <Text type="tertiary">平均跳数</Text>
                    <div className="metric-value">{pathData.avg_hop_count?.toFixed(1)}</div>
                  </Card>
                </Col>
                <Col span={6}>
                  <Card className="metric-card">
                    <Text type="tertiary">到达目标</Text>
                    <div className="metric-value">{pathData.total_reached?.toLocaleString()}</div>
                  </Card>
                </Col>
              </Row>
            )}

            {/* 路径表格 */}
            <Card title={`${pathType === 'as' ? 'AS' : 'ASGeo'} 路径列表`}>
              <Spin spinning={pathLoading}>
                <Table
                  dataSource={pathData?.paths || []}
                  columns={pathColumns}
                  pagination={{ pageSize: 20 }}
                  rowKey="path"
                  empty={<Empty description="暂无路径数据" />}
                />
              </Spin>
            </Card>
          </div>
        </TabPane>

        {/* Tab 3: 路径详情 */}
        <TabPane
          tab={<><IconSearch /> 路径详情</>}
          itemKey="detail"
        >
          <div className="tab-content">
            {/* 输入栏 */}
            <Card style={{ marginBottom: 16 }}>
              <Space spacing="loose" wrap>
                <div>
                  <Text type="tertiary" size="small" style={{ display: 'block', marginBottom: 4 }}>路径类型</Text>
                  <RadioGroup
                    type="button"
                    value={detailPathType}
                    onChange={(e) => setDetailPathType(e.target.value as 'as' | 'asgeo')}
                  >
                    <Radio value="as">AS 路径</Radio>
                    <Radio value="asgeo">ASGeo 路径</Radio>
                  </RadioGroup>
                </div>

                <div style={{ flex: 1, minWidth: 400 }}>
                  <Text type="tertiary" size="small" style={{ display: 'block', marginBottom: 4 }}>输入路径</Text>
                  <Input
                    placeholder="例如: AS16509->AS0->AS41967"
                    value={detailPathInput}
                    onChange={(e) => setDetailPathInput(e)}
                    onKeyPress={(e) => e.key === 'Enter' && loadPathDetail()}
                    style={{ width: '100%' }}
                  />
                </div>

                <Button type="primary" icon={<IconSearch />} onClick={loadPathDetail} loading={pathDetailLoading}>
                  查询
                </Button>
              </Space>
            </Card>

            {/* 详情展示 */}
            {pathDetailLoading ? (
              <Card style={{ padding: 60, textAlign: 'center' }}>
                <Spin size="large" />
                <Text type="tertiary" style={{ display: 'block', marginTop: 12 }}>正在加载路径详情...</Text>
              </Card>
            ) : pathDetail ? (
              <>
                {/* 路径信息 */}
                <Card style={{ marginBottom: 16 }}>
                  <Text type="tertiary" size="small">当前路径</Text>
                  <div style={{ marginTop: 4, marginBottom: 16 }}>
                    <Text strong style={{ fontFamily: 'monospace', fontSize: 12, wordBreak: 'break-all' }}>
                      {pathDetail.path}
                    </Text>
                  </div>

                  <Row gutter={16}>
                    <Col span={6}>
                      <Text type="tertiary" size="small">总路径数</Text>
                      <div style={{ fontSize: 20, fontWeight: 'bold', color: 'var(--semi-color-primary)' }}>
                        {pathDetail.total_traces?.toLocaleString()}
                      </div>
                    </Col>
                    <Col span={6}>
                      <Text type="tertiary" size="small">末端节点</Text>
                      <div style={{ fontSize: 20, fontWeight: 'bold' }}>{pathDetail.unique_terminals}</div>
                    </Col>
                    <Col span={6}>
                      <Text type="tertiary" size="small">Prefix24数</Text>
                      <div style={{ fontSize: 20, fontWeight: 'bold' }}>{pathDetail.unique_prefix24s}</div>
                    </Col>
                    <Col span={6}>
                      <Text type="tertiary" size="small">平均跳数</Text>
                      <div style={{
                        fontSize: 20,
                        fontWeight: 'bold',
                      }}>
                        {pathDetail.avg_hop_count?.toFixed(1) || '-'}
                      </div>
                    </Col>
                  </Row>

                  <div style={{ marginTop: 16 }}>
                    <Button
                      type="primary"
                      icon={<IconLineChartStroked />}
                      onClick={() => {
                        setPingPathInput(pathDetail.path)
                        setPingPathType(pathDetail.path_type as 'as' | 'asgeo')
                        setActiveTab('ping')
                      }}
                      disabled={pathDetail.prefix24s.length === 0}
                    >
                      查看关联 Ping 时序分析
                    </Button>
                  </div>
                </Card>

                {/* 详细信息标签页 */}
                <Tabs type="card">
                  <Tabs.TabPane tab={<><IconServer /> 末端节点 ({pathDetail.terminals?.length || 0})</>} itemKey="terminals">
                    <Table
                      dataSource={pathDetail.terminals || []}
                      columns={[
                        { title: '末端节点', dataIndex: 'terminal', render: (t: string) => <Text strong style={{ fontFamily: 'monospace' }}>{t}</Text> },
                        { title: '路径数', dataIndex: 'trace_count', width: 100, render: (c: number) => <Tag color="blue">{c?.toLocaleString()}</Tag> },
                        { title: 'Prefix24数', dataIndex: 'prefix24_count', width: 100 },
                        { title: '到达率', dataIndex: 'reach_rate', width: 100, render: (r: number) => <Tag color={r > 0.9 ? 'green' : 'orange'}>{(r * 100).toFixed(1)}%</Tag> },
                      ]}
                      pagination={{ pageSize: 10 }}
                      rowKey="terminal"
                      size="small"
                    />
                  </Tabs.TabPane>

                  <Tabs.TabPane tab={<><IconLink /> Prefix24 ({pathDetail.prefix24s?.length || 0})</>} itemKey="prefix24s">
                    <Table
                      dataSource={pathDetail.prefix24s || []}
                      columns={[
                        { title: 'Prefix24', dataIndex: 'prefix24', render: (t: string) => <Text style={{ fontFamily: 'monospace' }}>{t}</Text> },
                        { title: '路径数', dataIndex: 'trace_count', width: 100 },
                        { title: '独立IP', dataIndex: 'unique_ips', width: 100 },
                      ]}
                      pagination={{ pageSize: 10 }}
                      rowKey="prefix24"
                      size="small"
                    />
                  </Tabs.TabPane>

                  <Tabs.TabPane tab={<><IconHome /> 数据中心 ({pathDetail.data_centers?.length || 0})</>} itemKey="datacenters">
                    {pathDetail.data_centers && pathDetail.data_centers.length > 0 ? (
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                        {pathDetail.data_centers.map((item, idx) => (
                          <Tag key={idx} color={idx < 3 ? 'blue' : 'grey'} size="large">
                            {item.data_center} ({item.count})
                          </Tag>
                        ))}
                      </div>
                    ) : (
                      <Empty description="无数据中心数据" />
                    )}
                  </Tabs.TabPane>
                </Tabs>
              </>
            ) : (
              <Card style={{ padding: 60 }}>
                <Empty description="请输入路径进行查询" />
              </Card>
            )}
          </div>
        </TabPane>

        {/* Tab 4: Ping 时序分析 */}
        <TabPane
          tab={<><IconLineChartStroked /> Ping 时序分析</>}
          itemKey="ping"
        >
          <div className="tab-content">
            {/* 输入栏 */}
            <Card style={{ marginBottom: 16 }}>
              <Space spacing="loose" wrap>
                <div>
                  <Text type="tertiary" size="small" style={{ display: 'block', marginBottom: 4 }}>路径类型</Text>
                  <RadioGroup
                    type="button"
                    value={pingPathType}
                    onChange={(e) => setPingPathType(e.target.value as 'as' | 'asgeo')}
                  >
                    <Radio value="as">AS 路径</Radio>
                    <Radio value="asgeo">ASGeo 路径</Radio>
                  </RadioGroup>
                </div>

                <div style={{ flex: 1, minWidth: 400 }}>
                  <Text type="tertiary" size="small" style={{ display: 'block', marginBottom: 4 }}>输入路径</Text>
                  <Input
                    placeholder="例如: AS16509->AS0->AS41967"
                    value={pingPathInput}
                    onChange={(e) => setPingPathInput(e)}
                    onKeyPress={(e) => e.key === 'Enter' && loadPingTrendData()}
                    style={{ width: '100%' }}
                  />
                </div>

                <div>
                  <Text type="tertiary" size="small" style={{ display: 'block', marginBottom: 4 }}>时间粒度</Text>
                  <RadioGroup
                    type="button"
                    value={pingTrendInterval}
                    onChange={(e) => setPingTrendInterval(e.target.value)}
                  >
                    <Radio value="minute">分钟</Radio>
                    <Radio value="hour">小时</Radio>
                    <Radio value="day">天</Radio>
                  </RadioGroup>
                </div>

                <Button type="primary" icon={<IconLineChartStroked />} onClick={loadPingTrendData} loading={pingTrendLoading}>
                  分析
                </Button>

                <Button onClick={async () => {
                  // 直接测试 API 并显示结果
                  try {
                    const params = {
                      region: selectedRegion,
                      path: pingPathInput.trim() || 'AS16509->AS0->AS41967',
                      path_type: pingPathType,
                      interval: pingTrendInterval,
                    }
                    const data = await tracerouteApi.getPathPingTrend(params)
                    alert(`API 返回: time_series=${data.time_series?.length}, success=${data.success}`)
                    setPingTrendData(data)
                  } catch (e: any) {
                    alert('API 错误: ' + e.message)
                  }
                }}>
                  测试API
                </Button>

                <Button onClick={loadPingFilterOptions} loading={pingFilterLoading}>
                  加载筛选选项
                </Button>
              </Space>
            </Card>

            {/* 高级筛选 */}
            {pingFilterOptions && (
              <Card style={{ marginBottom: 16 }}>
                <Collapse defaultActiveKey={['filter']}>
                  <Collapse.Panel header="高级筛选" itemKey="filter">
                    <Row gutter={[16, 16]}>
                      <Col span={6}>
                        <Text type="tertiary" size="small" style={{ display: 'block', marginBottom: 4 }}>AS 筛选</Text>
                        <Select
                          style={{ width: '100%' }}
                          placeholder={`共 ${pingFilterOptions.as_options?.length || 0} 个 AS`}
                          value={selectedAsn || undefined}
                          onChange={(value) => setSelectedAsn(value ? Number(value) : null)}
                          showClear
                          filter
                          getPopupContainer={() => document.body}
                        >
                          {(pingFilterOptions.as_options || []).map((item) => (
                            <Select.Option key={item.asn} value={item.asn}>
                              AS{item.asn} ({item.as_name?.slice(0, 20) || 'N/A'}) - {item.sample_count}
                            </Select.Option>
                          ))}
                        </Select>
                      </Col>
                      <Col span={6}>
                        <Text type="tertiary" size="small" style={{ display: 'block', marginBottom: 4 }}>ASGeo 筛选</Text>
                        <Select
                          style={{ width: '100%' }}
                          placeholder={`共 ${pingFilterOptions.asgeo_options?.length || 0} 个 ASGeo`}
                          value={selectedAsgeo || undefined}
                          onChange={(value) => setSelectedAsgeo(value ? String(value) : null)}
                          showClear
                          filter
                          getPopupContainer={() => document.body}
                        >
                          {(pingFilterOptions.asgeo_options || []).map((item) => (
                            <Select.Option key={item.asgeo} value={item.asgeo}>
                              {item.asgeo} ({item.sample_count})
                            </Select.Option>
                          ))}
                        </Select>
                      </Col>
                      <Col span={6}>
                        <Text type="tertiary" size="small" style={{ display: 'block', marginBottom: 4 }}>ISP 筛选</Text>
                        <Select
                          style={{ width: '100%' }}
                          placeholder={`共 ${pingFilterOptions.isp_options?.length || 0} 个 ISP`}
                          value={selectedIsp || undefined}
                          onChange={(value) => setSelectedIsp(value ? String(value) : null)}
                          showClear
                          filter
                          getPopupContainer={() => document.body}
                        >
                          {(pingFilterOptions.isp_options || []).map((item) => (
                            <Select.Option key={item.isp} value={item.isp}>
                              {item.isp} ({item.sample_count})
                            </Select.Option>
                          ))}
                        </Select>
                      </Col>
                      <Col span={6}>
                        <Text type="tertiary" size="small" style={{ display: 'block', marginBottom: 4 }}>数据中心筛选</Text>
                        <Select
                          style={{ width: '100%' }}
                          placeholder={`共 ${pingFilterOptions.data_center_options?.length || 0} 个数据中心`}
                          value={selectedDataCenter || undefined}
                          onChange={(value) => setSelectedDataCenter(value ? String(value) : null)}
                          showClear
                          filter
                          getPopupContainer={() => document.body}
                        >
                          {(pingFilterOptions.data_center_options || []).map((item) => (
                            <Select.Option key={item.data_center} value={item.data_center}>
                              {item.data_center} ({item.sample_count})
                            </Select.Option>
                          ))}
                        </Select>
                      </Col>
                    </Row>
                  </Collapse.Panel>
                </Collapse>
              </Card>
            )}

            {/* 结果展示 */}
            {pingTrendLoading ? (
              <Card style={{ padding: 60, textAlign: 'center' }}>
                <Spin size="large" />
                <Text type="tertiary" style={{ display: 'block', marginTop: 12 }}>正在加载 Ping 时序数据...</Text>
              </Card>
            ) : pingTrendData ? (
              <>
                {/* 路径信息 */}
                <Banner
                  type="info"
                  icon={<IconServer />}
                  title="路径 Ping 时序分析"
                  description={`关联 ${pingTrendData.prefix24_count} 个 Prefix24`}
                  style={{ marginBottom: 16 }}
                />

                {/* 图表 - 直接在 JSX 中构造数据，和 index.tsx 完全一样 */}
                {pingTrendData.time_series?.length > 0 && (() => {
                  // 调试：打印原始数据
                  console.log('=== DEBUG ===')
                  console.log('pingTrendData.time_series length:', pingTrendData.time_series.length)
                  console.log('pingTrendData.time_series[0]:', pingTrendData.time_series[0])
                  console.log('pingTrendData.time_series[0].mean_rtt:', pingTrendData.time_series[0]?.mean_rtt)
                  console.log('pingTrendData.time_series[0]?.mean_rtt:', pingTrendData.time_series[0]?.['mean_rtt'])

                  // 手动构造数据
                  const timeSeries = pingTrendData.time_series
                  const meanData: number[] = []
                  const medianData: number[] = []
                  const p95Data: number[] = []

                  for (let i = 0; i < timeSeries.length; i++) {
                    meanData.push(timeSeries[i].mean_rtt)
                    medianData.push(timeSeries[i].median_rtt)
                    p95Data.push(timeSeries[i].percentiles?.p95)
                  }

                  console.log('meanData length:', meanData.length)
                  console.log('meanData[0]:', meanData[0])
                  console.log('meanData first 5:', meanData.slice(0, 5))

                  const chartData = {
                    title: '',
                    chartType: 'line' as const,
                    data: {
                      xAxis: timeSeries.map((item: any) => item.time?.substring(0, 16)),
                      series: [
                        { name: '平均 RTT', data: meanData },
                        { name: '中位数 RTT', data: medianData },
                        { name: 'P95 RTT', data: p95Data },
                      ],
                      yAxisName: 'RTT (ms)',
                    },
                  }
                  console.log('chartData.data.series[0].data length:', chartData.data.series[0].data.length)
                  console.log('chartData.data.series[0].data[0]:', chartData.data.series[0].data[0])

                  return (
                    <Card title="RTT 时间趋势" style={{ marginBottom: 16 }}>
                      <ChartDisplay data={chartData} height={350} />
                    </Card>
                  )
                })()}

                {/* 统计摘要 */}
                {pingTrendData.summary && pingTrendData.summary.total_samples > 0 && (
                  <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
                    <Col span={6}>
                      <Card className="metric-card">
                        <Text type="tertiary" size="small">总样本数</Text>
                        <div style={{ fontSize: 20, fontWeight: 'bold', color: 'var(--semi-color-primary)' }}>
                          {pingTrendData.summary.total_samples?.toLocaleString()}
                        </div>
                      </Card>
                    </Col>
                    <Col span={6}>
                      <Card className="metric-card">
                        <Text type="tertiary" size="small">平均 RTT</Text>
                        <div style={{ fontSize: 20, fontWeight: 'bold', color: 'var(--semi-color-primary)' }}>
                          {pingTrendData.summary.mean_rtt?.toFixed(2)} ms
                        </div>
                      </Card>
                    </Col>
                    <Col span={6}>
                      <Card className="metric-card">
                        <Text type="tertiary" size="small">中位数 RTT</Text>
                        <div style={{ fontSize: 20, fontWeight: 'bold', color: 'var(--semi-color-success)' }}>
                          {pingTrendData.summary.median_rtt?.toFixed(2)} ms
                        </div>
                      </Card>
                    </Col>
                    <Col span={6}>
                      <Card className="metric-card">
                        <Text type="tertiary" size="small">P95 RTT</Text>
                        <div style={{ fontSize: 20, fontWeight: 'bold', color: 'var(--semi-color-warning)' }}>
                          {pingTrendData.summary.percentiles?.p95?.toFixed(2)} ms
                        </div>
                      </Card>
                    </Col>
                  </Row>
                )}

                {/* Prefix24 列表 */}
                {pingTrendData.prefix24s && pingTrendData.prefix24s.length > 0 && (
                  <Card title={`关联 Prefix24 (${pingTrendData.prefix24_count}个)`}>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
                      {pingTrendData.prefix24s.slice(0, 20).map((prefix: string, idx: number) => (
                        <Tag key={idx} color="cyan" style={{ fontFamily: 'monospace' }}>{prefix}</Tag>
                      ))}
                      {pingTrendData.prefix24_count > 20 && (
                        <Tag color="grey">+{pingTrendData.prefix24_count - 20} 更多</Tag>
                      )}
                    </div>
                  </Card>
                )}
              </>
            ) : (
              <Card style={{ padding: 60 }}>
                <Empty description="请输入路径进行 Ping 时序分析" />
              </Card>
            )}
          </div>
        </TabPane>
      </Tabs>
    </div>
  )
}

export default TracerouteDeepDive

/**
 * 地区概览组件
 * 展示一个地区的 AS、ASGeo、数据中心、ISP 等元数据统计和排行
 * 支持二级 Geo 筛选和前缀导出功能
 */
import { useState, useEffect, useCallback } from 'react'
import {
  Card,
  Typography,
  Select,
  Table,
  Tag,
  Space,
  Spin,
  Empty,
  Tabs,
  TabPane,
  Button,
  Row,
  Col,
  Progress,
  Modal,
} from '@douyinfe/semi-ui'
import {
  IconServer,
  IconGlobe,
  IconHome,
  IconSearch,
  IconDownload,
  IconFilter,
  IconUserGroup,
} from '@douyinfe/semi-icons'
import axios from 'axios'

const { Text } = Typography

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

// 数据类型
interface AsData {
  asn: number
  as_name: string
  sample_count: number
  display: string
  unique_ips?: number
  prefix24_count?: number
}

interface AsgeoData {
  asgeo: string
  asn: number
  country: string
  as_name: string
  sample_count: number
  unique_ips?: number
  prefix24_count?: number
}

interface DataCenterData {
  data_center: string
  sample_count: number
}

interface IspData {
  asn: number
  as_name: string
  prefix24_count: number
  isp_domain_count: number
  unique_ips: number
  sample_count: number
}

interface IspDomainData {
  isp_domain: string
  prefix24: string
  sample_count: number
  unique_ips: number
  avg_rtt: number | null
}

interface IspPrefix24Data {
  prefix24: string
  isp_domain: string
  country: string
  city: string
  sample_count: number
  unique_ips: number
  avg_rtt: number | null
  median_rtt: number | null
}

interface Prefix24Data {
  prefix24: string
  sample_count: number
  unique_ips: number
  asn?: number
  as_name?: string
  country?: string
  city?: string
  avg_rtt?: number
  median_rtt?: number
  p95_rtt?: number
}

interface GeoOption {
  geo: string
  sample_count: number
  asn_count: number
}

interface RegionOverviewProps {
  regions: string[]
  regionsLoading: boolean
}

function RegionOverview({ regions, regionsLoading }: RegionOverviewProps) {
  const [selectedRegion, setSelectedRegion] = useState<string>('')
  const [selectedGeo, setSelectedGeo] = useState<string>('')  // 二级 Geo 筛选
  const [activeTab, setActiveTab] = useState<string>('as')
  const [searchText, setSearchText] = useState('')

  // 数据状态
  const [asList, setAsList] = useState<AsData[]>([])
  const [asgeoList, setAsgeoList] = useState<AsgeoData[]>([])
  const [dcList, setDcList] = useState<DataCenterData[]>([])
  const [ispList, setIspList] = useState<IspData[]>([])
  const [geoOptions, setGeoOptions] = useState<GeoOption[]>([])
  const [loading, setLoading] = useState(false)
  const [loadingProgress, setLoadingProgress] = useState(0)

  // 选中的 AS 详情
  const [selectedAsn, setSelectedAsn] = useState<number | null>(null)
  const [asnPrefixes, setAsnPrefixes] = useState<Prefix24Data[]>([])
  const [asnPrefixesLoading, setAsnPrefixesLoading] = useState(false)

  // 选中的 ASGeo 详情
  const [selectedAsgeo, setSelectedAsgeo] = useState<string | null>(null)
  const [asgeoPrefixes, setAsgeoPrefixes] = useState<Prefix24Data[]>([])
  const [asgeoPrefixesLoading, setAsgeoPrefixesLoading] = useState(false)

  // 选中的 ISP 详情 (实际上是 AS 详情)
  const [selectedIsp, setSelectedIsp] = useState<number | null>(null)
  const [selectedIspName, setSelectedIspName] = useState<string>('')
  const [ispDomainList, setIspDomainList] = useState<IspDomainData[]>([])
  const [ispPrefix24List, setIspPrefix24List] = useState<IspPrefix24Data[]>([])
  const [ispDetailLoading, setIspDetailLoading] = useState(false)
  const [ispDetailTab, setIspDetailTab] = useState<string>('domain')

  // 导出状态
  const [exportModalVisible, setExportModalVisible] = useState(false)
  const [exportData, setExportData] = useState<Prefix24Data[]>([])
  const [exportLoading, setExportLoading] = useState(false)

  const apiBase = getApiBase()

  // 提取 Geo 列表（从 ASGeo 中提取国家部分）
  const extractGeoList = useCallback((asgeos: AsgeoData[]): GeoOption[] => {
    const geoMap = new Map<string, { sample_count: number; asn_count: number }>()

    asgeos.forEach(item => {
      if (item.country) {
        const existing = geoMap.get(item.country) || { sample_count: 0, asn_count: 0 }
        geoMap.set(item.country, {
          sample_count: existing.sample_count + item.sample_count,
          asn_count: existing.asn_count + 1
        })
      }
    })

    return Array.from(geoMap.entries())
      .map(([geo, data]) => ({
        geo,
        sample_count: data.sample_count,
        asn_count: data.asn_count
      }))
      .sort((a, b) => b.sample_count - a.sample_count)
  }, [])

  // 加载地区数据
  const loadRegionData = useCallback(async (region: string) => {
    if (!region) return

    setLoading(true)
    setLoadingProgress(0)

    try {
      const progressInterval = setInterval(() => {
        setLoadingProgress(prev => Math.min(prev + 10, 90))
      }, 100)

      const [asRes, asgeoRes, dcRes, ispRes] = await Promise.all([
        axios.get(`${apiBase}/api/clickhouse/metadata/asns`, {
          params: { region, limit: 500 }
        }),
        axios.get(`${apiBase}/api/clickhouse/metadata/asgeos`, {
          params: { region, limit: 500 }
        }),
        axios.get(`${apiBase}/api/clickhouse/metadata/data-centers`, {
          params: { region, limit: 100 }
        }),
        axios.get(`${apiBase}/api/clickhouse/metadata/isps/stats`, {
          params: { region, limit: 200 }
        }),
      ])

      clearInterval(progressInterval)
      setLoadingProgress(100)

      const asns = asRes.data.asns || []
      const asgeos = asgeoRes.data.asgeos || []

      setAsList(asns)
      setAsgeoList(asgeos)
      setDcList(dcRes.data.data_centers || [])
      setIspList(ispRes.data.isps || [])
      setGeoOptions(extractGeoList(asgeos))
    } catch (error) {
      console.error('Failed to load region data:', error)
    } finally {
      setLoading(false)
    }
  }, [apiBase, extractGeoList])

  // 加载 AS 的前缀列表
  const loadAsnPrefixes = useCallback(async (asn: number) => {
    if (!selectedRegion || !asn) return

    setAsnPrefixesLoading(true)
    try {
      const response = await axios.get(`${apiBase}/api/clickhouse/metadata/prefix24s`, {
        params: { region: selectedRegion, asn: asn, limit: 500 }
      })
      setAsnPrefixes(response.data.prefix24s || [])
    } catch (error) {
      console.error('Failed to load AS prefixes:', error)
    } finally {
      setAsnPrefixesLoading(false)
    }
  }, [selectedRegion, apiBase])

  // 加载 ASGeo 的前缀列表（通过 export API）
  const loadAsgeoPrefixes = useCallback(async (asgeo: string) => {
    if (!selectedRegion || !asgeo) return

    setAsgeoPrefixesLoading(true)
    try {
      const response = await axios.post(`${apiBase}/api/clickhouse/metadata/export/prefix24s`, {
        region: selectedRegion,
        asgeo: asgeo,
        limit: 500
      })
      setAsgeoPrefixes(response.data.prefix24s || [])
    } catch (error) {
      console.error('Failed to load ASGeo prefixes:', error)
    } finally {
      setAsgeoPrefixesLoading(false)
    }
  }, [selectedRegion, apiBase])

  // 加载 ISP 详情 (按 AS)
  const loadIspDetail = useCallback(async (asn: number, asName: string) => {
    if (!selectedRegion || !asn) return

    setIspDetailLoading(true)
    setSelectedIspName(asName)
    try {
      const response = await axios.post(`${apiBase}/api/clickhouse/metadata/isp/detail`, {
        region: selectedRegion,
        asn: asn,
        limit: 1000
      })
      setIspDomainList(response.data.domain_list || [])
      setIspPrefix24List(response.data.prefix24_list || [])
    } catch (error) {
      console.error('Failed to load ISP detail:', error)
    } finally {
      setIspDetailLoading(false)
    }
  }, [selectedRegion, apiBase])

  // 导出前缀数据
  const exportPrefixes = useCallback(async (filter: { asn?: number; asgeo?: string; geo?: string }) => {
    if (!selectedRegion) return

    setExportLoading(true)
    try {
      const response = await axios.post(`${apiBase}/api/clickhouse/metadata/export/prefix24s`, {
        region: selectedRegion,
        country: filter.geo,  // geo 就是 country
        ...filter,
        limit: 2000
      })
      setExportData(response.data.prefix24s || [])
      setExportModalVisible(true)
    } catch (error) {
      console.error('Failed to export prefixes:', error)
    } finally {
      setExportLoading(false)
    }
  }, [selectedRegion, apiBase])

  // 下载 CSV
  const downloadCSV = (data: Prefix24Data[], filename: string) => {
    const headers = ['prefix24', 'asn', 'as_name', 'country', 'city', 'sample_count', 'unique_ips', 'avg_rtt', 'median_rtt', 'p95_rtt']
    const csvContent = [
      headers.join(','),
      ...data.map(row => headers.map(h => row[h as keyof Prefix24Data] || '').join(','))
    ].join('\n')

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
    const link = document.createElement('a')
    link.href = URL.createObjectURL(blob)
    link.download = `${filename}.csv`
    link.click()
  }

  // 下载 ISP Domain 列表 CSV
  const downloadIspDomainCSV = (data: IspDomainData[], filename: string) => {
    const headers = ['isp_domain', 'prefix24', 'sample_count', 'unique_ips', 'avg_rtt']
    const csvContent = [
      headers.join(','),
      ...data.map(row => headers.map(h => row[h as keyof IspDomainData] ?? '').join(','))
    ].join('\n')

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
    const link = document.createElement('a')
    link.href = URL.createObjectURL(blob)
    link.download = `${filename}.csv`
    link.click()
  }

  // 下载 ISP Prefix24 列表 CSV
  const downloadIspPrefix24CSV = (data: IspPrefix24Data[], filename: string) => {
    const headers = ['prefix24', 'isp_domain', 'country', 'city', 'sample_count', 'unique_ips', 'avg_rtt', 'median_rtt']
    const csvContent = [
      headers.join(','),
      ...data.map(row => headers.map(h => row[h as keyof IspPrefix24Data] ?? '').join(','))
    ].join('\n')

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
    const link = document.createElement('a')
    link.href = URL.createObjectURL(blob)
    link.download = `${filename}.csv`
    link.click()
  }

  // 地区变化时加载数据
  useEffect(() => {
    if (selectedRegion) {
      loadRegionData(selectedRegion)
      setSelectedAsn(null)
      setSelectedAsgeo(null)
      setSelectedIsp(null)
      setSelectedGeo('')
    }
  }, [selectedRegion, loadRegionData])

  // 选中 AS 时加载前缀
  useEffect(() => {
    if (selectedAsn) {
      loadAsnPrefixes(selectedAsn)
      setSelectedAsgeo(null)  // 关闭 ASGeo 详情
      setSelectedIsp(null)  // 关闭 ISP 详情
    }
  }, [selectedAsn, loadAsnPrefixes])

  // 选中 ASGeo 时加载前缀
  useEffect(() => {
    if (selectedAsgeo) {
      loadAsgeoPrefixes(selectedAsgeo)
      setSelectedAsn(null)  // 关闭 AS 详情
      setSelectedIsp(null)  // 关闭 ISP 详情
    }
  }, [selectedAsgeo, loadAsgeoPrefixes])

  // 选中 ISP 时加载详情
  useEffect(() => {
    if (selectedIsp && selectedIspName) {
      loadIspDetail(selectedIsp, selectedIspName)
      setSelectedAsn(null)  // 关闭 AS 详情
      setSelectedAsgeo(null)  // 关闭 ASGeo 详情
    }
  }, [selectedIsp, selectedIspName, loadIspDetail])

  // 根据 Geo 筛选数据
  const filteredAsList = (() => {
    let list = asList
    if (selectedGeo) {
      // 按 Geo 筛选：筛选出该 Geo 下有样本的 AS
      const asnsInGeo = new Set(
        asgeoList
          .filter(a => a.country === selectedGeo)
          .map(a => a.asn)
      )
      list = list.filter(item => asnsInGeo.has(item.asn))
    }
    if (searchText) {
      list = list.filter(item =>
        item.display.toLowerCase().includes(searchText.toLowerCase()) ||
        String(item.asn).includes(searchText)
      )
    }
    return list
  })()

  const filteredAsgeoList = (() => {
    let list = asgeoList
    if (selectedGeo) {
      list = list.filter(item => item.country === selectedGeo)
    }
    if (searchText) {
      list = list.filter(item =>
        item.asgeo.toLowerCase().includes(searchText.toLowerCase()) ||
        item.as_name?.toLowerCase().includes(searchText.toLowerCase())
      )
    }
    return list
  })()

  const filteredDcList = searchText
    ? dcList.filter(item =>
        item.data_center.toLowerCase().includes(searchText.toLowerCase())
      )
    : dcList

  const filteredIspList = searchText
    ? ispList.filter(item =>
        item.as_name.toLowerCase().includes(searchText.toLowerCase()) ||
        String(item.asn).includes(searchText)
      )
    : ispList

  // 计算统计数据
  // totalSamples is used for reference but not displayed currently
  // const totalSamples = filteredAsList.reduce((sum, item) => sum + item.sample_count, 0)

  // 当前右侧显示的是 AS 详情、ASGeo 详情还是 ISP 详情
  const showRightPanel = selectedAsn || selectedAsgeo || selectedIsp

  return (
    <div className="region-overview">
      {/* 地区选择 + Geo 二级筛选 */}
      <Card style={{ marginBottom: 16 }}>
        <Space style={{ width: '100%', justifyContent: 'space-between' }}>
          <Space>
            <Text>地区:</Text>
            <Select
              value={selectedRegion}
              onChange={(value) => setSelectedRegion(String(value))}
              placeholder="选择地区"
              style={{ width: 180 }}
              loading={regionsLoading}
              filter
            >
              {regions.map((region) => (
                <Select.Option key={region} value={region}>
                  {region}
                </Select.Option>
              ))}
            </Select>

            {/* 二级 Geo 筛选 */}
            {selectedRegion && geoOptions.length > 0 && (
              <>
                <Text type="tertiary">|</Text>
                <Space>
                  <IconFilter style={{ color: '#888' }} />
                  <Text>Geo 筛选:</Text>
                  <Select
                    value={selectedGeo}
                    onChange={(value) => {
                      setSelectedGeo(String(value || ''))
                      setSelectedAsn(null)
                      setSelectedAsgeo(null)
                    }}
                    placeholder="全部 Geo"
                    style={{ width: 180 }}
                    emptyContent={
                      <div style={{ padding: 8 }}>
                        <Text type="tertiary">暂无 Geo 数据</Text>
                      </div>
                    }
                  >
                    <Select.Option key="" value="">
                      <Text type="tertiary">全部 Geo</Text>
                    </Select.Option>
                    {geoOptions.map((item) => (
                      <Select.Option key={item.geo} value={item.geo}>
                        <Space>
                          <Tag color="cyan" size="small">{item.geo}</Tag>
                          <Text type="tertiary" size="small">
                            ({item.asn_count} AS, {item.sample_count.toLocaleString()} 样本)
                          </Text>
                        </Space>
                      </Select.Option>
                    ))}
                  </Select>
                </Space>
              </>
            )}
          </Space>

          <Space>
            <IconSearch style={{ color: '#999' }} />
            <input
              type="text"
              placeholder="搜索..."
              value={searchText}
              onChange={(e) => setSearchText(e.target.value)}
              style={{
                width: 160,
                padding: '6px 12px',
                border: '1px solid #e8e8e8',
                borderRadius: 4,
                fontSize: 14
              }}
            />
          </Space>
        </Space>
      </Card>

      {!selectedRegion ? (
        <Card>
          <Empty
            title="请选择地区"
            description="选择一个地区以查看该地区的 AS、ASGeo、数据中心等概览信息"
          />
        </Card>
      ) : loading ? (
        <Card>
          <div style={{ textAlign: 'center', padding: 60 }}>
            <Spin size="large" />
            <div style={{ marginTop: 16 }}>
              <Text type="tertiary">正在从 ClickHouse 加载 {selectedRegion} 的数据...</Text>
            </div>
            <div style={{ marginTop: 12, padding: '0 100px' }}>
              <Progress percent={loadingProgress} showInfo style={{ width: '100%' }} />
            </div>
          </div>
        </Card>
      ) : (
        <>
          {/* 统计概览 */}
          <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
            <Col span={6}>
              <Card>
                <div style={{ textAlign: 'center' }}>
                  <IconServer style={{ fontSize: 24, color: '#5C6BC0' }} />
                  <div style={{ fontSize: 28, fontWeight: 'bold', marginTop: 8 }}>{filteredAsList.length}</div>
                  <Text type="tertiary">AS 数量</Text>
                </div>
              </Card>
            </Col>
            <Col span={6}>
              <Card>
                <div style={{ textAlign: 'center' }}>
                  <IconGlobe style={{ fontSize: 24, color: '#26A69A' }} />
                  <div style={{ fontSize: 28, fontWeight: 'bold', marginTop: 8 }}>{filteredAsgeoList.length}</div>
                  <Text type="tertiary">ASGeo 数量</Text>
                </div>
              </Card>
            </Col>
            <Col span={6}>
              <Card>
                <div style={{ textAlign: 'center' }}>
                  <IconUserGroup style={{ fontSize: 24, color: '#42A5F5' }} />
                  <div style={{ fontSize: 28, fontWeight: 'bold', marginTop: 8 }}>{ispList.length}</div>
                  <Text type="tertiary">ISP 数量</Text>
                </div>
              </Card>
            </Col>
            <Col span={6}>
              <Card>
                <div style={{ textAlign: 'center' }}>
                  <IconHome style={{ fontSize: 24, color: '#AB47BC' }} />
                  <div style={{ fontSize: 28, fontWeight: 'bold', marginTop: 8 }}>{dcList.length}</div>
                  <Text type="tertiary">数据中心</Text>
                </div>
              </Card>
            </Col>
          </Row>

          {/* 主内容区域 */}
          <Row gutter={[16, 16]}>
            {/* 左侧: 数据列表 */}
            <Col span={showRightPanel ? 16 : 24}>
              <Card>
                <Tabs activeKey={activeTab} onChange={setActiveTab}>
                  <TabPane tab={<><IconServer /> AS 排行</>} itemKey="as">
                    <div style={{ marginBottom: 8 }}>
                      <Button
                        size="small"
                        icon={<IconDownload />}
                        loading={exportLoading}
                        onClick={() => exportPrefixes(selectedGeo ? { geo: selectedGeo } : {})}
                      >
                        导出 {selectedGeo && `(Geo: ${selectedGeo})`}
                      </Button>
                    </div>
                    <Table
                      dataSource={filteredAsList}
                      columns={[
                        {
                          title: 'AS号',
                          dataIndex: 'asn',
                          width: 100,
                          render: (value: number) => <Tag color="blue">AS{value}</Tag>,
                        },
                        {
                          title: 'AS名称',
                          dataIndex: 'as_name',
                          ellipsis: true,
                          render: (value: string) => value || '-',
                        },
                        {
                          title: 'C段数',
                          dataIndex: 'prefix24_count',
                          width: 90,
                          sorter: (a?: AsData, b?: AsData) => (a?.prefix24_count || 0) - (b?.prefix24_count || 0),
                          render: (value: number) => value?.toLocaleString() || '-',
                        },
                        {
                          title: 'IP数',
                          dataIndex: 'unique_ips',
                          width: 90,
                          sorter: (a?: AsData, b?: AsData) => (a?.unique_ips || 0) - (b?.unique_ips || 0),
                          render: (value: number) => value?.toLocaleString() || '-',
                        },
                        {
                          title: '样本数',
                          dataIndex: 'sample_count',
                          width: 100,
                          sorter: (a?: AsData, b?: AsData) => (a?.sample_count || 0) - (b?.sample_count || 0),
                          render: (value: number) => value?.toLocaleString(),
                        },
                        {
                          title: '操作',
                          width: 150,
                          render: (_: any, record: AsData) => (
                            <Space>
                              <Button size="small" onClick={() => setSelectedAsn(record.asn)}>前缀</Button>
                              <Button size="small" type="tertiary" icon={<IconDownload />} onClick={() => exportPrefixes({ asn: record.asn })} />
                            </Space>
                          ),
                        },
                      ]}
                      pagination={{ pageSize: 15 }}
                      rowKey="asn"
                      size="small"
                      scroll={{ y: 500 }}
                    />
                  </TabPane>

                  <TabPane tab={<><IconGlobe /> ASGeo 排行</>} itemKey="asgeo">
                    <Table
                      dataSource={filteredAsgeoList}
                      columns={[
                        {
                          title: 'ASGeo',
                          dataIndex: 'asgeo',
                          width: 150,
                          render: (value: string) => <Tag color="teal">{value}</Tag>,
                        },
                        {
                          title: 'AS名称',
                          dataIndex: 'as_name',
                          ellipsis: true,
                          render: (value: string) => value || '-',
                        },
                        {
                          title: 'Geo',
                          dataIndex: 'country',
                          width: 70,
                          render: (value: string) => <Tag color="cyan">{value}</Tag>,
                        },
                        {
                          title: 'C段数',
                          dataIndex: 'prefix24_count',
                          width: 90,
                          sorter: (a?: AsgeoData, b?: AsgeoData) => (a?.prefix24_count || 0) - (b?.prefix24_count || 0),
                          render: (value: number) => value?.toLocaleString() || '-',
                        },
                        {
                          title: 'IP数',
                          dataIndex: 'unique_ips',
                          width: 90,
                          sorter: (a?: AsgeoData, b?: AsgeoData) => (a?.unique_ips || 0) - (b?.unique_ips || 0),
                          render: (value: number) => value?.toLocaleString() || '-',
                        },
                        {
                          title: '样本数',
                          dataIndex: 'sample_count',
                          width: 100,
                          sorter: (a?: AsgeoData, b?: AsgeoData) => (a?.sample_count || 0) - (b?.sample_count || 0),
                          render: (value: number) => value?.toLocaleString(),
                        },
                        {
                          title: '操作',
                          width: 150,
                          render: (_: any, record: AsgeoData) => (
                            <Space>
                              <Button size="small" onClick={() => setSelectedAsgeo(record.asgeo)}>前缀</Button>
                              <Button size="small" type="tertiary" icon={<IconDownload />} onClick={() => exportPrefixes({ asgeo: record.asgeo })} />
                            </Space>
                          ),
                        },
                      ]}
                      pagination={{ pageSize: 15 }}
                      rowKey="asgeo"
                      size="small"
                      scroll={{ y: 500 }}
                    />
                  </TabPane>

                  <TabPane tab={<><IconHome /> 数据中心</>} itemKey="dc">
                    <Table
                      dataSource={filteredDcList}
                      columns={[
                        {
                          title: '数据中心',
                          dataIndex: 'data_center',
                          ellipsis: true,
                          render: (value: string) => <Tag color="violet">{value}</Tag>,
                        },
                        {
                          title: '样本数',
                          dataIndex: 'sample_count',
                          width: 100,
                          sorter: (a?: DataCenterData, b?: DataCenterData) => (a?.sample_count || 0) - (b?.sample_count || 0),
                          render: (value: number) => value?.toLocaleString(),
                        },
                      ]}
                      pagination={{ pageSize: 15 }}
                      rowKey="data_center"
                      size="small"
                      scroll={{ y: 500 }}
                    />
                  </TabPane>

                  <TabPane tab={<><IconUserGroup /> ISP 排行</>} itemKey="isp">
                    <Table
                      dataSource={filteredIspList}
                      columns={[
                        {
                          title: 'ISP (AS号)',
                          dataIndex: 'asn',
                          width: 110,
                          render: (value: number) => (
                            <Tag color="blue">AS{value}</Tag>
                          ),
                        },
                        {
                          title: 'AS名称',
                          dataIndex: 'as_name',
                          ellipsis: true,
                        },
                        {
                          title: 'C段数量',
                          dataIndex: 'prefix24_count',
                          width: 100,
                          sorter: (a?: IspData, b?: IspData) => (a?.prefix24_count || 0) - (b?.prefix24_count || 0),
                          render: (value: number) => <Text strong style={{ color: '#1976d2' }}>{value}</Text>,
                        },
                        {
                          title: '域名数',
                          dataIndex: 'isp_domain_count',
                          width: 80,
                          sorter: (a?: IspData, b?: IspData) => (a?.isp_domain_count || 0) - (b?.isp_domain_count || 0),
                          render: (value: number) => value,
                        },
                        {
                          title: 'IP数量',
                          dataIndex: 'unique_ips',
                          width: 100,
                          sorter: (a?: IspData, b?: IspData) => (a?.unique_ips || 0) - (b?.unique_ips || 0),
                          render: (value: number) => value?.toLocaleString(),
                        },
                        {
                          title: '样本数量',
                          dataIndex: 'sample_count',
                          width: 100,
                          sorter: (a?: IspData, b?: IspData) => (a?.sample_count || 0) - (b?.sample_count || 0),
                          render: (value: number) => value?.toLocaleString(),
                        },
                        {
                          title: '操作',
                          width: 80,
                          render: (_: any, record: IspData) => (
                            <Button size="small" onClick={() => {
                              setSelectedIsp(record.asn)
                              setSelectedIspName(record.as_name)
                            }}>
                              详情
                            </Button>
                          ),
                        },
                      ]}
                      pagination={{ pageSize: 15 }}
                      rowKey="asn"
                      size="small"
                      scroll={{ y: 500 }}
                    />
                  </TabPane>
                </Tabs>
              </Card>
            </Col>

            {/* 右侧: AS 前缀详情 */}
            {selectedAsn && (
              <Col span={8}>
                <Card
                  title={
                    <Space>
                      <Text>AS{selectedAsn} 前缀</Text>
                      <Button size="small" type="tertiary" onClick={() => setSelectedAsn(null)}>关闭</Button>
                    </Space>
                  }
                >
                  {asnPrefixesLoading ? (
                    <div style={{ textAlign: 'center', padding: 40 }}><Spin /></div>
                  ) : asnPrefixes.length > 0 ? (
                    <>
                      <div style={{ marginBottom: 8 }}>
                        <Button size="small" icon={<IconDownload />} onClick={() => downloadCSV(asnPrefixes, `AS${selectedAsn}_prefix24s`)}>
                          导出CSV ({asnPrefixes.length}条)
                        </Button>
                      </div>
                      <Table
                        dataSource={asnPrefixes}
                        columns={[
                          { title: 'IP前缀', dataIndex: 'prefix24', width: 120, render: (v: string) => <Tag color="cyan">{v}.0/24</Tag> },
                          { title: '样本数', dataIndex: 'sample_count', width: 80, render: (v: number) => v?.toLocaleString() },
                          { title: 'IP数', dataIndex: 'unique_ips', width: 70, render: (v: number) => v?.toLocaleString() },
                        ]}
                        pagination={false}
                        rowKey="prefix24"
                        size="small"
                        scroll={{ y: 400 }}
                      />
                    </>
                  ) : (
                    <Empty description="暂无数据" />
                  )}
                </Card>
              </Col>
            )}

            {/* 右侧: ASGeo 前缀详情 */}
            {selectedAsgeo && (
              <Col span={8}>
                <Card
                  title={
                    <Space>
                      <Text>{selectedAsgeo} 前缀</Text>
                      <Button size="small" type="tertiary" onClick={() => setSelectedAsgeo(null)}>关闭</Button>
                    </Space>
                  }
                >
                  {asgeoPrefixesLoading ? (
                    <div style={{ textAlign: 'center', padding: 40 }}><Spin /></div>
                  ) : asgeoPrefixes.length > 0 ? (
                    <>
                      <div style={{ marginBottom: 8 }}>
                        <Button size="small" icon={<IconDownload />} onClick={() => downloadCSV(asgeoPrefixes, `${selectedAsgeo}_prefix24s`)}>
                          导出CSV ({asgeoPrefixes.length}条)
                        </Button>
                      </div>
                      <Table
                        dataSource={asgeoPrefixes}
                        columns={[
                          { title: 'IP前缀', dataIndex: 'prefix24', width: 120, render: (v: string) => <Tag color="cyan">{v}.0/24</Tag> },
                          { title: '样本数', dataIndex: 'sample_count', width: 80, render: (v: number) => v?.toLocaleString() },
                          { title: 'IP数', dataIndex: 'unique_ips', width: 70, render: (v: number) => v?.toLocaleString() },
                        ]}
                        pagination={false}
                        rowKey="prefix24"
                        size="small"
                        scroll={{ y: 400 }}
                      />
                    </>
                  ) : (
                    <Empty description="暂无数据" />
                  )}
                </Card>
              </Col>
            )}

            {/* 右侧: ISP 详情 */}
            {selectedIsp && (
              <Col span={8}>
                <Card
                  title={
                    <Space>
                      <Text>AS{selectedIsp} {selectedIspName}</Text>
                      <Button size="small" type="tertiary" onClick={() => setSelectedIsp(null)}>关闭</Button>
                    </Space>
                  }
                >
                  {ispDetailLoading ? (
                    <div style={{ textAlign: 'center', padding: 40 }}><Spin /></div>
                  ) : (
                    <Tabs activeKey={ispDetailTab} onChange={setIspDetailTab} size="small">
                      <TabPane tab={`域名列表 (${ispDomainList.length})`} itemKey="domain">
                        <div style={{ marginBottom: 8 }}>
                          <Button size="small" icon={<IconDownload />} onClick={() => downloadIspDomainCSV(ispDomainList, `AS${selectedIsp}_domains`)}>
                            导出CSV
                          </Button>
                        </div>
                        <Table
                          dataSource={ispDomainList}
                          columns={[
                            { title: '域名', dataIndex: 'isp_domain', ellipsis: true, render: (v: string) => <Tag color="blue" size="small">{v}</Tag> },
                            { title: 'C段', dataIndex: 'prefix24', width: 120, render: (v: string) => <Tag color="cyan" size="small">{v}.0/24</Tag> },
                            { title: 'IP数', dataIndex: 'unique_ips', width: 60 },
                          ]}
                          pagination={false}
                          rowKey={(r) => r ? `${r.isp_domain}-${r.prefix24}` : Math.random().toString()}
                          size="small"
                          scroll={{ y: 280 }}
                        />
                      </TabPane>
                      <TabPane tab={`C段列表 (${ispPrefix24List.length})`} itemKey="prefix24">
                        <div style={{ marginBottom: 8 }}>
                          <Button size="small" icon={<IconDownload />} onClick={() => downloadIspPrefix24CSV(ispPrefix24List, `AS${selectedIsp}_prefix24`)}>
                            导出CSV
                          </Button>
                        </div>
                        <Table
                          dataSource={ispPrefix24List}
                          columns={[
                            { title: 'IP前缀', dataIndex: 'prefix24', width: 120, render: (v: string) => <Tag color="cyan" size="small">{v}.0/24</Tag> },
                            { title: '域名', dataIndex: 'isp_domain', ellipsis: true },
                            { title: '国家', dataIndex: 'country', width: 50 },
                            { title: 'IP数', dataIndex: 'unique_ips', width: 60 },
                          ]}
                          pagination={false}
                          rowKey="prefix24"
                          size="small"
                          scroll={{ y: 280 }}
                        />
                      </TabPane>
                    </Tabs>
                  )}
                </Card>
              </Col>
            )}
          </Row>
        </>
      )}

      {/* 导出数据模态框 */}
      <Modal
        title="前缀数据导出"
        visible={exportModalVisible}
        onCancel={() => setExportModalVisible(false)}
        footer={
          <Space>
            <Button onClick={() => setExportModalVisible(false)}>关闭</Button>
            <Button
              type="primary"
              icon={<IconDownload />}
              onClick={() => {
                downloadCSV(exportData, `prefix24s_export_${Date.now()}`)
                setExportModalVisible(false)
              }}
            >
              下载 CSV
            </Button>
          </Space>
        }
        width={900}
      >
        <Table
          dataSource={exportData.slice(0, 100)}
          columns={[
            { title: '前缀', dataIndex: 'prefix24', width: 130 },
            { title: 'AS', dataIndex: 'asn', width: 80 },
            { title: 'AS名称', dataIndex: 'as_name', ellipsis: true },
            { title: '国家', dataIndex: 'country', width: 60 },
            { title: '样本数', dataIndex: 'sample_count', width: 80 },
            { title: 'IP数', dataIndex: 'unique_ips', width: 70 },
          ]}
          pagination={false}
          rowKey="prefix24"
          size="small"
          scroll={{ y: 400 }}
        />
        {exportData.length > 100 && (
          <Text type="tertiary" style={{ marginTop: 8, display: 'block' }}>
            显示前 100 条，共 {exportData.length} 条数据。点击"下载 CSV"导出完整数据。
          </Text>
        )}
      </Modal>
    </div>
  )
}

export default RegionOverview

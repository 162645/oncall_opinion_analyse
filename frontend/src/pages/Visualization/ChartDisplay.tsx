/**
 * 图表展示组件
 * 支持折线图、柱状图、饼图、热力图等
 * 支持多指标勾选展示
 * 支持下载图片到本地
 */
import { useState, useMemo, useRef, useCallback } from 'react'
import {
  Card,
  Typography,
  Space,
  Button,
  Select,
  Tag,
  Empty,
  Spin,
  CheckboxGroup,
  Checkbox,
  Collapse,
  Divider,
  Toast,
} from '@douyinfe/semi-ui'
import {
  IconDownload,
  IconLineChartStroked,
  IconBarChartVStroked,
  IconPieChart2Stroked,
  IconRefresh,
  IconSetting,
} from '@douyinfe/semi-icons'
import ReactECharts from 'echarts-for-react'
import type { EChartsOption } from 'echarts'
import './ChartDisplay.css'

const { Text, Title } = Typography

export interface ChartData {
  title?: string
  chartType: 'line' | 'bar' | 'pie' | 'heatmap' | 'scatter' | 'radar'
  data: {
    xAxis?: string[]
    yAxis?: string[]
    series: Array<{
      name: string
      data: (number | null)[]
    }>
    yAxisName?: string
    name?: string
    data?: Array<{ name: string; value: number }>
    min?: number
    max?: number
    indicators?: Array<{ name: string; max: number }>
    xAxisName?: string
  }
  summary?: {
    totalRecords?: number
    timeRange?: string
    dimensions?: string[]
    distribution?: any
    topAsn?: number
    topAsnName?: string
    hopDistribution?: any
  }
}

interface ChartDisplayProps {
  data: ChartData | null
  loading?: boolean
  onChartTypeChange?: (type: ChartData['chartType']) => void
  onRefresh?: () => void
  height?: number
  showControls?: boolean
}

function ChartDisplay({
  data,
  loading = false,
  onChartTypeChange,
  onRefresh,
  height = 400,
  showControls = true,
}: ChartDisplayProps) {
  const chartRef = useRef<any>(null)
  const [currentType, setCurrentType] = useState<ChartData['chartType']>('bar')

  // 可选指标列表（从数据中提取）
  const availableSeries = useMemo(() => {
    if (!data?.data?.series) return []
    return data.data.series.map((s, index) => ({
      label: s.name,
      value: index,
    }))
  }, [data?.data?.series])

  // 已选中的指标
  const [selectedMetrics, setSelectedMetrics] = useState<number[]>([])

  // 初始化时默认选中所有指标
  useMemo(() => {
    if (availableSeries.length > 0 && selectedMetrics.length === 0) {
      setSelectedMetrics(availableSeries.map(s => s.value))
    }
  }, [availableSeries])

  // 过滤后的系列数据
  const filteredSeries = useMemo(() => {
    if (!data?.data?.series) return []
    return data.data.series.filter((_, index) => selectedMetrics.includes(index))
  }, [data?.data?.series, selectedMetrics])

  // 生成 ECharts 配置
  const chartOption: EChartsOption = useMemo(() => {
    if (!data || !data.data) return {}

    // 使用过滤后的系列
    const modifiedData = {
      ...data.data,
      series: filteredSeries,
    }

    return generateChartOption(data.chartType || currentType, modifiedData, data.title)
  }, [data, currentType, filteredSeries])

  // 切换图表类型
  const handleTypeChange = (type: ChartData['chartType']) => {
    setCurrentType(type)
    onChartTypeChange?.(type)
  }

  // 下载图表为 PNG
  const downloadChartPNG = useCallback(() => {
    if (!chartRef.current) {
      Toast.warning({ content: '图表未就绪', duration: 3 })
      return
    }

    try {
      const echartsInstance = chartRef.current.getEchartsInstance?.()
      if (!echartsInstance) {
        Toast.warning({ content: '图表实例未找到', duration: 3 })
        return
      }

      const url = echartsInstance.getDataURL({
        type: 'png',
        pixelRatio: 2, // 高清图片
        backgroundColor: '#fff',
      })

      const link = document.createElement('a')
      link.href = url
      link.download = `chart-${data?.title || 'network-analysis'}-${Date.now()}.png`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)

      Toast.success({ content: '图片已下载', duration: 3 })
    } catch (error) {
      console.error('Download error:', error)
      Toast.error({ content: '下载失败，请重试', duration: 3 })
    }
  }, [data?.title])

  // 下载图表为 SVG
  const downloadChartSVG = useCallback(() => {
    if (!chartRef.current) {
      Toast.warning({ content: '图表未就绪', duration: 3 })
      return
    }

    try {
      const echartsInstance = chartRef.current.getEchartsInstance?.()
      if (!echartsInstance) {
        Toast.warning({ content: '图表实例未找到', duration: 3 })
        return
      }

      const url = echartsInstance.getDataURL({
        type: 'svg',
        backgroundColor: '#fff',
      })

      const link = document.createElement('a')
      link.href = url
      link.download = `chart-${data?.title || 'network-analysis'}-${Date.now()}.svg`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)

      Toast.success({ content: 'SVG 已下载', duration: 3 })
    } catch (error) {
      console.error('Download error:', error)
      Toast.error({ content: '下载失败，请重试', duration: 3 })
    }
  }, [data?.title])

  // 全选/取消全选指标
  const toggleAllMetrics = () => {
    if (selectedMetrics.length === availableSeries.length) {
      setSelectedMetrics([])
    } else {
      setSelectedMetrics(availableSeries.map(s => s.value))
    }
  }

  if (loading) {
    return (
      <Card className="chart-display chart-loading">
        <div className="loading-container">
          <Spin size="large" />
          <Text type="tertiary" style={{ marginTop: 16 }}>正在加载数据...</Text>
        </div>
      </Card>
    )
  }

  if (!data || !data.data) {
    return (
      <Card className="chart-display chart-empty">
        <Empty description="暂无数据，请选择筛选条件后查询" style={{ padding: 40 }} />
      </Card>
    )
  }

  return (
    <Card className="chart-display">
      {/* 头部 */}
      <div className="chart-header">
        <div className="chart-title-area">
          {data.title && <Title heading={5}>{data.title}</Title>}
          {data.summary && (
            <Space style={{ marginLeft: 12 }}>
              {data.summary.totalRecords && (
                <Tag color="blue">记录数: {data.summary.totalRecords.toLocaleString()}</Tag>
              )}
              {data.summary.timeRange && (
                <Tag color="green">时间范围: {data.summary.timeRange}</Tag>
              )}
            </Space>
          )}
        </div>

        {showControls && (
          <Space>
            {/* 图表类型选择 */}
            <Select
              value={currentType}
              onChange={(value) => handleTypeChange(value as ChartData['chartType'])}
              style={{ width: 120 }}
            >
              <Select.Option value="line">
                <Space>
                  <IconLineChartStroked />
                  折线图
                </Space>
              </Select.Option>
              <Select.Option value="bar">
                <Space>
                  <IconBarChartVStroked />
                  柱状图
                </Space>
              </Select.Option>
              <Select.Option value="pie">
                <Space>
                  <IconPieChart2Stroked />
                  饼图
                </Space>
              </Select.Option>
            </Select>

            {onRefresh && (
              <Button icon={<IconRefresh />} onClick={onRefresh}>
                刷新
              </Button>
            )}

            {/* 下载按钮 */}
            <Select
              style={{ width: 100 }}
              placeholder="下载"
              onChange={(value) => {
                if (value === 'png') downloadChartPNG()
                if (value === 'svg') downloadChartSVG()
              }}
            >
              <Select.Option value="png">
                <Space>
                  <IconDownload />
                  PNG 图片
                </Space>
              </Select.Option>
              <Select.Option value="svg">
                <Space>
                  <IconDownload />
                  SVG 矢量图
                </Space>
              </Select.Option>
            </Select>
          </Space>
        )}
      </div>

      {/* 指标选择器（当有多个指标时显示） */}
      {availableSeries.length > 1 && (
        <Collapse accordion style={{ marginBottom: 12 }}>
          <Collapse.Panel
            header={
              <Space>
                <IconSetting />
                <Text>指标选择 ({selectedMetrics.length}/{availableSeries.length})</Text>
              </Space>
            }
            itemKey="metrics"
          >
            <div className="metrics-selector">
              <div className="metrics-actions">
                <Button size="small" onClick={toggleAllMetrics}>
                  {selectedMetrics.length === availableSeries.length ? '取消全选' : '全选'}
                </Button>
              </div>
              <CheckboxGroup
                value={selectedMetrics}
                onChange={(values) => setSelectedMetrics(values as number[])}
                style={{ width: '100%' }}
              >
                <Space wrap>
                  {availableSeries.map((metric) => (
                    <Checkbox key={metric.value} value={metric.value}>
                      {metric.label}
                    </Checkbox>
                  ))}
                </Space>
              </CheckboxGroup>
            </div>
          </Collapse.Panel>
        </Collapse>
      )}

      {/* 图表内容 */}
      <div className="chart-content">
        <ReactECharts
          ref={chartRef}
          option={chartOption}
          style={{ height }}
          notMerge={true}
          opts={{ renderer: 'canvas' }}
        />
      </div>

      {/* 图表底部统计信息 */}
      {data.summary && (
        <div className="chart-footer">
          <Divider margin="12px" />
          <Space wrap>
            {data.summary.distribution && (
              <>
                <Tag color="purple">AS 数: {data.summary.distribution.unique_asns}</Tag>
                <Tag color="cyan">国家数: {data.summary.distribution.unique_countries}</Tag>
                <Tag color="teal">前缀数: {data.summary.distribution.unique_prefixes}</Tag>
                <Tag color="green">IP 数: {data.summary.distribution.unique_ips}</Tag>
              </>
            )}
            {data.summary.topAsn && (
              <Tag color="blue">Top AS: {data.summary.topAsn} {data.summary.topAsnName}</Tag>
            )}
          </Space>
        </div>
      )}
    </Card>
  )
}

// 生成图表配置
function generateChartOption(
  chartType: ChartData['chartType'],
  data: any,
  title?: string
): EChartsOption {
  const baseOption: EChartsOption = {
    title: {
      text: title || '',
      left: 'center',
      textStyle: {
        fontSize: 14,
      },
    },
    tooltip: {
      trigger: chartType === 'pie' ? 'item' : 'axis',
      confine: true,
    },
    legend: {
      bottom: 10,
      type: 'scroll',
    },
    toolbox: {
      feature: {
        dataZoom: { title: { zoom: '区域缩放', back: '区域还原' } },
        restore: { title: '还原' },
      },
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '15%',
      top: '10%',
      containLabel: true,
    },
  }

  switch (chartType) {
    case 'line':
      return {
        ...baseOption,
        xAxis: {
          type: 'category',
          data: data.xAxis || [],
          axisLabel: {
            rotate: data.xAxis && data.xAxis.length > 10 ? 45 : 0,
            interval: 'auto',
          },
        },
        yAxis: {
          type: 'value',
          name: data.yAxisName || '值',
        },
        series: (data.series || []).map((s: any) => ({
          name: s.name,
          type: 'line',
          smooth: true,
          data: s.data,
          areaStyle: { opacity: 0.1 },
          symbol: 'circle',
          symbolSize: 6,
        })),
      }

    case 'bar':
      return {
        ...baseOption,
        xAxis: {
          type: 'category',
          data: data.xAxis || [],
          axisLabel: {
            rotate: data.xAxis && data.xAxis.length > 10 ? 45 : 0,
            interval: 'auto',
          },
        },
        yAxis: {
          type: 'value',
          name: data.yAxisName || '值',
        },
        series: (data.series || []).map((s: any, i: number) => ({
          name: s.name,
          type: 'bar',
          data: s.data,
          itemStyle: {
            color: getChartColor(i),
          },
          barMaxWidth: 60,
        })),
      }

    case 'pie':
      return {
        ...baseOption,
        series: [
          {
            name: data.name || '分布',
            type: 'pie',
            radius: ['40%', '70%'],
            center: ['50%', '50%'],
            avoidLabelOverlap: false,
            itemStyle: {
              borderRadius: 10,
              borderColor: '#fff',
              borderWidth: 2,
            },
            label: {
              show: true,
              formatter: '{b}: {d}%',
            },
            emphasis: {
              label: {
                show: true,
                fontSize: 14,
                fontWeight: 'bold',
              },
            },
            data: (data.data || []).map((d: any, i: number) => ({
              ...d,
              itemStyle: { color: getChartColor(i) },
            })),
          },
        ],
      }

    case 'scatter':
      return {
        ...baseOption,
        xAxis: {
          type: 'value',
          name: data.xAxisName || 'X',
        },
        yAxis: {
          type: 'value',
          name: data.yAxisName || 'Y',
        },
        series: (data.series || []).map((s: any, i: number) => ({
          name: s.name,
          type: 'scatter',
          data: s.data,
          symbolSize: 8,
          itemStyle: {
            color: getChartColor(i),
          },
        })),
      }

    case 'radar':
      return {
        ...baseOption,
        radar: {
          indicator: data.indicators || [],
          shape: 'polygon',
          splitNumber: 5,
        },
        series: [
          {
            name: data.name || '雷达图',
            type: 'radar',
            data: (data.series || []).map((s: any, i: number) => ({
              name: s.name,
              value: s.data,
              itemStyle: { color: getChartColor(i) },
              areaStyle: { opacity: 0.3 },
            })),
          },
        ],
      }

    default:
      return baseOption
  }
}

// 获取图表颜色
function getChartColor(index: number): string {
  const colors = [
    '#5B8FF9',
    '#5AD8A6',
    '#5D7092',
    '#F6BD16',
    '#E86452',
    '#6DC8EC',
    '#945FB9',
    '#FF9D4D',
    '#61DDAA',
    '#65789B',
    '#F6903D',
    '#D0605C',
    '#73C0DE',
    '#3BA272',
    '#FC8452',
  ]
  return colors[index % colors.length]
}

export default ChartDisplay

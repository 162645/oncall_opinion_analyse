/**
 * 图表展示组件
 * 支持柱状图、折线图、饼图等多种图表类型
 * 支持图表大小调整、缩放查看、X轴密度调整
 * 支持时间周期概览和下钻查看
 */
import { useState, useMemo, useRef, useEffect } from 'react'
import { Empty, Spin, Typography, Space, Tag, Button, Slider, RadioGroup, Radio } from '@douyinfe/semi-ui'
import { IconRefresh, IconMinus, IconPlus } from '@douyinfe/semi-icons'

const { Title, Text } = Typography

export interface ChartData {
  title?: string
  chartType: 'bar' | 'line' | 'pie' | 'scatter' | 'histogram' | 'treemap' | 'metric'
  data: {
    xAxis?: string[]
    series?: Array<{
      name: string
      data: (number | null)[]
    }>
    labels?: string[]
    values?: number[]
    yAxisName?: string
    timeData?: Array<{
      time: string
      value: number
    }>
  }
  summary?: Record<string, any>
  // 时间钻取回调
  onTimeDrillDown?: (startTime: string, endTime: string) => void
}

interface ChartDisplayProps {
  data: ChartData | null
  height?: number
  loading?: boolean
  resizable?: boolean
  onTimeRangeSelect?: (startTime: string, endTime: string) => void
}

// 颜色主题
const COLORS = ['#5C6BC0', '#42A5F5', '#66BB6A', '#FFA726', '#EF5350', '#AB47BC', '#26A69A', '#EC407A']

function ChartDisplay({ data, height = 300, loading = false, resizable = true, onTimeRangeSelect }: ChartDisplayProps) {
  const [chartHeight, setChartHeight] = useState(height)
  const [chartWidth, setChartWidth] = useState<number | 'auto'>('auto')

  // 调试：打印接收到的数据 - VERSION 2
  console.log('=== ChartDisplay V2 ===')
  console.log('[ChartDisplay] Received data:', data)
  if (data?.data?.series) {
    console.log('[ChartDisplay] Series count:', data.data.series.length)
    data.data.series.forEach((s: any, i: number) => {
      console.log(`[ChartDisplay] Series[${i}]: name="${s.name}", dataLength=${s.data?.length}, firstValue=${s.data?.[0]}, validCount=${s.data?.filter((v: any) => v !== null && v !== undefined).length}`)
    })
  }

  // 缩放和视图控制
  const [zoomLevel, setZoomLevel] = useState(1)  // 1=显示全部, 2=放大2倍等
  const [viewStart, setViewStart] = useState(0)  // 视图起始位置 (0-1)
  const [viewMode, setViewMode] = useState<'overview' | 'detail'>('overview')

  // 时间周期选择 - 用于下钻
  const [selectedTimeRange, setSelectedTimeRange] = useState<{ start: number; end: number } | null>(null)

  // 点击数据点显示数值
  const [clickedPoint, setClickedPoint] = useState<{ x: number; y: number; value: number; seriesName: string; time: string } | null>(null)

  const containerRef = useRef<HTMLDivElement>(null)

  // 监听容器尺寸变化
  const [containerWidth, setContainerWidth] = useState(800)

  useEffect(() => {
    const updateWidth = () => {
      if (containerRef.current) {
        setContainerWidth(containerRef.current.clientWidth)
      }
    }
    // 初始化时获取宽度
    updateWidth()
    // 监听窗口变化
    window.addEventListener('resize', updateWidth)
    return () => window.removeEventListener('resize', updateWidth)
  }, [])

  // 数据变化时也更新宽度
  useEffect(() => {
    if (containerRef.current) {
      setContainerWidth(containerRef.current.clientWidth)
    }
  }, [data])

  // 重置视图
  const resetView = () => {
    setZoomLevel(1)
    setViewStart(0)
    setViewMode('overview')
    setSelectedTimeRange(null)
    setClickedPoint(null)
  }

  // 自动计算宽度
  useEffect(() => {
    if (containerRef.current && chartWidth === 'auto') {
      const containerWidth = containerRef.current.clientWidth
      if (containerWidth > 0) {
        setChartWidth(containerWidth - 32)
      }
    }
  }, [chartWidth])

  // 重置视图当数据变化时
  useEffect(() => {
    resetView()
  }, [data])

  // 计算最大值用于Y轴
  const maxValue = useMemo(() => {
    if (!data?.data?.series && !data?.data?.values) return 100

    if (data.data.series) {
      const allValues = data.data.series.flatMap(s => s.data.filter(v => v !== null) as number[])
      return Math.max(...allValues, 1) * 1.1
    }

    if (data.data.values) {
      return Math.max(...data.data.values, 1) * 1.1
    }

    return 100
  }, [data])

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: 60 }}>
        <Spin size="large" />
      </div>
    )
  }

  if (!data) {
    return <Empty description="暂无图表数据" />
  }

  const { chartType, data: chartData, title } = data

  // 渲染指标卡片
  const renderMetricCard = () => {
    const { series = [] } = chartData
    if (series.length === 0) return <Empty description="无数据" />

    return (
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 16 }}>
        {series.map((s, idx) => (
          <div
            key={idx}
            style={{
              background: '#f8f9fa',
              padding: 16,
              borderRadius: 8,
              minWidth: 150,
            }}
          >
            <Text type="tertiary" size="small">{s.name}</Text>
            <Title heading={3} style={{ margin: '8px 0 0' }}>
              {s.data[0]?.toFixed(2) || '-'}
            </Title>
          </div>
        ))}
      </div>
    )
  }

  // 渲染柱状图
  const renderBarChart = () => {
    const { xAxis = [], series = [] } = chartData
    if (xAxis.length === 0 || series.length === 0) {
      return <Empty description="无数据" />
    }

    // 使用容器宽度，确保不超出可视区域，并保证最小宽度
    const svgWidth = Math.max(400, containerWidth - 32)
    const padding = { left: 70, right: 30, top: 40, bottom: 100 }
    const chartAreaWidth = Math.max(200, svgWidth - padding.left - padding.right)
    // 柱宽自适应容器宽度
    const barWidth = Math.min(40, (chartAreaWidth / xAxis.length) * 0.6)
    const svgHeight = chartHeight
    const chartAreaHeight = svgHeight - padding.top - padding.bottom

    return (
      <svg width="100%" height={svgHeight} style={{ display: 'block' }} viewBox={`0 0 ${svgWidth} ${svgHeight}`} preserveAspectRatio="xMidYMid meet">
        {/* 网格线 */}
          {[0, 0.25, 0.5, 0.75, 1].map((ratio) => {
            const y = padding.top + chartAreaHeight * (1 - ratio)
            return (
              <line
                key={ratio}
                x1={padding.left}
                y1={y}
                x2={svgWidth - padding.right}
                y2={y}
                stroke="#f0f0f0"
              />
            )
          })}

          {/* Y轴 */}
          <line x1={padding.left} y1={padding.top} x2={padding.left} y2={svgHeight - padding.bottom} stroke="#e8e8e8" />
          {/* X轴 */}
          <line x1={padding.left} y1={svgHeight - padding.bottom} x2={svgWidth - padding.right} y2={svgHeight - padding.bottom} stroke="#e8e8e8" />

          {/* Y轴刻度和标签 */}
          {[0, 0.25, 0.5, 0.75, 1].map((ratio, idx) => {
            const y = padding.top + chartAreaHeight * (1 - ratio)
            const value = Math.round(maxValue * ratio)
            return (
              <g key={idx}>
                <line x1={padding.left - 5} y1={y} x2={padding.left} y2={y} stroke="#999" />
                <text x={padding.left - 10} y={y + 4} textAnchor="end" fontSize={12} fill="#666">
                  {value}
                </text>
              </g>
            )
          })}

          {/* Y轴标签 */}
          <text x={20} y={svgHeight / 2} fontSize={12} fill="#666" transform={`rotate(-90, 20, ${svgHeight / 2})`}>
            {chartData.yAxisName || '值'}
          </text>

          {/* 柱状图 + 数值标签 */}
          {series.map((s, seriesIdx) => {
            const color = COLORS[seriesIdx % COLORS.length]
            const groupWidth = barWidth * series.length + 15

            return s.data.map((value, idx) => {
              if (value === null || value === undefined) return null
              const barHeight = Math.max(2, (value / maxValue) * chartAreaHeight)
              const x = padding.left + 10 + idx * groupWidth + seriesIdx * (barWidth + 2)
              const y = svgHeight - padding.bottom - barHeight

              return (
                <g key={`${seriesIdx}-${idx}`}>
                  <rect
                    x={x}
                    y={y}
                    width={barWidth}
                    height={barHeight}
                    fill={color}
                    rx={2}
                    opacity={0.85}
                  />
                  {/* 数值标签 - 显示在柱子顶部 */}
                  <text
                    x={x + barWidth / 2}
                    y={y - 5}
                    textAnchor="middle"
                    fontSize={10}
                    fill="#333"
                    fontWeight="500"
                  >
                    {value.toFixed(1)}
                  </text>
                </g>
              )
            })
          })}

          {/* X轴标签 - 倾斜显示避免重叠 */}
          {xAxis.map((label, idx) => {
            const groupWidth = barWidth * series.length + 15
            const x = padding.left + 10 + idx * groupWidth + (groupWidth - barWidth) / 2
            const displayLabel = label && label.length > 12 ? `${label.substring(0, 12)}...` : (label || '')
            return (
              <text
                key={idx}
                x={x}
                y={svgHeight - padding.bottom + 15}
                fontSize={10}
                fill="#666"
                textAnchor="end"
                transform={`rotate(-45, ${x}, ${svgHeight - padding.bottom + 15})`}
              >
                {displayLabel}
              </text>
            )
          })}

          {/* 图例 */}
          {series.map((s, idx) => (
            <g key={`legend-${idx}`}>
              <rect x={padding.left + idx * 110} y={10} width={14} height={14} fill={COLORS[idx % COLORS.length]} rx={2} />
              <text x={padding.left + idx * 110 + 20} y={21} fontSize={12} fill="#333">{s.name}</text>
            </g>
          ))}
        </svg>
    )
  }

  // 渲染折线图 - 时间序列优化，支持概览/详情切换
  const renderLineChart = () => {
    const { xAxis = [], series = [] } = chartData

    console.log('[renderLineChart] chartData:', chartData)
    console.log('[renderLineChart] xAxis length:', xAxis.length)
    console.log('[renderLineChart] series:', series)
    console.log('[renderLineChart] series[0]?.data:', series[0]?.data)
    console.log('[renderLineChart] series[0]?.data type:', Array.isArray(series[0]?.data) ? 'array' : typeof series[0]?.data)

    if (series.length === 0) {
      return <Empty description="无数据系列" />
    }

    const hasValidData = series.some(s => s.data && s.data.some(v => v !== null && v !== undefined))
    console.log('[renderLineChart] hasValidData:', hasValidData)

    if (!hasValidData) {
      return <Empty description="数据为空" />
    }

    const padding = { left: 70, right: 30, top: 50, bottom: 100 }
    // 使用容器宽度，确保不超出可视区域，并保证最小宽度
    const svgWidth = Math.max(400, containerWidth - 32)

    const totalDataLength = xAxis.length || series[0]?.data?.length || 1

    // 根据视图模式计算可见数据范围
    // viewStart 是 0-1 的比例，表示视图起始位置
    // zoomLevel 表示放大倍数，越大看到的范围越小（细节越多）
    const visibleRatio = 1 / zoomLevel  // 可见范围占总数据的比例
    const startIndex = Math.floor(viewStart * (1 - visibleRatio) * totalDataLength)
    const visibleLength = Math.max(5, Math.floor(totalDataLength * visibleRatio))

    const actualStartIndex = Math.max(0, Math.min(startIndex, totalDataLength - visibleLength))
    const endIndex = Math.min(actualStartIndex + visibleLength, totalDataLength)

    // 获取可见数据
    const visibleXAxis = xAxis.slice(actualStartIndex, endIndex)
    const visibleSeries = series.map(s => ({
      ...s,
      data: s.data.slice(actualStartIndex, endIndex)
    }))

    // 计算可见数据的 Y 轴范围 (移除错误的 useMemo)
    const allVisibleValues = visibleSeries.flatMap(s => s.data.filter(v => v !== null && v !== undefined) as number[])
    const visibleMaxValue = Math.max(...allVisibleValues, 1) * 1.1

    // SVG 宽度固定为容器宽度，数据点自动适应
    const svgHeight = chartHeight
    const chartAreaHeight = Math.max(100, svgHeight - padding.top - padding.bottom)
    const chartAreaWidth = Math.max(200, svgWidth - padding.left - padding.right)

    return (
      <div>
        {/* 视图控制面板 */}
        <div style={{
          marginBottom: 12,
          padding: '12px 16px',
          background: '#f8f9fa',
          borderRadius: 8,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: 12
        }}>
          {/* 左侧：模式切换 */}
          <Space>
            <Text type="tertiary" size="small">视图模式:</Text>
            <RadioGroup
              type="button"
              value={viewMode}
              onChange={(e) => {
                const mode = e.target.value
                setViewMode(mode)
                if (mode === 'overview') {
                  setZoomLevel(1)
                  setViewStart(0)
                } else {
                  setZoomLevel(Math.min(3, Math.ceil(totalDataLength / 50)))
                }
              }}
            >
              <Radio value="overview">概览 (看整体)</Radio>
              <Radio value="detail">详情 (看细节)</Radio>
            </RadioGroup>
          </Space>

          {/* 中间：缩放控制 */}
          <Space>
            <Text type="tertiary" size="small">缩放:</Text>
            <Button
              size="small"
              icon={<IconMinus />}
              onClick={() => setZoomLevel(prev => Math.max(1, prev - 1))}
              disabled={zoomLevel <= 1}
            />
            <Slider
              value={zoomLevel}
              onChange={(value) => setZoomLevel(value as number)}
              min={1}
              max={Math.max(100, totalDataLength)}
              step={1}
              style={{ width: 120 }}
            />
            <Button
              size="small"
              icon={<IconPlus />}
              onClick={() => setZoomLevel(prev => prev + 1)}
              disabled={totalDataLength / zoomLevel < 3}
            />
            <Text size="small">{zoomLevel}x</Text>
          </Space>

          {/* 右侧：位置滑动 */}
          {zoomLevel > 1 && (
            <Space>
              <Text type="tertiary" size="small">位置:</Text>
              <Slider
                value={viewStart * 100}
                onChange={(value) => setViewStart((value as number) / 100)}
                min={0}
                max={100}
                step={1}
                style={{ width: 150 }}
              />
              <Text size="small">
                {actualStartIndex + 1}-{endIndex} / {totalDataLength}
              </Text>
            </Space>
          )}

          {/* 重置按钮 */}
          <Button
            size="small"
            icon={<IconRefresh />}
            onClick={resetView}
          >
            重置视图
          </Button>
        </div>

        {/* 时间周期概览条 - 显示所有时间周期，点击可放大查看 */}
        {totalDataLength > 5 && (
          <div style={{
            marginBottom: 12,
            padding: '12px 16px',
            background: '#fff',
            border: '1px solid #e8e8e8',
            borderRadius: 8,
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
              <Text type="tertiary" size="small">
                📅 时间周期概览 (点击时间段可放大查看该区域)
              </Text>
              <Text type="tertiary" size="small">
                共 {totalDataLength} 个时间点 | 当前显示: {actualStartIndex + 1}-{endIndex}
              </Text>
            </div>
            <div style={{ position: 'relative', height: 50 }}>
              <svg width="100%" height="50" preserveAspectRatio="none" style={{ display: 'block' }}>
                {/* 绘制迷你时间轴 */}
                {(() => {
                  // 使用 ref 获取实际宽度
                  const miniWidth = 800
                  const miniHeight = 40
                  const miniPadding = 10

                  // 计算时间分组 - 根据数据量动态分组
                  const groupCount = Math.min(48, Math.max(12, Math.ceil(totalDataLength / 10)))
                  const groupSize = Math.ceil(totalDataLength / groupCount)

                  const timeGroups: { label: string; startIndex: number; endIndex: number; avgValue: number }[] = []

                  for (let i = 0; i < totalDataLength; i += groupSize) {
                    const end = Math.min(i + groupSize, totalDataLength)
                    const groupData = series[0]?.data.slice(i, end).filter(v => v !== null && v !== undefined) as number[]
                    const avg = groupData.length > 0 ? groupData.reduce((a, b) => a + b, 0) / groupData.length : 0
                    const startTime = xAxis[i] || ''
                    timeGroups.push({
                      label: startTime.substring(5, 16),  // 截取 MM-DD HH:mm 部分
                      startIndex: i,
                      endIndex: end,
                      avgValue: avg,
                    })
                  }

                  const maxAvg = Math.max(...timeGroups.map(g => g.avgValue), 1)
                  const barWidth = (miniWidth - miniPadding * 2) / timeGroups.length
                  const isSelected = (group: typeof timeGroups[0]) =>
                    selectedTimeRange && selectedTimeRange.start === group.startIndex

                  return timeGroups.map((group, idx) => {
                    const x = miniPadding + idx * barWidth
                    const barHeight = Math.max(2, (group.avgValue / maxAvg) * miniHeight * 0.9)
                    const y = miniHeight - barHeight

                    return (
                      <g key={idx}>
                        <rect
                          x={x}
                          y={y}
                          width={barWidth - 1}
                          height={barHeight}
                          fill={isSelected(group) ? '#1890ff' : '#91d5ff'}
                          rx={1}
                          style={{ cursor: 'pointer', transition: 'fill 0.2s' }}
                          onMouseEnter={(e) => {
                            if (!isSelected(group)) {
                              (e.target as SVGRectElement).setAttribute('fill', '#69c0ff')
                            }
                          }}
                          onMouseLeave={(e) => {
                            if (!isSelected(group)) {
                              (e.target as SVGRectElement).setAttribute('fill', '#91d5ff')
                            }
                          }}
                          onClick={() => {
                            // 点击后放大该时间段
                            setSelectedTimeRange({ start: group.startIndex, end: group.endIndex })
                            // 计算缩放级别和位置
                            const newZoom = Math.ceil(totalDataLength / (group.endIndex - group.startIndex))
                            const newViewStart = group.startIndex / totalDataLength
                            setZoomLevel(newZoom)
                            setViewStart(newViewStart)
                            setViewMode('detail')
                            if (onTimeRangeSelect && xAxis[group.startIndex] && xAxis[group.endIndex - 1]) {
                              onTimeRangeSelect(xAxis[group.startIndex], xAxis[group.endIndex - 1])
                            }
                          }}
                        />
                        {/* 显示当前可视区域标记 */}
                        {group.startIndex >= actualStartIndex && group.endIndex <= endIndex && zoomLevel > 1 && (
                          <rect
                            x={x}
                            y={0}
                            width={barWidth - 1}
                            height={2}
                            fill="#ff4d4f"
                          />
                        )}
                      </g>
                    )
                  })
                })()}
              </svg>
            </div>
            {selectedTimeRange && (
              <div style={{ marginTop: 4, display: 'flex', alignItems: 'center', gap: 8 }}>
                <Tag color="blue" size="small">
                  选中: {xAxis[selectedTimeRange.start]?.substring(0, 16)} ~ {xAxis[selectedTimeRange.end - 1]?.substring(0, 16)}
                </Tag>
                <Button
                  size="small"
                  onClick={() => {
                    setSelectedTimeRange(null)
                    setZoomLevel(1)
                    setViewStart(0)
                    setViewMode('overview')
                  }}
                >
                  查看全部
                </Button>
              </div>
            )}
          </div>
        )}

        {/* 图表区域 - 宽度自适应，增加高度容纳X轴标签 */}
        <svg width="100%" height={svgHeight + 60} style={{ display: 'block' }} viewBox={`0 0 ${svgWidth} ${svgHeight + 60}`} preserveAspectRatio="xMidYMid meet">
            {/* 背景网格 */}
            <defs>
              <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
                <path d="M 40 0 L 0 0 0 40" fill="none" stroke="#f5f5f5" strokeWidth="1" />
              </pattern>
            </defs>
            <rect x={padding.left} y={padding.top} width={chartAreaWidth} height={chartAreaHeight} fill="url(#grid)" />

            {/* 水平参考线 */}
            {[0, 0.25, 0.5, 0.75, 1].map((ratio) => {
              const y = padding.top + chartAreaHeight * (1 - ratio)
              return (
                <line
                  key={ratio}
                  x1={padding.left}
                  y1={y}
                  x2={svgWidth - padding.right}
                  y2={y}
                  stroke="#e0e0e0"
                  strokeWidth="1"
                />
              )
            })}

            {/* Y轴 */}
            <line x1={padding.left} y1={padding.top} x2={padding.left} y2={svgHeight - padding.bottom} stroke="#ccc" strokeWidth="2" />
            {/* X轴 */}
            <line x1={padding.left} y1={svgHeight - padding.bottom} x2={svgWidth - padding.right} y2={svgHeight - padding.bottom} stroke="#ccc" strokeWidth="2" />

            {/* Y轴刻度 */}
            {[0, 0.25, 0.5, 0.75, 1].map((ratio, idx) => {
              const y = padding.top + chartAreaHeight * (1 - ratio)
              const value = Math.round(visibleMaxValue * ratio)
              return (
                <g key={idx}>
                  <line x1={padding.left - 8} y1={y} x2={padding.left} y2={y} stroke="#999" strokeWidth="2" />
                  <text x={padding.left - 12} y={y + 4} textAnchor="end" fontSize={12} fill="#666" fontWeight="500">
                    {value}
                  </text>
                </g>
              )
            })}

            {/* Y轴标签 */}
            <text x={20} y={svgHeight / 2} fontSize={13} fill="#333" fontWeight="500" transform={`rotate(-90, 20, ${svgHeight / 2})`}>
              {chartData.yAxisName || 'RTT (ms)'}
            </text>

            {/* 折线 - 每个指标一条线 */}
            {visibleSeries.map((s, seriesIdx) => {
              if (!s.data || s.data.length === 0) return null

              const color = COLORS[seriesIdx % COLORS.length]
              const dataLength = s.data.length
              const step = dataLength > 1 ? chartAreaWidth / (dataLength - 1) : chartAreaWidth / 2

              const points = s.data
                .map((value, idx) => {
                  if (value === null || value === undefined || isNaN(value)) return null
                  const x = padding.left + (dataLength > 1 ? idx * step : chartAreaWidth / 2)
                  const safeValue = Math.max(0, Math.min(value, visibleMaxValue))
                  const y = padding.top + chartAreaHeight * (1 - safeValue / visibleMaxValue)
                  return { x, y, value }
                })
                .filter(Boolean) as { x: number; y: number; value: number }[]

              if (points.length === 0) return null

              // 单点情况
              if (points.length === 1) {
                return (
                  <g key={seriesIdx}>
                    <circle cx={points[0].x} cy={points[0].y} r={10} fill={color} stroke="#fff" strokeWidth={3} />
                    <text x={points[0].x} y={points[0].y - 16} textAnchor="middle" fontSize={12} fill="#333" fontWeight="500">
                      {points[0].value.toFixed(2)}
                    </text>
                  </g>
                )
              }

              // 多点情况 - 绘制折线
              const pathD = points.map((p, idx) => `${idx === 0 ? 'M' : 'L'} ${p.x} ${p.y}`).join(' ')

              return (
                <g key={seriesIdx}>
                  {/* 面积填充 */}
                  <path
                    d={`${pathD} L ${points[points.length - 1].x} ${svgHeight - padding.bottom} L ${points[0].x} ${svgHeight - padding.bottom} Z`}
                    fill={color}
                    opacity={0.1}
                  />
                  {/* 折线 */}
                  <path
                    d={pathD}
                    fill="none"
                    stroke={color}
                    strokeWidth={viewMode === 'detail' ? 2 : 2.5}
                    strokeLinejoin="round"
                    strokeLinecap="round"
                  />
                  {/* 数据点 - 详情模式或数据点较少时显示，点击显示数值 */}
                  {(viewMode === 'detail' || points.length <= 100) && points.map((p, idx) => {
                    const timeLabel = visibleXAxis[idx] || ''
                    const isClicked = clickedPoint &&
                      clickedPoint.x === p.x &&
                      clickedPoint.seriesName === s.name
                    return (
                      <g key={idx}>
                        <circle
                          cx={p.x}
                          cy={p.y}
                          r={isClicked ? 6 : (viewMode === 'detail' ? 4 : 3)}
                          fill={color}
                          stroke="#fff"
                          strokeWidth={2}
                          style={{ cursor: 'pointer' }}
                          onClick={() => {
                            setClickedPoint({
                              x: p.x,
                              y: p.y,
                              value: p.value,
                              seriesName: s.name,
                              time: timeLabel,
                            })
                          }}
                        />
                        {/* 点击后显示数值气泡 */}
                        {isClicked && (
                          <g>
                            {/* 气泡背景 */}
                            <rect
                              x={p.x - 45}
                              y={p.y - 40}
                              width={90}
                              height={30}
                              fill="#333"
                              rx={4}
                              opacity={0.9}
                            />
                            {/* 数值文本 */}
                            <text
                              x={p.x}
                              y={p.y - 25}
                              textAnchor="middle"
                              fontSize={11}
                              fill="#fff"
                              fontWeight="500"
                            >
                              {p.value.toFixed(2)} ms
                            </text>
                            {/* 时间文本 */}
                            <text
                              x={p.x}
                              y={p.y - 15}
                              textAnchor="middle"
                              fontSize={9}
                              fill="#ccc"
                            >
                              {timeLabel.substring(0, 16)}
                            </text>
                            {/* 关闭按钮 */}
                            <text
                              x={p.x + 40}
                              y={p.y - 35}
                              textAnchor="middle"
                              fontSize={10}
                              fill="#fff"
                              style={{ cursor: 'pointer' }}
                              onClick={() => setClickedPoint(null)}
                            >
                              ×
                            </text>
                          </g>
                        )}
                      </g>
                    )
                  })}
                </g>
              )
            })}

            {/* X轴标签 - 根据缩放级别和视图模式智能调整 */}
            {visibleXAxis.length > 0 && (() => {
              const dataLength = visibleXAxis.length
              const step = dataLength > 1 ? chartAreaWidth / (dataLength - 1) : chartAreaWidth / 2

              // 根据缩放级别和视图模式决定标签密度
              let maxLabels: number
              if (viewMode === 'overview') {
                maxLabels = Math.floor(chartAreaWidth / 80)  // 概览模式：较少标签
              } else {
                maxLabels = Math.floor(chartAreaWidth / 50)  // 详情模式：较多标签
              }

              const labelStep = Math.max(1, Math.ceil(dataLength / maxLabels))

              return visibleXAxis.map((label, idx) => {
                // 智能选择显示的标签
                const shouldShow = idx === 0 ||
                  idx === dataLength - 1 ||
                  idx % labelStep === 0

                if (!shouldShow) return null

                const x = padding.left + (dataLength > 1 ? idx * step : chartAreaWidth / 2)
                const displayLabel = label && label.length > 16 ? label.substring(0, 16) : (label || '')
                const xAxisY = svgHeight - padding.bottom

                return (
                  <text
                    key={idx}
                    x={x}
                    y={xAxisY + 20}
                    fontSize={viewMode === 'detail' ? 10 : 11}
                    fill="#666"
                    textAnchor="end"
                    transform={`rotate(-35, ${x}, ${xAxisY + 20})`}
                  >
                    {displayLabel}
                  </text>
                )
              })
            })()}

            {/* 图例 - 放在顶部 */}
            <g>
              {visibleSeries.map((s, idx) => {
                const legendX = padding.left + (idx % 4) * 140
                const legendY = 10 + Math.floor(idx / 4) * 22
                return (
                  <g key={`legend-${idx}`}>
                    <line x1={legendX} y1={legendY + 7} x2={legendX + 20} y2={legendY + 7} stroke={COLORS[idx % COLORS.length]} strokeWidth={3} />
                    <circle cx={legendX + 10} cy={legendY + 7} r={4} fill={COLORS[idx % COLORS.length]} />
                    <text x={legendX + 26} y={legendY + 11} fontSize={12} fill="#333">{s.name}</text>
                  </g>
                )
              })}
            </g>
          </svg>

        {/* 数据范围提示 */}
        <div style={{ marginTop: 8, textAlign: 'center' }}>
          <Text type="tertiary" size="small">
            显示: {actualStartIndex + 1} - {endIndex} / 共 {totalDataLength} 个时间点
            {zoomLevel > 1 && ` | 已放大 ${zoomLevel}x`}
          </Text>
        </div>
      </div>
    )
  }

  // 渲染饼图
  const renderPieChart = () => {
    const { labels = [], values = [] } = chartData
    if (labels.length === 0 || values.length === 0) {
      return <Empty description="无数据" />
    }

    const total = values.reduce((a, b) => a + b, 0)
    const cx = 150
    const cy = chartHeight / 2
    const radius = Math.min(100, chartHeight / 2 - 30)

    let startAngle = -Math.PI / 2
    const slices: Array<{ startAngle: number; endAngle: number; color: string; label: string; value: number }> = []

    values.forEach((value, idx) => {
      const angle = (value / total) * 2 * Math.PI
      slices.push({
        startAngle,
        endAngle: startAngle + angle,
        color: COLORS[idx % COLORS.length],
        label: labels[idx] || `项目${idx + 1}`,
        value,
      })
      startAngle += angle
    })

    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <svg width={300} height={chartHeight}>
          {slices.map((slice, idx) => {
            const x1 = cx + radius * Math.cos(slice.startAngle)
            const y1 = cy + radius * Math.sin(slice.startAngle)
            const x2 = cx + radius * Math.cos(slice.endAngle)
            const y2 = cy + radius * Math.sin(slice.endAngle)
            const largeArc = (slice.endAngle - slice.startAngle) > Math.PI ? 1 : 0

            const path = `M ${cx} ${cy} L ${x1} ${y1} A ${radius} ${radius} 0 ${largeArc} 1 ${x2} ${y2} Z`

            return (
              <path key={idx} d={path} fill={slice.color} opacity={0.85} stroke="#fff" strokeWidth={2} />
            )
          })}
        </svg>

        {/* 图例 */}
        <div style={{ marginLeft: 20 }}>
          {slices.map((slice, idx) => (
            <div key={idx} style={{ display: 'flex', alignItems: 'center', marginBottom: 8 }}>
              <div style={{ width: 12, height: 12, background: slice.color, borderRadius: 2, marginRight: 8 }} />
              <Text>{slice.label}: {slice.value} ({((slice.value / total) * 100).toFixed(1)}%)</Text>
            </div>
          ))}
        </div>
      </div>
    )
  }

  // 根据图表类型渲染
  const renderChart = () => {
    switch (chartType) {
      case 'bar':
        return renderBarChart()
      case 'line':
        return renderLineChart()
      case 'pie':
        return renderPieChart()
      case 'metric':
        return renderMetricCard()
      default:
        return <Empty description={`暂不支持 ${chartType} 类型图表`} />
    }
  }

  return (
    <div ref={containerRef} style={{ background: '#fff', borderRadius: 8, padding: 16 }}>
      {/* 标题和控制栏 - 和分位数图一样的布局 */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12, flexWrap: 'wrap', gap: 8 }}>
        <Title heading={5} style={{ margin: 0, whiteSpace: 'pre-line' }}>
          {title || '时间趋势分析'}
        </Title>
        {resizable && (
          <Space wrap>
            <Text type="tertiary" size="small">高度:</Text>
            <Slider
              value={chartHeight}
              onChange={(value) => setChartHeight(value as number)}
              min={200}
              max={600}
              step={50}
              style={{ width: 100 }}
            />
            <Text size="small">{chartHeight}px</Text>
            <div style={{ width: 16 }} />
            <Text type="tertiary" size="small">缩放:</Text>
            <Button
              size="small"
              icon={<IconMinus />}
              onClick={() => setZoomLevel(Math.max(1, zoomLevel - 1))}
              disabled={zoomLevel <= 1}
            />
            <Slider
              value={zoomLevel}
              onChange={(value) => setZoomLevel(value as number)}
              min={1}
              max={20}
              style={{ width: 80 }}
            />
            <Button
              size="small"
              icon={<IconPlus />}
              onClick={() => setZoomLevel(zoomLevel + 1)}
            />
            <Button
              size="small"
              icon={<IconRefresh />}
              onClick={resetView}
            >
              重置
            </Button>
          </Space>
        )}
      </div>
      {renderChart()}
      {data.summary && (
        <div style={{ marginTop: 16 }}>
          <Space wrap>
            {data.summary.totalRecords !== undefined && (
              <Tag color="blue">总记录: {data.summary.totalRecords}</Tag>
            )}
            {data.summary.timeRange && (
              <Tag color="green">数据时间: {data.summary.timeRange}</Tag>
            )}
          </Space>
        </div>
      )}
    </div>
  )
}

export default ChartDisplay

/**
 * 分位数范围图表组件
 * 专门用于显示多条分位数曲线，支持渐变色和交互
 * 支持柱状图和折线图两种模式
 */
import { useState, useRef, useEffect } from 'react'
import { Empty, Spin, Typography, Space, Tag, Button, Slider } from '@douyinfe/semi-ui'
import { IconRefresh, IconPlus, IconMinus } from '@douyinfe/semi-icons'

const { Title, Text } = Typography

interface SeriesItem {
  name: string
  data: (number | null)[]
  percentile?: number
  color?: string
}

interface PercentileRangeChartProps {
  data: {
    title?: string
    data?: {
      xAxis?: string[]
      series?: SeriesItem[]
      yAxisName?: string
    }
    summary?: Record<string, any>
  } | null
  height?: number
  loading?: boolean
  chartType?: 'bar' | 'line'  // 新增图表类型支持
}

// 根据分位数值生成颜色
const getPercentileColor = (p: number, minP: number, maxP: number): string => {
  const ratio = (p - minP) / (maxP - minP || 1)
  // 从蓝色 (低分位数) 到红色 (高分位数) 的渐变
  const r = Math.round(50 + ratio * 200)
  const g = Math.round(100 + (1 - Math.abs(ratio - 0.5) * 2) * 100)
  const b = Math.round(200 - ratio * 150)
  return `rgb(${r}, ${g}, ${b})`
}

function PercentileRangeChart({ data, height = 350, loading = false, chartType = 'line' }: PercentileRangeChartProps) {
  const [chartHeight, setChartHeight] = useState(height)
  const [containerWidth, setContainerWidth] = useState(800)
  const [zoomLevel, setZoomLevel] = useState(1)
  const [viewStart, setViewStart] = useState(0)
  const [clickedPoint, setClickedPoint] = useState<{ x: number; y: number; value: number; percentile: number; time: string } | null>(null)
  const [hoveredPercentile, setHoveredPercentile] = useState<number | null>(null)

  const containerRef = useRef<HTMLDivElement>(null)

  // 调试输出
  console.log('PercentileRangeChart render:', {
    loading,
    hasData: !!data,
    dataStructure: data ? Object.keys(data) : null,
    hasSeries: !!data?.data?.series,
    seriesLength: data?.data?.series?.length,
    seriesData: data?.data?.series?.map((s: any) => ({
      name: s.name,
      dataLength: s.data?.length,
      nonNullCount: s.data?.filter((v: any) => v !== null).length
    }))
  })

  useEffect(() => {
    const updateWidth = () => {
      if (containerRef.current) {
        const width = containerRef.current.clientWidth
        console.log('PercentileRangeChart updateWidth:', width)
        setContainerWidth(width > 0 ? width : 800)
      }
    }
    // 延迟更新以确保 DOM 已渲染
    const timer = setTimeout(updateWidth, 100)
    window.addEventListener('resize', updateWidth)
    return () => {
      clearTimeout(timer)
      window.removeEventListener('resize', updateWidth)
    }
  }, [])

  useEffect(() => {
    if (containerRef.current) {
      const width = containerRef.current.clientWidth
      if (width > 0) {
        setContainerWidth(width)
      }
    }
  }, [data])

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: 60, background: '#fff', border: '1px solid #1890ff', borderRadius: '0 0 8px 8px' }}>
        <Spin size="large" />
        <Text type="tertiary" style={{ display: 'block', marginTop: 16 }}>加载分位数数据中...</Text>
      </div>
    )
  }

  if (!data || !data.data?.series || data.data.series.length === 0) {
    return (
      <div style={{ padding: 40, background: '#fff', border: '1px solid #1890ff', borderRadius: '0 0 8px 8px', textAlign: 'center' }}>
        <Empty description="无分位数数据" />
        <Text type="tertiary" size="small" style={{ display: 'block', marginTop: 8 }}>
          调试: data={data ? '有' : '无'}, series={data?.data?.series ? `${data.data.series.length}条` : '无'}
        </Text>
      </div>
    )
  }

  const { xAxis = [], series = [] } = data.data

  // 性能优化：当数据量过大时进行抽样
  const MAX_POINTS_PER_SERIES = 500  // 每条曲线最大点数
  const MAX_TOTAL_POINTS = 30000     // 总最大点数（曲线数 * 每条曲线点数）

  const totalPoints = series.length * (xAxis.length || series[0]?.data?.length || 0)

  // 计算抽样间隔
  const sampleInterval = totalPoints > MAX_TOTAL_POINTS
    ? Math.ceil(totalPoints / MAX_TOTAL_POINTS)
    : (xAxis.length > MAX_POINTS_PER_SERIES ? Math.ceil(xAxis.length / MAX_POINTS_PER_SERIES) : 1)

  // 对数据进行抽样
  const sampledXAxis = sampleInterval > 1 ? xAxis.filter((_, idx) => idx % sampleInterval === 0) : xAxis
  const sampledSeries = sampleInterval > 1
    ? series.map((s: SeriesItem) => ({
        ...s,
        data: s.data.filter((_, idx) => idx % sampleInterval === 0)
      }))
    : series

  // 根据图表高度动态调整底部padding，确保X轴标签有足够空间
  const paddingBottom = Math.max(80, chartHeight * 0.25)
  const padding = { left: 70, right: 30, top: 50, bottom: paddingBottom }
  const svgWidth = Math.max(400, containerWidth - 32)  // 确保最小宽度
  const svgHeight = chartHeight
  const chartAreaWidth = Math.max(200, svgWidth - padding.left - padding.right)  // 确保最小绘图区域
  const chartAreaHeight = Math.max(100, svgHeight - padding.top - padding.bottom)

  const totalDataLength = sampledXAxis.length || sampledSeries[0]?.data?.length || 1

  // 调试输出
  console.log('PercentileRangeChart dimensions:', {
    containerWidth,
    svgWidth,
    svgHeight,
    chartAreaWidth,
    chartAreaHeight,
    originalPoints: xAxis.length,
    sampledPoints: sampledXAxis.length,
    seriesCount: series.length,
    sampleInterval,
    totalPoints
  })

  // 缩放逻辑
  const visibleRatio = 1 / zoomLevel
  const startIndex = Math.floor(viewStart * (1 - visibleRatio) * totalDataLength)
  const visibleLength = Math.max(5, Math.floor(totalDataLength * visibleRatio))
  const actualStartIndex = Math.max(0, Math.min(startIndex, totalDataLength - visibleLength))
  const endIndex = Math.min(actualStartIndex + visibleLength, totalDataLength)

  const visibleXAxis = sampledXAxis.slice(actualStartIndex, endIndex)
  const visibleSeries = sampledSeries.map((s: SeriesItem) => ({
    ...s,
    data: s.data.slice(actualStartIndex, endIndex)
  }))

  // 计算最大值
  const allValues = visibleSeries.flatMap((s: SeriesItem) => s.data.filter((v): v is number => v !== null && v !== undefined))
  const maxValue = (allValues.length > 0 ? Math.max(...allValues) : 1) * 1.1

  // 获取分位数范围
  const percentiles = sampledSeries.map((s: SeriesItem) => s.percentile).filter((v): v is number => v !== undefined)
  const minPercentile = percentiles.length > 0 ? Math.min(...percentiles) : 0
  const maxPercentile = percentiles.length > 0 ? Math.max(...percentiles) : 100

  const resetView = () => {
    setZoomLevel(1)
    setViewStart(0)
    setClickedPoint(null)
  }

  return (
    <div ref={containerRef} style={{
      background: '#fff',
      borderRadius: '0 0 8px 8px',
      padding: 16,
      paddingBottom: 24,
      border: '1px solid #1890ff',
      borderTop: 'none'
    }}>
      {/* 调试信息 */}
      <div style={{ marginBottom: 8, padding: '4px 8px', background: '#f0f0f0', borderRadius: 4, fontSize: 12, color: '#666' }}>
        容器宽度: {containerWidth}px | SVG宽度: {svgWidth}px | 绘图区域: {chartAreaWidth}x{chartAreaHeight}px | 数据点: {totalDataLength} | 曲线: {series.length}条
      </div>
      {/* 标题和控制栏 */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12, flexWrap: 'wrap', gap: 8 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <Title heading={5} style={{ color: '#1890ff', margin: 0 }}>{data.title || '分位数分布图'}</Title>
          {sampleInterval > 1 && (
            <Tag color="orange" size="small">数据已抽样 (每{sampleInterval}点取1点)</Tag>
          )}
        </div>
        <Space wrap>
          <Text type="tertiary" size="small">高度:</Text>
          <Slider value={chartHeight} onChange={(v) => setChartHeight(v as number)} min={250} max={600} step={50} style={{ width: 100 }} />
          <Text size="small">{chartHeight}px</Text>
          <div style={{ width: 16 }} />
          <Text type="tertiary" size="small">缩放:</Text>
          <Button size="small" icon={<IconMinus />} onClick={() => setZoomLevel(Math.max(1, zoomLevel - 1))} disabled={zoomLevel <= 1} />
          <Slider value={zoomLevel} onChange={(v) => setZoomLevel(v as number)} min={1} max={20} style={{ width: 80 }} />
          <Button size="small" icon={<IconPlus />} onClick={() => setZoomLevel(zoomLevel + 1)} />
          <Button size="small" icon={<IconRefresh />} onClick={resetView}>重置</Button>
        </Space>
      </div>

      {/* 图表滚动容器 - 固定最大高度，超出时显示滚动条 */}
      <div style={{
        maxHeight: 500,
        overflowY: 'auto',
        overflowX: 'hidden',
        border: '1px solid #e8e8e8',
        borderRadius: 4
      }}>

      {/* 分位数颜色图例 */}
      <div style={{ marginBottom: 12, padding: '8px 12px', background: '#f8f9fa', borderRadius: 6 }}>
        <Text type="tertiary" size="small" style={{ marginRight: 8 }}>分位数颜色:</Text>
        <Space wrap spacing={4}>
          <Tag style={{ background: getPercentileColor(minPercentile, minPercentile, maxPercentile), color: '#fff' }}>P{minPercentile} (低)</Tag>
          <Text type="tertiary" size="small">→</Text>
          <Tag style={{ background: getPercentileColor(maxPercentile, minPercentile, maxPercentile), color: '#fff' }}>P{maxPercentile} (高)</Tag>
          <Text type="tertiary" size="small" style={{ marginLeft: 16 }}>共 {series.length} 条曲线</Text>
        </Space>
        {hoveredPercentile !== null && (
          <Tag color="blue" style={{ marginLeft: 16 }}>当前: P{hoveredPercentile}</Tag>
        )}
      </div>

      {/* 图表区域 - 增加额外高度容纳X轴标签 */}
      <svg width="100%" height={svgHeight + 60} style={{ display: 'block' }} viewBox={`0 0 ${svgWidth} ${svgHeight + 60}`} preserveAspectRatio="xMidYMid meet">
        {/* 背景网格 */}
        <defs>
          <pattern id="percentileGrid" width="40" height="40" patternUnits="userSpaceOnUse">
            <path d="M 40 0 L 0 0 0 40" fill="none" stroke="#f5f5f5" strokeWidth="1" />
          </pattern>
        </defs>
        <rect x={padding.left} y={padding.top} width={chartAreaWidth} height={chartAreaHeight} fill="url(#percentileGrid)" />

        {/* Y轴 */}
        <line x1={padding.left} y1={padding.top} x2={padding.left} y2={svgHeight - padding.bottom} stroke="#ccc" strokeWidth="2" />
        <line x1={padding.left} y1={svgHeight - padding.bottom} x2={svgWidth - padding.right} y2={svgHeight - padding.bottom} stroke="#ccc" strokeWidth="2" />

        {/* Y轴刻度 */}
        {[0, 0.25, 0.5, 0.75, 1].map((ratio, idx) => {
          const y = padding.top + chartAreaHeight * (1 - ratio)
          const value = Math.round(maxValue * ratio)
          return (
            <g key={idx}>
              <line x1={padding.left - 8} y1={y} x2={padding.left} y2={y} stroke="#999" strokeWidth="2" />
              <text x={padding.left - 12} y={y + 4} textAnchor="end" fontSize={12} fill="#666">{value}</text>
            </g>
          )
        })}

        {/* Y轴标签 */}
        <text x={20} y={svgHeight / 2} fontSize={13} fill="#333" transform={`rotate(-90, 20, ${svgHeight / 2})`}>
          {data.data?.yAxisName || 'RTT (ms)'}
        </text>

        {/* 绘制每条分位数曲线/柱状图 */}
        {chartType === 'bar' ? (
          // 柱状图模式 - 汇总视图，横轴是分位数指标
          (() => {
            // 计算每个分位数的平均值
            const percentileAverages = visibleSeries.map((s: SeriesItem) => {
              const validValues = s.data.filter((v): v is number => v !== null && v !== undefined && !isNaN(v))
              const avg = validValues.length > 0 ? validValues.reduce((a, b) => a + b, 0) / validValues.length : 0
              return {
                percentile: s.percentile || 50,
                average: avg,
                color: s.color || getPercentileColor(s.percentile || 50, minPercentile, maxPercentile)
              }
            })

            const barWidth = Math.max(20, (chartAreaWidth - 40) / percentileAverages.length - 8)
            const barGap = 8

            return percentileAverages.map((item, idx) => {
              const barHeight = Math.max(2, (item.average / maxValue) * chartAreaHeight)
              const x = padding.left + 20 + idx * (barWidth + barGap)
              const y = svgHeight - padding.bottom - barHeight
              const isHovered = hoveredPercentile === item.percentile

              return (
                <g key={idx}>
                  <rect
                    x={x}
                    y={y}
                    width={barWidth}
                    height={barHeight}
                    fill={item.color}
                    opacity={isHovered ? 1 : 0.8}
                    rx={4}
                    style={{ cursor: 'pointer' }}
                    onMouseEnter={() => setHoveredPercentile(item.percentile)}
                    onMouseLeave={() => setHoveredPercentile(null)}
                    onClick={() => setClickedPoint({
                      x: x + barWidth / 2,
                      y: y,
                      value: item.average,
                      percentile: item.percentile,
                      time: `P${item.percentile} 平均值`,
                    })}
                  />
                  {/* 数值标签 - 显示在柱子上方 */}
                  <text
                    x={x + barWidth / 2}
                    y={y - 8}
                    fontSize={10}
                    fill="#333"
                    textAnchor="middle"
                    fontWeight="500"
                  >
                    {item.average.toFixed(1)}
                  </text>
                  {/* X轴标签 - 分位数名称 */}
                  <text
                    x={x + barWidth / 2}
                    y={svgHeight - padding.bottom + 20}
                    fontSize={11}
                    fill="#666"
                    textAnchor="middle"
                  >
                    P{item.percentile}
                  </text>
                </g>
              )
            })
          })()
        ) : (
          // 折线图模式
          visibleSeries.map((s: SeriesItem, seriesIdx: number) => {
            if (!s.data || s.data.length === 0) return null

            const dataLength = s.data.length
            const step = dataLength > 1 ? chartAreaWidth / (dataLength - 1) : chartAreaWidth / 2

            const points = s.data
              .map((value: number | null, idx: number) => {
                if (value === null || value === undefined || isNaN(value)) return null
                const x = padding.left + (dataLength > 1 ? idx * step : chartAreaWidth / 2)
                const y = padding.top + chartAreaHeight * (1 - value / maxValue)
                return { x, y, value }
              })
              .filter(Boolean) as { x: number; y: number; value: number }[]

            if (points.length === 0) return null

            const pathD = points.map((p, idx) => `${idx === 0 ? 'M' : 'L'} ${p.x} ${p.y}`).join(' ')
            const color = s.color || getPercentileColor(s.percentile || 50, minPercentile, maxPercentile)
            const isHovered = hoveredPercentile === s.percentile

            return (
              <g
                key={seriesIdx}
                onMouseEnter={() => s.percentile !== undefined && setHoveredPercentile(s.percentile)}
                onMouseLeave={() => setHoveredPercentile(null)}
              >
                {/* 折线 */}
                <path
                  d={pathD}
                  fill="none"
                  stroke={color}
                  strokeWidth={isHovered ? 3 : 1.5}
                  strokeLinejoin="round"
                  strokeLinecap="round"
                  opacity={isHovered ? 1 : 0.7}
                />
                {/* 数据点 - 仅在缩放后或悬停时显示 */}
                {(zoomLevel > 2 || isHovered) && points.length <= 200 && points.map((p, idx) => {
                  const isClicked = clickedPoint && clickedPoint.x === p.x && clickedPoint.percentile === s.percentile
                  return (
                    <circle
                      key={idx}
                      cx={p.x}
                      cy={p.y}
                      r={isClicked ? 5 : 3}
                      fill={color}
                      stroke="#fff"
                      strokeWidth={1}
                      style={{ cursor: 'pointer' }}
                      onClick={() => s.percentile !== undefined && setClickedPoint({
                        x: p.x,
                        y: p.y,
                        value: p.value,
                        percentile: s.percentile,
                        time: visibleXAxis[idx] || '',
                      })}
                    />
                  )
                })}
              </g>
            )
          })
        )}

        {/* X轴标签 - 仅在折线图模式下显示时间 */}
        {chartType !== 'bar' && visibleXAxis.length > 0 && (() => {
          const dataLength = visibleXAxis.length
          const step = dataLength > 1 ? chartAreaWidth / (dataLength - 1) : chartAreaWidth / 2
          const maxLabels = Math.floor(chartAreaWidth / 80)
          const labelStep = Math.max(1, Math.ceil(dataLength / maxLabels))
          const xAxisY = svgHeight - padding.bottom

          return visibleXAxis.map((label: string, idx: number) => {
            if (idx !== 0 && idx !== dataLength - 1 && idx % labelStep !== 0) return null
            const x = padding.left + (dataLength > 1 ? idx * step : chartAreaWidth / 2)
            return (
              <text
                key={idx}
                x={x}
                y={xAxisY + 20}
                fontSize={11}
                fill="#666"
                textAnchor="end"
                transform={`rotate(-35, ${x}, ${xAxisY + 20})`}
              >
                {label.substring(0, 16)}
              </text>
            )
          })
        })()}

        {/* 点击显示数值气泡 */}
        {clickedPoint && (
          <g>
            <rect x={clickedPoint.x - 50} y={clickedPoint.y - 50} width={100} height={40} fill="#333" rx={4} opacity={0.9} />
            <text x={clickedPoint.x} y={clickedPoint.y - 35} textAnchor="middle" fontSize={12} fill="#fff" fontWeight="500">
              P{clickedPoint.percentile}: {clickedPoint.value.toFixed(2)} ms
            </text>
            <text x={clickedPoint.x} y={clickedPoint.y - 20} textAnchor="middle" fontSize={10} fill="#ccc">
              {clickedPoint.time.substring(0, 16)}
            </text>
            <text x={clickedPoint.x + 45} y={clickedPoint.y - 45} textAnchor="middle" fontSize={10} fill="#fff" style={{ cursor: 'pointer' }} onClick={() => setClickedPoint(null)}>×</text>
          </g>
        )}
      </svg>

      {/* 数据范围提示 */}
      <div style={{ marginTop: 8, textAlign: 'center' }}>
        <Text type="tertiary" size="small">
          {chartType === 'bar'
            ? `共 ${series.length} 个分位数指标 | 显示各分位数的平均 RTT 值`
            : `显示: ${actualStartIndex + 1} - ${endIndex} / 共 ${totalDataLength} 个时间点${zoomLevel > 1 ? ` | 已放大 ${zoomLevel}x` : ''}`
          }
        </Text>
      </div>
      </div>
    </div>
  )
}

export default PercentileRangeChart

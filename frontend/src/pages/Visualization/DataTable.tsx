/**
 * 数据表格组件
 * 支持排序、筛选、分页
 */
import { useState, useMemo } from 'react'
import {
  Card,
  Table,
  Typography,
  Button,
  Space,
  Input,
  Tag,
  Tooltip,
  Dropdown,
} from '@douyinfe/semi-ui'
import {
  IconDownload,
  IconSearch,
  IconRefresh,
  IconExport,
} from '@douyinfe/semi-icons'
import type { ColumnProps } from '@douyinfe/semi-ui/lib/es/table'
import './DataTable.css'

const { Text } = Typography

interface DataTableProps {
  data: Record<string, any>[]
  columns?: ColumnProps[]
  loading?: boolean
  title?: string
  pageSize?: number
  onRowClick?: (record: Record<string, any>) => void
  onRefresh?: () => void
  showSearch?: boolean
  showExport?: boolean
}

function DataTable({
  data,
  columns: propColumns,
  loading = false,
  title,
  pageSize = 10,
  onRowClick,
  onRefresh,
  showSearch = true,
  showExport = true,
}: DataTableProps) {
  const [searchText, setSearchText] = useState('')

  // 自动生成列配置
  const columns: ColumnProps[] = useMemo(() => {
    if (propColumns && propColumns.length > 0) {
      return propColumns
    }

    if (!data || data.length === 0) {
      return []
    }

    // 根据数据自动推断列配置
    const firstRow = data[0]
    return Object.keys(firstRow).map((key) => ({
      title: formatColumnName(key),
      dataIndex: key,
      key,
      sorter: (a: any, b: any) => {
        const aVal = a[key]
        const bVal = b[key]
        if (typeof aVal === 'number' && typeof bVal === 'number') {
          return aVal - bVal
        }
        return String(aVal).localeCompare(String(bVal))
      },
      render: (text: any) => renderCellValue(text, key),
    }))
  }, [data, propColumns])

  // 过滤数据
  const filteredData = useMemo(() => {
    if (!searchText) return data

    return data.filter((row) =>
      Object.values(row).some((value) =>
        String(value).toLowerCase().includes(searchText.toLowerCase())
      )
    )
  }, [data, searchText])

  // 导出 CSV
  const exportCSV = () => {
    if (!filteredData || filteredData.length === 0) return

    const headers = columns.map((col) => col.title).join(',')
    const rows = filteredData.map((row) =>
      columns.map((col) => {
        const value = row[col.dataIndex as string]
        // 处理包含逗号或引号的值
        const strValue = String(value ?? '')
        if (strValue.includes(',') || strValue.includes('"')) {
          return `"${strValue.replace(/"/g, '""')}"`
        }
        return strValue
      }).join(',')
    )

    const csv = [headers, ...rows].join('\n')
    const blob = new Blob(['﻿' + csv], { type: 'text/csv;charset=utf-8;' })
    const link = document.createElement('a')
    link.href = URL.createObjectURL(blob)
    link.download = `data-${Date.now()}.csv`
    link.click()
  }

  // 导出 JSON
  const exportJSON = () => {
    if (!filteredData || filteredData.length === 0) return

    const json = JSON.stringify(filteredData, null, 2)
    const blob = new Blob([json], { type: 'application/json' })
    const link = document.createElement('a')
    link.href = URL.createObjectURL(blob)
    link.download = `data-${Date.now()}.json`
    link.click()
  }

  if (!data || data.length === 0) {
    return null
  }

  return (
    <Card className="data-table-card">
      {/* 头部 */}
      <div className="table-header">
        <Space>
          {title && <Text strong>{title}</Text>}
          <Tag>{filteredData.length} 条记录</Tag>
        </Space>

        <Space>
          {/* 搜索 */}
          {showSearch && (
            <Input
              prefix={<IconSearch />}
              placeholder="搜索..."
              value={searchText}
              onChange={setSearchText}
              style={{ width: 200 }}
            />
          )}

          {/* 刷新 */}
          {onRefresh && (
            <Button icon={<IconRefresh />} onClick={onRefresh}>
              刷新
            </Button>
          )}

          {/* 导出 */}
          {showExport && (
            <Dropdown
              trigger="click"
              position="bottomRight"
              render={
                <Dropdown.Menu>
                  <Dropdown.Item onClick={exportCSV}>
                    <IconDownload style={{ marginRight: 8 }} />
                    导出 CSV
                  </Dropdown.Item>
                  <Dropdown.Item onClick={exportJSON}>
                    <IconExport style={{ marginRight: 8 }} />
                    导出 JSON
                  </Dropdown.Item>
                </Dropdown.Menu>
              }
            >
              <Button icon={<IconDownload />}>导出</Button>
            </Dropdown>
          )}
        </Space>
      </div>

      {/* 表格 */}
      <div className="data-table-scroll" role="region" aria-label={title || '查询结果表格'}>
        <Table
          columns={columns}
          dataSource={filteredData}
          loading={loading}
          pagination={{
            pageSize,
            showSizeChanger: true,
            pageSizeOpts: [10, 20, 50, 100],
          }}
          onRow={(record) => record ? {
            onClick: () => onRowClick?.(record),
            style: { cursor: onRowClick ? 'pointer' : 'default' },
          } : {}}
          // 固定纵向视口，避免表格被外层页面/页脚裁剪；横向仍可滚动查看全部字段。
          scroll={{ x: 'max-content', y: 420 }}
          size="small"
          bordered
        />
      </div>
    </Card>
  )
}

// 格式化列名
function formatColumnName(key: string): string {
  // 特殊字段名称映射
  const nameMap: Record<string, string> = {
    'coefficient_of_variation': '变异系数 (CV)',
    'skewness': '偏度',
    'kurtosis': '峰度',
    'iqr': '四分位距 (IQR)',
    'geometric_mean': '几何平均',
    'std_rtt': '标准差',
    'var_rtt': '方差',
    'mean_rtt': '平均 RTT',
    'median_rtt': '中位数 RTT',
    'min_rtt': '最小 RTT',
    'max_rtt': '最大 RTT',
    'total_samples': '总样本数',
    'valid_samples': '有效样本数',
    'unique_asns': '唯一 AS 数',
    'unique_countries': '唯一国家数',
    'unique_prefixes': '唯一前缀数',
    'unique_ips': '唯一 IP 数',
    'sample_count': '样本数',
    'ip_asn': 'AS 号',
    'prefix24': '/24 前缀',
    'asgeo': 'AS+Geo',
    'asn': 'AS 号',
  }

  if (nameMap[key]) {
    return nameMap[key]
  }

  // 转换下划线为空格，首字母大写
  return key
    .split('_')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ')
}

// 渲染单元格值
function renderCellValue(value: any, key: string): React.ReactNode {
  if (value === null || value === undefined) {
    return <Text type="tertiary">-</Text>
  }

  // 数字格式化
  if (typeof value === 'number') {
    // RTT 相关字段保留小数
    if (key.toLowerCase().includes('rtt') || key.toLowerCase().includes('latency')) {
      return <Tag color="blue">{value.toFixed(2)} ms</Tag>
    }
    // 变异系数 - 显示为百分比
    if (key === 'coefficient_of_variation' || key === 'cv') {
      const cvValue = value * 100
      const color = cvValue > 100 ? 'red' : cvValue > 50 ? 'orange' : 'green'
      return <Tag color={color}>{cvValue.toFixed(1)}%</Tag>
    }
    // 偏度和峰度
    if (key === 'skewness') {
      const color = Math.abs(value) > 2 ? 'red' : Math.abs(value) > 1 ? 'orange' : 'green'
      return <Tooltip content={`偏度衡量数据分布的不对称性。正值表示右偏，负值表示左偏。`}>
        <Tag color={color}>{value.toFixed(3)}</Tag>
      </Tooltip>
    }
    if (key === 'kurtosis') {
      const color = value > 7 ? 'red' : value > 3 ? 'orange' : 'green'
      return <Tooltip content={`峰度衡量数据分布的尖峭程度。正态分布为3，大于3表示尖峰。`}>
        <Tag color={color}>{value.toFixed(3)}</Tag>
      </Tooltip>
    }
    // IQR
    if (key === 'iqr') {
      return <Tooltip content={`四分位距 = P75 - P25，反映中间50%数据的离散程度`}>
        <Tag color="cyan">{value.toFixed(2)} ms</Tag>
      </Tooltip>
    }
    // 几何平均
    if (key === 'geometric_mean') {
      return <Tooltip content={`几何平均值，对数正态分布的均值估计`}>
        <Tag color="blue">{value.toFixed(2)} ms</Tag>
      </Tooltip>
    }
    // 百分比
    if (key.toLowerCase().includes('rate') || key.toLowerCase().includes('percent')) {
      return <Tag color="green">{(value * 100).toFixed(2)}%</Tag>
    }
    // 大数字格式化
    if (value > 10000) {
      return value.toLocaleString()
    }
    return value.toFixed(2)
  }

  // AS 号
  if (key.toLowerCase().includes('asn') || key.toLowerCase() === 'as') {
    return <Tag color="purple">AS{value}</Tag>
  }

  // 状态
  if (key.toLowerCase() === 'status' || key.toLowerCase() === 'state') {
    const color = value === 'success' || value === 'normal' ? 'green' : value === 'warning' ? 'orange' : 'red'
    return <Tag color={color}>{value}</Tag>
  }

  // 长文本截断
  const strValue = String(value)
  if (strValue.length > 50) {
    return (
      <Tooltip content={strValue}>
        <span>{strValue.substring(0, 50)}...</span>
      </Tooltip>
    )
  }

  return strValue
}

export default DataTable

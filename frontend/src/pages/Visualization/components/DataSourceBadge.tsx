/**
 * 数据源标记组件
 * 显示数据是全量还是抽样
 */
import { Tag, Tooltip } from '@douyinfe/semi-ui'
import { IconInfoCircle } from '@douyinfe/semi-icons'

interface DataSourceBadgeProps {
  source: 'full' | 'quarter' | 'unknown'
  samplingRate?: number
  size?: 'small' | 'default' | 'large'
}

function DataSourceBadge({ source, size = 'default' }: DataSourceBadgeProps) {
  const getConfig = () => {
    switch (source) {
      case 'full':
        return {
          color: 'green' as const,
          text: '全量数据',
          tooltip: '完整数据集，未进行抽样',
        }
      case 'quarter':
        return {
          color: 'orange' as const,
          text: '1/4 抽样',
          tooltip: '抽样率为 25%，适合大规模数据分析。可通过关联 Ping 数据获取完整 RTT 信息。',
        }
      default:
        return {
          color: 'grey' as const,
          text: '未知',
          tooltip: '数据源信息不可用',
        }
    }
  }

  const config = getConfig()

  return (
    <Tooltip content={config.tooltip}>
      <Tag color={config.color} size={size}>
        {config.text}
        <IconInfoCircle style={{ marginLeft: 4, opacity: 0.7 }} />
      </Tag>
    </Tooltip>
  )
}

export default DataSourceBadge

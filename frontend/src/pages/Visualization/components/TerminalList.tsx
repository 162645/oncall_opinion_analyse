/**
 * 末端节点列表组件
 * 显示末端 AS/ASGeo 节点列表，支持点击选择
 */
import { List, Typography, Tag, Space, Empty, Spin } from '@douyinfe/semi-ui'
import { IconServer, IconLink } from '@douyinfe/semi-icons'
import type { TerminalNode } from '../../../api/traceroute'

const { Text } = Typography

interface TerminalListProps {
  terminals: TerminalNode[]
  loading?: boolean
  selectedTerminal?: string
  onTerminalSelect: (terminal: TerminalNode) => void
}

function TerminalList({
  terminals,
  loading = false,
  selectedTerminal,
  onTerminalSelect,
}: TerminalListProps) {
  if (loading) {
    return (
      <div style={{ padding: 40, textAlign: 'center' }}>
        <Spin size="large" />
        <Text type="tertiary" style={{ display: 'block', marginTop: 12 }}>
          正在加载末端节点...
        </Text>
      </div>
    )
  }

  if (!terminals || terminals.length === 0) {
    return (
      <Empty
        title="无末端节点数据"
        description="当前筛选条件下没有找到末端节点"
        style={{ padding: 40 }}
      />
    )
  }

  return (
    <div className="terminal-list">
      <List
        dataSource={terminals}
        renderItem={(item) => {
          const isSelected = selectedTerminal === item.terminal
          return (
            <List.Item
              className={`terminal-item ${isSelected ? 'selected' : ''}`}
              style={{
                padding: '12px 16px',
                cursor: 'pointer',
                backgroundColor: isSelected ? 'var(--semi-color-primary-light-default)' : 'transparent',
                borderLeft: isSelected ? '3px solid var(--semi-color-primary)' : '3px solid transparent',
                transition: 'all 0.2s',
              }}
              onClick={() => onTerminalSelect(item)}
            >
              <div style={{ width: '100%' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <Space>
                    <IconServer style={{ color: 'var(--semi-color-primary)' }} />
                    <Text strong>{item.terminal}</Text>
                  </Space>
                  <Tag color="blue">{item.trace_count} 条路径</Tag>
                </div>

                <div style={{ marginTop: 8, display: 'flex', gap: 16, flexWrap: 'wrap' }}>
                  <Space spacing={8}>
                    <IconLink style={{ color: 'var(--semi-color-tertiary)' }} />
                    <Text type="tertiary" size="small">
                      {item.prefix24_count} 个前缀
                    </Text>
                  </Space>
                  <Text type="tertiary" size="small">
                    平均跳数: {item.avg_hop_count?.toFixed(1) || '-'}
                  </Text>
                  <Text type="tertiary" size="small">
                    独立路径: {item.path_count || '-'}
                  </Text>
                </div>

                {item.sample_paths && item.sample_paths.length > 0 && (
                  <div style={{ marginTop: 8 }}>
                    <Text type="tertiary" size="small">示例路径:</Text>
                    <div style={{ marginTop: 4 }}>
                      {item.sample_paths.slice(0, 2).map((path, idx) => (
                        <Tag key={idx} size="small" style={{ marginRight: 4, marginBottom: 4 }}>
                          {path.path.length > 30 ? path.path.substring(0, 30) + '...' : path.path}
                        </Tag>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </List.Item>
          )
        }}
      />
    </div>
  )
}

export default TerminalList

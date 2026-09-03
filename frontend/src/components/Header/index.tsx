import { Typography, Space, Badge } from '@douyinfe/semi-ui'
import { IconBell } from '@douyinfe/semi-icons'
import './Header.css'

const { Text, Title } = Typography

function LayoutHeader() {
  return (
    <div className="layout-header">
      <div className="header-left">
        <Title heading={4} style={{ margin: 0, color: '#1890ff' }}>
          Oncall Opinion Analyse
        </Title>
        <Text type="tertiary" style={{ marginLeft: 12 }}>
          智能运维诊断平台
        </Text>
      </div>
      <div className="header-right">
        <Space spacing={16}>
          <Badge count={3} type="danger">
            <IconBell size="large" style={{ cursor: 'pointer', color: '#666' }} />
          </Badge>
          <Text>Admin</Text>
        </Space>
      </div>
    </div>
  )
}

export default LayoutHeader

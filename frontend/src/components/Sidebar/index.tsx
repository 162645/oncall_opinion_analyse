import { Nav } from '@douyinfe/semi-ui'
import {
  IconCommentStroked,
  IconBarChartHStroked,
  IconFile,
  IconWrench,
  IconSetting,
  IconHome,
} from '@douyinfe/semi-icons'
import { useNavigate, useLocation } from 'react-router-dom'
import type { OnSelectedData } from '@douyinfe/semi-ui/lib/es/navigation'
import './Sidebar.css'

function LayoutSider() {
  const navigate = useNavigate()
  const location = useLocation()

  // 智能对话是默认入口，数据分析紧随其后，保持原有使用顺序。
  const items = [
    { itemKey: '/chat', text: '智能对话', icon: <IconCommentStroked /> },
    { itemKey: '/visualization', text: '数据分析', icon: <IconBarChartHStroked /> },
    { itemKey: '/knowledge', text: '知识库', icon: <IconFile /> },
    { itemKey: '/skills', text: 'Skill', icon: <IconWrench /> },
    { itemKey: '/settings', text: '设置', icon: <IconSetting /> },
    { itemKey: '/home', text: '关于', icon: <IconHome /> },
  ]

  const handleSelect = (data: OnSelectedData) => {
    const key = data.itemKey as string
    navigate(key)
  }

  return (
    <div className="layout-sider">
      <Nav
        items={items}
        selectedKeys={[location.pathname]}
        onSelect={handleSelect}
        style={{ height: '100%' }}
      />
    </div>
  )
}

export default LayoutSider

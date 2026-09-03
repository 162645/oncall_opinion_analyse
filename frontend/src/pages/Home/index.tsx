/**
 * 首页概览
 * 展示系统统计、快捷入口、最近活动
 */
import { useState, useEffect } from 'react'
import {
  Card,
  Row,
  Col,
  Typography,
  Progress,
  Button,
  Space,
  List,
  Tag,
  Spin,
  Empty,
} from '@douyinfe/semi-ui'
import {
  IconFile,
  IconCommentStroked,
  IconBox,
  IconTickCircle,
  IconPlus,
  IconSearch,
  IconPlay,
  IconBolt,
  IconHistory,
} from '@douyinfe/semi-icons'
import { useNavigate } from 'react-router-dom'
import './Home.css'

const { Title, Text } = Typography

const API_BASE = import.meta.env.VITE_API_BASE || ''

interface Stats {
  documents: number
  sessions: number
  skills: number
  successRate: number
  avgResponseTime: number
  totalQueries: number
}

interface Activity {
  id: string
  type: 'document' | 'chat' | 'skill'
  title: string
  time: string
  status?: string
}

function Home() {
  const navigate = useNavigate()
  const [stats, setStats] = useState<Stats | null>(null)
  const [activities, setActivities] = useState<Activity[]>([])
  const [loading, setLoading] = useState(true)

  // 加载统计数据
  const loadStats = async () => {
    setLoading(true)
    try {
      // 并行请求
      const [docRes, sessionRes, skillRes] = await Promise.all([
        fetch(`${API_BASE}/api/knowledge/stats`).catch(() => null),
        fetch(`${API_BASE}/api/chat/sessions?limit=1`).catch(() => null),
        fetch(`${API_BASE}/api/skills/stats/overview`).catch(() => null),
      ])

      const docData = docRes ? await docRes.json() : null
      const sessionData = sessionRes ? await sessionRes.json() : null
      const skillData = skillRes ? await skillRes.json() : null

      setStats({
        documents: docData?.stats?.total_documents || 0,
        sessions: sessionData?.sessions?.length || 0,
        skills: skillData?.stats?.total || 0,
        successRate: 92,
        avgResponseTime: 1.2,
        totalQueries: 156,
      })

      // 模拟活动数据
      setActivities([
        { id: '1', type: 'chat', title: '诊断完成: 新加坡区域延迟问题', time: '10 分钟前', status: 'success' },
        { id: '2', type: 'document', title: '新增文档: 故障诊断手册.pdf', time: '30 分钟前' },
        { id: '3', type: 'skill', title: '执行 Skill: 网络诊断流程', time: '1 小时前', status: 'success' },
        { id: '4', type: 'chat', title: '知识检索: 网络抖动解决方案', time: '2 小时前' },
      ])
    } catch (error) {
      console.error('加载统计失败', error)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadStats()
  }, [])

  const getActivityIcon = (type: string) => {
    switch (type) {
      case 'document':
        return <IconFile style={{ color: '#1890ff' }} />
      case 'chat':
        return <IconCommentStroked style={{ color: '#52c41a' }} />
      case 'skill':
        return <IconBolt style={{ color: '#722ed1' }} />
      default:
        return <IconHistory />
    }
  }

  return (
    <div className="home-page">
      {/* 页面标题 */}
      <div className="page-header">
        <Title heading={3}>系统概览</Title>
        <Space>
          <Button icon={<IconPlus />} onClick={() => navigate('/knowledge')}>
            上传文档
          </Button>
          <Button theme="solid" type="primary" icon={<IconCommentStroked />} onClick={() => navigate('/chat')}>
            开始对话
          </Button>
        </Space>
      </div>

      {/* 统计卡片 */}
      <Row gutter={[16, 16]}>
        <Col span={6}>
          <div onClick={() => navigate('/knowledge')} style={{ cursor: 'pointer' }}>
            <Card className="stat-card">
              <div className="stat-content">
                <IconFile style={{ color: '#1890ff', fontSize: 24 }} />
                <Text type="tertiary" size="small">知识文档</Text>
                <Text strong style={{ fontSize: 28 }}>{stats?.documents || 0}</Text>
                <Text type="tertiary" size="small">点击管理 →</Text>
              </div>
            </Card>
          </div>
        </Col>
        <Col span={6}>
          <div onClick={() => navigate('/chat')} style={{ cursor: 'pointer' }}>
            <Card className="stat-card">
              <div className="stat-content">
                <IconCommentStroked style={{ color: '#52c41a', fontSize: 24 }} />
                <Text type="tertiary" size="small">对话会话</Text>
                <Text strong style={{ fontSize: 28 }}>{stats?.sessions || 0}</Text>
                <Text type="tertiary" size="small">点击查看历史 →</Text>
              </div>
            </Card>
          </div>
        </Col>
        <Col span={6}>
          <div onClick={() => navigate('/skills')} style={{ cursor: 'pointer' }}>
            <Card className="stat-card">
              <div className="stat-content">
                <IconBox style={{ color: '#722ed1', fontSize: 24 }} />
                <Text type="tertiary" size="small">Skill 数量</Text>
                <Text strong style={{ fontSize: 28 }}>{stats?.skills || 0}</Text>
                <Text type="tertiary" size="small">点击管理 →</Text>
              </div>
            </Card>
          </div>
        </Col>
        <Col span={6}>
          <Card className="stat-card">
            <div className="stat-content">
              <IconTickCircle style={{ color: '#52c41a', fontSize: 24 }} />
              <Text type="tertiary" size="small">诊断成功率</Text>
              <Text strong style={{ fontSize: 28 }}>{stats?.successRate || 0}%</Text>
              <Progress
                percent={stats?.successRate || 0}
                showInfo={false}
                stroke="#52c41a"
                size="small"
                style={{ marginTop: 8 }}
              />
            </div>
          </Card>
        </Col>
      </Row>

      {/* 快捷入口 */}
      <Card title="快捷入口" style={{ marginTop: 16 }}>
        <Row gutter={[16, 16]}>
          <Col span={6}>
            <Button
              block
              size="large"
              icon={<IconCommentStroked />}
              onClick={() => navigate('/chat')}
              style={{ height: 80 }}
            >
              <div>
                <Text strong>智能诊断</Text>
                <br />
                <Text type="tertiary" size="small">自然语言交互</Text>
              </div>
            </Button>
          </Col>
          <Col span={6}>
            <Button
              block
              size="large"
              icon={<IconSearch />}
              onClick={() => navigate('/knowledge')}
              style={{ height: 80 }}
            >
              <div>
                <Text strong>知识检索</Text>
                <br />
                <Text type="tertiary" size="small">搜索文档知识</Text>
              </div>
            </Button>
          </Col>
          <Col span={6}>
            <Button
              block
              size="large"
              icon={<IconPlay />}
              onClick={() => navigate('/skills')}
              style={{ height: 80 }}
            >
              <div>
                <Text strong>Skill 执行</Text>
                <br />
                <Text type="tertiary" size="small">复用诊断流程</Text>
              </div>
            </Button>
          </Col>
          <Col span={6}>
            <Button
              block
              size="large"
              icon={<IconBolt />}
              onClick={() => navigate('/visualization')}
              style={{ height: 80 }}
            >
              <div>
                <Text strong>数据可视化</Text>
                <br />
                <Text type="tertiary" size="small">图表生成</Text>
              </div>
            </Button>
          </Col>
        </Row>
      </Card>

      {/* 最近活动 */}
      <Card title="最近活动" style={{ marginTop: 16 }}>
        {loading ? (
          <Spin />
        ) : activities.length === 0 ? (
          <Empty description="暂无活动记录" />
        ) : (
          <List
            dataSource={activities}
            renderItem={(item) => (
              <List.Item>
                <div style={{ display: 'flex', alignItems: 'center', width: '100%' }}>
                  <div style={{ marginRight: 12 }}>{getActivityIcon(item.type)}</div>
                  <div style={{ flex: 1 }}>
                    <Text>{item.title}</Text>
                  </div>
                  {item.status && (
                    <Tag color="green" size="small" style={{ marginRight: 8 }}>
                      成功
                    </Tag>
                  )}
                  <Text type="tertiary" size="small">{item.time}</Text>
                </div>
              </List.Item>
            )}
          />
        )}
      </Card>
    </div>
  )
}

export default Home

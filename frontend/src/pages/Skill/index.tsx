/**
 * Skill 管理页面 - 自动从后端加载
 */
import { useState, useEffect } from 'react'
import {
  Table, Button, Modal, Form, Tag, Space, Typography, Card, Tabs, TabPane,
  Toast, Empty, Collapse, Row, Col, Select, Popconfirm,
} from '@douyinfe/semi-ui'
import {
  IconStar, IconServer, IconBolt, IconPulse, IconPlus, IconDelete, IconEdit, IconUser,
} from '@douyinfe/semi-icons'
import axios from 'axios'
import './Skill.css'

const { Title, Text, Paragraph } = Typography
const API_BASE = import.meta.env.VITE_API_BASE || ''

interface SkillItem {
  id: string
  name: string
  description: string
  category: string
  tags?: string[]
  trigger?: { keywords?: string[] }
  workflow?: any[]
  source: 'builtin' | 'system' | 'user'
}

interface Tool {
  name: string
  description: string
  category: string
  source: string
}

interface MCPTool {
  name: string
  description: string
  server: string
  category: string
}

const TOOL_OPTIONS = [
  { value: 'network_viz', label: '网络可视化分析' },
  { value: 'clickhouse_query', label: 'ClickHouse 查询' },
  { value: 'ping_analysis', label: 'Ping 分析' },
]

const ACTION_OPTIONS = [
  { value: 'ping_overall', label: 'Ping 整体统计' },
  { value: 'ping_trend', label: 'Ping 时序趋势' },
  { value: 'trace_terminal_analysis', label: '末端节点分析' },
  { value: 'trace_path_analysis', label: '路径分析' },
  { value: 'region_overview', label: '地区概览' },
]

const CATEGORY_OPTIONS = [
  { value: 'analysis', label: '分析' },
  { value: 'visualization', label: '可视化' },
  { value: 'query', label: '查询' },
  { value: 'custom', label: '自定义' },
]

function SkillPage() {
  // 默认数据（当API不可用时使用）
  const defaultSkills: SkillItem[] = [
    { id: 'skill-network-viz', name: '网络可视化分析', description: '分析 Traceroute 路径、Ping 数据、末端节点等网络测量数据', category: 'visualization', source: 'system', tags: ['网络', '可视化'], trigger: { keywords: ['traceroute', '路径分析'] } },
    { id: 'skill-ping-analysis', name: 'Ping数据分析', description: '分析 Ping 测量数据，计算 RTT 统计指标', category: 'analysis', source: 'system', tags: ['Ping', 'RTT'], trigger: { keywords: ['ping', 'rtt'] } },
    { id: 'skill-ping-trend', name: '延迟趋势分析', description: '分析 Ping 数据的时间趋势', category: 'analysis', source: 'system', tags: ['趋势', '时序'], trigger: { keywords: ['趋势', '时序'] } },
    { id: 'skill-traceroute-analysis', name: 'Traceroute路径分析', description: '分析 Traceroute 路径数据', category: 'analysis', source: 'system', tags: ['Traceroute', '路径'], trigger: { keywords: ['traceroute', '路径'] } },
    { id: 'skill-terminal-analysis', name: '末端节点分析', description: '分析末端节点分布', category: 'analysis', source: 'system', tags: ['末端', '节点'], trigger: { keywords: ['末端', '终端'] } },
    { id: 'skill-path-ping-trend', name: '路径Ping时序分析', description: '分析特定路径的Ping数据时序趋势', category: 'analysis', source: 'system', tags: ['路径', 'Ping', '时序'], trigger: { keywords: ['路径ping', '路径时序'] } },
    { id: 'skill-region-overview', name: '地区网络概览', description: '获取地区网络测量数据概览', category: 'analysis', source: 'system', tags: ['概览', '地区'], trigger: { keywords: ['概览', '地区'] } },
  ]

  const defaultTools: Tool[] = [
    { name: 'network_viz', description: '网络可视化工具', category: 'network', source: 'plugins' },
    { name: 'clickhouse_query', description: '查询网络测量数据', category: 'database', source: 'plugins' },
    { name: 'ping_analysis', description: '分析 Ping 数据', category: 'analysis', source: 'plugins' },
    { name: 'trace_analysis', description: '分析 Traceroute 数据', category: 'analysis', source: 'plugins' },
  ]

  const [allSkills, setAllSkills] = useState<SkillItem[]>(defaultSkills)
  const [userSkills, setUserSkills] = useState<SkillItem[]>([])
  const [allTools, setAllTools] = useState<Tool[]>(defaultTools)
  const [mcpTools] = useState<MCPTool[]>([])
  const [loading, setLoading] = useState(true)

  const [detailVisible, setDetailVisible] = useState(false)
  const [selectedSkill, setSelectedSkill] = useState<SkillItem | null>(null)
  const [createModalVisible, setCreateModalVisible] = useState(false)
  const [editingSkill, setEditingSkill] = useState<SkillItem | null>(null)
  const [formApi, setFormApi] = useState<any>(null)

  // 从后端加载数据
  useEffect(() => {
    const loadData = async () => {
      setLoading(true)
      try {
        // 并行加载所有数据
        const [systemRes, builtinRes, userRes, toolsRes] = await Promise.all([
          axios.get(`${API_BASE}/api/skills/system/list`).catch(() => null),
          axios.get(`${API_BASE}/api/skills/builtin/list`).catch(() => null),
          axios.get(`${API_BASE}/api/skills/user/list`).catch(() => null),
          axios.get(`${API_BASE}/api/skills/tools/list`).catch(() => null),
        ])

        // 合并系统技能和内置技能
        const apiSkills: SkillItem[] = [
          ...(systemRes?.data?.skills || []).map((s: any) => ({ ...s, source: 'system' as const })),
          ...(builtinRes?.data?.skills || []).map((s: any) => ({ ...s, source: 'builtin' as const })),
        ]

        // 只有API返回了有效数据才更新，否则保持默认
        if (apiSkills.length > 0) {
          console.log('从后端加载技能:', apiSkills.length, '个')
          setAllSkills(apiSkills)
        } else {
          console.log('使用默认技能数据')
        }

        // 用户技能
        if (userRes && userRes.data?.skills?.length > 0) {
          setUserSkills(userRes.data.skills.map((s: any) => ({ ...s, source: 'user' as const })))
        }

        // 工具列表
        if (toolsRes && toolsRes.data?.tools?.length > 0) {
          setAllTools(toolsRes.data.tools)
        }
      } catch (e) {
        console.error('加载失败，使用默认数据:', e)
      } finally {
        setLoading(false)
      }
    }
    loadData()
  }, [])

  const openDetail = (skill: SkillItem) => { setSelectedSkill(skill); setDetailVisible(true) }
  const openCreateModal = () => { setEditingSkill(null); setCreateModalVisible(true) }
  const openEditModal = (skill: SkillItem) => { setEditingSkill(skill); setCreateModalVisible(true) }

  const handleSaveSkill = async () => {
    const values = formApi?.getValues() || {}
    if (!values.name || !values.description) {
      Toast.error({ content: '请填写名称和描述', duration: 3 })
      return
    }
    const skillData: SkillItem = {
      id: editingSkill?.id || `user-skill-${Date.now()}`,
      name: values.name,
      description: values.description,
      category: values.category || 'analysis',
      tags: (values.tags || '').split(',').map((t: string) => t.trim()).filter(Boolean),
      trigger: { keywords: (values.keywords || '').split(',').map((k: string) => k.trim()).filter(Boolean) },
      workflow: [{ step_type: 'tool', name: values.name, config: { tool: values.tool || 'network_viz', action: values.action || 'ping_overall' } }],
      source: 'user',
    }
    try {
      await axios.post(`${API_BASE}/api/skills/user/create`, skillData)
      Toast.success({ content: '保存成功', duration: 3 })
      setUserSkills(prev => editingSkill ? prev.map(s => s.id === editingSkill.id ? skillData : s) : [...prev, skillData])
    } catch { Toast.error({ content: '保存失败', duration: 3 }) }
    setCreateModalVisible(false)
  }

  const handleDeleteSkill = async (skillId: string) => {
    try {
      await axios.delete(`${API_BASE}/api/skills/user/${skillId}`)
      Toast.success({ content: '删除成功', duration: 3 })
      setUserSkills(prev => prev.filter(s => s.id !== skillId))
    } catch { Toast.error({ content: '删除失败', duration: 3 }) }
  }

  const skillColumns = [
    { title: 'ID', dataIndex: 'id', width: 180, render: (t: string) => <Text style={{ fontFamily: 'monospace', fontSize: 12 }}>{t}</Text> },
    { title: '名称', dataIndex: 'name', width: 150, render: (text: string, r: SkillItem) => <a onClick={() => openDetail(r)}>{text}</a> },
    { title: '描述', dataIndex: 'description', ellipsis: true, render: (t: string) => <Text type="tertiary">{t}</Text> },
    { title: '分类', dataIndex: 'category', width: 80, render: (t: string) => <Tag color="blue">{t}</Tag> },
    { title: '来源', dataIndex: 'source', width: 80, render: (t: string) => <Tag color={t === 'system' ? 'purple' : t === 'builtin' ? 'cyan' : 'green'}>{t === 'system' ? '系统' : t === 'builtin' ? '内置' : '自定义'}</Tag> },
  ]

  const userColumns = [...skillColumns, {
    title: '操作', width: 120, render: (_: any, r: SkillItem) => (
      <Space>
        <Button size="small" icon={<IconEdit />} onClick={() => openEditModal(r)} />
        <Popconfirm title="确认删除？" onConfirm={() => handleDeleteSkill(r.id)}><Button size="small" icon={<IconDelete />} type="danger" /></Popconfirm>
      </Space>
    ),
  }]

  const toolColumns = [
    { title: '工具名称', dataIndex: 'name', width: 200, render: (t: string) => <Text strong style={{ fontFamily: 'monospace' }}>{t}</Text> },
    { title: '描述', dataIndex: 'description', ellipsis: true },
    { title: '分类', dataIndex: 'category', width: 100, render: (t: string) => <Tag color="cyan">{t}</Tag> },
    { title: '来源', dataIndex: 'source', width: 80, render: (t: string) => <Tag color={t === 'plugins' ? 'blue' : 'purple'}>{t}</Tag> },
  ]

  const mcpColumns = [
    { title: '工具名称', dataIndex: 'name', width: 200, render: (t: string) => <Space><Text strong>{t}</Text><Tag size="small" color="purple">MCP</Tag></Space> },
    { title: '描述', dataIndex: 'description', ellipsis: true },
    { title: '服务器', dataIndex: 'server', width: 100, render: (t: string) => <Tag>{t}</Tag> },
  ]

  return (
    <div className="skill-page">
      <Title heading={3} style={{ marginBottom: 8 }}>技能与工具管理</Title>
      <Text type="tertiary" style={{ marginBottom: 24, display: 'block' }}>查看系统可用的技能和工具，创建自定义技能</Text>

      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col span={6}><Card><Text type="tertiary">系统技能</Text><Title heading={2}>{allSkills.length}</Title></Card></Col>
        <Col span={6}><Card><Text type="tertiary">自定义技能</Text><Title heading={2}>{userSkills.length}</Title></Card></Col>
        <Col span={6}><Card><Text type="tertiary">工具数量</Text><Title heading={2}>{allTools.length}</Title></Card></Col>
        <Col span={6}><Card><Text type="tertiary">MCP工具</Text><Title heading={2}>{mcpTools.length}</Title></Card></Col>
      </Row>

      <Tabs defaultActiveKey="skills">
        <TabPane tab={<><IconStar /> 系统技能 ({allSkills.length})</>} itemKey="skills">
          <Card>
            <Text type="tertiary" style={{ marginBottom: 16, display: 'block' }}>系统预定义的网络分析技能，可在智能对话中自动触发</Text>
            <Table dataSource={allSkills} columns={skillColumns} pagination={{ pageSize: 15 }} rowKey="id" loading={loading} />
          </Card>
        </TabPane>

        <TabPane tab={<><IconUser /> 我的技能 ({userSkills.length})</>} itemKey="user">
          <Card>
            <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between' }}>
              <Text type="tertiary">创建自定义技能，定义触发关键词和执行逻辑</Text>
              <Button icon={<IconPlus />} type="primary" onClick={openCreateModal}>创建技能</Button>
            </div>
            {userSkills.length === 0 ? <Empty description="暂无自定义技能" style={{ padding: 40 }}><Button type="primary" icon={<IconPlus />} onClick={openCreateModal}>创建第一个技能</Button></Empty> : <Table dataSource={userSkills} columns={userColumns} pagination={false} rowKey="id" />}
          </Card>
        </TabPane>

        <TabPane tab={<><IconPulse /> 工具列表 ({allTools.length})</>} itemKey="tools">
          <Card>
            <Text type="tertiary" style={{ marginBottom: 16, display: 'block' }}>工具是技能执行的基础能力单元</Text>
            <Table dataSource={allTools} columns={toolColumns} pagination={{ pageSize: 15 }} rowKey="name" loading={loading} />
          </Card>
        </TabPane>

        <TabPane tab={<><IconServer /> MCP工具 ({mcpTools.length})</>} itemKey="mcp">
          <Card>
            <Text type="tertiary" style={{ marginBottom: 16, display: 'block' }}>MCP工具可直接被AI模型调用</Text>
            <Table dataSource={mcpTools} columns={mcpColumns} pagination={false} rowKey="name" />
          </Card>
        </TabPane>

        <TabPane tab={<><IconBolt /> 使用说明</>} itemKey="help">
          <Card>
            <Title heading={5}>如何使用技能</Title>
            <Paragraph>在智能对话页面，直接输入包含关键词的问题即可触发对应的技能。</Paragraph>
            <Title heading={5} style={{ marginTop: 16 }}>示例查询</Title>
            <Collapse>
              <Collapse.Panel header="网络分析" itemKey="network">
                <ul style={{ margin: 0, paddingLeft: 20 }}>
                  <li><Text>分析 UKRAINE 地区的 traceroute 路径</Text></li>
                  <li><Text>查看 UKRAINE 的 Ping 统计</Text></li>
                  <li><Text>UKRAINE 末端节点分析</Text></li>
                </ul>
              </Collapse.Panel>
              <Collapse.Panel header="延迟趋势" itemKey="trend">
                <ul style={{ margin: 0, paddingLeft: 20 }}>
                  <li><Text>查看 UKRAINE 的延迟趋势</Text></li>
                  <li><Text>分析 UKRAINE 的 RTT 时间序列</Text></li>
                </ul>
              </Collapse.Panel>
            </Collapse>
            <Title heading={5} style={{ marginTop: 16 }}>支持的地区</Title>
            <Space wrap>{['UKRAINE', 'RUSSIA', 'CHINA', 'US', 'JAPAN', 'GERMANY', 'FRANCE', 'UK', 'BRAZIL', 'INDIA'].map(r => <Tag key={r} color="blue">{r}</Tag>)}</Space>
          </Card>
        </TabPane>
      </Tabs>

      <Modal title={selectedSkill?.name} visible={detailVisible} onCancel={() => setDetailVisible(false)} footer={null} width={600}>
        {selectedSkill && (
          <div>
            <Paragraph><Text strong>ID：</Text><Text style={{ fontFamily: 'monospace' }}>{selectedSkill.id}</Text></Paragraph>
            <Paragraph style={{ marginTop: 8 }}><Text strong>描述：</Text>{selectedSkill.description}</Paragraph>
            <Paragraph style={{ marginTop: 12 }}><Text strong>分类：</Text><Tag color="blue" style={{ marginLeft: 8 }}>{selectedSkill.category}</Tag></Paragraph>
            {selectedSkill.tags && selectedSkill.tags.length > 0 && <Paragraph style={{ marginTop: 12 }}><Text strong>标签：</Text><Space style={{ marginLeft: 8 }}>{selectedSkill.tags.map((t, i) => <Tag key={i}>{t}</Tag>)}</Space></Paragraph>}
            {selectedSkill.trigger?.keywords && selectedSkill.trigger.keywords.length > 0 && (
              <div style={{ marginTop: 12 }}><Text strong>触发关键词：</Text><div style={{ marginTop: 8, display: 'flex', flexWrap: 'wrap', gap: 4 }}>{selectedSkill.trigger.keywords.map((k, i) => <Tag key={i} color="purple">{k}</Tag>)}</div></div>
            )}
            {selectedSkill.workflow && selectedSkill.workflow.length > 0 && (
              <div style={{ marginTop: 12 }}>
                <Text strong>执行配置：</Text>
                <Card style={{ marginTop: 8, padding: 12 }}>
                  {selectedSkill.workflow.map((step, i) => (
                    <div key={i}><Text>工具: </Text><Tag color="blue">{step.config?.tool || 'unknown'}</Tag>{step.config?.action && <><Text style={{ marginLeft: 8 }}>操作: </Text><Tag color="cyan">{step.config.action}</Tag></>}</div>
                  ))}
                </Card>
              </div>
            )}
          </div>
        )}
      </Modal>

      <Modal title={editingSkill ? '编辑技能' : '创建技能'} visible={createModalVisible} onCancel={() => setCreateModalVisible(false)} onOk={() => formApi?.submit()} okText="保存" width={700}>
        <Form getFormApi={(api) => setFormApi(api)} onSubmit={handleSaveSkill} initValues={{ name: editingSkill?.name || '', description: editingSkill?.description || '', category: editingSkill?.category || 'analysis', keywords: editingSkill?.trigger?.keywords?.join(', ') || '', tags: editingSkill?.tags?.join(', ') || '', tool: editingSkill?.workflow?.[0]?.config?.tool || 'network_viz', action: editingSkill?.workflow?.[0]?.config?.action || 'ping_overall' }}>
          <Row gutter={16}>
            <Col span={12}><Form.Input field="name" label="名称" placeholder="输入技能名称" rules={[{ required: true, message: '请输入名称' }]} /></Col>
            <Col span={12}><Form.Select field="category" label="分类">{CATEGORY_OPTIONS.map(o => <Select.Option key={o.value} value={o.value}>{o.label}</Select.Option>)}</Form.Select></Col>
          </Row>
          <Form.TextArea field="description" label="描述" placeholder="描述这个技能的功能" rules={[{ required: true, message: '请输入描述' }]} style={{ marginTop: 12 }} />
          <Form.Input field="keywords" label="触发关键词" placeholder="多个关键词用逗号分隔" style={{ marginTop: 12 }} helpText="用户输入包含这些关键词时会触发此技能" />
          <Form.Input field="tags" label="标签" placeholder="多个标签用逗号分隔" style={{ marginTop: 12 }} />
          <Card style={{ marginTop: 16, marginBottom: 12 }} title="执行配置">
            <Row gutter={16}>
              <Col span={12}><Form.Select field="tool" label="调用工具" style={{ width: '100%' }}>{TOOL_OPTIONS.map(o => <Select.Option key={o.value} value={o.value}>{o.label}</Select.Option>)}</Form.Select></Col>
              <Col span={12}><Form.Select field="action" label="操作类型" style={{ width: '100%' }}>{ACTION_OPTIONS.map(o => <Select.Option key={o.value} value={o.value}>{o.label}</Select.Option>)}</Form.Select></Col>
            </Row>
            <Text type="tertiary" size="small" style={{ marginTop: 8, display: 'block' }}>当用户触发此技能时，将调用指定工具执行对应操作</Text>
          </Card>
        </Form>
      </Modal>
    </div>
  )
}

export default SkillPage

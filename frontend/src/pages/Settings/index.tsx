/**
 * 增强版系统设置页面
 * 支持API配置、模型连接测试、超时设置等
 */
import { useState, useEffect } from 'react'
import {
  Card,
  Typography,
  Select,
  Button,
  Toast,
  Space,
  Tag,
  Row,
  Col,
  InputNumber,
  Switch,
  Banner,
  Spin,
  Collapse,
  Input,
} from '@douyinfe/semi-ui'
import {
  IconSetting,
  IconServer,
  IconRefresh,
  IconSave,
  IconTickCircle,
  IconCrossCircleStroked,
  IconAlertTriangle,
  IconLink,
  IconKey,
  IconEyeOpened,
  IconEyeClosed,
} from '@douyinfe/semi-icons'
import axios from 'axios'
import './Settings.css'

const { Title, Text } = Typography

// 默认配置
const DEFAULT_CONFIG = {
  // API 配置
  apiBaseUrl: '',
  requestTimeout: 60000, // 60秒

  // ClickHouse 配置
  clickhouseHost: 'oncall-clickhouse',
  clickhousePort: 9000,
  clickhouseDatabase: 'net_measure',

  // LLM API Keys
  buptApiKey: '',
  openaiApiKey: '',
  anthropicApiKey: '',

  // 模型配置
  defaultProvider: 'deepseek',
  defaultModel: 'deepseek-chat',
  maxThinkingTime: 600,

  // 功能开关
  enableLongThinking: true,
  enableTrace: true,
  enableChart: true,
  enableSkillRecommend: true,
  saveHistory: true,
}

interface ConnectionStatus {
  api: 'connected' | 'disconnected' | 'testing' | 'unknown'
  clickhouse: 'connected' | 'disconnected' | 'testing' | 'unknown'
  llm: 'connected' | 'disconnected' | 'testing' | 'unknown'
}

interface Provider {
  name: string
  display_name: string
  models: Array<{
    id: string
    name: string
    max_tokens: number
    tier: string
  }>
}

function Settings() {
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>({
    api: 'unknown',
    clickhouse: 'unknown',
    llm: 'unknown',
  })
  const [providers, setProviders] = useState<Provider[]>([])
  const [config, setConfig] = useState(DEFAULT_CONFIG)
  const [hasChanges, setHasChanges] = useState(false)

  // API Key 可见性状态
  const [showBuptKey, setShowBuptKey] = useState(false)

  // LLM 连接测试详情
  const [llmTestResult, setLlmTestResult] = useState<{
    deepseek: { status: string; message: string }
    bupt: { status: string; message: string }
    openai: { status: string; message: string }
    claude: { status: string; message: string }
  } | null>(null)

  // 加载配置
  useEffect(() => {
    loadConfig()
    loadProviders()
    testAllConnections()
  }, [])

  // 从 localStorage 加载配置
  const loadConfig = () => {
    try {
      const saved = localStorage.getItem('app_config')
      if (saved) {
        const parsed = JSON.parse(saved)
        // 旧版本可能保存了 localhost，生产环境应通过当前域名同源代理访问
        if (parsed.apiBaseUrl && /localhost|127\.0\.0\.1/.test(parsed.apiBaseUrl)) {
          parsed.apiBaseUrl = ''
        }
        setConfig({ ...DEFAULT_CONFIG, ...parsed })
      }
    } catch (error) {
      console.error('Failed to load config:', error)
    }
  }

  // 保存配置到 localStorage
  const saveConfig = async () => {
    try {
      localStorage.setItem('app_config', JSON.stringify(config))

      // 保存 API Keys 到后端
      await saveApiKeys()

      Toast.success({ content: '设置已保存', duration: 3 })
      setHasChanges(false)

      // 更新 axios 默认配置
      axios.defaults.baseURL = config.apiBaseUrl
      axios.defaults.timeout = config.requestTimeout
    } catch (error) {
      Toast.error({ content: '保存失败', duration: 3 })
    }
  }

  // 加载模型提供商
  const loadProviders = async () => {
    try {
      const response = await axios.get(`${config.apiBaseUrl}/api/llm/providers`)
      if (response.data.success && response.data.providers) {
        setProviders(response.data.providers)
      }
    } catch (error) {
      console.error('Failed to load providers:', error)
    }
  }

  // 测试所有连接
  const testAllConnections = async () => {
    await Promise.all([
      testApiConnection(),
      testClickHouseConnection(),
      testLLMConnection(),
    ])
  }

  // 测试 API 连接
  const testApiConnection = async () => {
    setConnectionStatus(prev => ({ ...prev, api: 'testing' }))
    try {
      const response = await axios.get(`${config.apiBaseUrl}/health`, {
        timeout: 5000,
      })
      if (response.data.status === 'healthy') {
        setConnectionStatus(prev => ({ ...prev, api: 'connected' }))
      } else {
        setConnectionStatus(prev => ({ ...prev, api: 'disconnected' }))
      }
    } catch (error) {
      setConnectionStatus(prev => ({ ...prev, api: 'disconnected' }))
    }
  }

  // 测试 ClickHouse 连接
  const testClickHouseConnection = async () => {
    setConnectionStatus(prev => ({ ...prev, clickhouse: 'testing' }))
    try {
      const response = await axios.get(`${config.apiBaseUrl}/api/clickhouse/regions`, {
        timeout: 10000,
      })
      if (response.data.success || response.data.regions) {
        setConnectionStatus(prev => ({ ...prev, clickhouse: 'connected' }))
      } else {
        setConnectionStatus(prev => ({ ...prev, clickhouse: 'disconnected' }))
      }
    } catch (error) {
      setConnectionStatus(prev => ({ ...prev, clickhouse: 'disconnected' }))
    }
  }

  // 测试 LLM 连接
  const testLLMConnection = async () => {
    setConnectionStatus(prev => ({ ...prev, llm: 'testing' }))
    try {
      const response = await axios.get(`${config.apiBaseUrl}/api/llm/test-connection`, {
        timeout: 30000,
      })
      if (response.data.success && response.data.results) {
        setLlmTestResult(response.data.results)

        // 任一已配置的模型提供商连接成功，即认为 LLM 可用
        if (Object.values(response.data.results).some((item: any) => ['connected', 'configured'].includes(item?.status))) {
          setConnectionStatus(prev => ({ ...prev, llm: 'connected' }))
        } else {
          setConnectionStatus(prev => ({ ...prev, llm: 'disconnected' }))
        }
      } else {
        setConnectionStatus(prev => ({ ...prev, llm: 'disconnected' }))
      }
    } catch (error) {
      setConnectionStatus(prev => ({ ...prev, llm: 'disconnected' }))
    }
  }

  // 保存 API Key 到后端
  const saveApiKeys = async () => {
    try {
      await axios.post(`${config.apiBaseUrl}/api/llm/config`, {
        deepseek_api_key: config.buptApiKey,
        openai_api_key: config.openaiApiKey,
        anthropic_api_key: config.anthropicApiKey,
      })
      Toast.success({ content: 'API Keys 已保存', duration: 3 })
    } catch (error) {
      console.error('Failed to save API keys:', error)
      // 即使保存到后端失败，前端也会保存在 localStorage
    }
  }

  // 更新配置
  const updateConfig = (key: string, value: any) => {
    setConfig(prev => ({ ...prev, [key]: value }))
    setHasChanges(true)
  }

  // 获取连接状态图标
  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'connected':
        return <IconTickCircle style={{ color: 'var(--semi-color-success)' }} />
      case 'disconnected':
        return <IconCrossCircleStroked style={{ color: 'var(--semi-color-danger)' }} />
      case 'testing':
        return <Spin size="small" />
      default:
        return <IconAlertTriangle style={{ color: 'var(--semi-color-warning)' }} />
    }
  }

  // 获取连接状态文本
  const getStatusText = (status: string) => {
    switch (status) {
      case 'connected':
        return <Tag color="green">已连接</Tag>
      case 'disconnected':
        return <Tag color="red">未连接</Tag>
      case 'testing':
        return <Tag color="blue">测试中...</Tag>
      default:
        return <Tag color="grey">未知</Tag>
    }
  }

  return (
    <div className="settings-page">
      <Title heading={3} style={{ marginBottom: 24 }}>
        <IconSetting style={{ marginRight: 8 }} />
        系统设置
      </Title>

      {/* 连接状态概览 */}
      <Card style={{ marginBottom: 16 }}>
        <div className="connection-overview">
          <Space spacing="loose">
            <div className="connection-item">
              <Space>
                {getStatusIcon(connectionStatus.api)}
                <Text>后端 API</Text>
                {getStatusText(connectionStatus.api)}
                <Button size="small" onClick={testApiConnection}>
                  测试
                </Button>
              </Space>
            </div>
            <div className="connection-item">
              <Space>
                {getStatusIcon(connectionStatus.clickhouse)}
                <Text>ClickHouse</Text>
                {getStatusText(connectionStatus.clickhouse)}
                <Button size="small" onClick={testClickHouseConnection}>
                  测试
                </Button>
              </Space>
            </div>
            <div className="connection-item">
              <Space>
                {getStatusIcon(connectionStatus.llm)}
                <Text>LLM 模型</Text>
                {getStatusText(connectionStatus.llm)}
                <Button size="small" onClick={testLLMConnection}>
                  测试
                </Button>
              </Space>
            </div>
          </Space>
        </div>
      </Card>

      {/* 连接问题提示 */}
      {connectionStatus.llm === 'disconnected' && (
        <Banner
          type="warning"
          title="LLM 模型连接失败"
          description={
            <div>
              <p>可能的原因：</p>
              <ul>
                <li>请确认服务器可以访问 api.deepseek.com</li>
                <li>请确认服务器环境变量已配置 DeepSeek API Key</li>
                <li>网络受限时请检查服务器出口防火墙</li>
              </ul>
            </div>
          }
          style={{ marginBottom: 16 }}
        />
      )}

      <Row gutter={[16, 16]}>
        {/* 左侧：配置设置 */}
        <Col span={16}>
          {/* API 配置 */}
          <Card title={<><IconLink /> API 配置</>} style={{ marginBottom: 16 }}>
            <div style={{ marginBottom: 20 }}>
              <Text strong style={{ display: 'block', marginBottom: 8 }}>后端 API 地址</Text>
              <input
                type="text"
                className="semi-input"
                value={config.apiBaseUrl}
                onChange={(e) => updateConfig('apiBaseUrl', e.target.value)}
                placeholder=""
                style={{ width: '100%', padding: '8px 12px', borderRadius: 4, border: '1px solid var(--semi-color-border)' }}
              />
              <Text type="tertiary" size="small">留空使用当前页面的同源代理；生产环境无需填写 localhost</Text>
            </div>
            <div style={{ marginBottom: 20 }}>
              <Text strong style={{ display: 'block', marginBottom: 8 }}>请求超时时间 (毫秒)</Text>
              <InputNumber
                value={config.requestTimeout}
                onChange={(value) => updateConfig('requestTimeout', value as number)}
                min={5000}
                max={300000}
                step={1000}
                style={{ width: '100%' }}
              />
              <Text type="tertiary" size="small">API 请求的最大等待时间，超时后会自动取消</Text>
            </div>
          </Card>

          {/* API Keys 配置 */}
          <Card title={<><IconKey /> API Keys 配置</>} style={{ marginBottom: 16 }}>
            <Banner
              type="info"
              title="API Key 安全提示"
              description="API Keys 仅保存在本地浏览器和后端服务器，不会上传到任何第三方服务。"
              style={{ marginBottom: 16 }}
            />

            {/* DeepSeek API Key */}
            <div style={{ marginBottom: 20 }}>
              <Text strong style={{ display: 'block', marginBottom: 8 }}>
                DeepSeek API Key
                <Tag size="small" color="green" style={{ marginLeft: 8 }}>当前使用</Tag>
              </Text>
              <Space style={{ width: '100%' }}>
                <Input
                  type={showBuptKey ? 'text' : 'password'}
                  value={config.buptApiKey}
                  onChange={(value) => updateConfig('buptApiKey', value)}
                  placeholder="留空使用服务器已配置的 Key"
                  style={{ flex: 1 }}
                />
                <Button
                  icon={showBuptKey ? <IconEyeClosed /> : <IconEyeOpened />}
                  onClick={() => setShowBuptKey(!showBuptKey)}
                />
              </Space>
              <Text type="tertiary" size="small">
                系统默认使用 DeepSeek。输入新 Key 后点击“保存设置”即可更新当前服务。
                <a href="https://platform.deepseek.com/api_keys" target="_blank" rel="noopener noreferrer" style={{ marginLeft: 4 }}>
                  获取 DeepSeek Key →
                </a>
              </Text>
            </div>

            {/* LLM 连接测试结果 */}
            {llmTestResult && (
              <Card style={{ backgroundColor: 'var(--semi-color-bg-1)', marginTop: 16 }}>
                <Text strong style={{ display: 'block', marginBottom: 8 }}>连接测试结果</Text>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <Text style={{ width: 100 }}>DeepSeek:</Text>
                    {llmTestResult.deepseek?.status === 'connected' ? (
                      <Tag color="green">{llmTestResult.deepseek.message}</Tag>
                    ) : (
                      <Tag color="red">{llmTestResult.deepseek?.message || '未连接'}</Tag>
                    )}
                  </div>
                </div>
              </Card>
            )}
          </Card>

          {/* ClickHouse 配置 */}
          <Card title={<><IconServer /> ClickHouse 配置</>} style={{ marginBottom: 16 }}>
            <Banner type="info" title="服务器端数据源" description="ClickHouse 由服务器统一管理，浏览器无需填写或修改连接参数。当前数据源为乌克兰网络测量数据。" style={{ marginBottom: 16 }} />
            <Row gutter={16}>
              <Col span={12}>
                <div style={{ marginBottom: 16 }}>
                  <Text strong style={{ display: 'block', marginBottom: 8 }}>数据库地址</Text>
                  <input
                    type="text"
                    className="semi-input"
                    value={config.clickhouseHost}
                    disabled
                    placeholder="oncall-clickhouse"
                    style={{ width: '100%', padding: '8px 12px', borderRadius: 4, border: '1px solid var(--semi-color-border)' }}
                  />
                </div>
              </Col>
              <Col span={12}>
                <div style={{ marginBottom: 16 }}>
                  <Text strong style={{ display: 'block', marginBottom: 8 }}>端口</Text>
                  <InputNumber
                    value={config.clickhousePort}
                    disabled
                    min={1}
                    max={65535}
                    style={{ width: '100%' }}
                  />
                </div>
              </Col>
            </Row>
            <div style={{ marginBottom: 16 }}>
              <Text strong style={{ display: 'block', marginBottom: 8 }}>数据库名称</Text>
              <input
                type="text"
                className="semi-input"
                value={config.clickhouseDatabase}
                disabled
                placeholder="net_measure"
                style={{ width: '100%', padding: '8px 12px', borderRadius: 4, border: '1px solid var(--semi-color-border)' }}
              />
            </div>
          </Card>

          {/* 模型配置 */}
          <Card title="🤖 模型配置" style={{ marginBottom: 16 }}>
            <div style={{ marginBottom: 20 }}>
              <Text strong style={{ display: 'block', marginBottom: 8 }}>默认提供商</Text>
              <Select
                value={config.defaultProvider}
                onChange={(value) => updateConfig('defaultProvider', value as string)}
                style={{ width: '100%' }}
              >
                {providers.map((p) => (
                  <Select.Option key={p.name} value={p.name}>
                    {p.display_name}
                  </Select.Option>
                ))}
              </Select>
            </div>

            <div style={{ marginBottom: 20 }}>
              <Text strong style={{ display: 'block', marginBottom: 8 }}>默认模型</Text>
              <Select
                value={config.defaultModel}
                onChange={(value) => updateConfig('defaultModel', value as string)}
                style={{ width: '100%' }}
              >
                <Select.Option value="deepseek-chat">DeepSeek Chat - 推荐</Select.Option>
                <Select.Option value="deepseek-reasoner">DeepSeek Reasoner</Select.Option>
              </Select>
            </div>

            <div style={{ marginBottom: 16 }}>
              <Text strong style={{ display: 'block', marginBottom: 8 }}>最大思考时间 (秒)</Text>
              <InputNumber
                value={config.maxThinkingTime}
                onChange={(value) => updateConfig('maxThinkingTime', value as number)}
                min={60}
                max={3600}
                step={60}
                style={{ width: '100%' }}
              />
              <Text type="tertiary" size="small">Agent 深度思考的最大时间限制</Text>
            </div>
          </Card>

          {/* 功能开关 */}
          <Card title="⚙️ 功能设置">
            <div style={{ marginBottom: 16 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <Text strong>启用深度思考</Text>
                  <br />
                  <Text type="tertiary" size="small">启用 Agent 深度思考模式，适合复杂问题</Text>
                </div>
                <Switch checked={config.enableLongThinking} onChange={(checked) => updateConfig('enableLongThinking', checked)} />
              </div>
            </div>

            <div style={{ marginBottom: 16 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <Text strong>显示执行追踪</Text>
                  <br />
                  <Text type="tertiary" size="small">在对话中展示 Agent 执行步骤和推理过程</Text>
                </div>
                <Switch checked={config.enableTrace} onChange={(checked) => updateConfig('enableTrace', checked)} />
              </div>
            </div>

            <div style={{ marginBottom: 16 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <Text strong>自动生成图表</Text>
                  <br />
                  <Text type="tertiary" size="small">检测到数据查询时自动生成可视化图表</Text>
                </div>
                <Switch checked={config.enableChart} onChange={(checked) => updateConfig('enableChart', checked)} />
              </div>
            </div>

            <div style={{ marginBottom: 16 }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <Text strong>Skill 智能推荐</Text>
                  <br />
                  <Text type="tertiary" size="small">根据对话内容自动推荐可复用的 Skill</Text>
                </div>
                <Switch checked={config.enableSkillRecommend} onChange={(checked) => updateConfig('enableSkillRecommend', checked)} />
              </div>
            </div>

            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <Text strong>保存对话历史</Text>
                  <br />
                  <Text type="tertiary" size="small">自动保存对话记录到历史列表</Text>
                </div>
                <Switch checked={config.saveHistory} onChange={(checked) => updateConfig('saveHistory', checked)} />
              </div>
            </div>
          </Card>
        </Col>

        {/* 右侧：帮助信息 */}
        <Col span={8}>
          {/* 保存按钮 */}
          <Card style={{ marginBottom: 16 }}>
            <Space vertical style={{ width: '100%' }}>
              {hasChanges && (
                <Banner
                  type="info"
                  description="您有未保存的更改"
                />
              )}
              <Button
                type="primary"
                theme="solid"
                block
                size="large"
                icon={<IconSave />}
                onClick={saveConfig}
                disabled={!hasChanges}
              >
                保存设置
              </Button>
              <Button
                block
                onClick={() => {
                  setConfig(DEFAULT_CONFIG)
                  setHasChanges(true)
                }}
              >
                恢复默认设置
              </Button>
            </Space>
          </Card>

          {/* 帮助信息 */}
          <Card title="使用帮助" style={{ marginBottom: 16 }}>
            <Collapse accordion>
              <Collapse.Panel header="关于 DeepSeek" itemKey="deepseek">
                <div style={{ padding: 8 }}>
                  <Text type="tertiary" size="small">
                    当前系统使用 DeepSeek 官方 API，模型和 Key 由服务器端统一配置。
                    <br /><br />
                    <strong>注意：</strong>需要连接校园网才能访问。如果您在校外，请使用 VPN 或配置其他模型提供商。
                  </Text>
                </div>
              </Collapse.Panel>
              <Collapse.Panel header="关于 ClickHouse" itemKey="clickhouse">
                <div style={{ padding: 8 }}>
                  <Text type="tertiary" size="small">
                    ClickHouse 用于存储网络测量数据。如果您看到"未连接"，请检查：
                    <br /><br />
                    1. ClickHouse 服务是否运行<br />
                    2. 数据库配置是否正确<br />
                    3. 是否已导入测量数据
                  </Text>
                </div>
              </Collapse.Panel>
              <Collapse.Panel header="关于 Skill 系统" itemKey="skill">
                <div style={{ padding: 8 }}>
                  <Text type="tertiary" size="small">
                    Skill 系统可以将成功的对话提炼为可复用的技能：
                    <br /><br />
                    1. 在对话完成后，点击"提炼为 Skill"<br />
                    2. 为 Skill 起一个有意义的名字<br />
                    3. 系统会自动提取关键步骤<br />
                    4. 下次遇到类似问题可快速复用
                  </Text>
                </div>
              </Collapse.Panel>
            </Collapse>
          </Card>

          {/* 快捷操作 */}
          <Card title="快捷操作">
            <Space vertical style={{ width: '100%' }}>
              <Button
                block
                icon={<IconRefresh />}
                onClick={testAllConnections}
              >
                重新测试所有连接
              </Button>
              <Button
                block
                onClick={() => {
                  localStorage.clear()
                  Toast.success({ content: '缓存已清理', duration: 3 })
                  window.location.reload()
                }}
              >
                清理所有缓存
              </Button>
            </Space>
          </Card>
        </Col>
      </Row>
    </div>
  )
}

export default Settings

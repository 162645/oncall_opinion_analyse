import { useState, useEffect } from 'react'
import {
  Card,
  Table,
  Button,
  Space,
  Typography,
  Tag,
  Modal,
  Upload,
  Input,
  Select,
  Toast,
  Empty,
  Popconfirm,
  Descriptions,
  Tabs,
  TabPane,
  List,
  Checkbox,
  Divider,
  Spin,
} from '@douyinfe/semi-ui'
import type { BasicSelectValue } from '@douyinfe/semi-ui/lib/es/select'
import {
  IconUpload,
  IconSearch,
  IconRefresh,
  IconFile,
  IconDelete,
  IconChevronRight,
} from '@douyinfe/semi-icons'
import './Knowledge.css'

const { Title, Text } = Typography

const API_BASE = import.meta.env.VITE_API_BASE || ''

interface Chunk {
  chunk_id: string
  content: string
  position: number
}

interface Document {
  id: string
  title: string
  doc_type: string
  file_name: string
  file_size: number
  status: string
  chunk_count: number
  created_at: string
  updated_at: string
  content_preview?: string
  metadata?: Record<string, any>
  chunks?: Chunk[]
}

function Knowledge() {
  const [documents, setDocuments] = useState<Document[]>([])
  const [loading, setLoading] = useState(false)
  const [uploadVisible, setUploadVisible] = useState(false)
  const [fileList, setFileList] = useState<any[]>([])
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedType, setSelectedType] = useState<string>()

  // 新增状态
  const [detailVisible, setDetailVisible] = useState(false)
  const [selectedDoc, setSelectedDoc] = useState<Document | null>(null)
  const [selectedRows, setSelectedRows] = useState<string[]>([])
  const [chunksLoading, setChunksLoading] = useState(false)

  useEffect(() => {
    loadDocuments()
  }, [])

  const loadDocuments = async () => {
    setLoading(true)
    try {
      const response = await fetch(`${API_BASE}/api/knowledge/documents`)
      const data = await response.json()
      if (data.success) {
        setDocuments(data.documents || [])
      } else {
        setDocuments([])
      }
    } catch (error) {
      console.error('Failed to load documents:', error)
      setDocuments([])
    } finally {
      setLoading(false)
    }
  }

  const handleUpload = async () => {
    if (fileList.length === 0) {
      Toast.warning({ content: '请选择要上传的文件', duration: 3 })
      return
    }

    const formData = new FormData()
    fileList.forEach((file) => {
      formData.append('files', file as any)
    })

    try {
      const response = await fetch(`${API_BASE}/api/knowledge/batch`, {
        method: 'POST',
        body: formData,
      })
      const data = await response.json()
      if (data.success) {
        Toast.success({ content: `成功上传 ${data.total} 个文件`, duration: 3 })
        setUploadVisible(false)
        setFileList([])
        loadDocuments()
      }
    } catch (error) {
      Toast.error({ content: '上传失败', duration: 3 })
    }
  }

  const handleDelete = async (docId: string) => {
    try {
      const response = await fetch(`/api/knowledge/documents/${docId}`, {
        method: 'DELETE',
      })
      const data = await response.json()
      if (data.success) {
        Toast.success({ content: '删除成功', duration: 3 })
        loadDocuments()
        if (detailVisible) {
          setDetailVisible(false)
        }
      }
    } catch (error) {
      Toast.error({ content: '删除失败', duration: 3 })
    }
  }

  // 批量删除
  const handleBatchDelete = async () => {
    if (selectedRows.length === 0) {
      Toast.warning({ content: '请先选择要删除的文档', duration: 3 })
      return
    }

    Modal.confirm({
      title: '确认批量删除',
      content: `确定要删除选中的 ${selectedRows.length} 个文档吗？此操作不可恢复。`,
      onOk: async () => {
        let successCount = 0
        for (const docId of selectedRows) {
          try {
            const response = await fetch(`/api/knowledge/documents/${docId}`, {
              method: 'DELETE',
            })
            if (response.ok) {
              successCount++
            }
          } catch (error) {
            console.error(`删除 ${docId} 失败`)
          }
        }
        Toast.success({ content: `成功删除 ${successCount} 个文档`, duration: 3 })
        setSelectedRows([])
        loadDocuments()
      },
    })
  }

  // 查看文档详情
  const viewDocument = async (docId: string) => {
    setChunksLoading(true)
    setDetailVisible(true)

    try {
      const response = await fetch(`/api/knowledge/documents/${docId}`)
      const data = await response.json()
      if (data.success && data.document) {
        setSelectedDoc(data.document)
      }
    } catch (error) {
      Toast.error({ content: '获取文档详情失败', duration: 3 })
    } finally {
      setChunksLoading(false)
    }
  }

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return bytes + ' B'
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
  }

  const getTypeColor = (type: string): 'blue' | 'cyan' | 'green' | 'grey' | 'violet' => {
    const colors: Record<string, 'blue' | 'cyan' | 'green' | 'grey' | 'violet'> = {
      pdf: 'blue',
      word: 'cyan',
      markdown: 'green',
      text: 'grey',
    }
    return colors[type] || 'violet'
  }

  const getStatusColor = (status: string): 'green' | 'blue' | 'orange' | 'red' | 'grey' => {
    const colors: Record<string, 'green' | 'blue' | 'orange' | 'red' | 'grey'> = {
      ready: 'green',
      processing: 'blue',
      pending: 'orange',
      failed: 'red',
    }
    return colors[status] || 'grey'
  }

  const getStatusText = (status: string) => {
    const texts: Record<string, string> = {
      ready: '就绪',
      processing: '处理中',
      pending: '等待中',
      failed: '失败',
    }
    return texts[status] || status
  }

  const handleTypeChange = (value: BasicSelectValue | undefined) => {
    setSelectedType(value ? String(value) : undefined)
  }

  const columns = [
    {
      title: (
        <Checkbox
          checked={selectedRows.length === documents.length && documents.length > 0}
          indeterminate={selectedRows.length > 0 && selectedRows.length < documents.length}
          onChange={(e) => {
            if (e.target.checked) {
              setSelectedRows(documents.map(d => d.id))
            } else {
              setSelectedRows([])
            }
          }}
        />
      ),
      dataIndex: 'select',
      width: 50,
      render: (_: any, record: Document) => (
        <Checkbox
          checked={selectedRows.includes(record.id)}
          onChange={(e) => {
            if (e.target.checked) {
              setSelectedRows([...selectedRows, record.id])
            } else {
              setSelectedRows(selectedRows.filter(id => id !== record.id))
            }
          }}
        />
      ),
    },
    {
      title: '文件名',
      dataIndex: 'file_name',
      render: (text: string) => (
        <Space>
          <IconFile />
          <Text>{text}</Text>
        </Space>
      ),
    },
    {
      title: '类型',
      dataIndex: 'doc_type',
      render: (type: string) => (
        <Tag color={getTypeColor(type)}>{type.toUpperCase()}</Tag>
      ),
    },
    {
      title: '大小',
      dataIndex: 'file_size',
      render: (size: number) => formatFileSize(size),
    },
    {
      title: '分块数',
      dataIndex: 'chunk_count',
    },
    {
      title: '状态',
      dataIndex: 'status',
      render: (status: string) => (
        <Tag color={getStatusColor(status)}>{getStatusText(status)}</Tag>
      ),
    },
    {
      title: '更新时间',
      dataIndex: 'updated_at',
      render: (date: string) => new Date(date).toLocaleString(),
    },
    {
      title: '操作',
      render: (_: any, record: Document) => (
        <Space>
          <Button
            size="small"
            theme="borderless"
            onClick={() => viewDocument(record.id)}
          >
            查看
          </Button>
          <Popconfirm
            title="确定删除该文档？"
            content="删除后将同时移除向量数据"
            onConfirm={() => handleDelete(record.id)}
          >
            <Button size="small" type="danger" theme="borderless" icon={<IconDelete />}>
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ]

  return (
    <div className="knowledge-page">
      <div className="page-header">
        <Title heading={3}>知识库管理</Title>
        <Space>
          {selectedRows.length > 0 && (
            <Button
              type="danger"
              icon={<IconDelete />}
              onClick={handleBatchDelete}
            >
              删除选中 ({selectedRows.length})
            </Button>
          )}
          <Button theme="solid" type="primary" onClick={() => setUploadVisible(true)}>
            <IconUpload /> 上传文档
          </Button>
        </Space>
      </div>

      <Card>
        <div className="toolbar">
          <Space>
            <Input
              placeholder="搜索文档..."
              prefix={<IconSearch />}
              value={searchQuery}
              onChange={setSearchQuery}
              style={{ width: 200 }}
            />
            <Select
              placeholder="文件类型"
              style={{ width: 120 }}
              value={selectedType}
              onChange={handleTypeChange}
            >
              <Select.Option value="">全部</Select.Option>
              <Select.Option value="pdf">PDF</Select.Option>
              <Select.Option value="word">Word</Select.Option>
              <Select.Option value="markdown">Markdown</Select.Option>
              <Select.Option value="text">文本</Select.Option>
            </Select>
            <Button icon={<IconRefresh />} onClick={loadDocuments}>
              刷新
            </Button>
          </Space>
        </div>

        <Table
          columns={columns}
          dataSource={documents}
          loading={loading}
          pagination={{ pageSize: 10 }}
          empty={<Empty description="暂无文档，点击上传按钮添加" />}
        />
      </Card>

      {/* 上传弹窗 */}
      <Modal
        title="上传文档"
        visible={uploadVisible}
        onCancel={() => setUploadVisible(false)}
        onOk={handleUpload}
        okText="上传"
        cancelText="取消"
      >
        <Upload
          draggable
          fileList={fileList}
          onChange={({ fileList }) => setFileList(fileList)}
          accept=".pdf,.doc,.docx,.md,.txt,.json,.csv"
          multiple
        >
          <div className="upload-area">
            <IconUpload size="extra-large" style={{ color: '#999' }} />
            <Text type="tertiary" style={{ marginTop: 12 }}>
              点击或拖拽文件到此区域上传
            </Text>
            <Text type="tertiary" size="small">
              支持 PDF、Word、Markdown、TXT、JSON、CSV 格式
            </Text>
          </div>
        </Upload>
      </Modal>

      {/* 文档详情弹窗 */}
      <Modal
        title={
          <Space>
            <IconFile />
            <span>{selectedDoc?.title || '文档详情'}</span>
          </Space>
        }
        visible={detailVisible}
        onCancel={() => {
          setDetailVisible(false)
          setSelectedDoc(null)
        }}
        footer={
          <Space>
            <Button onClick={() => setDetailVisible(false)}>关闭</Button>
            <Button
              type="danger"
              onClick={() => {
                if (selectedDoc) {
                  handleDelete(selectedDoc.id)
                }
              }}
            >
              删除文档
            </Button>
          </Space>
        }
        width={800}
      >
        {chunksLoading ? (
          <div style={{ textAlign: 'center', padding: 40 }}>
            <Spin size="large" />
          </div>
        ) : selectedDoc ? (
          <Tabs defaultActiveKey="info">
            <TabPane tab="基本信息" itemKey="info">
              <Descriptions>
                <Descriptions.Item itemKey="文件名">{selectedDoc.file_name}</Descriptions.Item>
                <Descriptions.Item itemKey="类型">
                  <Tag color={getTypeColor(selectedDoc.doc_type)}>
                    {selectedDoc.doc_type.toUpperCase()}
                  </Tag>
                </Descriptions.Item>
                <Descriptions.Item itemKey="大小">
                  {formatFileSize(selectedDoc.file_size)}
                </Descriptions.Item>
                <Descriptions.Item itemKey="状态">
                  <Tag color={getStatusColor(selectedDoc.status)}>
                    {getStatusText(selectedDoc.status)}
                  </Tag>
                </Descriptions.Item>
                <Descriptions.Item itemKey="分块数">{selectedDoc.chunk_count}</Descriptions.Item>
                <Descriptions.Item itemKey="创建时间">
                  {new Date(selectedDoc.created_at).toLocaleString()}
                </Descriptions.Item>
                <Descriptions.Item itemKey="更新时间">
                  {new Date(selectedDoc.updated_at).toLocaleString()}
                </Descriptions.Item>
              </Descriptions>

              <Divider margin={24}>内容预览</Divider>
              <div className="content-preview">
                <Text>{selectedDoc.content_preview || '暂无内容预览'}</Text>
              </div>
            </TabPane>

            <TabPane tab="分块列表" itemKey="chunks">
              {selectedDoc.chunk_count > 0 ? (
                <List
                  dataSource={Array.from({ length: Math.min(selectedDoc.chunk_count, 20) }, (_, i) => ({
                    id: `chunk-${i}`,
                    position: i,
                  }))}
                  renderItem={(item) => (
                    <List.Item
                      className="chunk-item"
                      style={{ cursor: 'pointer' }}
                    >
                      <Space>
                        <Tag>分块 {item.position + 1}</Tag>
                        <IconChevronRight style={{ color: '#999' }} />
                      </Space>
                    </List.Item>
                  )}
                />
              ) : (
                <Empty description="暂无分块数据" />
              )}
              {selectedDoc.chunk_count > 20 && (
                <Text type="tertiary" size="small" style={{ marginTop: 8, display: 'block' }}>
                  显示前 20 个分块，共 {selectedDoc.chunk_count} 个
                </Text>
              )}
            </TabPane>

            <TabPane tab="元数据" itemKey="metadata">
              {selectedDoc.metadata && Object.keys(selectedDoc.metadata).length > 0 ? (
                <Descriptions>
                  {Object.entries(selectedDoc.metadata).map(([key, value]) => (
                    <Descriptions.Item key={key} itemKey={key}>
                      {typeof value === 'object' ? JSON.stringify(value) : String(value)}
                    </Descriptions.Item>
                  ))}
                </Descriptions>
              ) : (
                <Empty description="暂无元数据" />
              )}
            </TabPane>
          </Tabs>
        ) : (
          <Empty description="文档不存在" />
        )}
      </Modal>
    </div>
  )
}

export default Knowledge

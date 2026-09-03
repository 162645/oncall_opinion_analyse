# v4 版本优化文档

> **版本**: 4.0
> **日期**: 2025-05-20
> **核心优化**: 知识库管理 + Web 前端 + 前沿 Agent 技术

---

## 一、优化背景

### 1.1 v3 已完成

| 模块 | 内容 | 状态 |
|------|------|------|
| 思考过程可视化 | Trace 模块 | ✅ |
| 自然语言可视化 | 图表生成 | ✅ |
| MCP 集成 | 文件/内存/时间工具 | ✅ |

### 1.2 v4 目标

| 优化项 | 目标 | 预期收益 |
|--------|------|---------|
| 知识库管理 | 多格式文档上传、CRUD | 动态维护知识库 |
| Web 前端 | React + Semi Design | 直观用户交互 |
| Agent 模式管理 | 用户可选 + 系统自动 | 灵活性提升 |
| ReAct Agent | 推理-行动循环 | 复杂问题分解 |
| Self-Reflection | 自我反思 | 结果验证改进 |
| MinIO 存储 | 对象存储集成 | 生产级文件管理 |

---

## 二、实现过程

### 2.1 知识库管理模块

#### 文档数据模型

**文件**: `src/knowledge/models.py`

```python
@dataclass
class KnowledgeDocument:
    id: str
    title: str
    content: str
    doc_type: DocumentType
    file_path: str
    file_name: str
    file_size: int
    file_hash: str
    status: DocumentStatus
    metadata: Dict[str, Any]
    chunks: List[DocumentChunk]
```

#### 多格式文档解析器

**文件**: `src/knowledge/parser/`

| 解析器 | 支持格式 | 依赖库 |
|--------|---------|--------|
| PDFParser | .pdf | PyMuPDF / pdfplumber |
| WordParser | .doc, .docx | python-docx |
| MarkdownParser | .md, .markdown | PyYAML |
| TextParser | .txt | 内置 |

#### 解析流程

```
文档上传
    ↓
格式识别 (MIME Type)
    ↓
选择解析器 (ParserFactory)
    ↓
文本提取 + 结构识别
    ↓
智能分块 (Chunking)
    ↓
向量存储 (Qdrant)
```

---

### 2.2 FastAPI 后端

#### 应用结构

**文件**: `src/api/`

```
src/api/
├── main.py              # FastAPI 入口
├── router/
│   ├── knowledge.py     # 知识库 API
│   ├── chat.py          # 对话 API
│   ├── agent.py         # Agent 管理 API
│   └── health.py        # 健康检查
└── middleware/
    └── cors.py          # CORS 配置
```

#### API 端点

| 端点 | 方法 | 功能 |
|------|------|------|
| `/api/knowledge/upload` | POST | 上传文档 |
| `/api/knowledge/documents` | GET | 文档列表 |
| `/api/knowledge/documents/{id}` | GET/DELETE | 文档详情/删除 |
| `/api/knowledge/search` | POST | 知识检索 |
| `/api/chat/send` | POST | 发送消息 |
| `/api/chat/modes` | GET | 可用模式列表 |
| `/api/agent/list` | GET | Agent 列表 |

---

### 2.3 React 前端

#### 技术栈

| 技术 | 版本 | 用途 |
|------|------|------|
| React | 18 | UI 框架 |
| Semi Design | 2.50 | UI 组件库 |
| React Router | 6 | 路由管理 |
| Zustand | 4 | 状态管理 |
| Axios | 1.6 | HTTP 客户端 |
| Vite | 5 | 构建工具 |

#### 页面结构

**文件**: `frontend/src/pages/`

| 页面 | 路径 | 功能 |
|------|------|------|
| Home | /home | 系统概览仪表盘 |
| Knowledge | /knowledge | 知识库管理 |
| Chat | /chat | 智能对话 |
| Visualization | /visualization | 数据可视化 |
| Settings | /settings | 系统设置 |

#### 知识库管理界面

```
┌─────────────────────────────────────────────────────────────┐
│ 知识库管理                                    [+ 上传文档]   │
├─────────────────────────────────────────────────────────────┤
│ [搜索框]     筛选: [全部▼] [PDF] [Word] [MD]               │
├─────────────────────────────────────────────────────────────┤
│ 文件名          │ 类型 │ 大小   │ 状态   │ 更新时间        │
├─────────────────────────────────────────────────────────────┤
│ 诊断手册.pdf    │ PDF  │ 2.3 MB │ 就绪   │ 2025-05-20      │
│ SOP文档.docx    │ Word │ 1.1 MB │ 就绪   │ 2025-05-19      │
└─────────────────────────────────────────────────────────────┘
```

#### Agent 模式选择器

```
┌─────────────────────────────────────────────────────────────┐
│ 智能诊断助手                              [顺序▼] [并行]    │
│                                              [层级]  [辩论] │
├─────────────────────────────────────────────────────────────┤
│ 👤 用户: 新加坡区域网络延迟突增                             │
│                                                             │
│ 🤖 助手:                                                    │
│ ┌─────────────────────────────────────────────────────────┐ │
│ │ 📊 执行追踪                              [展开详情]     │ │
│ │ ├─ Step 1: 知识检索 (234ms)                            │ │
│ │ ├─ Step 2: 数据分析 (567ms)                            │ │
│ │ └─ Step 3: 诊断结论 (123ms)                            │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                             │
│ 根因分析: 新加坡到美国链路拥塞                              │
│ 置信度: 92%                                                 │
└─────────────────────────────────────────────────────────────┘
```

---

### 2.4 ReAct Agent

#### 核心思想

ReAct = Reasoning + Acting

```
循环执行:
1. Thought: 思考当前状态和下一步行动
2. Action: 选择工具并执行
3. Observation: 观察执行结果
4. 重复直到得出 Final Answer
```

#### 实现

**文件**: `src/agents/react/agent.py`

```python
class ReActAgent:
    async def execute(self, query: str, context: AgentContext) -> AgentResult:
        for step in range(self.max_steps):
            # 1. 思考
            thought = await self._think(query, steps)

            # 2. 检查是否有最终答案
            if thought.get("final_answer"):
                return AgentResult(success=True, data=thought["final_answer"])

            # 3. 执行行动
            result = await self._act(thought["action"], thought["action_input"])

            # 4. 记录观察
            steps.append(ReActStep(thought=thought, result=result))

        return AgentResult(success=False, error="Max steps reached")
```

#### 使用示例

```python
agent = ReActAgent(tools={
    "search": knowledge_search,
    "query": query_metrics,
})

result = await agent.execute(
    query="分析新加坡区域网络延迟突增的原因"
)
```

---

### 2.5 Self-Reflection Agent

#### 核心思想

自我反思机制，验证和改进结果

```
执行流程:
1. 执行基础诊断
2. 反思评估结果
   - 完整性
   - 准确性
   - 证据支持
   - 可操作性
3. 识别不足
4. 生成改进建议
5. 必要时重新执行
```

#### 实现

**文件**: `src/agents/reflection/agent.py`

```python
class ReflectionAgent:
    async def execute(self, context: AgentContext) -> AgentResult:
        for reflection_id in range(self.max_reflections):
            # 1. 执行基础 Agent
            result = await self.base_agent.execute(context)

            # 2. 反思评估
            reflection = await self._reflect(query, result)

            # 3. 检查分数
            if reflection.score >= self.min_score_threshold:
                return result

            # 4. 准备重试
            context = self._prepare_retry_context(context, reflection)

        return best_result
```

#### 评估维度

| 维度 | 说明 | 权重 |
|------|------|------|
| 完整性 | 是否覆盖所有方面 | 20% |
| 准确性 | 分析结论是否准确 | 25% |
| 证据支持 | 是否有数据支持 | 25% |
| 可操作性 | 解决方案是否可行 | 15% |
| 清晰度 | 表达是否清晰 | 15% |

---

### 2.6 MinIO 文件存储

#### 架构

```
┌─────────────────┐
│  FastAPI 服务   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  StorageService │ (接口)
└────────┬────────┘
         │
    ┌────┴────┐
    ▼         ▼
┌───────┐ ┌───────┐
│ Local │ │ MinIO │
│Storage│ │Storage│
└───────┘ └───────┘
  (开发)    (生产)
```

#### 实现

**文件**: `src/storage/`

```python
class MinIOStorage(StorageService):
    async def upload(self, file_name: str, file_data: BinaryIO) -> FileInfo:
        client = self._get_client()
        object_name = self._generate_object_name(file_name)
        client.put_object(self.bucket_name, object_name, file_data, ...)
        return FileInfo(...)

    async def download(self, file_path: str) -> bytes:
        response = client.get_object(self.bucket_name, object_name)
        return response.read()

    async def get_presigned_url(self, file_path: str, expires: int) -> str:
        return client.presigned_get_object(self.bucket_name, object_name, expires)
```

---

## 三、代码变更记录

### 3.1 新增文件

| 文件 | 功能 | 行数 |
|------|------|------|
| `src/knowledge/models.py` | 文档数据模型 | ~180 |
| `src/knowledge/parser/base.py` | 解析器基类 | ~80 |
| `src/knowledge/parser/pdf_parser.py` | PDF 解析 | ~120 |
| `src/knowledge/parser/word_parser.py` | Word 解析 | ~100 |
| `src/knowledge/parser/markdown_parser.py` | MD 解析 | ~100 |
| `src/knowledge/parser/text_parser.py` | 文本解析 | ~70 |
| `src/knowledge/parser/factory.py` | 解析器工厂 | ~80 |
| `src/api/main.py` | FastAPI 入口 | ~70 |
| `src/api/router/knowledge.py` | 知识库 API | ~200 |
| `src/api/router/chat.py` | 对话 API | ~180 |
| `src/api/router/agent.py` | Agent API | ~150 |
| `src/agents/react/agent.py` | ReAct Agent | ~250 |
| `src/agents/reflection/agent.py` | 反思 Agent | ~280 |
| `src/storage/base.py` | 存储接口 | ~80 |
| `src/storage/local_storage.py` | 本地存储 | ~150 |
| `src/storage/minio_storage.py` | MinIO 存储 | ~180 |
| `frontend/src/App.tsx` | 前端入口 | ~50 |
| `frontend/src/pages/Knowledge/` | 知识库页面 | ~200 |
| `frontend/src/pages/Chat/` | 对话页面 | ~250 |

**总计: ~2,800 行新代码**

---

## 四、启动方式

### 4.1 后端

```bash
# 安装依赖
pip install fastapi uvicorn python-multipart python-docx PyMuPDF pdfplumber pyyaml minio

# 启动服务
cd src && uvicorn api.main:app --reload --port 8000

# 访问 API 文档
open http://localhost:8000/docs
```

### 4.2 前端

```bash
# 安装依赖
cd frontend && npm install

# 启动开发服务器
npm run dev

# 访问
open http://localhost:5173
```

### 4.3 MinIO (可选)

```bash
# Docker 启动
docker run -d \
  --name minio \
  -p 9000:9000 \
  -p 9001:9001 \
  -e MINIO_ROOT_USER=minioadmin \
  -e MINIO_ROOT_PASSWORD=minioadmin \
  minio/minio server /data --console-address ":9001"

# 访问控制台
open http://localhost:9001
```

---

## 五、效果展示

### 5.1 知识库管理

- ✅ 支持 PDF、Word、Markdown、TXT 格式
- ✅ 文档上传、列表、搜索、删除
- ✅ 批量上传支持

### 5.2 智能对话

- ✅ 4 种 Agent 模式选择
- ✅ 执行追踪可视化
- ✅ 置信度显示

### 5.3 ReAct Agent

- ✅ 推理-行动循环
- ✅ 自动工具选择
- ✅ 思考过程记录

### 5.4 Self-Reflection

- ✅ 结果质量评估
- ✅ 改进建议生成
- ✅ 自动重试机制

---

## 六、后续规划

| Phase | 内容 | 状态 |
|-------|------|------|
| v4.0 | 知识库 + 前端 + ReAct + Reflection | ✅ 本版本 |
| v4.1 | Redis 缓存集成 | 📅 计划中 |
| v4.2 | 实时监控仪表盘 | 📅 计划中 |
| v4.3 | 多语言支持 | 📅 计划中 |

---

## 七、依赖清单

```txt
# 后端
fastapi>=0.109.0
uvicorn>=0.27.0
python-multipart>=0.0.6
python-docx>=1.1.0
PyMuPDF>=1.23.0
pdfplumber>=0.10.0
PyYAML>=6.0
minio>=7.2.0

# 前端
react>=18.2.0
@douyinfe/semi-ui>=2.50.0
react-router-dom>=6.22.0
zustand>=4.5.0
axios>=1.6.0
echarts>=5.5.0
```
> 历史设计文档：其中的 ReAct 方案已被当前主链路的 LangGraph 状态机、Reflection 和 Tool Runtime 取代，示例代码不属于当前运行时。

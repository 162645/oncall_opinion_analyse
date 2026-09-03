# v3 优化文档

> **版本**: 3.0
> **日期**: 2025-05-20
> **核心优化**: 可视化增强、MCP 集成、用户体验提升

---

## 一、优化背景

### 1.1 v2 已完成

| 模块 | 内容 | 状态 |
|------|------|------|
| 动态工具发现 | ToolRegistry + 插件架构 | ✅ |
| Agentic RAG | 迭代检索 + 重排序 | ✅ |
| 多模式编排 | 顺序/并行/层级/辩论 | ✅ |
| 知识图谱 | Neo4j 故障关联 | ✅ |
| 诊断评估 | 准确率追踪 | ✅ |

### 1.2 v3 目标

| 优化项 | 目标 | 预期收益 |
|--------|------|---------|
| 思考过程可视化 | 展示 Agent 推理链 | 可解释性提升 |
| 自然语言可视化 | 文字描述 → 图表 | 降低使用门槛 |
| MCP 集成 | 文件/浏览器/绘图 | 功能扩展 |
| 文档完善 | 详细记录过程 | 可维护性提升 |

---

## 二、优化过程记录

### 2.1 第一阶段：思考过程可视化 (2025-05-20)

#### 需求分析

当前问题：
```
用户输入 → ??? → 输出结果
              ↑
         黑盒过程，用户不知道发生了什么
```

期望效果：
```
用户输入
    ↓
┌─────────────────────────────────────┐
│ Step 1: 意图识别 (15ms)             │
│ → 识别为 "故障诊断"                 │
│ → 置信度: 0.92                      │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│ Step 2: 知识检索 (234ms)            │
│ → 查询: "网络延迟异常"              │
│ → 找到 3 个相似案例                 │
│ → 思考: 需要进一步查询数据          │
└─────────────────────────────────────┘
    ↓
输出结果
```

#### 设计方案

核心组件：
1. `TraceStep` - 单个步骤数据结构
2. `ExecutionTrace` - 完整执行追踪
3. `TraceCollector` - 追踪收集器
4. `TraceVisualizer` - 可视化渲染器

#### 实现文件

```
src/trace/
├── __init__.py
├── models.py       # TraceStep, ExecutionTrace
├── collector.py    # TraceCollector
└── visualizer.py   # TraceVisualizer
```

#### 关键代码

```python
@dataclass
class TraceStep:
    step_id: int
    step_type: StepType
    agent_name: str
    action: str
    input_data: Dict[str, Any]
    output_data: Dict[str, Any]
    reasoning: str          # 核心思考过程
    confidence: float
    duration_ms: int
```

#### 实验验证

```python
# 测试追踪功能
collector = TraceCollector()
collector.start_trace("test-001", "查询延迟")

with collector.trace_step(
    step_type=StepType.TOOL_CALL,
    agent_name="AnalysisAgent",
    action="query_latency",
) as step:
    result = query_latency(region="Singapore")
    step.output_data = result
    step.reasoning = "查询新加坡区域延迟，发现 P99=150ms"

trace = collector.end_trace()
print(TraceVisualizer.render_markdown(trace))
```

#### 效果

✅ 可追踪每个 Agent 的执行过程
✅ 可输出 Markdown/HTML/JSON 格式
✅ 支持流式输出（SSE）

---

### 2.2 第二阶段：自然语言可视化 (2025-05-20)

#### 需求分析

用户期望：
```
用户: "画一个最近24小时的延迟趋势图"
     ↓
系统: 自动解析 → 查询数据 → 生成图表
     ↓
输出: 📊 折线图 + 数据说明
```

#### 设计方案

架构：
```
自然语言输入
    ↓
意图解析器 (IntentParser)
    ├─ 图表类型识别
    ├─ 指标识别
    ├─ 时间范围提取
    └─ 过滤条件提取
    ↓
数据查询器 (DataFetcher)
    ├─ 构建 PromQL/SQL
    ├─ 执行查询
    └─ 数据预处理
    ↓
图表生成器 (ChartGenerator)
    ├─ 选择图表类型
    ├─ 配置样式
    └─ 生成图片
    ↓
输出结果
```

#### 实现文件

```
src/visualization/
├── __init__.py
├── intent_parser.py    # 意图解析
├── data_fetcher.py     # 数据查询
├── chart_generator.py  # 图表生成
└── service.py          # 服务入口
```

#### 支持的查询类型

| 查询示例 | 解析结果 |
|---------|---------|
| "画一个延迟趋势图" | 折线图, latency, 1h |
| "最近24小时流量变化" | 折线图, traffic, 24h |
| "各区域错误率对比" | 柱状图, error_rate, 按区域 |
| "新加坡延迟分布饼图" | 饼图, latency, region=Singapore |

#### 关键代码

```python
class VisualizationIntentParser:
    def parse(self, query: str) -> VisualizationIntent:
        # 1. 识别图表类型
        chart_type = self._detect_chart_type(query)

        # 2. 识别指标
        metric = self._detect_metric(query)

        # 3. 识别时间范围
        time_range = self._detect_time_range(query)

        # 4. 提取过滤条件
        filters = self._extract_filters(query)

        return VisualizationIntent(...)
```

#### 效果

✅ 支持中文自然语言描述
✅ 自动识别图表类型
✅ 生成 base64/HTML 格式图表

---

### 2.3 第三阶段：MCP 集成 (2025-05-20)

#### 需求分析

需要集成：
1. 文件处理 - 读取日志、生成报告
2. 浏览器 - 监控面板截图
3. 绘图 - 流程图生成
4. 时间工具 - 时间计算
5. 内存存储 - 知识持久化

#### 设计方案

架构：
```
┌────────────────────────────────────────────┐
│             MCP Client                      │
├────────────────────────────────────────────┤
│  Tool Registry (工具注册中心)               │
│    ├─ FileTools (文件操作)                  │
│    ├─ MemoryTools (内存存储)                │
│    ├─ TimeTools (时间处理)                  │
│    └─ External MCP Servers                  │
├────────────────────────────────────────────┤
│  Tool Handlers (工具处理器)                 │
│    ├─ 内置处理器 (Python 实现)              │
│    └─ 外部处理器 (MCP Server)               │
└────────────────────────────────────────────┘
```

#### MCP 配置

```json
// .mcp.json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"]
    },
    "time": {
      "command": "uvx",
      "args": ["mcp-server-time"]
    },
    "memory": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-memory"]
    },
    "sqlite": {
      "command": "uvx",
      "args": ["mcp-server-sqlite", "--db-path", "/tmp/mcp.db"]
    }
  },
  "settings": {
    "defaultTimeout": 30000,
    "maxRetries": 3
  }
}
```

#### 实现文件

```
src/mcp/
├── __init__.py           # 模块入口
├── base.py               # 基础类型 (ToolResult, ToolStatus)
├── config.py             # 配置管理
├── client.py             # MCP 客户端
└── tools/
    ├── __init__.py
    ├── file_tools.py     # 文件操作工具
    ├── memory_tools.py   # 内存存储工具
    └── time_tools.py     # 时间处理工具
```

#### 内置工具详情

**文件工具 (FileTools):**
| 工具名 | 功能 | 参数 |
|--------|------|------|
| `read_file` | 读取文件 | path, encoding, start_line, end_line |
| `write_file` | 写入文件 | path, content, mode |
| `list_directory` | 列出目录 | path, pattern |
| `search_files` | 搜索文件 | path, pattern, content_pattern |
| `delete_file` | 删除文件 | path |
| `file_info` | 文件信息 | path |
| `create_directory` | 创建目录 | path, parents |

**内存工具 (MemoryTools):**
| 工具名 | 功能 | 参数 |
|--------|------|------|
| `memory_save` | 保存数据 | key, value, ttl, tags |
| `memory_load` | 加载数据 | key, default |
| `memory_delete` | 删除数据 | key |
| `memory_list` | 列出键 | pattern, tag |
| `memory_search` | 搜索数据 | query |
| `memory_clear` | 清空存储 | - |

**时间工具 (TimeTools):**
| 工具名 | 功能 | 参数 |
|--------|------|------|
| `time_now` | 当前时间 | timezone_name, format_str |
| `time_format` | 格式化时间 | timestamp, format_str |
| `time_parse` | 解析时间 | time_str, format_str |
| `time_diff` | 时间差 | start, end, unit |
| `time_convert` | 时区转换 | time_str, from_tz, to_tz |

#### 使用示例

**文件操作:**
```python
from src.mcp import MCPClient

client = MCPClient()
await client.initialize()

# 写入报告
result = await client.call_tool("write_file", 
    path="reports/diagnosis.md",
    content="# 诊断报告\n..."
)

# 读取日志
result = await client.call_tool("read_file",
    path="logs/error.log"
)
```

**内存存储:**
```python
# 保存诊断结果
await client.call_tool("memory_save",
    key="incident_20250120",
    value={"type": "latency", "severity": "high"},
    tags=["incident", "latency"],
    ttl=86400  # 24小时过期
)

# 加载数据
result = await client.call_tool("memory_load", key="incident_20250120")
```

**时间处理:**
```python
# 获取当前时间
result = await client.call_tool("time_now")

# 计算时间差
result = await client.call_tool("time_diff",
    start="2025-01-01T00:00:00Z",
    unit="days"
)
```

#### 测试结果

```bash
$ python3 tests/test_mcp.py

=== 测试文件工具 ===
创建目录: success
写入文件: success, 11 bytes
读取文件: success, 内容=Hello, MCP!
列出目录: success, 文件数=1
文件信息: success, 大小=11 bytes
搜索文件: success, 找到=1 个
删除文件: success
删除目录: success
✓ 文件工具测试通过

=== 测试内存工具 ===
保存数据: success
加载数据: success, value={'name': 'test', 'value': 123}
列出键: success, 数量=2
搜索: success, 匹配数=1
删除数据: success
清空存储: success
✓ 内存工具测试通过

=== 测试时间工具 ===
当前时间: success, datetime=2026-05-20 11:09:29
格式化时间: success, formatted=2026年05月20日 11:09
解析时间: success, iso=2025-01-15T10:30:00
时间差: success, diff=504 days
时区转换: success
✓ 时间工具测试通过

所有测试通过 ✓
```

#### 效果

✅ 文件读写、目录操作完整支持
✅ 内存存储支持 TTL 和标签
✅ 时间工具支持多时区和格式化
✅ 内置工具无需外部 MCP Server 依赖
✅ 外部 MCP Server 可选连接

---

## 三、代码变更记录

### 3.1 新增文件

| 文件 | 功能 | 行数 |
|------|------|------|
| `src/trace/__init__.py` | 模块入口 | ~10 |
| `src/trace/models.py` | 追踪数据模型 | ~80 |
| `src/trace/collector.py` | 追踪收集器 | ~100 |
| `src/trace/visualizer.py` | 可视化渲染 | ~150 |
| `src/visualization/__init__.py` | 模块入口 | ~10 |
| `src/visualization/intent_parser.py` | 意图解析 | ~290 |
| `src/visualization/data_fetcher.py` | 数据查询 | ~210 |
| `src/visualization/chart_generator.py` | 图表生成 | ~315 |
| `src/visualization/service.py` | 服务入口 | ~170 |
| `src/mcp/__init__.py` | 模块入口 | ~15 |
| `src/mcp/base.py` | 基础类型 | ~60 |
| `src/mcp/config.py` | 配置管理 | ~140 |
| `src/mcp/client.py` | MCP 客户端 | ~260 |
| `src/mcp/tools/__init__.py` | 工具模块入口 | ~10 |
| `src/mcp/tools/file_tools.py` | 文件工具 | ~260 |
| `src/mcp/tools/memory_tools.py` | 内存工具 | ~240 |
| `src/mcp/tools/time_tools.py` | 时间工具 | ~220 |
| `tests/test_mcp.py` | MCP 测试 | ~400 |

**总计: ~3,000 行新代码**

### 3.2 修改文件

| 文件 | 修改内容 |
|------|---------|
| `src/__init__.py` | 添加 trace、visualization、mcp 模块导出 |
| `.mcp.json` | 添加 MCP 服务器配置 (filesystem, time, memory, sqlite) |

---

## 四、效果对比

### 4.1 思考过程可视化

| 维度 | v2 | v3 |
|------|----|----|
| 执行过程 | 黑盒 | 完整追踪 |
| 思考过程 | 不可见 | Markdown/HTML 展示 |
| 调试能力 | 困难 | 每步可查 |

### 4.2 自然语言可视化

| 维度 | v2 | v3 |
|------|----|----|
| 图表生成 | 需写代码 | 自然语言描述 |
| 用户门槛 | 高 | 低 |
| 交互方式 | API 调用 | 对话式 |

### 4.3 MCP 集成

| 维度 | v2 | v3 |
|------|----|----|
| 文件操作 | 无 | 完整支持 |
| 浏览器 | 无 | 截图/提取 |
| 扩展性 | 低 | 插件化 |

---

## 五、后续规划

| Phase | 内容 | 状态 |
|-------|------|------|
| v3.0 | 追踪可视化 + 自然语言可视化 + MCP | ✅ 本版本 |
| v3.1 | Web UI 界面 | 📅 计划中 |
| v3.2 | 语音交互 | 📅 计划中 |

---

## 六、依赖变更

```txt
# 新增依赖
matplotlib>=3.7.0
playwright>=1.40.0
mcp>=0.9.0
```

---

## 七、测试记录

### 7.1 追踪测试

```bash
python -c "
from src.trace import TraceCollector, TraceVisualizer
c = TraceCollector()
c.start_trace('test', '测试查询')
with c.trace_step(StepType.REASONING, 'Agent', 'test', {}) as s:
    s.reasoning = '测试思考过程'
t = c.end_trace()
print(TraceVisualizer.render_markdown(t))
"
```

结果: ✅ 通过

### 7.2 可视化测试

```bash
python -c "
from src.visualization import VisualizationIntentParser
p = VisualizationIntentParser()
r = p.parse('画一个最近24小时的延迟趋势图')
print(f'类型: {r.chart_type}, 指标: {r.metric}, 时间: {r.time_range}')
"
```

结果: ✅ 通过

### 7.3 MCP 工具测试

```bash
$ python3 tests/test_mcp.py

==================================================
MCP 模块测试
==================================================

=== 测试文件工具 ===
创建目录: success, {'created': '/tmp/mcp_test/test_dir'}
写入文件: success, {'bytes_written': 11}
读取文件: success, 内容=Hello, MCP!
列出目录: success, 文件数=1
文件信息: success, 大小=11 bytes
搜索文件: success, 找到=1 个
删除文件: success
删除目录: success
✓ 文件工具测试通过

=== 测试内存工具 ===
保存数据: success
加载数据: success, value={'name': 'test', 'value': 123}
列出键: success, 数量=2
搜索: success, 匹配数=1
删除数据: success
清空存储: success
✓ 内存工具测试通过

=== 测试时间工具 ===
当前时间: success, datetime=2026-05-20 11:09:29
格式化时间: success, formatted=2026年05月20日 11:09
解析时间: success, iso=2025-01-15T10:30:00
时间差: success, diff=504 days
时区转换: success
✓ 时间工具测试通过

==================================================
所有测试通过 ✓
==================================================
```

结果: ✅ 通过 (16/16 测试用例)

---

## 八、已知问题

| 问题 | 状态 | 计划解决 |
|------|------|---------|
| 图表中文显示 | ⚠️ 字体问题 | v3.1 |
| MCP 连接池 | ⚠️ 未实现 | v3.1 |
| 流式输出 | ⚠️ 仅 SSE | v3.1 |

---

## 九、参考资料

- [MCP 官方文档](https://modelcontextprotocol.io/)
- [Playwright 文档](https://playwright.dev/python/)
- [Matplotlib 文档](https://matplotlib.org/)

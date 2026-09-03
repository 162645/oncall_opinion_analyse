# 现成可用 Skills 汇总

## 一、LangChain 内置工具 (可直接导入)

```python
from langchain.tools import (
    # 搜索类
    DuckDuckGoSearchRun,      # DuckDuckGo 搜索
    GoogleSearchAPIWrapper,   # Google 搜索
    BingSearchAPIWrapper,     # Bing 搜索

    # 数据库类
    SQLDatabase,              # SQL 数据库查询
    SQLDatabaseChain,         # 自然语言转 SQL

    # 文件类
    ReadFileTool,             # 读取文件
    WriteFileTool,            # 写入文件
    ListDirectoryTool,        # 列出目录

    # 代码执行
    PythonREPLTool,           # Python 代码执行
    ShellTool,                # Shell 命令

    # API 类
    RequestsGetTool,          # HTTP GET
    RequestsPostTool,         # HTTP POST

    # 数学计算
    LLMMathChain,             # 数学运算

    # 维基百科
    WikipediaQueryRun,        # 维基百科查询
)
```

### 2. 安装即可用

```bash
pip install langchain
pip install langchain-community  # 社区工具
```

### 3. 使用示例

```python
from langchain.agents import initialize_agent, AgentType
from langchain.tools import DuckDuckGoSearchRun, PythonREPLTool
from langchain_openai import ChatOpenAI

# 初始化 LLM
llm = ChatOpenAI(model="gpt-4")

# 加载工具
tools = [
    DuckDuckGoSearchRun(),    # 网络搜索
    PythonREPLTool(),         # 执行 Python
]

# 创建 Agent
agent = initialize_agent(
    tools=tools,
    llm=llm,
    agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    verbose=True  # 显示思考过程
)

# 执行
result = agent.run("搜索最新的 Python 版本并计算 2**100")
```

## 二、社区运维工具 (需简单配置)

### 1. Prometheus 工具

```python
from langchain_community.tools import PrometheusQueryTool

# 配置 Prometheus URL
tool = PrometheusQueryTool(
    prometheus_url="http://localhost:9090"
)

# 执行查询
result = tool.run("up")
```

### 2. Redis 工具

```python
from langchain_community.tools import Redis
from redis import Redis as RedisClient

redis_client = RedisClient(host="localhost", port=6379)
tool = Redis(redis_client)

# 执行命令
result = tool.run("GET mykey")
```

### 3. SQL 数据库

```python
from langchain_community.tools import SQLDatabaseTool
from langchain_community.utilities import SQLDatabase

db = SQLDatabase.from_uri("sqlite:///mydb.db")
tool = SQLDatabaseTool(db=db)

# 自然语言转 SQL
result = tool.run("查询最近10条告警记录")
```

## 三、第三方工具包

### 1. CrewAI Tools

```bash
pip install crewai-tools
```

```python
from crewai_tools import (
    ScrapeWebsiteTool,        # 网页抓取
    FileReadTool,             # 文件读取
    DirectoryReadTool,        # 目录读取
    CodeDocsSearchTool,       # 代码文档搜索
    CodeInterpreterTool,      # 代码解释
)

# 使用
scraper = ScrapeWebsiteTool()
content = scraper.run("https://example.com")
```

### 2. LlamaIndex Tools

```bash
pip install llama-index
```

```python
from llama_index.tools import (
    QueryEngineTool,
    FunctionTool,
)

# 自定义函数工具
def query_prometheus(query: str) -> str:
    """查询 Prometheus 指标"""
    # 实现查询逻辑
    return result

tool = FunctionTool.from_defaults(fn=query_prometheus)
```

## 四、你的项目可以直接用的

| 工具 | 用途 | 安装 |
|------|------|------|
| `DuckDuckGoSearchRun` | 网络搜索 | 内置 |
| `PythonREPLTool` | 执行 Python | 内置 |
| `ReadFileTool` | 读取日志文件 | 内置 |
| `RequestsGetTool` | HTTP API 调用 | 内置 |
| `SQLDatabaseTool` | 数据库查询 | 需配置连接 |

## 五、推荐组合

```python
# 你的项目推荐的工具组合
from langchain.tools import (
    PythonREPLTool,
    ReadFileTool,
    RequestsGetTool,
)
from langchain_community.tools import SQLDatabaseTool

tools = [
    PythonREPLTool(),         # 执行分析脚本
    ReadFileTool(),           # 读取日志文件
    RequestsGetTool(),        # 调用外部 API
    # SQLDatabaseTool(...),   # 查询数据库 (需配置)
]
```

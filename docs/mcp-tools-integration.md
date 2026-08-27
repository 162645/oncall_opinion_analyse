# 可集成的 MCP 和 Tools 汇总

> 更新日期: 2025-05-20
> 数据来源: [mcp-awesome.com](https://mcp-awesome.com), [mcpservers.org](https://mcpservers.org)

## 一、文件处理类

### 1. Filesystem MCP (官方)

```bash
# 安装
npm install @modelcontextprotocol/server-filesystem
```

```json
// .mcp.json 配置
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/path/to/allowed/dir"]
    }
  }
}
```

**功能:**
- 读取文件
- 写入文件
- 列出目录
- 搜索文件
- 移动/复制文件

### 2. PDF Reader MCP

```bash
npm install @anthropic-ai/mcp-server-pdf
```

**功能:**
- 读取 PDF 文件
- 提取文本和图片
- PDF 元数据解析

### 3. Excel/CSV MCP

```python
# Python 实现
from mcp.server import Server

class ExcelMCP:
    def read_excel(self, path: str) -> dict:
        """读取 Excel 文件"""
        import pandas as pd
        df = pd.read_excel(path)
        return df.to_dict()

    def write_excel(self, path: str, data: dict):
        """写入 Excel 文件"""
        import pandas as pd
        df = pd.DataFrame(data)
        df.to_excel(path, index=False)
```

---

## 二、浏览器类

### 1. Playwright MCP (推荐)

```bash
npm install @anthropic-ai/mcp-server-playwright
```

```json
{
  "mcpServers": {
    "playwright": {
      "command": "npx",
      "args": ["-y", "@anthropic-ai/mcp-server-playwright"]
    }
  }
}
```

**功能:**
- 打开网页
- 截图
- 点击/输入
- 提取页面内容
- 执行 JavaScript
- 表单填写

**使用示例:**
```python
# 截图
await mcp.call("playwright_screenshot", {"url": "https://grafana.example.com"})

# 提取内容
content = await mcp.call("playwright_extract", {"selector": ".alert-list"})

# 点击按钮
await mcp.call("playwright_click", {"selector": "#submit-btn"})
```

### 2. Puppeteer MCP

```bash
npm install @anthropic-ai/mcp-server-puppeteer
```

**功能:**
- 浏览器自动化
- 网页抓取
- PDF 生成
- 性能分析

### 3. FireCrawl MCP

```bash
npm install firecrawl-mcp
```

**功能:**
- 智能网页抓取
- 结构化数据提取
- 批量爬取

---

## 三、绘图/可视化类

### 1. Mermaid MCP (流程图)

```bash
npm install mcp-server-mermaid
```

**功能:**
- 生成流程图
- 时序图
- 甘特图
- 类图

```python
# 生成流程图
result = await mcp.call("mermaid_generate", {
    "code": """
    graph TD
        A[告警触发] --> B{判断类型}
        B -->|网络| C[网络诊断]
        B -->|服务| D[服务诊断]
        C --> E[根因分析]
        D --> E
        E --> F[生成报告]
    """
})
```

### 2. Chart.js MCP (图表)

```python
# 自定义实现
class ChartMCP:
    def generate_chart(
        self,
        chart_type: str,  # line/bar/pie/doughnut
        data: dict,
        title: str,
    ) -> str:
        """生成图表并返回 base64 图片"""
        import matplotlib.pyplot as plt
        import io
        import base64

        fig, ax = plt.subplots()

        if chart_type == "line":
            ax.plot(data["labels"], data["values"])
        elif chart_type == "bar":
            ax.bar(data["labels"], data["values"])
        elif chart_type == "pie":
            ax.pie(data["values"], labels=data["labels"])

        ax.set_title(title)

        # 转为 base64
        buf = io.BytesIO()
        fig.savefig(buf, format="png")
        buf.seek(0)
        return base64.b64encode(buf.read()).decode()
```

### 3. PlantUML MCP

```bash
npm install mcp-server-plantuml
```

**功能:**
- UML 图生成
- 架构图
- 部署图

---

## 四、数据库类

### 1. SQLite MCP (官方)

```json
{
  "mcpServers": {
    "sqlite": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-sqlite", "/path/to/db.sqlite"]
    }
  }
}
```

### 2. PostgreSQL MCP

```bash
npm install @anthropic-ai/mcp-server-postgres
```

### 3. MongoDB MCP

```bash
npm install mcp-server-mongodb
```

---

## 五、监控/运维类

### 1. Prometheus MCP (自定义)

```python
from mcp.server import Server
import requests

class PrometheusMCP:
    def __init__(self, url: str):
        self.url = url

    def query(self, promql: str) -> dict:
        """查询 Prometheus 指标"""
        resp = requests.get(
            f"{self.url}/api/v1/query",
            params={"query": promql}
        )
        return resp.json()

    def query_range(
        self,
        promql: str,
        start: str,
        end: str,
        step: str = "1m"
    ) -> dict:
        """范围查询"""
        resp = requests.get(
            f"{self.url}/api/v1/query_range",
            params={
                "query": promql,
                "start": start,
                "end": end,
                "step": step
            }
        )
        return resp.json()
```

### 2. Kubernetes MCP

```bash
npm install mcp-server-kubernetes
```

**功能:**
- 查询 Pod 状态
- 查看日志
- 描述资源
- 执行命令

### 3. Docker MCP

```bash
npm install mcp-server-docker
```

**功能:**
- 容器管理
- 镜像操作
- 日志查看

---

## 六、搜索/查询类

### 1. Google Search MCP

```bash
npm install mcp-server-google-search
```

### 2. DuckDuckGo MCP

```bash
npm install mcp-server-duckduckgo
```

### 3. Exa Search MCP (AI 搜索)

```bash
npm install mcp-server-exa
```

---

## 七、其他实用类

### 1. GitHub MCP (官方)

```bash
npm install @anthropic-ai/mcp-server-github
```

**功能:**
- 仓库管理
- Issue/PR 操作
- 代码搜索
- 文件操作

### 2. Slack MCP

```bash
npm install mcp-server-slack
```

**功能:**
- 发送消息
- 读取频道
- 用户信息

### 3. Memory MCP (记忆)

```bash
npm install @anthropic-ai/mcp-server-memory
```

**功能:**
- 持久化记忆
- 知识图谱存储
- 上下文保持

### 4. Sequential Thinking MCP

```bash
npm install @anthropic-ai/mcp-server-sequential-thinking
```

**功能:**
- 结构化思考
- 步骤推理
- 问题分解

### 5. Time MCP

```bash
npm install @anthropic-ai/mcp-server-time
```

**功能:**
- 获取当前时间
- 时区转换
- 时间计算

---

## 八、推荐集成方案

### 你的项目推荐配置

```json
// .mcp.json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "./logs", "./reports"]
    },
    "playwright": {
      "command": "npx",
      "args": ["-y", "@anthropic-ai/mcp-server-playwright"]
    },
    "sqlite": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-sqlite", "./data/oncall.db"]
    },
    "memory": {
      "command": "npx",
      "args": ["-y", "@anthropic-ai/mcp-server-memory"]
    },
    "time": {
      "command": "npx",
      "args": ["-y", "@anthropic-ai/mcp-server-time"]
    }
  }
}
```

### 优先级排序

| 优先级 | MCP | 用途 |
|--------|-----|------|
| 🔴 P0 | filesystem | 日志文件读取、报告生成 |
| 🔴 P0 | playwright | 监控面板截图、网页内容提取 |
| 🟡 P1 | sqlite | 本地数据存储 |
| 🟡 P1 | memory | 诊断上下文记忆 |
| 🟢 P2 | mermaid | 流程图生成 |
| 🟢 P2 | time | 时间处理 |

---

## 九、自定义 MCP 示例

### 日志分析 MCP

```python
# mcp_servers/log_analyzer.py
from mcp.server import Server
from mcp.types import Tool, TextContent
import re
from pathlib import Path

class LogAnalyzerMCP(Server):
    """日志分析 MCP 服务器"""

    def __init__(self, log_dir: str):
        super().__init__("log-analyzer")
        self.log_dir = Path(log_dir)

    @Tool(
        name="analyze_logs",
        description="分析日志文件，提取错误和警告"
    )
    async def analyze_logs(
        self,
        file_pattern: str = "*.log",
        keywords: list = None,
    ) -> dict:
        """分析日志"""
        keywords = keywords or ["ERROR", "WARN", "exception"]

        results = []
        for log_file in self.log_dir.glob(file_pattern):
            with open(log_file) as f:
                for line_num, line in enumerate(f, 1):
                    if any(kw in line for kw in keywords):
                        results.append({
                            "file": str(log_file),
                            "line": line_num,
                            "content": line.strip(),
                        })

        return {
            "total_matches": len(results),
            "matches": results[:100],  # 限制返回数量
        }

    @Tool(
        name="extract_trace_id",
        description="从日志中提取 trace_id"
    )
    async def extract_trace_id(self, log_content: str) -> list:
        """提取 trace_id"""
        pattern = r'trace[_-]?id[=:]\s*([a-f0-9]+)'
        return list(set(re.findall(pattern, log_content, re.I)))

    @Tool(
        name="generate_report",
        description="生成日志分析报告"
    )
    async def generate_report(self, analysis_result: dict) -> str:
        """生成 Markdown 报告"""
        report = ["# 日志分析报告\n"]
        report.append(f"## 统计\n")
        report.append(f"- 匹配数: {analysis_result['total_matches']}\n")
        report.append(f"\n## 详情\n")

        for match in analysis_result["matches"][:20]:
            report.append(f"- **{match['file']}:{match['line']}**\n")
            report.append(f"  `{match['content']}`\n")

        return "".join(report)
```

### 监控面板截图 MCP

```python
# mcp_servers/dashboard_capture.py
from mcp.server import Server
from mcp.types import Tool
import asyncio

class DashboardCaptureMCP(Server):
    """监控面板截图 MCP"""

    def __init__(self):
        super().__init__("dashboard-capture")
        self.browser = None

    async def init_browser(self):
        from playwright.async_api import async_playwright
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch()

    @Tool(
        name="capture_grafana",
        description="截取 Grafana 监控面板"
    )
    async def capture_grafana(
        self,
        url: str,
        dashboard_id: str,
        output_path: str,
        wait_seconds: int = 5,
    ) -> dict:
        """截取 Grafana 面板"""
        if not self.browser:
            await self.init_browser()

        page = await self.browser.new_page()
        await page.goto(f"{url}/d/{dashboard_id}")
        await page.wait_for_timeout(wait_seconds * 1000)

        await page.screenshot(path=output_path, full_page=True)
        await page.close()

        return {
            "success": True,
            "path": output_path,
            "url": f"{url}/d/{dashboard_id}",
        }

    @Tool(
        name="extract_metrics",
        description="从监控页面提取指标数据"
    )
    async def extract_metrics(self, url: str, selectors: list) -> dict:
        """提取监控指标"""
        if not self.browser:
            await self.init_browser()

        page = await self.browser.new_page()
        await page.goto(url)
        await page.wait_for_load_state("networkidle")

        metrics = {}
        for selector in selectors:
            elements = await page.query_selector_all(selector["selector"])
            values = [await e.inner_text() for e in elements]
            metrics[selector["name"]] = values

        await page.close()
        return metrics
```

---

## 十、安装和使用

### 1. 一键安装

```bash
# 安装所有推荐的 MCP
npm install -g @modelcontextprotocol/server-filesystem \
    @anthropic-ai/mcp-server-playwright \
    @modelcontextprotocol/server-sqlite \
    @anthropic-ai/mcp-server-memory \
    @anthropic-ai/mcp-server-time
```

### 2. Python 项目集成

```python
# 使用 MCP 客户端
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

async def use_mcp():
    server_params = StdioServerParameters(
        command="npx",
        args=["-y", "@modelcontextprotocol/server-filesystem", "./logs"],
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # 调用工具
            result = await session.call_tool(
                "read_file",
                arguments={"path": "error.log"}
            )
            print(result)
```

---

## Sources

- [Awesome MCP Servers](https://mcp-awesome.com/)
- [MCP Directory](https://mcp.directory/awesome-mcp-servers)
- [mcpservers.org](https://mcpservers.org)
- [Anthropic MCP Documentation](https://modelcontextprotocol.io/)

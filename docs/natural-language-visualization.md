# 自然语言可视化方案

> 用户用自然语言描述，系统自动生成图表

## 一、功能场景

```
用户: "帮我画一个新加坡区域最近 24 小时的延迟趋势图"
     ↓
系统: 自动解析 → 查询数据 → 生成图表
     ↓
输出: 📊 延迟趋势折线图
```

## 二、架构设计

```
┌─────────────────────────────────────────────────────────┐
│                    自然语言输入                           │
│  "画一个延迟趋势图，显示最近1小时的数据"                   │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│                  意图解析器 (Intent Parser)              │
│  • 图表类型识别: 折线图/柱状图/饼图                      │
│  • 数据源识别: 延迟/流量/错误率                          │
│  • 时间范围提取: 最近1小时/今天/本周                      │
│  • 过滤条件提取: 区域/服务/PSM                           │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│                  数据查询器 (Data Fetcher)               │
│  • 构建 SQL/PromQL 查询                                  │
│  • 执行查询                                              │
│  • 数据预处理                                            │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│                  图表生成器 (Chart Generator)            │
│  • 自动选择图表类型                                      │
│  • 配置图表样式                                          │
│  • 生成图片/HTML                                         │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│                      输出结果                            │
│  📊 图表 + 📝 数据说明 + 🔍 原始数据                     │
└─────────────────────────────────────────────────────────┘
```

## 三、核心实现

### 1. 意图解析器

```python
from dataclasses import dataclass
from typing import Optional, List
from enum import Enum
import re

class ChartType(Enum):
    LINE = "line"           # 折线图 - 趋势
    BAR = "bar"             # 柱状图 - 对比
    PIE = "pie"             # 饼图 - 占比
    SCATTER = "scatter"     # 散点图 - 分布
    HEATMAP = "heatmap"     # 热力图 - 密度
    GAUGE = "gauge"         # 仪表盘 - 单值
    TABLE = "table"         # 表格 - 详情

@dataclass
class VisualizationIntent:
    """可视化意图"""
    chart_type: ChartType
    metric: str              # 指标: latency, traffic, error_rate
    time_range: str          # 时间范围: 1h, 24h, 7d
    group_by: Optional[str]  # 分组: region, service
    filters: dict            # 过滤条件
    title: Optional[str]     # 图表标题
    raw_query: str           # 原始查询

class VisualizationIntentParser:
    """可视化意图解析器"""

    def __init__(self, llm_client=None):
        self.llm_client = llm_client

        # 关键词映射
        self.chart_keywords = {
            ChartType.LINE: ["趋势", "变化", "走势", "折线", "曲线", "trend", "line"],
            ChartType.BAR: ["对比", "比较", "柱状", "条形", "compare", "bar"],
            ChartType.PIE: ["占比", "比例", "分布", "饼图", "pie", "percentage"],
            ChartType.SCATTER: ["分布", "散点", "scatter"],
            ChartType.HEATMAP: ["热力", "密度", "heatmap"],
            ChartType.GAUGE: ["仪表", "进度", "当前值", "gauge"],
            ChartType.TABLE: ["表格", "列表", "详情", "table"],
        }

        self.metric_keywords = {
            "latency": ["延迟", "延迟", "rtt", "latency", "响应时间"],
            "traffic": ["流量", "吞吐", "qps", "traffic", "throughput"],
            "error_rate": ["错误率", "失败率", "error", "failure"],
            "packet_loss": ["丢包", "loss", "丢包率"],
            "cpu": ["cpu", "处理器", "cpu使用率"],
            "memory": ["内存", "memory", "内存使用率"],
        }

        self.time_keywords = {
            "1h": ["最近1小时", "1小时", "past 1 hour", "last hour"],
            "24h": ["最近24小时", "1天", "今天", "past 24 hours", "today"],
            "7d": ["最近7天", "一周", "本周", "past 7 days", "this week"],
            "30d": ["最近30天", "一个月", "本月", "past 30 days"],
        }

    def parse(self, query: str) -> VisualizationIntent:
        """解析自然语言查询"""
        query_lower = query.lower()

        # 1. 识别图表类型
        chart_type = self._detect_chart_type(query_lower)

        # 2. 识别指标
        metric = self._detect_metric(query_lower)

        # 3. 识别时间范围
        time_range = self._detect_time_range(query_lower)

        # 4. 提取过滤条件
        filters = self._extract_filters(query)

        # 5. 识别分组
        group_by = self._detect_group_by(query_lower)

        # 6. 生成标题
        title = self._generate_title(chart_type, metric, time_range)

        return VisualizationIntent(
            chart_type=chart_type,
            metric=metric,
            time_range=time_range,
            group_by=group_by,
            filters=filters,
            title=title,
            raw_query=query,
        )

    def _detect_chart_type(self, query: str) -> ChartType:
        """检测图表类型"""
        for chart_type, keywords in self.chart_keywords.items():
            for kw in keywords:
                if kw in query:
                    return chart_type

        # 默认: 趋势类用折线图，对比类用柱状图
        if "趋势" in query or "变化" in query:
            return ChartType.LINE
        if "对比" in query or "比较" in query:
            return ChartType.BAR

        return ChartType.LINE  # 默认折线图

    def _detect_metric(self, query: str) -> str:
        """检测指标"""
        for metric, keywords in self.metric_keywords.items():
            for kw in keywords:
                if kw in query:
                    return metric
        return "latency"  # 默认

    def _detect_time_range(self, query: str) -> str:
        """检测时间范围"""
        for time_range, keywords in self.time_keywords.items():
            for kw in keywords:
                if kw in query:
                    return time_range
        return "1h"  # 默认最近1小时

    def _extract_filters(self, query: str) -> dict:
        """提取过滤条件"""
        filters = {}

        # 区域
        region_patterns = [
            r"(新加坡|Singapore)[-_]?(Central)?",
            r"(美国|US)[-_]?(East|West)?",
            r"(北京|Beijing|上海|Shanghai)",
        ]
        for pattern in region_patterns:
            match = re.search(pattern, query, re.I)
            if match:
                filters["region"] = match.group(0)
                break

        # PSM
        psm_match = re.search(r"psm[：:\s]*([a-zA-Z0-9_.-]+)", query, re.I)
        if psm_match:
            filters["psm"] = psm_match.group(1)

        return filters

    def _detect_group_by(self, query: str) -> Optional[str]:
        """检测分组"""
        if "按区域" in query or "by region" in query:
            return "region"
        if "按服务" in query or "by service" in query:
            return "service"
        if "按时间" in query or "by time" in query:
            return "time"
        return None

    def _generate_title(
        self,
        chart_type: ChartType,
        metric: str,
        time_range: str,
    ) -> str:
        """生成标题"""
        metric_names = {
            "latency": "网络延迟",
            "traffic": "网络流量",
            "error_rate": "错误率",
            "packet_loss": "丢包率",
        }
        time_names = {
            "1h": "最近1小时",
            "24h": "最近24小时",
            "7d": "最近7天",
        }

        return f"{metric_names.get(metric, metric)} {time_names.get(time_range, time_range)}趋势图"
```

### 2. 数据查询器

```python
from dataclasses import dataclass
from typing import Dict, Any, Optional
import requests
from datetime import datetime, timedelta

@dataclass
class DataQuery:
    """数据查询"""
    query_type: str          # sql, promql, api
    query_string: str
    params: dict

class DataFetcher:
    """数据查询器"""

    def __init__(
        self,
        prometheus_url: str = "http://localhost:9090",
        database_url: str = None,
    ):
        self.prometheus_url = prometheus_url
        self.database_url = database_url

    def fetch(self, intent: VisualizationIntent) -> Dict[str, Any]:
        """根据意图获取数据"""
        # 构建查询
        if intent.metric in ["latency", "traffic", "error_rate"]:
            return self._fetch_from_prometheus(intent)
        else:
            return self._fetch_from_database(intent)

    def _fetch_from_prometheus(self, intent: VisualizationIntent) -> Dict:
        """从 Prometheus 获取数据"""
        # 构建 PromQL
        promql = self._build_promql(intent)

        # 计算时间范围
        end_time = datetime.now()
        start_time = self._parse_time_range(intent.time_range)

        # 查询
        response = requests.get(
            f"{self.prometheus_url}/api/v1/query_range",
            params={
                "query": promql,
                "start": start_time.timestamp(),
                "end": end_time.timestamp(),
                "step": self._calculate_step(intent.time_range),
            }
        )

        data = response.json()

        # 格式化数据
        return self._format_prometheus_data(data, intent)

    def _build_promql(self, intent: VisualizationIntent) -> str:
        """构建 PromQL 查询"""
        metric_map = {
            "latency": 'histogram_quantile(0.99, rate(http_request_duration_seconds_bucket[5m]))',
            "traffic": 'rate(http_requests_total[5m])',
            "error_rate": 'rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m])',
        }

        promql = metric_map.get(intent.metric, 'up')

        # 添加过滤条件
        if intent.filters:
            labels = []
            for key, value in intent.filters.items():
                labels.append(f'{key}="{value}"')
            if labels:
                promql = promql.replace("{", "{" + ",".join(labels) + ",", 1)

        return promql

    def _format_prometheus_data(
        self,
        raw_data: Dict,
        intent: VisualizationIntent,
    ) -> Dict:
        """格式化 Prometheus 数据"""
        if raw_data.get("status") != "success":
            return {"error": "Query failed"}

        result = raw_data.get("data", {}).get("result", [])

        labels = []
        values = []

        for item in result:
            metric_labels = item.get("metric", {})
            values_data = item.get("values", [])

            # 提取标签
            label = metric_labels.get(intent.group_by, "value") if intent.group_by else "value"
            labels.append(label)

            # 提取值
            for timestamp, value in values_data:
                values.append({
                    "time": datetime.fromtimestamp(timestamp).isoformat(),
                    "value": float(value),
                    "label": label,
                })

        return {
            "labels": labels,
            "values": values,
            "metric": intent.metric,
            "time_range": intent.time_range,
        }

    def _fetch_from_database(self, intent: VisualizationIntent) -> Dict:
        """从数据库获取数据"""
        # 构建 SQL
        sql = self._build_sql(intent)

        # 执行查询
        # ...

        return {}

    def _parse_time_range(self, time_range: str) -> datetime:
        """解析时间范围"""
        ranges = {
            "1h": timedelta(hours=1),
            "24h": timedelta(hours=24),
            "7d": timedelta(days=7),
            "30d": timedelta(days=30),
        }
        delta = ranges.get(time_range, timedelta(hours=1))
        return datetime.now() - delta

    def _calculate_step(self, time_range: str) -> str:
        """计算查询步长"""
        steps = {
            "1h": "1m",
            "24h": "5m",
            "7d": "1h",
            "30d": "6h",
        }
        return steps.get(time_range, "1m")
```

### 3. 图表生成器

```python
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')  # 非交互模式
import io
import base64
from typing import Dict, Any, Optional

class ChartGenerator:
    """图表生成器"""

    def __init__(self, style: str = "seaborn"):
        plt.style.use(style)
        self.figsize = (10, 6)

    def generate(
        self,
        data: Dict[str, Any],
        intent: VisualizationIntent,
        output_format: str = "base64",  # base64, html, file
    ) -> str:
        """生成图表"""
        # 选择图表类型
        if intent.chart_type == ChartType.LINE:
            return self._generate_line(data, intent, output_format)
        elif intent.chart_type == ChartType.BAR:
            return self._generate_bar(data, intent, output_format)
        elif intent.chart_type == ChartType.PIE:
            return self._generate_pie(data, intent, output_format)
        else:
            return self._generate_line(data, intent, output_format)

    def _generate_line(
        self,
        data: Dict,
        intent: VisualizationIntent,
        output_format: str,
    ) -> str:
        """生成折线图"""
        fig, ax = plt.subplots(figsize=self.figsize)

        # 按标签分组
        grouped_data = {}
        for item in data.get("values", []):
            label = item.get("label", "value")
            if label not in grouped_data:
                grouped_data[label] = {"times": [], "values": []}
            grouped_data[label]["times"].append(item["time"])
            grouped_data[label]["values"].append(item["value"])

        # 绘制每条线
        for label, group in grouped_data.items():
            ax.plot(
                range(len(group["times"])),
                group["values"],
                label=label,
                marker='o',
                markersize=3,
            )

        # 配置
        ax.set_title(intent.title or "趋势图")
        ax.set_xlabel("时间")
        ax.set_ylabel(self._get_ylabel(intent.metric))
        ax.legend()
        ax.grid(True, alpha=0.3)

        # x轴标签
        times = list(grouped_data.values())[0]["times"] if grouped_data else []
        step = max(1, len(times) // 10)
        ax.set_xticks(range(0, len(times), step))
        ax.set_xticklabels([times[i][-8:-3] for i in range(0, len(times), step)], rotation=45)

        return self._output_chart(fig, output_format)

    def _generate_bar(
        self,
        data: Dict,
        intent: VisualizationIntent,
        output_format: str,
    ) -> str:
        """生成柱状图"""
        fig, ax = plt.subplots(figsize=self.figsize)

        labels = data.get("labels", [])
        values = [v["value"] for v in data.get("values", [])]

        ax.bar(labels[:20], values[:20])
        ax.set_title(intent.title or "对比图")
        ax.set_ylabel(self._get_ylabel(intent.metric))

        plt.xticks(rotation=45, ha='right')

        return self._output_chart(fig, output_format)

    def _generate_pie(
        self,
        data: Dict,
        intent: VisualizationIntent,
        output_format: str,
    ) -> str:
        """生成饼图"""
        fig, ax = plt.subplots(figsize=(8, 8))

        labels = data.get("labels", [])
        values = [v["value"] for v in data.get("values", [])]

        ax.pie(values[:10], labels=labels[:10], autopct='%1.1f%%')
        ax.set_title(intent.title or "占比图")

        return self._output_chart(fig, output_format)

    def _output_chart(self, fig, output_format: str) -> str:
        """输出图表"""
        if output_format == "base64":
            buf = io.BytesIO()
            fig.savefig(buf, format="png", dpi=100, bbox_inches='tight')
            buf.seek(0)
            plt.close(fig)
            return base64.b64encode(buf.read()).decode()

        elif output_format == "html":
            import mpld3
            html = mpld3.fig_to_html(fig)
            plt.close(fig)
            return html

        else:  # file
            path = f"/tmp/chart_{datetime.now().strftime('%Y%m%d%H%M%S')}.png"
            fig.savefig(path, dpi=100, bbox_inches='tight')
            plt.close(fig)
            return path

    def _get_ylabel(self, metric: str) -> str:
        """获取 Y 轴标签"""
        labels = {
            "latency": "延迟 (ms)",
            "traffic": "请求量 (QPS)",
            "error_rate": "错误率 (%)",
            "packet_loss": "丢包率 (%)",
        }
        return labels.get(metric, metric)
```

### 4. 自然语言可视化服务

```python
from dataclasses import dataclass

@dataclass
class VisualizationResult:
    """可视化结果"""
    success: bool
    chart_base64: Optional[str] = None
    chart_html: Optional[str] = None
    title: str = ""
    description: str = ""
    data_summary: dict = None
    error: Optional[str] = None

class NaturalLanguageVisualization:
    """自然语言可视化服务"""

    def __init__(
        self,
        prometheus_url: str = "http://localhost:9090",
    ):
        self.intent_parser = VisualizationIntentParser()
        self.data_fetcher = DataFetcher(prometheus_url=prometheus_url)
        self.chart_generator = ChartGenerator()

    async def visualize(self, query: str) -> VisualizationResult:
        """
        从自然语言生成可视化

        Args:
            query: 自然语言查询，如 "画一个延迟趋势图"

        Returns:
            可视化结果
        """
        try:
            # 1. 解析意图
            intent = self.intent_parser.parse(query)

            # 2. 获取数据
            data = self.data_fetcher.fetch(intent)

            if "error" in data:
                return VisualizationResult(
                    success=False,
                    error=data["error"],
                )

            # 3. 生成图表
            chart_base64 = self.chart_generator.generate(
                data=data,
                intent=intent,
                output_format="base64",
            )

            # 4. 生成描述
            description = self._generate_description(intent, data)

            return VisualizationResult(
                success=True,
                chart_base64=chart_base64,
                title=intent.title,
                description=description,
                data_summary={
                    "data_points": len(data.get("values", [])),
                    "time_range": intent.time_range,
                    "metric": intent.metric,
                },
            )

        except Exception as e:
            return VisualizationResult(
                success=False,
                error=str(e),
            )

    def _generate_description(
        self,
        intent: VisualizationIntent,
        data: Dict,
    ) -> str:
        """生成图表描述"""
        values = data.get("values", [])
        if not values:
            return "无数据"

        numeric_values = [v["value"] for v in values]

        return f"""
图表说明:
- 指标: {intent.metric}
- 时间范围: {intent.time_range}
- 数据点数: {len(values)}
- 最大值: {max(numeric_values):.2f}
- 最小值: {min(numeric_values):.2f}
- 平均值: {sum(numeric_values)/len(numeric_values):.2f}
        """.strip()


# 使用示例
async def main():
    service = NaturalLanguageVisualization(
        prometheus_url="http://localhost:9090"
    )

    # 自然语言查询
    queries = [
        "画一个最近24小时的延迟趋势图",
        "帮我生成一个各区域流量对比的柱状图",
        "显示错误率的占比饼图",
    ]

    for query in queries:
        result = await service.visualize(query)
        if result.success:
            print(f"✅ {result.title}")
            print(f"   数据点: {result.data_summary['data_points']}")
        else:
            print(f"❌ 错误: {result.error}")
```

## 四、支持的查询示例

| 查询 | 解析结果 |
|------|---------|
| "画一个延迟趋势图" | 折线图, latency, 1h |
| "最近24小时流量变化" | 折线图, traffic, 24h |
| "各区域错误率对比" | 柱状图, error_rate, 按区域分组 |
| "新加坡延迟分布饼图" | 饼图, latency, region=Singapore |
| "最近一周的丢包率趋势" | 折线图, packet_loss, 7d |

## 五、集成到项目

```python
# 在 Agent 中使用
from src.agents import AgentContext, AgentResult

class VisualizationAgent:
    """可视化 Agent"""

    def __init__(self):
        self.viz_service = NaturalLanguageVisualization()

    async def execute(self, context: AgentContext) -> AgentResult:
        result = await self.viz_service.visualize(context.query)

        return AgentResult(
            agent_name="VisualizationAgent",
            success=result.success,
            data={
                "chart_base64": result.chart_base64,
                "title": result.title,
                "description": result.description,
            },
            error=result.error,
        )
```

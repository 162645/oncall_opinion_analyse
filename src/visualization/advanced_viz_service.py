"""
高级可视化服务
整合复杂意图解析、数据获取、图表生成
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import asyncio

from .advanced_service import (
    AdvancedVisualizationParser,
    ComplexVisualizationIntent,
    ComplexVisualizationResult,
    DataSeries,
    ChartType,
)
from .advanced_data_fetcher import AdvancedDataFetcher
from .advanced_chart_generator import AdvancedChartGenerator


class AdvancedVisualizationService:
    """
    高级可视化服务

    支持复杂的可视化需求:
    - 多指标组合对比
    - 多数据源关联查询
    - 复杂筛选和分组
    - 双Y轴图表
    - 散点图和相关性分析
    - 热力图

    使用示例:
    ```python
    service = AdvancedVisualizationService()

    # 复杂查询示例
    queries = [
        "对比新加坡和美国区域的延迟趋势",
        "显示最近24小时CPU和内存使用率的组合图",
        "按服务分组，显示P99延迟和错误率的散点图",
        "最近7天每日订单量与延迟的关系",
    ]

    for query in queries:
        result = await service.visualize(query)
        if result.success:
            print(f"图表已生成: {result.title}")
    ```
    """

    def __init__(
        self,
        prometheus_url: str = "http://localhost:9090",
        clickhouse_url: Optional[str] = None,
        output_format: str = "base64",
    ):
        self.parser = AdvancedVisualizationParser()
        self.data_fetcher = AdvancedDataFetcher(
            prometheus_url=prometheus_url,
            clickhouse_url=clickhouse_url,
        )
        self.chart_generator = AdvancedChartGenerator()
        self.output_format = output_format

    async def visualize(self, query: str) -> ComplexVisualizationResult:
        """
        从自然语言生成复杂可视化

        Args:
            query: 自然语言查询

        Returns:
            ComplexVisualizationResult
        """
        try:
            # 1. 解析复杂意图
            intent = self.parser.parse(query)

            # 2. 获取数据
            data_series = await self.data_fetcher.fetch(intent)

            if not data_series or all(len(s.values) == 0 for s in data_series):
                return ComplexVisualizationResult(
                    success=False,
                    error="未找到数据",
                    intent=intent,
                )

            # 3. 生成图表
            chart_output = self.chart_generator.generate(
                data_series=data_series,
                intent=intent,
                output_format=self.output_format,
            )

            # 4. 生成描述
            description = self._generate_description(intent, data_series)

            # 5. 构建结果
            result = ComplexVisualizationResult(
                success=True,
                title=intent.title,
                description=description,
                intent=intent,
                data_series=data_series,
            )

            if self.output_format == "base64":
                result.chart_base64 = chart_output
            elif self.output_format == "html":
                result.chart_html = chart_output
            else:
                result.chart_base64 = chart_output

            return result

        except Exception as e:
            return ComplexVisualizationResult(
                success=False,
                error=str(e),
            )

    def _generate_description(
        self,
        intent: ComplexVisualizationIntent,
        data_series: List[DataSeries],
    ) -> str:
        """生成图表描述"""
        lines = []

        lines.append(f"📊 **{intent.title}**")
        lines.append("")

        # 图表类型说明
        chart_type_names = {
            ChartType.LINE: "折线图（趋势展示）",
            ChartType.BAR: "柱状图（对比分析）",
            ChartType.PIE: "饼图（占比分布）",
            ChartType.SCATTER: "散点图（相关性分析）",
            ChartType.HEATMAP: "热力图（密度分布）",
            ChartType.COMBO: "组合图（多指标展示）",
            ChartType.AREA: "面积图（趋势展示）",
        }
        lines.append(f"- 图表类型: {chart_type_names.get(intent.chart_type, '其他')}")

        # 指标说明
        if intent.metrics:
            metric_names = [m.alias or m.name for m in intent.metrics]
            lines.append(f"- 分析指标: {', '.join(metric_names)}")

        # 时间范围
        time_names = {
            "15m": "最近15分钟",
            "1h": "最近1小时",
            "6h": "最近6小时",
            "24h": "最近24小时",
            "7d": "最近7天",
            "30d": "最近30天",
        }
        lines.append(f"- 时间范围: {time_names.get(intent.time_range, intent.time_range)}")

        # 数据统计
        for series in data_series[:3]:
            values = [v.get('value', 0) for v in series.values if v.get('value') is not None]
            if values:
                lines.append(f"- {series.name}: 最大 {max(values):.2f}, 最小 {min(values):.2f}, 平均 {sum(values)/len(values):.2f}")

        # 筛选条件
        if intent.filters:
            filter_str = ", ".join([f"{k}={v}" for k, v in intent.filters.items()])
            lines.append(f"- 筛选条件: {filter_str}")

        # 分组信息
        if intent.group_by:
            lines.append(f"- 分组维度: {', '.join(intent.group_by)}")

        # 置信度
        lines.append(f"- 解析置信度: {intent.confidence:.0%}")

        return "\n".join(lines)

    def get_supported_queries(self) -> List[Dict[str, str]]:
        """获取支持的复杂查询示例"""
        return self.parser.get_supported_complex_queries()


# 同步版本
def visualize_advanced_sync(query: str, **kwargs) -> ComplexVisualizationResult:
    """
    同步可视化函数

    Args:
        query: 自然语言查询

    Returns:
        ComplexVisualizationResult
    """
    async def _visualize():
        service = AdvancedVisualizationService(**kwargs)
        return await service.visualize(query)

    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(_visualize())

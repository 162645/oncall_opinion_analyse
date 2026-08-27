"""
自然语言可视化服务
整合意图解析、数据查询、图表生成
"""

from dataclasses import dataclass
from typing import Any, Dict, Optional

from .intent_parser import VisualizationIntentParser, VisualizationIntent
from .data_fetcher import DataFetcher
from .chart_generator import ChartGenerator


@dataclass
class VisualizationResult:
    """可视化结果"""
    success: bool
    chart_base64: Optional[str] = None
    chart_html: Optional[str] = None
    chart_path: Optional[str] = None
    title: str = ""
    description: str = ""
    intent: Optional[VisualizationIntent] = None
    data_summary: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class NaturalLanguageVisualization:
    """
    自然语言可视化服务

    从自然语言描述生成图表

    使用示例:
    ```python
    service = NaturalLanguageVisualization()
    result = await service.visualize("画一个最近24小时的延迟趋势图")

    if result.success:
        print(result.chart_base64)  # base64 编码的图片
    ```
    """

    def __init__(
        self,
        prometheus_url: str = "http://localhost:9090",
        output_format: str = "base64",
    ):
        self.intent_parser = VisualizationIntentParser()
        self.data_fetcher = DataFetcher(prometheus_url=prometheus_url)
        self.chart_generator = ChartGenerator()
        self.output_format = output_format

    async def visualize(self, query: str) -> VisualizationResult:
        """
        从自然语言生成可视化

        Args:
            query: 自然语言查询，如 "画一个延迟趋势图"

        Returns:
            VisualizationResult: 可视化结果
        """
        try:
            # 1. 解析意图
            intent = self.intent_parser.parse(query)

            # 2. 获取数据
            data = self.data_fetcher.fetch(intent)

            if not data.get("values"):
                return VisualizationResult(
                    success=False,
                    error="未找到数据",
                    intent=intent,
                )

            # 3. 生成图表
            chart_output = self.chart_generator.generate(
                data=data,
                intent=intent,
                output_format=self.output_format,
            )

            # 4. 生成描述
            description = self._generate_description(intent, data)

            # 5. 构建结果
            result = VisualizationResult(
                success=True,
                title=intent.title,
                description=description,
                intent=intent,
                data_summary={
                    "data_points": len(data.get("values", [])),
                    "time_range": intent.time_range,
                    "metric": intent.metric,
                    "chart_type": intent.chart_type.value,
                },
            )

            if self.output_format == "base64":
                result.chart_base64 = chart_output
            elif self.output_format == "html":
                result.chart_html = chart_output
            else:
                result.chart_path = chart_output

            return result

        except Exception as e:
            return VisualizationResult(
                success=False,
                error=str(e),
            )

    def _generate_description(
        self,
        intent: VisualizationIntent,
        data: Dict[str, Any],
    ) -> str:
        """生成图表描述"""
        values = data.get("values", [])
        if not values:
            return "无数据"

        numeric_values = [v.get("value", 0) for v in values]

        description = f"""图表说明:
- 指标: {intent.metric}
- 时间范围: {intent.time_range}
- 图表类型: {intent.chart_type.value}
- 数据点数: {len(values)}
- 最大值: {max(numeric_values):.2f}
- 最小值: {min(numeric_values):.2f}
- 平均值: {sum(numeric_values)/len(numeric_values):.2f}"""

        if intent.filters:
            description += f"\n- 过滤条件: {intent.filters}"

        return description

    def get_supported_queries(self) -> list:
        """获取支持的查询示例"""
        return self.intent_parser.get_supported_queries()


# 同步版本（方便非异步环境使用）
def visualize_sync(query: str, **kwargs) -> VisualizationResult:
    """
    同步可视化函数

    Args:
        query: 自然语言查询

    Returns:
        VisualizationResult
    """
    import asyncio

    async def _visualize():
        service = NaturalLanguageVisualization(**kwargs)
        return await service.visualize(query)

    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(_visualize())

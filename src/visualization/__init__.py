"""
自然语言可视化模块
实现从自然语言描述生成图表

支持:
- 简单可视化: 单指标趋势图、对比图等
- 高级可视化: 多指标组合、多数据源、散点图、热力图等
"""

from .intent_parser import (
    VisualizationIntentParser,
    VisualizationIntent,
    ChartType,
)
from .data_fetcher import DataFetcher
from .chart_generator import ChartGenerator
from .service import NaturalLanguageVisualization, VisualizationResult

# 高级可视化模块
from .advanced_service import (
    AdvancedVisualizationParser,
    ComplexVisualizationIntent,
    ComplexVisualizationResult,
    MetricSpec,
    AxisSpec,
    DataSeries,
    DataSource,
    AggregationType,
)
from .advanced_data_fetcher import AdvancedDataFetcher
from .advanced_chart_generator import AdvancedChartGenerator
from .advanced_viz_service import AdvancedVisualizationService

__all__ = [
    # 简单可视化
    "VisualizationIntentParser",
    "VisualizationIntent",
    "ChartType",
    "DataFetcher",
    "ChartGenerator",
    "NaturalLanguageVisualization",
    "VisualizationResult",
    # 高级可视化
    "AdvancedVisualizationParser",
    "AdvancedVisualizationService",
    "ComplexVisualizationIntent",
    "ComplexVisualizationResult",
    "MetricSpec",
    "AxisSpec",
    "DataSeries",
    "DataSource",
    "AggregationType",
    "AdvancedDataFetcher",
    "AdvancedChartGenerator",
]

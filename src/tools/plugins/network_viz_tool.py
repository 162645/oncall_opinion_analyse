"""
网络可视化工具
供 Agent 调用的 Traceroute 和 Ping 数据可视化工具
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import logging
import io
import base64

from src.tools.base import BaseTool, ToolMetadata, ToolResult, ToolCategory
from src.clickhouse import get_clickhouse_client
from src.clickhouse.analyzer import PingAnalyzer, TracerouteAnalyzer, AnalysisConfig

logger = logging.getLogger(__name__)


def get_chinese_font():
    """获取支持中文的字体"""
    import matplotlib.font_manager as fm

    # 优先使用的字体列表
    preferred_fonts = [
        'PingFang HK',      # macOS
        'PingFang SC',      # macOS
        'STHeiti',          # macOS
        'Songti SC',        # macOS
        'Heiti TC',         # macOS
        'Arial Unicode MS', # 通用
        'SimHei',           # Windows
        'Microsoft YaHei',  # Windows
        'WenQuanYi Micro Hei',  # Linux
    ]

    # 获取系统所有可用字体
    available_fonts = set([f.name for f in fm.fontManager.ttflist])

    # 找到第一个可用的中文字体
    for font in preferred_fonts:
        if font in available_fonts:
            return font

    # 如果找不到，返回默认字体
    return 'DejaVu Sans'


class NetworkVisualizationTool(BaseTool):
    """
    网络可视化工具

    提供 Traceroute 和 Ping 数据的可视化分析功能
    """

    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="network_viz",
            description="网络测量数据可视化工具，支持 Traceroute 路径分析、Ping 时序分析、末端节点分析等",
            category=ToolCategory.NETWORK,
            parameters={
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": [
                            "ping_overall",
                            "ping_trend",
                            "ping_by_asn",
                            "ping_by_asgeo",
                            "ping_by_datacenter",
                            "trace_terminal_analysis",
                            "trace_path_analysis",
                            "trace_path_detail",
                            "trace_path_ping_trend",
                            "region_overview",
                        ],
                        "description": "分析操作类型",
                    },
                    "region": {
                        "type": "string",
                        "description": "地区名称，如 UKRAINE、RUSSIA",
                    },
                    "path": {
                        "type": "string",
                        "description": "路径字符串（用于 path_detail 和 path_ping_trend）",
                    },
                    "path_type": {
                        "type": "string",
                        "enum": ["as", "asgeo"],
                        "description": "路径类型",
                        "default": "as",
                    },
                    "interval": {
                        "type": "string",
                        "enum": ["minute", "hour", "day"],
                        "description": "时间间隔（用于趋势分析）",
                        "default": "hour",
                    },
                    "start_time": {
                        "type": "string",
                        "description": "开始时间 (ISO 格式)",
                    },
                    "end_time": {
                        "type": "string",
                        "description": "结束时间 (ISO 格式)",
                    },
                    "top_n": {
                        "type": "integer",
                        "description": "返回数量限制",
                        "default": 50,
                    },
                    "filters": {
                        "type": "object",
                        "description": "额外筛选条件",
                    },
                },
                "required": ["action", "region"],
            },
            returns={
                "type": "object",
                "description": "可视化数据，包含结构化数据和图表图像（base64）",
            },
            examples=[
                {
                    "action": "ping_overall",
                    "region": "UKRAINE",
                },
                {
                    "action": "trace_terminal_analysis",
                    "region": "UKRAINE",
                    "path_type": "as",
                },
            ],
            tags=["network", "visualization", "traceroute", "ping", "analysis"],
        )

    async def execute(self, **params) -> ToolResult:
        """执行可视化分析"""
        try:
            action = params.get("action")
            region = params.get("region")

            if not action or not region:
                return ToolResult(
                    success=False,
                    error="缺少必需参数: action 或 region",
                )

            # 解析时间范围（用户指定的才使用）
            start_time = self._parse_time(params.get("start_time"))
            end_time = self._parse_time(params.get("end_time"))

            # 不设置默认时间范围，让 analyzer 使用全部数据
            # 因为测试数据可能是历史数据

            client = get_clickhouse_client()

            # 根据操作类型分发
            if action.startswith("ping_"):
                return await self._handle_ping_action(
                    client, action, region, start_time, end_time, params
                )
            elif action.startswith("trace_"):
                return await self._handle_trace_action(
                    client, action, region, start_time, end_time, params
                )
            elif action == "region_overview":
                return await self._handle_region_overview(
                    client, region, start_time, end_time
                )
            else:
                return ToolResult(
                    success=False,
                    error=f"未知操作类型: {action}",
                )

        except Exception as e:
            logger.error(f"NetworkVisualizationTool 执行失败: {e}")
            return ToolResult(
                success=False,
                error=str(e),
            )

    def _parse_time(self, time_str: Optional[str]) -> Optional[datetime]:
        """解析时间字符串"""
        if not time_str:
            return None
        try:
            return datetime.fromisoformat(time_str.replace("Z", "+00:00"))
        except ValueError:
            return None

    def _generate_bar_chart(self, labels: List[str], values: List[float], title: str) -> Optional[str]:
        """生成美观的柱状图并返回 base64"""
        try:
            import matplotlib
            matplotlib.use('Agg')
            import matplotlib.pyplot as plt
            import numpy as np

            # 设置中文字体
            plt.rcParams['font.sans-serif'] = [get_chinese_font(), 'DejaVu Sans']
            plt.rcParams['axes.unicode_minus'] = False

            # 创建图形，设置样式
            fig, ax = plt.subplots(figsize=(14, 7))
            fig.patch.set_facecolor('#fafafa')
            ax.set_facecolor('#fafafa')

            # 截断过长的标签
            labels = [str(l)[:30] + '...' if len(str(l)) > 30 else str(l) for l in labels]

            # 使用渐变色
            colors = plt.cm.Blues(np.linspace(0.4, 0.9, len(labels)))

            # 绘制柱状图
            x = np.arange(len(labels))
            bars = ax.bar(x, values, color=colors, edgecolor='white', linewidth=1.5, width=0.7)

            # 高亮最大值
            max_idx = values.index(max(values))
            bars[max_idx].set_color('#ff4d4f')
            bars[max_idx].set_edgecolor('#ff4d4f')

            # 高亮最小值（如果查询包含"最低"）
            min_idx = values.index(min(values))
            bars[min_idx].set_color('#52c41a')
            bars[min_idx].set_edgecolor('#52c41a')

            # 在柱子上显示值
            for i, (bar, val) in enumerate(zip(bars, values)):
                color = '#333'
                if i == max_idx:
                    color = '#ff4d4f'
                elif i == min_idx:
                    color = '#52c41a'
                ax.text(
                    bar.get_x() + bar.get_width() / 2,
                    bar.get_height() + max(values) * 0.02,
                    f'{val:,.0f}',
                    ha='center',
                    va='bottom',
                    fontsize=10,
                    fontweight='bold' if i in [max_idx, min_idx] else 'normal',
                    color=color,
                )

            # 设置标题和标签
            ax.set_title(title, fontsize=16, fontweight='bold', pad=20, color='#333')
            ax.set_xticks(x)
            ax.set_xticklabels(labels, rotation=35, ha='right', fontsize=10, color='#666')

            # 美化网格
            ax.yaxis.grid(True, linestyle='--', alpha=0.5, color='#ccc')
            ax.xaxis.grid(False)
            ax.set_axisbelow(True)

            # 移除边框
            for spine in ['top', 'right']:
                ax.spines[spine].set_visible(False)
            for spine in ['bottom', 'left']:
                ax.spines[spine].set_color('#ddd')

            # 添加图例说明
            legend_elements = [
                plt.Rectangle((0,0),1,1, facecolor='#52c41a', edgecolor='white', label='最低值'),
                plt.Rectangle((0,0),1,1, facecolor='#ff4d4f', edgecolor='white', label='最高值'),
            ]
            ax.legend(handles=legend_elements, loc='upper right', framealpha=0.9)

            plt.tight_layout()

            # 转换为 base64
            buf = io.BytesIO()
            fig.savefig(buf, format="png", dpi=120, bbox_inches='tight', facecolor=fig.get_facecolor())
            buf.seek(0)
            plt.close(fig)

            return base64.b64encode(buf.read()).decode()

        except ImportError:
            logger.warning("matplotlib not available, skipping chart generation")
            return None
        except Exception as e:
            logger.error(f"Failed to generate chart: {e}")
            return None

    def _generate_line_chart(self, times: List[str], series: List[Dict], title: str) -> Optional[str]:
        """生成折线图并返回 base64"""
        try:
            import matplotlib
            matplotlib.use('Agg')
            import matplotlib.pyplot as plt

            # 设置中文字体
            plt.rcParams['font.sans-serif'] = [get_chinese_font(), 'DejaVu Sans']
            plt.rcParams['axes.unicode_minus'] = False

            fig, ax = plt.subplots(figsize=(12, 5))

            colors = ['#1890ff', '#52c41a', '#faad14', '#f5222d', '#722ed1']

            for idx, s in enumerate(series):
                name = s.get('name', f'Series {idx+1}')
                data = s.get('data', [])
                color = colors[idx % len(colors)]

                ax.plot(range(len(data)), data, label=name, color=color, linewidth=2, marker='o', markersize=3)

            ax.set_title(title, fontsize=14, fontweight='bold')
            ax.set_xlabel('时间', fontsize=11)
            ax.set_ylabel('RTT (ms)', fontsize=11)
            ax.legend(loc='best')
            ax.grid(True, alpha=0.3)

            # 设置 X 轴标签
            if times:
                step = max(1, len(times) // 8)
                ax.set_xticks(range(0, len(times), step))
                ax.set_xticklabels([times[i][:10] if i < len(times) else '' for i in range(0, len(times), step)], rotation=45, ha='right', fontsize=8)

            plt.tight_layout()

            # 转换为 base64
            buf = io.BytesIO()
            fig.savefig(buf, format="png", dpi=100, bbox_inches='tight')
            buf.seek(0)
            plt.close(fig)

            return base64.b64encode(buf.read()).decode()

        except ImportError:
            logger.warning("matplotlib not available, skipping chart generation")
            return None
        except Exception as e:
            logger.error(f"Failed to generate chart: {e}")
            return None

    async def _handle_ping_action(
        self,
        client,
        action: str,
        region: str,
        start_time: datetime,
        end_time: datetime,
        params: dict,
    ) -> ToolResult:
        """处理 Ping 相关操作"""
        analyzer = PingAnalyzer(client)
        config = AnalysisConfig()
        filters = params.get("filters", {})

        if action == "ping_overall":
            result = analyzer.analyze_overall(
                region=region,
                start_time=start_time,
                end_time=end_time,
                config=config,
                **filters
            )
            return self._build_result(
                action=action,
                region=region,
                data=result,
                title=f"{region} 地区 Ping 整体统计",
                description="包含均值、中位数、分位数、标准差等统计指标",
            )

        elif action == "ping_trend":
            interval = params.get("interval", "hour")
            result = analyzer.analyze_time_trend(
                region=region,
                start_time=start_time,
                end_time=end_time,
                interval=interval,
                config=config,
                **filters
            )

            # 生成趋势图
            chart_base64 = None
            if isinstance(result, dict) and result.get("time_series"):
                time_series = result["time_series"]
                times = [item.get("time", "") for item in time_series]
                series = [{
                    "name": "mean_rtt",
                    "data": [item.get("mean_rtt") or item.get("mean") for item in time_series]
                }]
                chart_base64 = self._generate_line_chart(times, series, f"{region} Ping RTT 趋势")

            return self._build_result(
                action=action,
                region=region,
                data=result,
                title=f"{region} 地区 Ping 时序趋势",
                description=f"按 {interval} 聚合的 RTT 趋势数据",
                chart_base64=chart_base64,
            )

        elif action == "ping_by_asn":
            top_n = params.get("top_n", 50)
            result = analyzer.analyze_by_asn(
                region=region,
                start_time=start_time,
                end_time=end_time,
                top_n=top_n,
                config=config,
                **filters
            )
            return self._build_result(
                action=action,
                region=region,
                data=result,
                title=f"{region} 地区 AS 维度分析",
                description=f"Top {top_n} AS 的 Ping 统计数据",
            )

        elif action == "ping_by_asgeo":
            top_n = params.get("top_n", 50)
            result = analyzer.analyze_by_asgeo(
                region=region,
                start_time=start_time,
                end_time=end_time,
                top_n=top_n,
                config=config,
                **filters
            )

            # 生成柱状图 - 按平均 RTT 排序
            chart_base64 = None
            if isinstance(result, list) and len(result) > 0:
                # 按 mean_rtt 升序排序（最低延迟在前）
                sorted_result = sorted(result, key=lambda x: x.get("mean_rtt", 0) or 0)
                labels = [item.get("asgeo", "N/A")[:25] for item in sorted_result[:15]]
                values = [item.get("mean_rtt", 0) or 0 for item in sorted_result[:15]]
                chart_base64 = self._generate_bar_chart(labels, values, f"{region} ASGeo 平均 RTT 排名 (最低→最高)")

            return self._build_result(
                action=action,
                region=region,
                data=result,
                title=f"{region} 地区 ASGeo 延迟分析",
                description=f"Top {top_n} ASGeo 的 Ping 统计数据（按平均 RTT 排序）",
                chart_base64=chart_base64,
            )

        elif action == "ping_by_datacenter":
            top_n = params.get("top_n", 50)
            result = analyzer.analyze_by_data_center(
                region=region,
                start_time=start_time,
                end_time=end_time,
                top_n=top_n,
                config=config,
                **filters
            )
            return self._build_result(
                action=action,
                region=region,
                data=result,
                title=f"{region} 地区数据中心分析",
                description=f"Top {top_n} 数据中心的 Ping 统计数据",
            )

        else:
            return ToolResult(
                success=False,
                error=f"未知的 Ping 操作: {action}",
            )

    async def _handle_trace_action(
        self,
        client,
        action: str,
        region: str,
        start_time: datetime,
        end_time: datetime,
        params: dict,
    ) -> ToolResult:
        """处理 Traceroute 相关操作"""
        analyzer = TracerouteAnalyzer(client)
        path_type = params.get("path_type", "as")
        filters = params.get("filters", {})

        if action == "trace_terminal_analysis":
            top_n = params.get("top_n", 50)
            result = analyzer.analyze_terminal_nodes(
                region=region,
                start_time=start_time,
                end_time=end_time,
                terminal_type=path_type,
                top_n=top_n,
                **filters
            )

            # 生成柱状图 - result 是 dict，包含 terminals 列表
            chart_base64 = None
            terminals = result.get("terminals", []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
            if terminals and len(terminals) > 0:
                labels = [item.get("terminal", "N/A") for item in terminals[:15]]
                values = [item.get("trace_count", 0) for item in terminals[:15]]
                chart_base64 = self._generate_bar_chart(labels, values, f"{region} 末端节点分布")

            return self._build_result(
                action=action,
                region=region,
                data=result,
                title=f"{region} 地区末端节点分析",
                description=f"Top {top_n} 末端 {path_type.upper()} 节点统计",
                chart_base64=chart_base64,
            )

        elif action == "trace_path_analysis":
            top_n = params.get("top_n", 50)
            result = analyzer.analyze_paths_with_filter(
                region=region,
                start_time=start_time,
                end_time=end_time,
                path_type=path_type,
                top_n=top_n,
                **filters
            )

            # 生成柱状图 - result 是 dict，包含 paths 列表
            chart_base64 = None
            paths = result.get("paths", []) if isinstance(result, dict) else (result if isinstance(result, list) else [])
            if paths and len(paths) > 0:
                labels = [item.get("path", "N/A") for item in paths[:15]]
                values = [item.get("occurrence_count", 0) for item in paths[:15]]
                chart_base64 = self._generate_bar_chart(labels, values, f"{region} 路径分布")

            return self._build_result(
                action=action,
                region=region,
                data=result,
                title=f"{region} 地区路径分析",
                description=f"Top {top_n} {path_type.upper()} 路径统计",
                chart_base64=chart_base64,
            )

        elif action == "trace_path_detail":
            path = params.get("path")
            if not path:
                return ToolResult(
                    success=False,
                    error="trace_path_detail 需要 path 参数",
                )
            result = analyzer.get_path_detail(
                region=region,
                path=path,
                path_type=path_type,
                start_time=start_time,
                end_time=end_time,
            )
            return self._build_result(
                action=action,
                region=region,
                data=result,
                title=f"路径详情: {path[:50]}...",
                description=f"路径关联的末端节点和 Prefix24 信息",
            )

        elif action == "trace_path_ping_trend":
            path = params.get("path")
            if not path:
                return ToolResult(
                    success=False,
                    error="trace_path_ping_trend 需要 path 参数",
                )
            interval = params.get("interval", "hour")
            result = analyzer.analyze_path_ping_trend(
                region=region,
                path=path,
                path_type=path_type,
                interval=interval,
                start_time=start_time,
                end_time=end_time,
            )
            return self._build_result(
                action=action,
                region=region,
                data=result,
                title=f"路径 Ping 时序分析",
                description=f"路径关联的 Ping 数据时序趋势",
                chart_data=self._build_trend_chart(result, "路径 RTT 趋势"),
            )

        else:
            return ToolResult(
                success=False,
                error=f"未知的 Traceroute 操作: {action}",
            )

    async def _handle_region_overview(
        self,
        client,
        region: str,
        start_time: datetime,
        end_time: datetime,
    ) -> ToolResult:
        """处理地区概览"""
        ping_analyzer = PingAnalyzer(client)
        trace_analyzer = TracerouteAnalyzer(client)
        config = AnalysisConfig()

        # 获取 Ping 整体统计
        ping_stats = ping_analyzer.analyze_overall(
            region=region,
            start_time=start_time,
            end_time=end_time,
            config=config,
        )

        # 获取 Traceroute 路径统计
        trace_stats = trace_analyzer.analyze_path_statistics(
            region=region,
            start_time=start_time,
            end_time=end_time,
            top_n=10,
        )

        # 获取数据源信息
        try:
            data_source = trace_analyzer.get_data_source_info(region)
        except Exception:
            data_source = {}

        result = {
            "region": region,
            "ping_stats": ping_stats,
            "trace_stats": trace_stats,
            "data_source": data_source,
            "time_range": {
                "start": start_time.isoformat() if start_time else None,
                "end": end_time.isoformat() if end_time else None,
            },
        }

        return self._build_result(
            action="region_overview",
            region=region,
            data=result,
            title=f"{region} 地区网络概览",
            description="Ping 统计、路径统计和数据源信息",
        )

    def _build_result(
        self,
        action: str,
        region: str,
        data: Any,
        title: str,
        description: str,
        chart_data: Optional[Dict] = None,
        chart_base64: Optional[str] = None,
    ) -> ToolResult:
        """构建返回结果"""
        result_data = {
            "action": action,
            "region": region,
            "title": title,
            "description": description,
            "data": data,
            "timestamp": datetime.utcnow().isoformat(),
        }

        if chart_data:
            result_data["chart_data"] = chart_data

        if chart_base64:
            result_data["chart_base64"] = chart_base64

        return ToolResult(
            success=True,
            data=result_data,
            metadata={
                "action": action,
                "region": region,
                "has_chart": chart_base64 is not None or chart_data is not None,
            },
        )


# 工具注册函数
def register_network_viz_tools(registry):
    """注册网络可视化工具"""
    registry.register(NetworkVisualizationTool())

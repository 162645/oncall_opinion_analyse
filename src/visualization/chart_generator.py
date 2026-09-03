"""
图表生成器
根据数据和意图生成图表
"""

import io
import base64
from typing import Any, Dict, Optional, TYPE_CHECKING
import platform

if TYPE_CHECKING:
    from .intent_parser import VisualizationIntent, ChartType


def get_chinese_font():
    """获取支持中文的字体"""
    system = platform.system()

    if system == 'Darwin':  # macOS
        return 'PingFang SC'
    elif system == 'Windows':
        return 'Microsoft YaHei'
    else:  # Linux
        return 'WenQuanYi Micro Hei'


class ChartGenerator:
    """
    图表生成器

    支持生成:
    - 折线图
    - 柱状图
    - 饼图
    - 面积图
    """

    def __init__(self, style: str = "seaborn-v2_whitegrid"):
        self.style = style
        self.figsize = (10, 6)
        self._matplotlib_available = None

    def _check_matplotlib(self) -> bool:
        """检查 matplotlib 是否可用"""
        if self._matplotlib_available is None:
            try:
                import matplotlib
                matplotlib.use('Agg')
                self._matplotlib_available = True
            except ImportError:
                self._matplotlib_available = False
        return self._matplotlib_available

    def generate(
        self,
        data: Dict[str, Any],
        intent: "VisualizationIntent",
        output_format: str = "base64",
    ) -> str:
        """
        生成图表

        Args:
            data: 数据字典
            intent: 可视化意图
            output_format: 输出格式 (base64, html, file)

        Returns:
            图表数据（base64 或文件路径）
        """
        if not self._check_matplotlib():
            return self._generate_text_chart(data, intent)

        import matplotlib.pyplot as plt
        import matplotlib.dates as mdates
        from datetime import datetime

        # 设置中文字体
        plt.rcParams['font.sans-serif'] = [get_chinese_font(), 'DejaVu Sans']
        plt.rcParams['axes.unicode_minus'] = False

        # 设置样式
        try:
            plt.style.use(self.style)
        except Exception:
            pass  # 使用默认样式

        # 根据图表类型选择生成方法
        chart_type = intent.chart_type

        if chart_type.value == "line":
            fig = self._generate_line(data, intent, plt)
        elif chart_type.value == "bar":
            fig = self._generate_bar(data, intent, plt)
        elif chart_type.value == "pie":
            fig = self._generate_pie(data, intent, plt)
        elif chart_type.value == "area":
            fig = self._generate_area(data, intent, plt)
        else:
            fig = self._generate_line(data, intent, plt)

        return self._output_chart(fig, output_format)

    def _generate_line(self, data: Dict, intent, plt):
        """生成折线图"""
        fig, ax = plt.subplots(figsize=self.figsize)

        values = data.get("values", [])
        if not values:
            ax.text(0.5, 0.5, "暂无数据", ha='center', va='center')
            return fig

        # 按标签分组
        grouped_data: Dict[str, Dict] = {}
        for item in values:
            label = item.get("label", "value")
            if label not in grouped_data:
                grouped_data[label] = {"times": [], "vals": []}
            grouped_data[label]["times"].append(item.get("timestamp", ""))
            grouped_data[label]["vals"].append(item.get("value", 0))

        # 绘制每条线
        for label, group in grouped_data.items():
            times = list(range(len(group["times"])))
            ax.plot(
                times,
                group["vals"],
                label=label,
                marker='o',
                markersize=3,
                linewidth=2,
            )

        # 配置
        ax.set_title(intent.title or "趋势图", fontsize=14)
        ax.set_xlabel("时间", fontsize=12)
        ax.set_ylabel(self._get_ylabel(intent.metric), fontsize=12)
        ax.legend(loc='best')
        ax.grid(True, alpha=0.3)

        # X轴标签
        if grouped_data:
            first_group = list(grouped_data.values())[0]
            times = first_group["times"]
            step = max(1, len(times) // 8)
            ax.set_xticks(range(0, len(times), step))
            ax.set_xticklabels(
                [self._format_time(times[i]) for i in range(0, len(times), step)],
                rotation=45,
                ha='right',
            )

        plt.tight_layout()
        return fig

    def _generate_bar(self, data: Dict, intent, plt):
        """生成柱状图"""
        fig, ax = plt.subplots(figsize=self.figsize)

        values = data.get("values", [])
        if not values:
            ax.text(0.5, 0.5, "暂无数据", ha='center', va='center')
            return fig

        # 聚合数据
        label_values: Dict[str, float] = {}
        for item in values:
            label = item.get("label", "value")
            val = item.get("value", 0)
            if label not in label_values:
                label_values[label] = 0
            label_values[label] += val

        labels = list(label_values.keys())[:15]
        vals = [label_values[l] for l in labels]

        # 绘制柱状图
        bars = ax.bar(range(len(labels)), vals, color='steelblue')

        # 在柱子上显示值
        for bar, val in zip(bars, vals):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height(),
                f'{val:.1f}',
                ha='center',
                va='bottom',
                fontsize=10,
            )

        ax.set_title(intent.title or "对比图", fontsize=14)
        ax.set_ylabel(self._get_ylabel(intent.metric), fontsize=12)
        ax.set_xticks(range(len(labels)))
        ax.set_xticklabels(labels, rotation=45, ha='right')

        plt.tight_layout()
        return fig

    def _generate_pie(self, data: Dict, intent, plt):
        """生成饼图"""
        fig, ax = plt.subplots(figsize=(8, 8))

        values = data.get("values", [])
        if not values:
            ax.text(0.5, 0.5, "暂无数据", ha='center', va='center')
            return fig

        # 聚合数据
        label_values: Dict[str, float] = {}
        for item in values:
            label = item.get("label", "value")
            val = item.get("value", 0)
            if label not in label_values:
                label_values[label] = 0
            label_values[label] += val

        labels = list(label_values.keys())[:10]
        vals = [label_values[l] for l in labels]

        # 绘制饼图
        wedges, texts, autotexts = ax.pie(
            vals,
            labels=labels,
            autopct='%1.1f%%',
            startangle=90,
        )

        ax.set_title(intent.title or "分布图", fontsize=14)

        plt.tight_layout()
        return fig

    def _generate_area(self, data: Dict, intent, plt):
        """生成面积图"""
        fig, ax = plt.subplots(figsize=self.figsize)

        values = data.get("values", [])
        if not values:
            ax.text(0.5, 0.5, "暂无数据", ha='center', va='center')
            return fig

        # 提取数据
        times = list(range(len(values)))
        vals = [v.get("value", 0) for v in values]

        ax.fill_between(times, vals, alpha=0.4)
        ax.plot(times, vals, linewidth=2)

        ax.set_title(intent.title or "面积图", fontsize=14)
        ax.set_ylabel(self._get_ylabel(intent.metric), fontsize=12)
        ax.grid(True, alpha=0.3)

        plt.tight_layout()
        return fig

    def _generate_text_chart(self, data: Dict, intent) -> str:
        """生成文本图表（matplotlib 不可用时）"""
        values = data.get("values", [])
        if not values:
            return "暂无数据"

        lines = [f"# {intent.title or '数据图表'}", "", "```"]

        for item in values[:20]:
            timestamp = self._format_time(item.get("timestamp", ""))
            value = item.get("value", 0)
            label = item.get("label", "")

            # 简单的 ASCII 图
            bar_len = int(min(value / 10, 50))
            bar = "█" * bar_len
            lines.append(f"{timestamp} | {bar} {value:.2f}")

        lines.append("```")
        return "\n".join(lines)

    def _output_chart(self, fig, output_format: str) -> str:
        """输出图表"""
        import matplotlib.pyplot as plt

        if output_format == "base64":
            buf = io.BytesIO()
            fig.savefig(buf, format="png", dpi=100, bbox_inches='tight')
            buf.seek(0)
            plt.close(fig)
            return base64.b64encode(buf.read()).decode()

        elif output_format == "html":
            try:
                import mpld3
                html = mpld3.fig_to_html(fig)
                plt.close(fig)
                return html
            except ImportError:
                buf = io.BytesIO()
                fig.savefig(buf, format="png", dpi=100, bbox_inches='tight')
                buf.seek(0)
                plt.close(fig)
                return base64.b64encode(buf.read()).decode()

        else:  # file
            from datetime import datetime
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
            "cpu": "CPU 使用率 (%)",
            "memory": "内存 (MB)",
            "connection": "连接数",
        }
        return labels.get(metric, metric)

    def _format_time(self, timestamp: str) -> str:
        """格式化时间"""
        if not timestamp:
            return ""
        try:
            # ISO 格式转简短格式
            if "T" in timestamp:
                return timestamp[11:16]  # 只取 HH:MM
            return timestamp[:10]  # 只取日期
        except Exception:
            return timestamp

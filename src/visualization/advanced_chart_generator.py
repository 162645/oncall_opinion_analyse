"""
高级图表生成器
支持多指标、多轴、组合图等复杂图表
"""

import io
import base64
from typing import Any, Dict, List, Optional, TYPE_CHECKING
import platform

if TYPE_CHECKING:
    from .advanced_service import ComplexVisualizationIntent, ChartType, DataSeries


def get_chinese_font():
    """获取支持中文的字体"""
    system = platform.system()
    if system == 'Darwin':
        return 'PingFang SC'
    elif system == 'Windows':
        return 'Microsoft YaHei'
    else:
        return 'WenQuanYi Micro Hei'


class AdvancedChartGenerator:
    """
    高级图表生成器

    支持功能:
    - 多指标组合图
    - 双Y轴图表
    - 散点图（带回归线）
    - 热力图
    - 分组柱状图
    - 堆叠图
    """

    def __init__(self, figsize=(12, 7)):
        self.figsize = figsize
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
        data_series: List["DataSeries"],
        intent: "ComplexVisualizationIntent",
        output_format: str = "base64",
    ) -> str:
        """
        生成复杂图表

        Args:
            data_series: 数据系列列表
            intent: 可视化意图
            output_format: 输出格式

        Returns:
            图表数据
        """
        if not self._check_matplotlib():
            return self._generate_text_chart(data_series, intent)

        import matplotlib.pyplot as plt
        import matplotlib.dates as mdates
        import numpy as np

        # 设置中文字体
        plt.rcParams['font.sans-serif'] = [get_chinese_font(), 'DejaVu Sans']
        plt.rcParams['axes.unicode_minus'] = False

        chart_type = intent.chart_type.value

        # 根据图表类型选择生成方法
        if chart_type == "combo" or chart_type == "multi_axis":
            fig = self._generate_combo(data_series, intent, plt)
        elif chart_type == "scatter":
            fig = self._generate_scatter(data_series, intent, plt)
        elif chart_type == "heatmap":
            fig = self._generate_heatmap(data_series, intent, plt)
        elif chart_type == "line":
            fig = self._generate_multi_line(data_series, intent, plt)
        elif chart_type == "bar":
            fig = self._generate_grouped_bar(data_series, intent, plt)
        elif chart_type == "area":
            fig = self._generate_stacked_area(data_series, intent, plt)
        else:
            fig = self._generate_multi_line(data_series, intent, plt)

        return self._output_chart(fig, output_format)

    def _generate_combo(
        self,
        data_series: List["DataSeries"],
        intent: "ComplexVisualizationIntent",
        plt,
    ):
        """生成组合图（支持双Y轴）"""
        fig, ax1 = plt.subplots(figsize=self.figsize)

        if not data_series:
            ax1.text(0.5, 0.5, "暂无数据", ha='center', va='center', fontsize=14)
            return fig

        # 颜色配置
        colors = ['#2196F3', '#FF5722', '#4CAF50', '#9C27B0', '#FF9800']

        # 第一个系列在左轴
        series1 = data_series[0]
        values1 = [v.get('value', 0) for v in series1.values]
        times = list(range(len(values1)))

        ax1.plot(times, values1, color=colors[0], linewidth=2, marker='o', markersize=3, label=series1.name)
        ax1.set_xlabel('时间', fontsize=12)
        ax1.set_ylabel(series1.name, color=colors[0], fontsize=12)
        ax1.tick_params(axis='y', labelcolor=colors[0])
        ax1.grid(True, alpha=0.3)

        # 第二个系列在右轴（如果存在）
        if len(data_series) > 1:
            ax2 = ax1.twinx()
            series2 = data_series[1]
            values2 = [v.get('value', 0) for v in series2.values]

            ax2.plot(times, values2, color=colors[1], linewidth=2, marker='s', markersize=3, label=series2.name)
            ax2.set_ylabel(series2.name, color=colors[1], fontsize=12)
            ax2.tick_params(axis='y', labelcolor=colors[1])

        # 设置标题
        ax1.set_title(intent.title or "组合图", fontsize=14, fontweight='bold')

        # 图例
        lines1, labels1 = ax1.get_legend_handles_labels()
        if len(data_series) > 1:
            lines2, labels2 = ax2.get_legend_handles_labels()
            ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper left')
        else:
            ax1.legend(loc='upper left')

        plt.tight_layout()
        return fig

    def _generate_scatter(
        self,
        data_series: List["DataSeries"],
        intent: "ComplexVisualizationIntent",
        plt,
    ):
        """生成散点图（支持回归线）"""
        fig, ax = plt.subplots(figsize=self.figsize)

        if len(data_series) < 2:
            ax.text(0.5, 0.5, "散点图需要至少两个指标", ha='center', va='center')
            return fig

        series1 = data_series[0]
        series2 = data_series[1]

        x = [v.get('value', 0) for v in series1.values]
        y = [v.get('value', 0) for v in series2.values]

        # 确保长度一致
        min_len = min(len(x), len(y))
        x = x[:min_len]
        y = y[:min_len]

        # 绘制散点
        ax.scatter(x, y, alpha=0.6, c='#2196F3', s=50)

        # 添加回归线
        import numpy as np
        if len(x) > 1:
            z = np.polyfit(x, y, 1)
            p = np.poly1d(z)
            x_line = np.linspace(min(x), max(x), 100)
            ax.plot(x_line, p(x_line), "r--", alpha=0.8, label=f'趋势线 (y={z[0]:.2f}x+{z[1]:.2f})')

        # 计算相关系数
        if len(x) > 2:
            corr = np.corrcoef(x, y)[0, 1]
            ax.text(0.05, 0.95, f'相关系数: {corr:.3f}', transform=ax.transAxes, fontsize=10, verticalalignment='top')

        ax.set_xlabel(series1.name, fontsize=12)
        ax.set_ylabel(series2.name, fontsize=12)
        ax.set_title(intent.title or "散点图", fontsize=14, fontweight='bold')
        ax.grid(True, alpha=0.3)
        ax.legend()

        plt.tight_layout()
        return fig

    def _generate_heatmap(
        self,
        data_series: List["DataSeries"],
        intent: "ComplexVisualizationIntent",
        plt,
    ):
        """生成热力图"""
        fig, ax = plt.subplots(figsize=self.figsize)

        if not data_series:
            ax.text(0.5, 0.5, "暂无数据", ha='center', va='center')
            return fig

        import numpy as np

        # 构建热力图数据矩阵
        # 假设第一个系列包含热力图数据
        series = data_series[0]
        values = [v.get('value', 0) for v in series.values]

        # 尝试 reshape 成矩阵（简单处理）
        n = len(values)
        if n > 0:
            # 计算 nearest square
            import math
            cols = int(math.ceil(math.sqrt(n)))
            rows = int(math.ceil(n / cols))

            # pad with zeros
            padded = values + [0] * (rows * cols - n)
            data = np.array(padded).reshape(rows, cols)

            im = ax.imshow(data, cmap='YlOrRd', aspect='auto')
            fig.colorbar(im, ax=ax)

        ax.set_title(intent.title or "热力图", fontsize=14, fontweight='bold')

        plt.tight_layout()
        return fig

    def _generate_multi_line(
        self,
        data_series: List["DataSeries"],
        intent: "ComplexVisualizationIntent",
        plt,
    ):
        """生成多系列折线图"""
        fig, ax = plt.subplots(figsize=self.figsize)

        if not data_series:
            ax.text(0.5, 0.5, "暂无数据", ha='center', va='center')
            return fig

        colors = ['#2196F3', '#FF5722', '#4CAF50', '#9C27B0', '#FF9800', '#00BCD4']

        for i, series in enumerate(data_series[:6]):  # 最多6条线
            values = [v.get('value', 0) for v in series.values]
            times = list(range(len(values)))

            color = colors[i % len(colors)]
            ax.plot(times, values, color=color, linewidth=2, marker='o', markersize=3, label=series.name)

        ax.set_title(intent.title or "趋势图", fontsize=14, fontweight='bold')
        ax.set_xlabel('时间', fontsize=12)
        ax.set_ylabel('数值', fontsize=12)
        ax.legend(loc='best')
        ax.grid(True, alpha=0.3)

        plt.tight_layout()
        return fig

    def _generate_grouped_bar(
        self,
        data_series: List["DataSeries"],
        intent: "ComplexVisualizationIntent",
        plt,
    ):
        """生成分组柱状图"""
        fig, ax = plt.subplots(figsize=self.figsize)

        if not data_series:
            ax.text(0.5, 0.5, "暂无数据", ha='center', va='center')
            return fig

        import numpy as np

        colors = ['#2196F3', '#FF5722', '#4CAF50', '#9C27B0']

        # 获取标签（从第一个系列）
        labels = data_series[0].labels if data_series[0].labels else [f"Item {i+1}" for i in range(len(data_series[0].values))]

        x = np.arange(len(labels))
        width = 0.8 / len(data_series)

        for i, series in enumerate(data_series[:4]):
            values = [v.get('value', 0) for v in series.values]
            offset = (i - len(data_series) / 2 + 0.5) * width

            bars = ax.bar(x + offset, values, width, label=series.name, color=colors[i % len(colors)])

            # 在柱子上显示数值
            for bar, val in zip(bars, values):
                ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height(),
                       f'{val:.1f}', ha='center', va='bottom', fontsize=8)

        ax.set_title(intent.title or "对比图", fontsize=14, fontweight='bold')
        ax.set_xticks(x)
        ax.set_xticklabels(labels, rotation=45, ha='right')
        ax.legend(loc='best')
        ax.grid(True, alpha=0.3, axis='y')

        plt.tight_layout()
        return fig

    def _generate_stacked_area(
        self,
        data_series: List["DataSeries"],
        intent: "ComplexVisualizationIntent",
        plt,
    ):
        """生成堆叠面积图"""
        fig, ax = plt.subplots(figsize=self.figsize)

        if not data_series:
            ax.text(0.5, 0.5, "暂无数据", ha='center', va='center')
            return fig

        import numpy as np

        colors = ['#2196F3', '#FF5722', '#4CAF50', '#9C27B0']

        # 准备数据
        all_values = []
        labels = []

        for series in data_series[:4]:
            values = [v.get('value', 0) for v in series.values]
            all_values.append(values)
            labels.append(series.name)

        # 堆叠
        times = list(range(len(all_values[0])))
        ax.stackplot(times, all_values, labels=labels, colors=colors[:len(all_values)], alpha=0.8)

        ax.set_title(intent.title or "堆叠面积图", fontsize=14, fontweight='bold')
        ax.set_xlabel('时间', fontsize=12)
        ax.set_ylabel('数值', fontsize=12)
        ax.legend(loc='upper left')
        ax.grid(True, alpha=0.3)

        plt.tight_layout()
        return fig

    def _generate_text_chart(
        self,
        data_series: List["DataSeries"],
        intent: "ComplexVisualizationIntent",
    ) -> str:
        """生成文本图表（matplotlib 不可用时）"""
        lines = [f"# {intent.title or '数据图表'}", ""]

        for series in data_series:
            lines.append(f"\n## {series.name}")
            lines.append("```")
            for i, v in enumerate(series.values[:20]):
                val = v.get('value', 0)
                bar_len = int(min(val / 10, 50))
                bar = "█" * bar_len
                lines.append(f"{i+1:3d} | {bar} {val:.2f}")
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

        else:
            from datetime import datetime
            path = f"/tmp/chart_{datetime.now().strftime('%Y%m%d%H%M%S')}.png"
            fig.savefig(path, dpi=100, bbox_inches='tight')
            plt.close(fig)
            return path

"""
追踪可视化
"""

import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .models import ExecutionTrace, TraceStep, StepType


class TraceVisualizer:
    """
    追踪可视化

    将追踪数据渲染为不同格式
    """

    # 步骤类型对应的 emoji
    STEP_EMOJIS = {
        "router": "🔀",
        "retrieval": "📚",
        "tool_call": "🔧",
        "reasoning": "🧠",
        "decision": "✅",
        "error": "❌",
    }

    @staticmethod
    def render_markdown(trace: "ExecutionTrace") -> str:
        """
        渲染为 Markdown 格式

        Args:
            trace: 执行追踪

        Returns:
            Markdown 格式的追踪报告
        """
        lines = [
            f"# 执行追踪: {trace.session_id}",
            "",
            f"**查询**: {trace.query}",
            f"**状态**: {trace.status}",
            f"**总耗时**: {trace.total_duration_ms}ms",
            "",
            "---",
            "",
            "## 执行步骤",
            "",
        ]

        for step in trace.steps:
            emoji = TraceVisualizer.STEP_EMOJIS.get(
                step.step_type.value, "•"
            )

            lines.append(f"### {emoji} Step {step.step_id}: {step.action}")
            lines.append("")

            # 基本信息
            lines.append(f"| 属性 | 值 |")
            lines.append(f"|------|----|")
            lines.append(f"| Agent | {step.agent_name} |")
            lines.append(f"| 类型 | {step.step_type.value} |")
            lines.append(f"| 耗时 | {step.duration_ms}ms |")
            lines.append(f"| 置信度 | {step.confidence:.2f} |")
            lines.append("")

            # 思考过程
            if step.reasoning:
                lines.append("**思考过程**:")
                lines.append("```")
                lines.append(step.reasoning)
                lines.append("```")
                lines.append("")

            # 输入输出
            if step.input_data:
                lines.append("**输入**:")
                lines.append("```json")
                lines.append(json.dumps(step.input_data, ensure_ascii=False, indent=2)[:500])
                lines.append("```")
                lines.append("")

            if step.output_data:
                lines.append("**输出**:")
                lines.append("```json")
                lines.append(json.dumps(step.output_data, ensure_ascii=False, indent=2)[:500])
                lines.append("```")
                lines.append("")

            lines.append("---")
            lines.append("")

        # 最终结果
        if trace.final_result:
            lines.append("## 最终结果")
            lines.append("")
            lines.append("```")
            lines.append(str(trace.final_result)[:1000])
            lines.append("```")
            lines.append("")

        # 错误信息
        if trace.error:
            lines.append("## ❌ 错误")
            lines.append("")
            lines.append(f"```\n{trace.error}\n```")
            lines.append("")

        return "\n".join(lines)

    @staticmethod
    def render_html(trace: "ExecutionTrace") -> str:
        """
        渲染为 HTML 格式

        Args:
            trace: 执行追踪

        Returns:
            HTML 格式的追踪报告（可交互）
        """
        steps_html = ""

        for step in trace.steps:
            emoji = TraceVisualizer.STEP_EMOJIS.get(
                step.step_type.value, "•"
            )

            steps_html += f"""
<div class="step" data-type="{step.step_type.value}">
    <div class="step-header">
        <span class="step-emoji">{emoji}</span>
        <span class="step-title">Step {step.step_id}: {step.action}</span>
        <span class="step-duration">{step.duration_ms}ms</span>
    </div>

    <div class="step-meta">
        <span class="agent">Agent: {step.agent_name}</span>
        <span class="confidence">置信度: {step.confidence:.2f}</span>
    </div>

    {f'<div class="reasoning"><strong>思考过程:</strong><br>{step.reasoning}</div>' if step.reasoning else ''}

    <details class="step-details">
        <summary>详细信息</summary>
        <div class="input-data">
            <strong>输入:</strong>
            <pre>{json.dumps(step.input_data, ensure_ascii=False, indent=2)}</pre>
        </div>
        <div class="output-data">
            <strong>输出:</strong>
            <pre>{json.dumps(step.output_data, ensure_ascii=False, indent=2)}</pre>
        </div>
    </details>
</div>
"""

        return f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>执行追踪 - {trace.session_id}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 900px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
        }}

        .header {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}

        .header h1 {{
            margin: 0 0 10px 0;
            color: #333;
        }}

        .meta {{
            color: #666;
            font-size: 14px;
        }}

        .step {{
            background: white;
            padding: 15px;
            margin-bottom: 15px;
            border-radius: 8px;
            border-left: 4px solid #4CAF50;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}

        .step[data-type="error"] {{
            border-left-color: #f44336;
        }}

        .step[data-type="tool_call"] {{
            border-left-color: #2196F3;
        }}

        .step[data-type="reasoning"] {{
            border-left-color: #9C27B0;
        }}

        .step-header {{
            display: flex;
            align-items: center;
            margin-bottom: 10px;
        }}

        .step-emoji {{
            font-size: 24px;
            margin-right: 10px;
        }}

        .step-title {{
            flex: 1;
            font-weight: bold;
            color: #333;
        }}

        .step-duration {{
            background: #e0e0e0;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 12px;
        }}

        .step-meta {{
            font-size: 13px;
            color: #666;
            margin-bottom: 10px;
        }}

        .step-meta span {{
            margin-right: 15px;
        }}

        .confidence {{
            color: #4CAF50;
            font-weight: bold;
        }}

        .reasoning {{
            background: #fff3cd;
            padding: 10px;
            border-radius: 4px;
            margin: 10px 0;
            white-space: pre-wrap;
        }}

        .step-details {{
            margin-top: 10px;
        }}

        .step-details summary {{
            cursor: pointer;
            color: #666;
        }}

        .step-details pre {{
            background: #f5f5f5;
            padding: 10px;
            border-radius: 4px;
            overflow-x: auto;
            font-size: 12px;
        }}

        .status {{
            display: inline-block;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: bold;
        }}

        .status.completed {{
            background: #e8f5e9;
            color: #2e7d32;
        }}

        .status.failed {{
            background: #ffebee;
            color: #c62828;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>执行追踪</h1>
        <div class="meta">
            <p><strong>Session:</strong> {trace.session_id}</p>
            <p><strong>查询:</strong> {trace.query}</p>
            <p>
                <strong>状态:</strong>
                <span class="status {trace.status}">{trace.status}</span>
            </p>
            <p><strong>总耗时:</strong> {trace.total_duration_ms}ms</p>
            <p><strong>步骤数:</strong> {len(trace.steps)}</p>
        </div>
    </div>

    <div class="steps">
        {steps_html}
    </div>
</body>
</html>
"""

    @staticmethod
    def render_json(trace: "ExecutionTrace") -> str:
        """
        渲染为 JSON 格式

        Args:
            trace: 执行追踪

        Returns:
            JSON 格式的追踪数据
        """
        return json.dumps(
            trace.to_dict(),
            ensure_ascii=False,
            indent=2,
        )

    @staticmethod
    def render_summary(trace: "ExecutionTrace") -> str:
        """
        渲染为简短摘要

        Args:
            trace: 执行追踪

        Returns:
            简短的追踪摘要
        """
        lines = [
            f"📊 执行追踪: {trace.session_id}",
            f"📝 查询: {trace.query}",
            f"⏱️ 耗时: {trace.total_duration_ms}ms",
            f"📋 步骤: {len(trace.steps)} 步",
            "",
            "执行过程:",
        ]

        for step in trace.steps:
            emoji = TraceVisualizer.STEP_EMOJIS.get(
                step.step_type.value, "•"
            )
            lines.append(
                f"  {emoji} {step.agent_name}: {step.action} ({step.duration_ms}ms)"
            )

        return "\n".join(lines)

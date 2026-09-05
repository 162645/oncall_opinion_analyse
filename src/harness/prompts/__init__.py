"""Versioned prompt metadata shared by Harness observability and evals."""

PROMPT_VERSION = "harness-v1"

PROMPT_POLICY = (
    "只输出目标 Schema；不得生成裸 SQL、未注册工具或未经 Measurement Evidence "
    "支持的数字、实体和因果结论。Context 只能影响规划，不能成为测量事实。"
)

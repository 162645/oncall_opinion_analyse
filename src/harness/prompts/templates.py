"""Versioned prompt builders for the six Harness decision surfaces.

Keeping templates here makes prompt changes reviewable and gives traces a
stable version label. These prompts intentionally ask for bounded JSON; the
runtime remains the authority for validation and execution.
"""

from __future__ import annotations

import json
from typing import Any

from . import PROMPT_VERSION


def _dump(value: Any, limit: int = 8000) -> str:
    return json.dumps(value, ensure_ascii=False, default=str)[:limit]


def planner_prompt(*, query: str, task: dict, context: dict, evidence: list,
                   recipe: list, missing: list, budget: dict, ir_schema: dict) -> str:
    return (
        "你是网络测量分析 Next-Best-Action Planner。只输出 JSON 对象，不要 Markdown。"
        "格式为 {action: query|finish, queries: [{query_id, reason, expected_information_gain}]}；"
        "每轮默认只选 1 个 query，只有明确的并行价值才选 2 个。query_id 只能来自候选 Catalog；禁止 SQL、禁止新增工具。"
        f"\nUserQuery={query}\nTaskSpec={_dump(task)}\nCatalog={_dump(context.get('catalog', []))}"
        f"\nRecipeHints={_dump(context.get('recipe_hints', {}))}"
        f"\nSkillMatches={_dump(context.get('skill_matches', [])[:2])}"
        f"\nKnowledgeHints={_dump(context.get('knowledge', [])[:3], 4000)}"
        f"\nGraphHints={_dump(context.get('graph_context', [])[:3])}"
        f"\nPlanningContext={_dump(context.get('planning_context', {}), 5000)}"
        f"\nEvidence={_dump(evidence)}\nMissingRequirements={_dump(missing)}"
        f"\nRemainingBudget={_dump(budget)}\nRecipeCandidate={_dump(recipe)}"
        "\n若 Catalog 无法覆盖当前目标，仅在 planning_mode=long_tail 时使用 generated_query/query.ir。"
        f" QueryIRSchema={_dump(ir_schema)}"
        "\n请结合信息增益、成本与剩余预算选择当前最有价值且尚未成功执行的查询。"
    )


def renderer_prompt(*, claims: list, query: str) -> str:
    return (
        "你是已验证 Claim 的中文叙事渲染器。可以调整顺序、加入过渡句和结论边界，"
        "但不能增加事实 Claim、数字、对象、因果关系或根因判断。只能输出 JSON 对象："
        '{"summary":"自然中文总结","claims":[{"claim_id":"CL1","text":"..."}]}。'
        "summary 中只能使用 VerifiedClaims 的事实；必须保留所有 claim_id。"
        f"\nVerifiedClaims={_dump(claims)}\n用户问题：{query}"
    )

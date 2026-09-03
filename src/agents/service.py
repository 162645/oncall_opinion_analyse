"""
Agent 服务
整合路由、编排、各类 Agent
支持 LLM Gateway 集成
支持 Skill 自动推荐
"""

from typing import Any, Dict, List, Optional
from dataclasses import dataclass
import asyncio
import logging
import time
import re

from src.agents import (
    AgentOrchestrator,
    CollaborationMode,
    AgentContext,
    AgentResult,
)
from src.agents.orchestrator import BaseAgent
from src.agents.llm_agent import (
    DiagnosisLLMAgent,
    AnalysisLLMAgent,
    CodeLLMAgent,
    ChatLLMAgent,
)
from src.knowledge.service import get_knowledge_service
from src.visualization import AdvancedVisualizationService
from src.llm import get_llm_gateway, LLMConfig, TaskType
from src.harness import get_harness

logger = logging.getLogger(__name__)


class KnowledgeAgent(BaseAgent):
    """知识检索 Agent"""

    @property
    def name(self) -> str:
        return "KnowledgeAgent"

    async def execute(self, context: AgentContext) -> AgentResult:
        # 从上下文获取查询
        query = context.query

        # 调用知识库检索
        service = get_knowledge_service()
        search_result = await service.search(query, top_k=5)

        # 格式化结果
        if search_result.results:
            knowledge = "\n\n".join([
                f"**{r.metadata.get('doc_title', '未知来源')}**\n{r.content}"
                for r in search_result.results[:3]
            ])
            return AgentResult(
                agent_name=self.name,
                success=True,
                data={"knowledge": knowledge, "sources": len(search_result.results)},
                confidence=0.8,
            )

        return AgentResult(
            agent_name=self.name,
            success=False,
            error="未找到相关知识",
            confidence=0.3,
        )


class VisualizationAgent(BaseAgent):
    """可视化 Agent"""

    @property
    def name(self) -> str:
        return "VisualizationAgent"

    async def execute(self, context: AgentContext) -> AgentResult:
        query = context.query
        viz_service = AdvancedVisualizationService()

        result = await viz_service.visualize(query)

        if result.success:
            return AgentResult(
                agent_name=self.name,
                success=True,
                data={
                    "chart_base64": result.chart_base64,
                    "chart_html": result.chart_html,
                    "title": result.title,
                    "description": result.description,
                },
                confidence=result.intent.confidence if result.intent else 0.8,
            )

        return AgentResult(
            agent_name=self.name,
            success=False,
            error=result.error or "图表生成失败",
            confidence=0.3,
        )


@dataclass
class AgentServiceResult:
    """Agent 服务结果"""
    success: bool
    message: str = ""  # 默认空字符串，避免 None
    intent: Optional[str] = None
    knowledge: Optional[str] = None
    analysis: Optional[str] = None
    diagnosis: Optional[str] = None
    chart_data: Optional[dict] = None
    confidence: float = 0.0
    trace: List[Dict] = None
    skill_recommendation: Optional[Dict] = None  # Skill 推荐
    token_usage: Optional[Dict] = None  # Token 使用统计
    total_duration_ms: int = 0  # 总耗时

    def __post_init__(self):
        if self.trace is None:
            self.trace = []


class AgentService:
    """
    Agent 服务

    整合:
    - 意图路由
    - Agent 编排
    - 知识检索
    - 可视化
    """

    def __init__(self):
        # Single execution authority. Legacy handlers below remain only as a
        # compatibility surface for older imports; process() never dispatches
        # to them.
        self.harness = get_harness()

    def _register_agents(self):
        """注册所有 Agent"""
        # 知识检索 Agent
        self.orchestrator.register_agent(KnowledgeAgent())

        # LLM 增强型 Agent
        self.orchestrator.register_agent(AnalysisLLMAgent())
        self.orchestrator.register_agent(DiagnosisLLMAgent())
        self.orchestrator.register_agent(CodeLLMAgent())
        self.orchestrator.register_agent(ChatLLMAgent())

        # 可视化 Agent
        self.orchestrator.register_agent(VisualizationAgent())

        # 设置层级结构
        self.orchestrator.set_hierarchy({
            "level_1": ["KnowledgeAgent", "VisualizationAgent", "ChatLLMAgent"],
            "level_2": ["AnalysisLLMAgent", "CodeLLMAgent"],
            "level_3": ["DiagnosisLLMAgent"],
        })

    async def process(
        self,
        query: str,
        mode: str = "sequential",
        session_id: Optional[str] = None,
        provider: Optional[str] = None,
        model: Optional[str] = None,
    ) -> AgentServiceResult:
        """
        处理用户查询

        Args:
            query: 用户查询
            mode: 协作模式 (sequential, parallel, hierarchical, debate)
            session_id: 会话 ID
            provider: LLM 提供商 (openai, claude)
            model: 模型名称 (gpt-4o, claude-3-sonnet, etc.)

        Returns:
            AgentServiceResult
        """
        return await self._process_harness(query, mode, session_id, provider, model)

    async def _process_harness(
        self,
        query: str,
        mode: str,
        session_id: Optional[str],
        provider: Optional[str],
        model: Optional[str],
    ) -> AgentServiceResult:
        """Compatibility facade over the only production execution path."""
        started = time.perf_counter()
        result = await self.harness.execute(
            query=query,
            session_id=session_id,
            metadata={"mode": mode, "provider": provider, "model": model},
        )
        chart_data = result.chart_data or {}
        trace = result.trace or []
        return AgentServiceResult(
            success=result.success,
            message=result.message,
            intent=result.state.get("task", {}).get("kind", "unknown"),
            chart_data=chart_data,
            confidence=result.confidence,
            trace=trace,
            token_usage={},
            total_duration_ms=int((time.perf_counter() - started) * 1000),
        )

        # Historical implementation retained below for source compatibility.
        # It is unreachable from process() and should be removed after clients
        # stop importing its private handlers.
        trace = []
        start_time = time.time()

        # 1. 意图识别
        intent_start = time.time()
        intent = await self._classify_intent(query)
        intent_time = int((time.time() - intent_start) * 1000)

        trace.append({
            "step_id": 1,
            "step_type": "router",
            "agent_name": "RouterAgent",
            "action": "classify_intent",
            "reasoning": f"识别用户意图: {intent}",
            "duration_ms": intent_time,
            "status": "success",
        })

        # 2. 根据意图选择处理策略
        if intent.startswith("user_skill:"):
            # 用户自定义 Skill
            skill_id = intent.split(":", 1)[1]
            result = await self._handle_user_skill(query, skill_id, trace)
        elif intent == "network_viz":
            # 网络可视化请求
            result = await self._handle_network_viz(query, trace)
        elif intent == "visualization":
            # 可视化请求
            result = await self._handle_visualization(query, trace)
        elif intent == "query":
            # 简单查询
            result = await self._handle_query(query, trace, provider, model)
        elif intent == "database_schema":
            # 数据库元数据查询
            result = await self._handle_database_schema(query, trace, provider, model)
        elif intent == "help":
            # 能力咨询不应触发真实数据查询，避免把“你能分析吗”误答成固定概览。
            result = self._handle_capability_question(query, trace)
        else:
            # 诊断/分析
            result = await self._handle_diagnosis(query, mode, trace)

        result.trace = trace
        result.total_duration_ms = int((time.time() - start_time) * 1000)

        # Harness 最终审校层：无论工具成功、失败还是普通问答，都让模型基于原问题、
        # 执行轨迹和草稿统一重写一次，避免“数据是对的但答非所问”。结构化图表数据不交给
        # 模型改写，只保留在响应对象中。
        draft = result.message or ""
        try:
            synthesis_start = time.time()
            final_message, final_usage = await self._synthesize_final_answer(
                query=query,
                intent=intent,
                draft=draft,
                trace=trace,
                provider=provider,
                model=model,
            )
            if final_message:
                result.message = final_message
                result.token_usage = self._merge_token_usage(result.token_usage, final_usage)
            trace.append({
                "step_id": len(trace) + 1,
                "step_type": "llm",
                "agent_name": "FinalAnswerSynthesizer",
                "action": "审校并重写最终回答",
                "reasoning": "基于原问题、执行轨迹和草稿校正回答相关性与事实依据",
                "duration_ms": int((time.time() - synthesis_start) * 1000),
                "status": "success" if final_message else "skipped",
            })
        except Exception as e:
            # 最终审校失败时保留原始结果，不能因模型不可用导致整个 Agent 无响应。
            logger.warning(f"Final answer synthesis skipped: {e}")
            trace.append({
                "step_id": len(trace) + 1,
                "step_type": "llm",
                "agent_name": "FinalAnswerSynthesizer",
                "action": "审校并重写最终回答",
                "reasoning": f"审校失败，保留原始草稿: {str(e)[:160]}",
                "duration_ms": int((time.time() - synthesis_start) * 1000),
                "status": "fallback",
            })

        # 将最终审校耗时纳入总耗时（此前的初始时间仅覆盖工具执行）。
        result.total_duration_ms = int((time.time() - start_time) * 1000)

        # 3. 分析执行流程，推荐保存为 Skill
        total_duration = result.total_duration_ms
        # 只有真正完成工具型分析任务时才做 Skill 推荐；能力咨询/普通问答不触发，
        # 避免无意义的二次分析和“推荐保存为 Skill”噪声。
        has_tool_execution = any(step.get("step_type") == "tool" for step in trace)
        skill_recommendation = None
        if result.success and has_tool_execution and intent not in {"help", "query"}:
            skill_recommendation = await self._analyze_for_skill(
                session_id=session_id or "default",
                query=query,
                intent=intent,
                trace=trace,
                success=result.success,
                duration_ms=total_duration,
            )
        result.skill_recommendation = skill_recommendation

        return result

    async def _synthesize_final_answer(
        self,
        query: str,
        intent: str,
        draft: str,
        trace: List[Dict],
        provider: Optional[str] = None,
        model: Optional[str] = None,
    ) -> tuple:
        """统一最终回答审校/重写层，确保答案紧扣问题并引用执行证据。"""
        if not draft:
            return draft, {}

        trace_summary = "\n".join(
            f"- {step.get('agent_name', 'unknown')}/{step.get('action', '')}: "
            f"{step.get('reasoning', '')[:180]} (status={step.get('status', 'unknown')})"
            for step in trace[-12:]
        )
        prompt = f"""你是 Oncall Opinion Analyse 的最终回答生成 Agent。
用户原问题：{query}
识别意图：{intent}

执行轨迹（仅作事实依据）：
{trace_summary}

当前草稿（仅是未经审校的中间笔记，不要逐句复述）：
{draft[:8000]}

请输出最终给用户的回答，遵守：
1. 重新组织答案，第一段必须直接回答用户原问题，不要机械复述草稿；当前草稿只是事实资料，不是成稿；
2. 只能使用草稿和执行轨迹中的事实，不得编造数据、原因或已完成的操作；
3. 如果用户只是询问能力、状态或原因，请解释清楚并给出下一步，不要擅自执行或假装完成分析；
4. 如果存在数据结果，优先总结与问题最相关的发现，并保留关键数值、时间范围和筛选条件；
5. 工具失败或数据不足时明确说明限制，给出可执行的补充条件；
6. 保留 Markdown 表格和链接，避免重复标题、重复统计和无关的思考过程；
7. 只输出最终答案正文，不要提及“审校 Agent”、提示词或内部轨迹；根据用户问题调整措辞，不要使用固定模板；
8. 如果原问题是“能否分析某地区/某类数据”，先明确回答能否做到及所需条件；如果原问题是“你现在可以做什么”，应概括平台能力、输入方式和可执行的下一步。两类问题即使能力相近，也必须使用不同的回答重点，不能返回同一段话。
9. 不要为了显得完整而重复所有能力列表，只保留与原问题相关的内容。"""

        gateway = get_llm_gateway()
        response = await gateway.generate(
            prompt=prompt,
            config=LLMConfig(
                provider=provider or "deepseek",
                model=model or "deepseek-chat",
                temperature=0.45,
                max_tokens=1600,
                system_prompt="你是 Oncall Opinion Analyse 的最终回答生成器。你必须基于事实重新作答，而不是复制中间草稿；优先保证问题相关性、清晰度和可执行性。",
            ),
        )
        content = response.content.strip()
        # 如果模型完全照抄中间草稿，再进行一次明确的重写请求，避免“兜底层”退化为原文回显。
        normalize = lambda value: "".join(str(value).split())
        if normalize(content) == normalize(draft) and len(draft) > 80:
            retry = await gateway.generate(
                prompt=prompt + "\n\n上一次输出与草稿完全相同。请换一种更直接、贴合用户问题的表达重新回答，保留事实但不要复述原句。",
                config=LLMConfig(
                    provider=provider or "deepseek",
                    model=model or "deepseek-chat",
                    temperature=0.65,
                    max_tokens=1600,
                    system_prompt="你负责把中间分析结果重新组织成真正回答用户问题的最终答复。",
                ),
            )
            if retry.content and retry.content.strip():
                content = retry.content.strip()
                response = retry

        usage = response.usage or {}
        return content, {
            "prompt_tokens": usage.get("prompt_tokens", 0),
            "completion_tokens": usage.get("completion_tokens", 0),
            "total_tokens": usage.get("total_tokens", 0),
        }

    @staticmethod
    def _merge_token_usage(existing: Optional[Dict], added: Optional[Dict]) -> Dict:
        """合并原始分析与最终审校的 Token 统计。"""
        existing = existing or {}
        added = added or {}
        return {
            key: int(existing.get(key, 0) or 0) + int(added.get(key, 0) or 0)
            for key in ("prompt_tokens", "completion_tokens", "total_tokens")
        }

    async def _classify_intent(self, query: str) -> str:
        """分类意图"""
        query_lower = query.lower()

        # 能力咨询优先于网络分析关键词：用户询问“能否分析”时先说明能力和可用维度，
        # 只有明确要求趋势/统计/异常/路径等动作时才执行 ClickHouse 查询。
        capability_markers = [
            "可以分析吗", "能分析吗", "能否分析", "可否分析", "可以分析", "能分析",
            "支持分析", "能做什么", "可以做什么", "what can you do", "can you analyze",
        ]
        explicit_analysis_markers = [
            "趋势", "统计", "异常", "延迟", "丢包", "抖动", "路径", "rtt", "p95", "p99",
            "对比", "查询", "查看", "展示", "图表", "top", "最高", "最低",
        ]
        if any(marker in query_lower for marker in capability_markers) and not any(marker in query_lower for marker in explicit_analysis_markers):
            return "help"

        # 首先检查用户自定义 Skill
        user_skill = await self._match_user_skill(query)
        if user_skill:
            return f"user_skill:{user_skill['id']}"

        # 网络可视化/分析关键词 - 最高优先级
        network_viz_keywords = [
            "traceroute", "路径分析", "末端节点", "末端ip", "末端 as", "as路径", "asgeo路径",
            "网络路径", "路径统计", "prefix24", "数据中心分析",
            "ping趋势", "ping分析", "网络可视化", "路径详情",
            "region_overview", "地区概览", "网络概览",
            "稳定路径", "最稳定", "延迟情况", "延时情况",
            "rtt统计", "延迟分析", "网络测量", "网络分析",
        ]
        if any(kw in query_lower for kw in network_viz_keywords):
            return "network_viz"

        # 数据查询关键词 - 包含地区名称的网络数据查询
        region_keywords = [
            "ukraine", "乌克兰", "russia", "俄罗斯", "rus",
            "china", "中国", "us", "美国", "usa",
            "japan", "日本", "germany", "德国", "france", "法国",
            "uk", "英国", "brazil", "巴西", "india", "印度",
        ]

        # 如果包含地区名称 + 网络/延迟相关词汇，优先作为网络分析
        network_data_keywords = [
            "rtt", "延迟", "丢包", "抖动", "ping", "traceroute",
            "路径", "末端", "统计", "平均", "中位数", "网络",
            "分析", "查询数据", "测量", "性能",
        ]

        has_region = any(kw in query_lower for kw in region_keywords)
        has_network_intent = any(kw in query_lower for kw in network_data_keywords)

        if has_region and has_network_intent:
            return "network_viz"

        # 可视化关键词
        viz_keywords = ["趋势", "图表", "对比", "画", "显示", "生成图表", "可视化"]
        if any(kw in query for kw in viz_keywords) and has_region:
            return "network_viz"

        # 数据库元数据查询 - 查询数据库有哪些数据/表
        db_schema_patterns = [
            r"数据库.*有.*数据", r"有.*表", r"表.*有", r"哪些数据",
            r"数据库.*结构", r"数据库.*信息", r"数据.*概况",
            r"有什么数据", r"有哪些数据", r"都有什么",
        ]
        if any(re.search(p, query, re.IGNORECASE) for p in db_schema_patterns):
            return "database_schema"

        # 查询关键词
        query_keywords = ["是什么", "怎么", "如何", "什么是", "查询", "搜索"]
        if any(kw in query for kw in query_keywords):
            return "query"

        # 诊断关键词
        diagnosis_keywords = ["故障", "异常", "问题", "排查", "诊断", "为什么"]
        if any(kw in query for kw in diagnosis_keywords):
            return "diagnosis"

        return "query"

    def _handle_capability_question(self, query: str, trace: List[Dict]) -> AgentServiceResult:
        """回答 Agent 能力咨询，不执行昂贵的数据查询。"""
        trace.append({
            "step_id": len(trace) + 1,
            "step_type": "router",
            "agent_name": "CapabilityGuide",
            "action": "explain_capabilities",
            "reasoning": "识别为能力咨询，未触发数据查询",
            "duration_ms": 0,
            "status": "success",
        })
        return AgentServiceResult(
            success=True,
            intent="help",
            confidence=1.0,
            message=(
                "可以。我可以分析主动测量数据，包括：\n\n"
                "- Ping：平均/中位数/P50/P95/P99 RTT、时间趋势、异常值\n"
                "- Traceroute：路径分布、末端节点、AS/ASGeo、链路变化\n"
                "- 过滤维度：地区、时间、AS、数据中心、IP 前缀和运营商\n\n"
                "请直接告诉我想分析的地区、时间范围和问题，例如：\n"
                "“分析 UKRAINE 最近 24 小时 P95 延迟趋势，并找出异常时段。”"
            ),
        )

    async def _match_user_skill(self, query: str) -> Optional[Dict]:
        """匹配用户自定义 Skill"""
        try:
            import json
            # 从 localStorage 对应的存储中加载（这里简化为文件存储）
            from pathlib import Path
            skill_file = Path(__file__).parent.parent.parent / "data" / "user_skills.json"
            if skill_file.exists():
                with open(skill_file, "r", encoding="utf-8") as f:
                    user_skills = json.load(f)
            else:
                # 尝试从 Skill Service 加载
                from src.skill import get_skill_service
                service = get_skill_service()
                user_skills = []

            query_lower = query.lower()
            for skill in user_skills:
                keywords = skill.get("trigger", {}).get("keywords", [])
                for kw in keywords:
                    if kw.lower() in query_lower:
                        return skill
        except Exception as e:
            logger.debug(f"Failed to match user skill: {e}")
        return None

    async def _handle_visualization(
        self,
        query: str,
        trace: List[Dict],
    ) -> AgentServiceResult:
        """处理可视化请求"""
        import time

        viz_start = time.time()
        viz_result = await self.viz_service.visualize(query)
        viz_time = int((time.time() - viz_start) * 1000)

        trace.append({
            "step_id": len(trace) + 1,
            "step_type": "visualization",
            "agent_name": "VisualizationAgent",
            "action": "generate_chart",
            "reasoning": f"生成图表: {viz_result.title}",
            "duration_ms": viz_time,
            "status": "success" if viz_result.success else "failed",
        })

        if viz_result.success:
            return AgentServiceResult(
                success=True,
                message=f"📊 **{viz_result.title}**\n\n{viz_result.description}",
                intent="visualization",
                chart_data={
                    "base64": viz_result.chart_base64,
                    "title": viz_result.title,
                    "description": viz_result.description,
                },
                confidence=viz_result.intent.confidence if viz_result.intent else 0.8,
            )

        return AgentServiceResult(
            success=False,
            message=f"可视化生成失败: {viz_result.error}",
            intent="visualization",
            confidence=0.3,
        )

    async def _handle_network_viz(
        self,
        query: str,
        trace: List[Dict],
    ) -> AgentServiceResult:
        """处理网络可视化请求"""
        import time
        import re

        # Step 1: 解析查询参数
        parse_start = time.time()

        # 解析地区
        region_map = {
            "乌克兰": "UKRAINE", "ukraine": "UKRAINE",
            "俄罗斯": "RUSSIA", "russia": "RUSSIA", "rus": "RUSSIA",
            "中国": "CHINA", "china": "CHINA",
            "美国": "US", "usa": "US", "us": "US",
            "日本": "JAPAN", "japan": "JAPAN",
            "德国": "GERMANY", "germany": "GERMANY",
            "法国": "FRANCE", "france": "FRANCE",
            "英国": "UK", "uk": "UK", "britain": "UK",
            "巴西": "BRAZIL", "brazil": "BRAZIL",
            "印度": "INDIA", "india": "INDIA",
            "澳大利亚": "AUSTRALIA", "australia": "AUSTRALIA",
        }

        region = None
        query_lower = query.lower()
        for key, value in region_map.items():
            if key in query_lower:
                region = value
                break

        parse_time = int((time.time() - parse_start) * 1000)

        # 添加解析步骤
        trace.append({
            "step_id": len(trace) + 1,
            "step_type": "analysis",
            "agent_name": "QueryParser",
            "action": "parse_region",
            "reasoning": f"从查询中识别地区: {region or '未识别'}",
            "duration_ms": parse_time,
            "status": "success" if region else "warning",
        })

        if not region:
            return AgentServiceResult(
                success=False,
                message="请指定要分析的地区，如：UKRAINE、RUSSIA、CHINA 等",
                intent="network_viz",
                confidence=0.5,
            )

        # Step 2: 匹配 Skill
        skill_start = time.time()
        action = self._detect_network_action(query)

        # 获取对应的 Skill 名称
        skill_name_map = {
            "trace_terminal_analysis": "末端节点分析",
            "trace_path_analysis": "路径分析",
            "ping_overall": "Ping 统计分析",
            "ping_trend": "Ping 趋势分析",
            "ping_by_asn": "AS 级延迟分析",
            "ping_by_asgeo": "ASGeo 级延迟分析",
            "region_overview": "地区网络概览",
            "trace_path_ping_trend": "路径 Ping 时序分析",
        }
        skill_name = skill_name_map.get(action, "网络可视化分析")

        skill_time = int((time.time() - skill_start) * 1000)

        trace.append({
            "step_id": len(trace) + 1,
            "step_type": "router",
            "agent_name": "SkillMatcher",
            "action": "match_skill",
            "reasoning": f"匹配到技能: {skill_name} (action: {action})",
            "duration_ms": skill_time,
            "status": "success",
        })

        # Step 3: 解析路径类型
        path_type = "asgeo" if "asgeo" in query_lower else "as"

        # 解析路径（如果需要）
        path = None
        path_match = re.search(r'(AS\d+[->\s]+(?:AS\d+[->\s]*)*AS?\d*)', query, re.IGNORECASE)
        if path_match:
            path = path_match.group(1).replace(" ", "->").replace("->", "->")
            # 标准化路径格式
            if not path.startswith("AS"):
                path = "AS" + path

        # Step 4: 构建工具参数
        param_start = time.time()
        params = {
            "action": action,
            "region": region,
            "path_type": path_type,
        }
        if path:
            params["path"] = path
        param_time = int((time.time() - param_start) * 1000)

        trace.append({
            "step_id": len(trace) + 1,
            "step_type": "analysis",
            "agent_name": "ParamBuilder",
            "action": "build_params",
            "reasoning": f"构建工具参数: region={region}, action={action}, path_type={path_type}",
            "duration_ms": param_time,
            "status": "success",
        })

        # Step 5: 调用网络可视化工具
        tool_start = time.time()
        try:
            from src.tools.plugins.network_viz_tool import NetworkVisualizationTool

            tool = NetworkVisualizationTool()

            trace.append({
                "step_id": len(trace) + 1,
                "step_type": "tool",
                "agent_name": "NetworkVisualizationTool",
                "action": "initialize",
                "reasoning": f"初始化工具: NetworkVisualizationTool",
                "duration_ms": 0,
                "status": "success",
            })

            result = await tool.execute(**params)
            tool_time = int((time.time() - tool_start) * 1000)

            # 添加详细的工具调用结果
            result_summary = ""
            if result.success and result.data:
                data = result.data.get("data")
                if isinstance(data, list):
                    result_summary = f"返回 {len(data)} 条记录"
                elif isinstance(data, dict):
                    result_summary = f"返回数据: {list(data.keys())[:5]}"

            trace.append({
                "step_id": len(trace) + 1,
                "step_type": "tool",
                "agent_name": "NetworkVisualizationTool",
                "action": action,
                "tool_parameters": params,
                "tool_result_summary": result_summary,
                "reasoning": f"执行 {skill_name}: region={region}, 耗时 {tool_time}ms",
                "duration_ms": tool_time,
                "status": "success" if result.success else "failed",
            })

            if result.success and result.data:
                data = result.data
                chart_data = data.get("chart_data")
                chart_base64 = data.get("chart_base64")

                # Step 6: 格式化响应
                format_start = time.time()
                message = self._format_network_viz_message(data)
                format_time = int((time.time() - format_start) * 1000)

                trace.append({
                    "step_id": len(trace) + 1,
                    "step_type": "analysis",
                    "agent_name": "ResponseFormatter",
                    "action": "format_response",
                    "reasoning": "格式化分析结果为用户可读格式",
                    "duration_ms": format_time,
                    "status": "success",
                })

                # 构建图表数据
                result_chart_data = {
                    "structured": {
                        "type": action,
                        "data": data.get("data"),
                        "region": region,
                    },
                }

                # 添加 base64 图像
                if chart_base64:
                    result_chart_data["base64"] = chart_base64

                # 添加结构化图表数据
                if chart_data:
                    result_chart_data.update(chart_data)

                # 添加 ECharts 兼容数据
                result_data = data.get("data")
                if action == "trace_terminal_analysis" and result_data:
                    terminals = result_data.get("terminals", []) if isinstance(result_data, dict) else (result_data if isinstance(result_data, list) else [])
                    if terminals:
                        result_chart_data["x_axis"] = [t.get("terminal", "N/A")[:30] for t in terminals[:15]]
                        result_chart_data["series"] = [{
                            "name": "路径数",
                            "data": [t.get("trace_count", 0) for t in terminals[:15]]
                        }]
                        result_chart_data["chart_type"] = "bar"
                        result_chart_data["y_axis_name"] = "路径数"
                        result_chart_data["summary"] = {
                            "data_points": len(terminals),
                        }

                elif action == "trace_path_analysis" and result_data:
                    paths = result_data.get("paths", []) if isinstance(result_data, dict) else (result_data if isinstance(result_data, list) else [])
                    if paths:
                        result_chart_data["x_axis"] = [p.get("path", "N/A")[:40] for p in paths[:15]]
                        result_chart_data["series"] = [{
                            "name": "路径数",
                            "data": [p.get("occurrence_count", 0) for p in paths[:15]]
                        }]
                        result_chart_data["chart_type"] = "bar"
                        result_chart_data["y_axis_name"] = "路径数"

                elif action == "ping_trend" and result_data:
                    # result_data 可能是 list 或 dict
                    time_series = result_data if isinstance(result_data, list) else result_data.get("time_series", [])
                    if time_series:
                        # 只取最近 48 个数据点，避免图表过于密集
                        display_series = time_series[-48:] if len(time_series) > 48 else time_series
                        result_chart_data["x_axis"] = [t.get("time", "")[:16] for t in display_series]
                        result_chart_data["series"] = [{
                            "name": "平均 RTT (ms)",
                            "data": [t.get("mean_rtt") or t.get("mean") or 0 for t in display_series]
                        }]
                        result_chart_data["chart_type"] = "line"
                        result_chart_data["y_axis_name"] = "RTT (ms)"
                        result_chart_data["summary"] = {
                            "data_points": len(time_series),
                            "time_range": f"{time_series[0].get('time', '')[:10]} ~ {time_series[-1].get('time', '')[:10]}" if time_series else "",
                        }

                elif action == "ping_by_asgeo" and result_data:
                    # ASGeo 延迟分析
                    items = result_data if isinstance(result_data, list) else []
                    if items:
                        # 按 mean_rtt 排序（最低延迟在前）
                        sorted_items = sorted(items, key=lambda x: x.get("mean_rtt", 0) or 0)
                        result_chart_data["x_axis"] = [item.get("asgeo", "N/A")[:25] for item in sorted_items[:15]]
                        result_chart_data["series"] = [{
                            "name": "平均 RTT (ms)",
                            "data": [item.get("mean_rtt", 0) or 0 for item in sorted_items[:15]]
                        }]
                        result_chart_data["chart_type"] = "bar"
                        result_chart_data["y_axis_name"] = "RTT (ms)"
                        result_chart_data["summary"] = {
                            "data_points": len(items),
                            "lowest_asgeo": sorted_items[0].get("asgeo", "N/A") if sorted_items else None,
                            "lowest_rtt": sorted_items[0].get("mean_rtt", 0) if sorted_items else 0,
                        }

                elif action == "ping_by_asn" and result_data:
                    # AS 延迟分析
                    items = result_data if isinstance(result_data, list) else []
                    if items:
                        sorted_items = sorted(items, key=lambda x: x.get("mean_rtt", 0) or 0)
                        result_chart_data["x_axis"] = [f"AS{item.get('asn', 'N/A')}" for item in sorted_items[:15]]
                        result_chart_data["series"] = [{
                            "name": "平均 RTT (ms)",
                            "data": [item.get("mean_rtt", 0) or 0 for item in sorted_items[:15]]
                        }]
                        result_chart_data["chart_type"] = "bar"
                        result_chart_data["y_axis_name"] = "RTT (ms)"

                # Step 7: 使用 LLM 分析数据，生成智能解读
                analysis_start = time.time()
                ai_analysis, token_usage = await self._analyze_network_data_with_llm(
                    query=query,
                    action=action,
                    region=region,
                    data=data.get("data"),
                )
                analysis_time = int((time.time() - analysis_start) * 1000)

                if ai_analysis:
                    trace.append({
                        "step_id": len(trace) + 1,
                        "step_type": "llm",
                        "agent_name": "AnalysisLLMAgent",
                        "action": "analyze_network_data",
                        "reasoning": "使用 AI 分析网络数据，生成智能解读",
                        "duration_ms": analysis_time,
                        "status": "success",
                        "tokens": token_usage,
                    })
                    # 将 AI 分析添加到消息中
                    message = f"{message}\n\n---\n\n## 🤖 AI 分析\n\n{ai_analysis}"

                # 计算 token 使用总量
                total_token_usage = token_usage if token_usage else {}

                return AgentServiceResult(
                    success=True,
                    message=message,
                    intent="network_viz",
                    chart_data=result_chart_data,
                    confidence=0.9,
                    token_usage=total_token_usage,
                )

            return AgentServiceResult(
                success=False,
                message=f"网络可视化分析失败: {result.error}",
                intent="network_viz",
                confidence=0.3,
            )

        except Exception as e:
            logger.error(f"Network visualization failed: {e}")
            trace.append({
                "step_id": len(trace) + 1,
                "step_type": "tool",
                "agent_name": "NetworkVisualizationTool",
                "action": action,
                "reasoning": f"网络可视化失败: {str(e)}",
                "duration_ms": int((time.time() - tool_start) * 1000),
                "status": "failed",
            })

            return AgentServiceResult(
                success=False,
                message=f"网络可视化分析出错: {str(e)}",
                intent="network_viz",
                confidence=0.3,
            )

    def _detect_network_action(self, query: str) -> str:
        """检测网络可视化操作类型"""
        query_lower = query.lower()

        # 最高优先级：明确指定 ASGeo + RTT/延迟查询
        if "asgeo" in query_lower:
            if any(kw in query_lower for kw in ["rtt", "延迟", "延时", "平均", "最低", "最高", "latency"]):
                return "ping_by_asgeo"
            elif "末端" in query_lower:
                # 末端 ASGeo + 延迟相关 → 需要 ping_by_asgeo 来获取延迟数据
                return "ping_by_asgeo"
            return "ping_by_asgeo"

        # 明确指定 AS + RTT/延迟查询
        if "as" in query_lower and "asgeo" not in query_lower:
            if any(kw in query_lower for kw in ["rtt", "延迟", "延时", "平均", "最低", "最高", "latency"]):
                return "ping_by_asn"

        # 末端节点 + 延迟相关关键词 → 查询 Ping 数据
        if "末端" in query_lower or "terminal" in query_lower:
            if any(kw in query_lower for kw in ["rtt", "延迟", "延时", "平均", "最低", "最高", "latency"]):
                # 如果提到 ASGeo，用 ping_by_asgeo
                if "asgeo" in query_lower:
                    return "ping_by_asgeo"
                # 默认用 ping_by_asgeo，因为末端节点通常是地理维度
                return "ping_by_asgeo"
            # 只有末端节点，没有延迟关键词
            return "trace_terminal_analysis"

        # RTT/延迟查询，没有指定维度
        if any(kw in query_lower for kw in ["rtt", "延迟", "延时"]):
            if "平均" in query_lower or "最低" in query_lower or "最高" in query_lower:
                # 如果问最低/最高/平均，需要按维度分析
                return "ping_by_asgeo"  # 默认按 ASGeo 维度
            return "ping_overall"

        # Ping 趋势
        if "ping趋势" in query_lower or "ping时序" in query_lower or "rtt趋势" in query_lower:
            return "ping_trend"

        # 路径详情
        if "路径详情" in query_lower and ("ping" in query_lower or "时序" in query_lower):
            return "trace_path_ping_trend"
        if "路径" in query_lower and "详情" in query_lower:
            return "trace_path_detail"
        if "路径" in query_lower or "path" in query_lower or "as路径" in query_lower:
            return "trace_path_analysis"

        # Ping 查询
        if "ping" in query_lower:
            if "数据中心" in query_lower or "datacenter" in query_lower:
                return "ping_by_datacenter"
            return "ping_overall"

        # 概览
        if "概览" in query_lower or "overview" in query_lower:
            return "region_overview"

        # 稳定性
        if "稳定" in query_lower:
            return "trace_terminal_analysis"

        return "region_overview"

    def _format_network_viz_message(self, data: dict) -> str:
        """格式化网络可视化消息"""
        action = data.get("action", "")
        region = data.get("region", "")
        title = data.get("title", "")
        result_data = data.get("data", {})

        lines = [f"## 📊 {title}", ""]

        if action == "region_overview":
            ping_stats = result_data.get("ping_stats", {})
            if ping_stats and not ping_stats.get("error"):
                lines.append("### Ping 统计")
                lines.append(f"- 平均 RTT: {ping_stats.get('mean_rtt', 0):.2f} ms")
                lines.append(f"- 中位数 RTT: {ping_stats.get('median_rtt', 0):.2f} ms")
                lines.append(f"- 样本数: {ping_stats.get('total_samples', 0):,}")
                lines.append("")

            trace_stats = result_data.get("trace_stats", [])
            if trace_stats:
                lines.append(f"### 路径统计 (Top 5)")
                lines.append("| 路径 | 路径数 |")
                lines.append("|------|--------|")
                for item in trace_stats[:5]:
                    path = item.get("path", "")[:50]
                    lines.append(f"| {path}... | {item.get('occurrence_count', 0):,} |")

        elif action == "trace_terminal_analysis":
            # result_data 是 dict，包含 terminals 列表
            terminals = result_data.get("terminals", []) if isinstance(result_data, dict) else (result_data if isinstance(result_data, list) else [])
            if terminals:
                lines.append(f"| 末端节点 | 路径数 | Prefix24数 |")
                lines.append("|----------|--------|------------|")
                for item in terminals[:15]:
                    terminal = item.get("terminal", "")[:40]
                    lines.append(f"| {terminal} | {item.get('trace_count', 0):,} | {item.get('prefix24_count', 0)} |")

        elif action == "trace_path_analysis":
            paths = result_data.get("paths", [])
            if paths:
                lines.append(f"| 路径 | 路径数 |")
                lines.append("|------|--------|")
                for item in paths[:15]:
                    path = item.get("path", "")[:60]
                    lines.append(f"| {path}... | {item.get('occurrence_count', 0):,} |")

        elif action in ["ping_trend", "trace_path_ping_trend"]:
            # result_data 可能是 list 或 dict
            time_series = result_data if isinstance(result_data, list) else result_data.get("time_series", [])
            summary = result_data.get("summary", {}) if isinstance(result_data, dict) else {}

            if time_series:
                # 计算摘要统计
                total_samples = sum(t.get("sample_count", 0) for t in time_series)
                avg_rtt = sum(t.get("mean_rtt", 0) or 0 for t in time_series) / len(time_series) if time_series else 0
                min_rtt = min((t.get("min_rtt", 0) or 0 for t in time_series), default=0)
                max_rtt = max((t.get("max_rtt", 0) or 0 for t in time_series), default=0)

                lines.append("### 趋势统计摘要")
                lines.append(f"- 数据点数: {len(time_series)}")
                lines.append(f"- 总样本数: {total_samples:,}")
                lines.append(f"- 平均 RTT: {avg_rtt:.2f} ms")
                lines.append(f"- 最小 RTT: {min_rtt:.2f} ms")
                lines.append(f"- 最大 RTT: {max_rtt:.2f} ms")
                lines.append("")
                lines.append(f"时间范围: {time_series[0].get('time', '')[:10]} ~ {time_series[-1].get('time', '')[:10]}")

            if summary:
                lines.append("### 额外统计")
                lines.append(f"- 总样本数: {summary.get('total_samples', 0):,}")
                lines.append(f"- 平均 RTT: {summary.get('mean_rtt', 0):.2f} ms")

        elif action == "ping_overall":
            if result_data and not result_data.get("error"):
                lines.append("### RTT 统计")
                lines.append(f"- 平均: {result_data.get('mean_rtt', 0):.2f} ms")
                lines.append(f"- 中位数: {result_data.get('median_rtt', 0):.2f} ms")
                lines.append(f"- P90: {result_data.get('percentiles', {}).get('p90', 0):.2f} ms")
                lines.append(f"- P95: {result_data.get('percentiles', {}).get('p95', 0):.2f} ms")
                lines.append(f"- 样本数: {result_data.get('total_samples', 0):,}")

        elif action in ["ping_by_asn", "ping_by_asgeo"]:
            items = result_data if isinstance(result_data, list) else []
            if items:
                label = "AS" if action == "ping_by_asn" else "ASGeo"
                # 按平均 RTT 升序排序（最低延迟在前）
                sorted_items = sorted(items, key=lambda x: x.get("mean_rtt", 0) or 0)

                # 高亮最低延迟
                if sorted_items:
                    lowest = sorted_items[0]
                    lowest_name = lowest.get("asn" if action == "ping_by_asn" else "asgeo", "N/A")
                    lowest_rtt = lowest.get("mean_rtt", 0) or 0
                    lines.append(f"### 🏆 延迟最低: **{lowest_name}** (平均 {lowest_rtt:.2f} ms)")
                    lines.append("")

                lines.append(f"| 排名 | {label} | 平均 RTT | 中位数 RTT | 样本数 |")
                lines.append("|------|---------|----------|------------|--------|")
                for i, item in enumerate(sorted_items[:15], 1):
                    name = item.get("asn" if action == "ping_by_asn" else "asgeo", "N/A")
                    mean_rtt = item.get("mean_rtt", 0) or 0
                    median_rtt = item.get("median_rtt", 0) or 0
                    samples = item.get("sample_count", 0)
                    highlight = " ⭐" if i == 1 else ""
                    lines.append(f"| {i} | {name}{highlight} | {mean_rtt:.2f} ms | {median_rtt:.2f} ms | {samples:,} |")

        else:
            # 默认显示原始数据概要
            lines.append(f"操作: {action}")
            lines.append(f"地区: {region}")
            lines.append(f"数据类型: {type(result_data).__name__}")

        lines.append("")
        lines.append(f"📍 [在可视化页面查看详情](/visualization?region={region})")

        return "\n".join(lines)

    async def _analyze_network_data_with_llm(
        self,
        query: str,
        action: str,
        region: str,
        data: Any,
        provider: Optional[str] = None,
        model: Optional[str] = None,
    ) -> tuple:
        """使用 LLM 分析网络数据，生成智能解读"""
        import time

        if not data:
            return None, {}

        try:
            gateway = get_llm_gateway()

            # 根据不同操作类型构建不同的分析提示
            if action == "trace_terminal_analysis":
                # 末端节点分析
                terminals = data.get("terminals", []) if isinstance(data, dict) else (data if isinstance(data, list) else [])
                if not terminals:
                    return None, {}

                # 构建数据摘要
                top_terminals = terminals[:10]
                data_summary = f"""
**地区**: {region}
**末端节点数量**: {len(terminals)}

**Top 10 末端节点**:
"""
                for i, t in enumerate(top_terminals, 1):
                    terminal = t.get("terminal", "N/A")
                    trace_count = t.get("trace_count", 0)
                    prefix24_count = t.get("prefix24_count", 0)
                    data_summary += f"{i}. {terminal}: 路径数 {trace_count:,}, Prefix24数 {prefix24_count}\n"

                analysis_prompt = f"""你是一位网络性能分析专家。用户的问题是："{query}"

请基于以下末端节点数据进行分析：

{data_summary}

请从以下几个方面进行简洁、专业的分析（每点 2-3 句话）：

1. **关键发现**: 识别最主要的末端节点及其特征
2. **路径分布**: 分析路径集中度，是否存在主导路径
3. **网络拓扑洞察**: 从末端节点分布推断网络架构特点
4. **优化建议**: 针对该地区的网络优化建议

如果用户问的是"最低延迟"或"最稳定"，请根据路径数量和分布给出判断。"""

            elif action == "trace_path_analysis":
                # 路径分析
                paths = data.get("paths", []) if isinstance(data, dict) else (data if isinstance(data, list) else [])
                if not paths:
                    return None, {}

                top_paths = paths[:10]
                data_summary = f"""
**地区**: {region}
**路径数量**: {len(paths)}

**Top 10 路径**:
"""
                for i, p in enumerate(top_paths, 1):
                    path = p.get("path", "N/A")
                    count = p.get("occurrence_count", 0)
                    data_summary += f"{i}. {path}: {count:,} 次\n"

                analysis_prompt = f"""你是一位网络路径分析专家。用户的问题是："{query}"

请基于以下路径数据进行分析：

{data_summary}

请从以下几个方面进行简洁、专业的分析（每点 2-3 句话）：

1. **主要路径**: 识别最主要的网络路径
2. **路径多样性**: 分析路径的多样性程度
3. **AS 关系**: 分析路径中出现的 AS 及其关系
4. **可靠性评估**: 评估网络的整体可靠性"""

            elif action == "ping_overall":
                # Ping 整体统计
                if isinstance(data, dict) and not data.get("error"):
                    data_summary = f"""
**地区**: {region}
**平均 RTT**: {data.get('mean_rtt', 0):.2f} ms
**中位数 RTT**: {data.get('median_rtt', 0):.2f} ms
**最小 RTT**: {data.get('min_rtt', 0):.2f} ms
**最大 RTT**: {data.get('max_rtt', 0):.2f} ms
**标准差**: {data.get('std_rtt', 0):.2f} ms
**样本数**: {data.get('total_samples', 0):,}
**P90**: {data.get('percentiles', {}).get('p90', 0):.2f} ms
**P95**: {data.get('percentiles', {}).get('p95', 0):.2f} ms
"""
                else:
                    return None, {}

                analysis_prompt = f"""你是一位网络延迟分析专家。用户的问题是："{query}"

请基于以下延迟统计数据进行分析：

{data_summary}

请从以下几个方面进行简洁、专业的分析（每点 2-3 句话）：

1. **延迟水平评估**: 该地区的延迟是否正常？
2. **稳定性分析**: 根据标准差和分位数差异分析延迟稳定性
3. **异常检测**: 是否存在异常高延迟的情况？
4. **优化建议**: 针对该地区的优化建议"""

            elif action == "ping_trend":
                # Ping 趋势分析
                time_series = data if isinstance(data, list) else data.get("time_series", [])
                if not time_series:
                    return None, {}

                # 计算统计摘要
                avg_rtt = sum(t.get("mean_rtt", 0) or 0 for t in time_series) / len(time_series) if time_series else 0
                min_rtt = min((t.get("min_rtt", 0) or 0 for t in time_series), default=0)
                max_rtt = max((t.get("max_rtt", 0) or 0 for t in time_series), default=0)

                # 找出最高和最低延迟的时间点
                sorted_by_rtt = sorted(time_series, key=lambda x: x.get("mean_rtt", 0) or 0)
                lowest_point = sorted_by_rtt[0] if sorted_by_rtt else {}
                highest_point = sorted_by_rtt[-1] if sorted_by_rtt else {}

                data_summary = f"""
**地区**: {region}
**数据点数**: {len(time_series)}
**时间范围**: {time_series[0].get('time', '')[:10]} ~ {time_series[-1].get('time', '')[:10]}
**平均 RTT**: {avg_rtt:.2f} ms
**最小 RTT**: {min_rtt:.2f} ms
**最大 RTT**: {max_rtt:.2f} ms

**延迟最低时刻**: {lowest_point.get('time', 'N/A')[:16]} ({lowest_point.get('mean_rtt', 0):.2f} ms)
**延迟最高时刻**: {highest_point.get('time', 'N/A')[:16]} ({highest_point.get('mean_rtt', 0):.2f} ms)
"""

                analysis_prompt = f"""你是一位网络趋势分析专家。用户的问题是："{query}"

请基于以下 Ping 趋势数据进行分析：

{data_summary}

请从以下几个方面进行简洁、专业的分析（每点 2-3 句话）：

1. **趋势概览**: 整体延迟趋势如何？是否有明显波动？
2. **高峰时段**: 延迟最高的时段是何时？可能原因是什么？
3. **低峰时段**: 延迟最低的时段是何时？有何特点？
4. **优化建议**: 针对该趋势的优化建议"""

            elif action in ["ping_by_asn", "ping_by_asgeo"]:
                # AS/ASGeo 维度分析
                items = data if isinstance(data, list) else []
                if not items:
                    return None, {}

                label = "AS" if action == "ping_by_asn" else "ASGeo"
                # 按平均 RTT 升序排序（最低延迟在前）
                sorted_items = sorted(items, key=lambda x: x.get("mean_rtt", 0) or 0)
                lowest_items = sorted_items[:10]
                highest_items = sorted_items[-5:] if len(sorted_items) > 10 else []

                data_summary = f"""
**地区**: {region}
**分析维度**: {label}
**数量**: {len(items)}

**延迟最低的 Top 10 {label}**:
"""
                for i, item in enumerate(lowest_items, 1):
                    name = item.get("asn" if action == "ping_by_asn" else "asgeo", "N/A")
                    mean_rtt = item.get("mean_rtt", 0) or 0
                    median_rtt = item.get("median_rtt", 0) or 0
                    samples = item.get("sample_count", 0)
                    data_summary += f"{i}. {name}: 平均 {mean_rtt:.2f} ms, 中位数 {median_rtt:.2f} ms, 样本 {samples:,}\n"

                if highest_items:
                    data_summary += f"\n**延迟最高的 {label}**:\n"
                    for item in highest_items[-3:]:
                        name = item.get("asn" if action == "ping_by_asn" else "asgeo", "N/A")
                        mean_rtt = item.get("mean_rtt", 0) or 0
                        data_summary += f"- {name}: 平均 {mean_rtt:.2f} ms\n"

                # 判断用户意图
                if "最低" in query or "最低延迟" in query or "最低延迟" in query:
                    answer_hint = "用户在询问\"最低延迟\"，请明确指出哪个 ASGeo 延迟最低。"
                elif "最高" in query:
                    answer_hint = "用户在询问\"最高延迟\"，请明确指出哪个 ASGeo 延迟最高。"
                else:
                    answer_hint = ""

                analysis_prompt = f"""你是一位网络性能分析专家。用户的问题是："{query}"

{answer_hint}

请基于以下{label}维度的延迟数据进行分析：

{data_summary}

请从以下几个方面进行简洁、专业的分析（每点 2-3 句话）：

1. **直接回答**: 直接回答用户的问题，指出延迟最低/最高的{label}是哪个
2. **延迟分布**: 各{label}之间的延迟差异如何？
3. **可能原因**: 为什么某些{label}延迟较低/较高？
4. **选择建议**: 如果用户要选择最优路径，推荐哪些{label}？"""

            else:
                # 其他类型，使用通用分析
                data_summary = f"数据类型: {action}\n地区: {region}\n数据: {str(data)[:500]}"
                analysis_prompt = f"""你是一位网络分析专家。用户的问题是："{query}"

请简要分析以下数据：

{data_summary}

给出简洁的分析和建议。"""

            # 调用 LLM 生成分析
            llm_result = await gateway.generate(
                prompt=analysis_prompt,
                config=LLMConfig(
                    provider=provider or "deepseek",
                    model=model or "deepseek-chat",
                    max_tokens=1000,
                )
            )

            # 提取 token 使用信息
            token_usage = {
                "prompt_tokens": llm_result.usage.get("prompt_tokens", 0) if llm_result.usage else 0,
                "completion_tokens": llm_result.usage.get("completion_tokens", 0) if llm_result.usage else 0,
                "total_tokens": llm_result.usage.get("total_tokens", 0) if llm_result.usage else 0,
            }

            return llm_result.content, token_usage

        except Exception as e:
            logger.error(f"LLM analysis failed: {e}")
            return None, {}

    async def _handle_user_skill(
        self,
        query: str,
        skill_id: str,
        trace: List[Dict],
    ) -> AgentServiceResult:
        """处理用户自定义 Skill"""
        import time
        import json
        from pathlib import Path

        # 加载用户 Skill
        skill_file = Path(__file__).parent.parent.parent / "data" / "user_skills.json"
        user_skill = None
        if skill_file.exists():
            with open(skill_file, "r", encoding="utf-8") as f:
                user_skills = json.load(f)
                for s in user_skills:
                    if s.get("id") == skill_id:
                        user_skill = s
                        break

        if not user_skill:
            return AgentServiceResult(
                success=False,
                message=f"未找到自定义 Skill: {skill_id}",
                intent="user_skill",
                confidence=0.3,
            )

        # 获取工作流配置
        workflow = user_skill.get("workflow", [])
        if not workflow:
            return AgentServiceResult(
                success=False,
                message=f"Skill {user_skill.get('name')} 没有配置工作流",
                intent="user_skill",
                confidence=0.3,
            )

        # 执行工作流
        step = workflow[0]
        tool_name = step.get("config", {}).get("tool", "network_viz")
        action = step.get("config", {}).get("action", "ping_overall")

        # 解析地区（从查询中提取）
        region_map = {
            "乌克兰": "UKRAINE", "ukraine": "UKRAINE",
            "俄罗斯": "RUSSIA", "russia": "RUSSIA", "rus": "RUSSIA",
            "中国": "CHINA", "china": "CHINA",
            "美国": "US", "usa": "US",
            "日本": "JAPAN", "japan": "JAPAN",
            "德国": "GERMANY", "germany": "GERMANY",
            "法国": "FRANCE", "france": "FRANCE",
            "英国": "UK", "uk": "UK",
        }
        region = "UKRAINE"  # 默认
        query_lower = query.lower()
        for key, value in region_map.items():
            if key in query_lower:
                region = value
                break

        tool_start = time.time()
        try:
            if tool_name == "network_viz":
                from src.tools.plugins.network_viz_tool import NetworkVisualizationTool
                tool = NetworkVisualizationTool()
                params = {"action": action, "region": region}
                result = await tool.execute(**params)

                tool_time = int((time.time() - tool_start) * 1000)

                trace.append({
                    "step_id": len(trace) + 1,
                    "step_type": "user_skill",
                    "agent_name": f"UserSkill:{user_skill.get('name')}",
                    "action": action,
                    "tool_parameters": params,
                    "reasoning": f"执行用户自定义 Skill: {user_skill.get('name')}",
                    "duration_ms": tool_time,
                    "status": "success" if result.success else "failed",
                })

                if result.success and result.data:
                    message = self._format_network_viz_message(result.data)
                    return AgentServiceResult(
                        success=True,
                        message=message,
                        intent="user_skill",
                        chart_data=result.data.get("chart_data"),
                        confidence=0.85,
                        trace=trace,
                    )

            return AgentServiceResult(
                success=False,
                message=f"Skill 执行失败",
                intent="user_skill",
                confidence=0.5,
            )

        except Exception as e:
            logger.error(f"Failed to execute user skill: {e}")
            return AgentServiceResult(
                success=False,
                message=f"执行 Skill 时出错: {str(e)}",
                intent="user_skill",
                confidence=0.3,
            )

    async def _handle_query(
        self,
        query: str,
        trace: List[Dict],
        provider: Optional[str] = None,
        model: Optional[str] = None,
    ) -> AgentServiceResult:
        """处理查询请求"""
        import time
        import re

        # 检测是否是数据查询请求
        data_query_patterns = [
            r"数据库", r"查询.*数据", r"统计", r"平均值", r"平均\s*rtt",
            r"rtt", r"延迟", r"丢包", r"抖动",
            r"(ukraine|乌克兰|rus|俄罗斯|china|中国|us|美国)",
            r"ping.*数据", r"traceroute", r"路径", r"末端",
        ]

        is_data_query = any(re.search(p, query, re.IGNORECASE) for p in data_query_patterns)

        # 如果是数据查询，尝试调用数据库工具
        if is_data_query:
            db_result = await self._handle_data_query(query, trace, provider, model)
            if db_result:
                return db_result

        # 知识检索
        search_start = time.time()
        service = get_knowledge_service()
        search_result = await service.search(query, top_k=5)
        search_time = int((time.time() - search_start) * 1000)

        trace.append({
            "step_id": len(trace) + 1,
            "step_type": "retrieval",
            "agent_name": "KnowledgeAgent",
            "action": "search_knowledge",
            "reasoning": f"检索知识库，找到 {len(search_result.results)} 条结果",
            "duration_ms": search_time,
            "status": "success",
        })

        if search_result.results:
            knowledge = "\n\n---\n\n".join([
                f"**{r.metadata.get('doc_title', '知识库')}**\n{r.content}"
                for r in search_result.results[:3]
            ])

            return AgentServiceResult(
                success=True,
                message=f"📚 **知识检索结果**\n\n{knowledge}",
                intent="query",
                knowledge=knowledge,
                confidence=0.85,
            )

        # 知识库为空时，使用 LLM 直接回答
        llm_start = time.time()
        try:
            gateway = get_llm_gateway()
            llm_result = await gateway.generate(
                prompt=query,
                config=LLMConfig(
                    provider=provider or "bupt",
                    model=model or "deepseek-chat",
                    max_tokens=1024,
                )
            )
            llm_time = int((time.time() - llm_start) * 1000)

            # 收集 token 使用信息
            token_usage = {
                "prompt_tokens": llm_result.usage.get("prompt_tokens", 0),
                "completion_tokens": llm_result.usage.get("completion_tokens", 0),
                "total_tokens": llm_result.usage.get("prompt_tokens", 0) + llm_result.usage.get("completion_tokens", 0),
            }

            trace.append({
                "step_id": len(trace) + 1,
                "step_type": "llm",
                "agent_name": "ChatLLMAgent",
                "action": "generate_response",
                "reasoning": "使用 LLM 直接回答（知识库无相关内容）",
                "duration_ms": llm_time,
                "status": "success",
                "tokens": token_usage,
            })

            return AgentServiceResult(
                success=True,
                message=llm_result.content,
                intent="query",
                confidence=0.7,
                token_usage=token_usage,
            )
        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            return AgentServiceResult(
                success=True,
                message="知识库暂无相关内容。您可以尝试上传相关文档到知识库，或稍后再试。",
                intent="query",
                confidence=0.5,
            )

    async def _handle_data_query(
        self,
        query: str,
        trace: List[Dict],
        provider: Optional[str] = None,
        model: Optional[str] = None,
    ) -> Optional[AgentServiceResult]:
        """处理数据查询请求 - 支持多维度智能分析"""
        import time
        import re
        from datetime import datetime

        # 解析地区
        region_map = {
            "乌克兰": "UKRAINE", "ukraine": "UKRAINE",
            "俄罗斯": "RUSSIA", "russia": "RUSSIA", "rus": "RUSSIA",
            "中国": "CHINA", "china": "CHINA",
            "美国": "US", "usa": "US", "us": "US",
        }

        region = None
        for key, value in region_map.items():
            if key in query.lower():
                region = value
                break

        if not region:
            return None

        # 解析查询意图
        query_lower = query.lower()

        # 识别分析维度
        dimension = "overall"  # 默认整体分析
        if "as" in query_lower or "自治系统" in query or "运营商" in query:
            dimension = "asn"
        elif "asgeo" in query_lower or "地区" in query or "国家" in query:
            dimension = "asgeo"
        elif "前缀" in query or "prefix" in query_lower:
            dimension = "prefix24"

        # 识别排序方式
        sort_by = "sample_count"  # 默认按样本数
        if "最高" in query or "高延迟" in query or "最差" in query:
            sort_by = "mean_rtt_desc"
        elif "最低" in query or "低延迟" in query or "最好" in query:
            sort_by = "mean_rtt_asc"
        elif "最多" in query or "样本最多" in query:
            sort_by = "sample_count"

        # 解析时间范围
        start_time = None
        end_time = None
        time_match = re.search(r'(\d{4})年(\d{1,2})月?', query)
        if time_match:
            year = int(time_match.group(1))
            month = int(time_match.group(2))
            start_time = datetime(year, month, 1)
            if month == 12:
                end_time = datetime(year + 1, 1, 1)
            else:
                end_time = datetime(year, month + 1, 1)

        # 调用 ClickHouse 分析器
        db_start = time.time()
        try:
            from src.clickhouse import get_clickhouse_client
            from src.clickhouse.analyzer import PingAnalyzer, AnalysisConfig

            client = get_clickhouse_client()
            analyzer = PingAnalyzer(client)
            config = AnalysisConfig(percentiles=[50, 90, 95, 99])

            # 根据维度选择分析方法
            if dimension == "asn":
                data = analyzer.analyze_by_asn(
                    region=region,
                    top_n=20,
                    start_time=start_time,
                    end_time=end_time,
                    config=config
                )

                # 按延迟排序
                if sort_by == "mean_rtt_desc":
                    data = sorted(data, key=lambda x: x.get('mean_rtt', 0) or 0, reverse=True)
                elif sort_by == "mean_rtt_asc":
                    data = sorted(data, key=lambda x: x.get('mean_rtt', 0) or 0)

                db_time = int((time.time() - db_start) * 1000)
                trace.append({
                    "step_id": len(trace) + 1,
                    "step_type": "database",
                    "agent_name": "DataQueryAgent",
                    "action": "query_by_asn",
                    "reasoning": f"查询 {region} 地区按 AS 分组的延迟数据，按 {sort_by} 排序",
                    "duration_ms": db_time,
                    "status": "success",
                })

                if not data:
                    # 数据库查询返回空结果
                    time_info = ""
                    if start_time:
                        time_info = f"（时间范围: {start_time.strftime('%Y年%m月')}）"
                    return AgentServiceResult(
                        success=True,
                        message=f"📊 **{region} 地区 AS 数据查询结果**\n\n查询{time_info}未找到数据。可能原因：\n1. 指定的时间范围内没有测量数据\n2. 该地区暂无 AS 级别的统计数据\n\n请尝试：\n- 不指定时间范围，查询所有可用数据\n- 更换其他时间范围\n- 查询其他地区",
                        intent="query",
                        confidence=0.8,
                    )

                if data:
                    # 格式化 AS 维度数据
                    top_count = min(10, len(data))
                    table_rows = []
                    for i, item in enumerate(data[:top_count], 1):
                        asn = item.get('asn', 'N/A')
                        as_name = item.get('as_name', 'Unknown')[:30] if item.get('as_name') else 'Unknown'
                        table_rows.append(
                            f"| {i} | AS{asn} | {as_name} | {item.get('mean_rtt', 0):.2f} | {item.get('median_rtt', 0):.2f} | "
                            f"{item.get('min_rtt', 0):.2f} | {item.get('max_rtt', 0):.2f} | {item.get('sample_count', 0):,} |"
                        )

                    data_table = f"""📊 **{region} 地区 AS 延迟排名 (Top {top_count})**

| 排名 | AS 号 | AS 名称 | 平均 RTT | 中位数 RTT | 最小 RTT | 最大 RTT | 样本数 |
|------|-------|---------|----------|------------|----------|----------|--------|
{chr(10).join(table_rows)}

**统计概况:**
- 共 {len(data)} 个 AS
- 最高延迟: AS{data[0].get('asn', 'N/A')} ({data[0].get('mean_rtt', 0):.2f} ms)
- 最低延迟: AS{data[-1].get('asn', 'N/A')} ({data[-1].get('mean_rtt', 0):.2f} ms)
"""

                    # LLM 分析
                    analysis_result = await self._analyze_as_data(query, data, region, trace, provider, model)
                    if analysis_result:
                        return analysis_result

                    return AgentServiceResult(
                        success=True,
                        message=data_table,
                        intent="query",
                        confidence=0.9,
                    )

            elif dimension == "overall":
                stats = analyzer.analyze_overall(region=region, config=config, start_time=start_time, end_time=end_time)
                db_time = int((time.time() - db_start) * 1000)

                trace.append({
                    "step_id": len(trace) + 1,
                    "step_type": "database",
                    "agent_name": "DataQueryAgent",
                    "action": "query_overall",
                    "reasoning": f"查询 {region} 地区的整体统计数据",
                    "duration_ms": db_time,
                    "status": "success",
                })

                if stats and not stats.get("error"):
                    data_table = self._format_overall_stats(stats, region)
                    analysis_result = await self._analyze_overall_data(query, stats, region, trace, provider, model)
                    if analysis_result:
                        return analysis_result
                    return AgentServiceResult(success=True, message=data_table, intent="query", confidence=0.9)

            else:
                # 其他维度暂不支持
                return None

        except Exception as e:
            logger.error(f"Data query failed: {e}")
            trace.append({
                "step_id": len(trace) + 1,
                "step_type": "database",
                "agent_name": "DataQueryAgent",
                "action": "query_failed",
                "reasoning": f"数据库查询失败: {str(e)}",
                "duration_ms": int((time.time() - db_start) * 1000),
                "status": "failed",
            })

        return None

    def _format_overall_stats(self, stats: dict, region: str) -> str:
        """格式化整体统计数据 - 紧凑版"""
        cv = (stats.get('coefficient_of_variation', 0) or 0) * 100
        return f"""📊 **{region} 地区网络延迟统计**

| 指标 | 数值 | | 指标 | 数值 |
|------|------|---|------|------|
| 平均 RTT | {stats.get('mean_rtt', 0):.2f} ms | | 中位数 RTT | {stats.get('median_rtt', 0):.2f} ms |
| 最小 RTT | {stats.get('min_rtt', 0):.2f} ms | | 最大 RTT | {stats.get('max_rtt', 0):.2f} ms |
| 标准差 | {stats.get('std_rtt', 0):.2f} ms | | 变异系数 | {cv:.1f}% |
| 偏度 | {stats.get('skewness', 0):.3f} | | 峰度 | {stats.get('kurtosis', 0):.3f} |
| 样本数 | {stats.get('total_samples', 0):,} | | IQR | {stats.get('iqr', 0):.2f} ms |

**分位数:** P50={stats.get('percentiles', {}).get('p50', 0):.1f}ms | P90={stats.get('percentiles', {}).get('p90', 0):.1f}ms | P95={stats.get('percentiles', {}).get('p95', 0):.1f}ms | P99={stats.get('percentiles', {}).get('p99', 0):.1f}ms
"""

    async def _analyze_as_data(
        self,
        query: str,
        data: list,
        region: str,
        trace: List[Dict],
        provider: Optional[str] = None,
        model: Optional[str] = None,
    ) -> Optional[AgentServiceResult]:
        """分析 AS 维度数据"""
        import time

        if not data:
            return None

        analysis_start = time.time()
        try:
            gateway = get_llm_gateway()

            # 构建数据摘要
            top_as = data[:5]
            summary = f"""
**地区**: {region}
**AS 数量**: {len(data)}

**延迟最高的 AS (Top 5)**:
"""
            for i, item in enumerate(top_as, 1):
                summary += f"{i}. AS{item.get('asn', 'N/A')} - {item.get('as_name', 'Unknown')[:20]}: 平均 {item.get('mean_rtt', 0):.2f} ms, 样本 {item.get('sample_count', 0):,}\n"

            analysis_prompt = f"""你是一位网络性能分析专家。请基于以下 AS 级别的网络延迟数据进行分析。

{summary}

请从以下方面进行简洁分析（每点 2-3 句话）：
1. **延迟分布特征**: 延迟最高的 AS 是哪些？差异有多大？
2. **可能原因**: 为什么这些 AS 延迟较高？
3. **优化建议**: 针对高延迟 AS 的建议"""

            llm_result = await gateway.generate(
                prompt=analysis_prompt,
                config=LLMConfig(
                    provider=provider or "bupt",
                    model=model or "deepseek-chat",
                    max_tokens=800,
                )
            )
            analysis_time = int((time.time() - analysis_start) * 1000)

            token_usage = {
                "prompt_tokens": llm_result.usage.get("prompt_tokens", 0),
                "completion_tokens": llm_result.usage.get("completion_tokens", 0),
                "total_tokens": llm_result.usage.get("prompt_tokens", 0) + llm_result.usage.get("completion_tokens", 0),
            }

            trace.append({
                "step_id": len(trace) + 1,
                "step_type": "analysis",
                "agent_name": "AnalysisLLMAgent",
                "action": "analyze_as_data",
                "reasoning": "分析 AS 延迟数据",
                "duration_ms": analysis_time,
                "status": "success",
                "tokens": token_usage,
            })

            # 格式化数据表格 - 紧凑版
            top_count = min(10, len(data))
            table_rows = []
            for i, item in enumerate(data[:top_count], 1):
                asn = item.get('asn', 'N/A')
                as_name = item.get('as_name', 'Unknown')[:25] if item.get('as_name') else 'Unknown'
                table_rows.append(
                    f"| {i} | AS{asn} | {as_name} | {item.get('mean_rtt', 0):.1f} | {item.get('median_rtt', 0):.1f} | "
                    f"{item.get('min_rtt', 0):.1f} | {item.get('max_rtt', 0):.1f} | {item.get('sample_count', 0):,} |"
                )

            data_table = f"""📊 **{region} 地区 AS 延迟排名**

| 排名 | AS号 | 名称 | 均值 | 中位数 | 最小 | 最大 | 样本 |
|------|------|------|------|--------|------|------|------|
{chr(10).join(table_rows)}
*共{len(data)}个AS | 最高AS{data[0].get('asn', 'N/A')}({data[0].get('mean_rtt', 0):.1f}ms) | 最低AS{data[-1].get('asn', 'N/A')}({data[-1].get('mean_rtt', 0):.1f}ms)*

**📈 分析:**
{llm_result.content}"""

            return AgentServiceResult(
                success=True,
                message=data_table,
                intent="query",
                confidence=0.9,
                token_usage=token_usage,
            )

        except Exception as e:
            logger.error(f"AS analysis failed: {e}")
            return None

    async def _analyze_overall_data(
        self,
        query: str,
        stats: dict,
        region: str,
        trace: List[Dict],
        provider: Optional[str] = None,
        model: Optional[str] = None,
    ) -> Optional[AgentServiceResult]:
        """分析整体数据"""
        import time

        analysis_start = time.time()
        try:
            gateway = get_llm_gateway()

            analysis_prompt = f"""你是一位网络性能分析专家。请基于以下网络延迟数据，进行专业的分析解读。

**地区**: {region}
**数据概览**:
- 平均 RTT: {stats.get('mean_rtt', 0):.2f} ms
- 中位数 RTT: {stats.get('median_rtt', 0):.2f} ms
- 变异系数: {(stats.get('coefficient_of_variation', 0) or 0) * 100:.1f}%
- 偏度: {stats.get('skewness', 0):.3f}
- 峰度: {stats.get('kurtosis', 0):.3f}

请从以下几个方面进行简洁分析（每点 2-3 句话）：
1. **整体延迟水平评估**: 该地区的延迟是否正常？
2. **延迟稳定性分析**: 根据变异系数、偏度等指标分析稳定性
3. **潜在问题诊断**: 可能存在哪些网络问题？
4. **优化建议**: 针对该地区的网络优化建议"""

            llm_result = await gateway.generate(
                prompt=analysis_prompt,
                config=LLMConfig(
                    provider=provider or "bupt",
                    model=model or "deepseek-chat",
                    max_tokens=800,
                )
            )
            analysis_time = int((time.time() - analysis_start) * 1000)

            token_usage = {
                "prompt_tokens": llm_result.usage.get("prompt_tokens", 0),
                "completion_tokens": llm_result.usage.get("completion_tokens", 0),
                "total_tokens": llm_result.usage.get("prompt_tokens", 0) + llm_result.usage.get("completion_tokens", 0),
            }

            trace.append({
                "step_id": len(trace) + 1,
                "step_type": "analysis",
                "agent_name": "AnalysisLLMAgent",
                "action": "analyze_overall_data",
                "reasoning": "分析整体网络数据",
                "duration_ms": analysis_time,
                "status": "success",
                "tokens": token_usage,
            })

            data_table = self._format_overall_stats(stats, region)
            message = f"""{data_table}

---

## 📈 数据分析

{llm_result.content}
"""

            return AgentServiceResult(
                success=True,
                message=message,
                intent="query",
                confidence=0.9,
                token_usage=token_usage,
            )

        except Exception as e:
            logger.error(f"Overall analysis failed: {e}")
            return None

    async def _handle_database_schema(
        self,
        query: str,
        trace: List[Dict],
        provider: Optional[str] = None,
        model: Optional[str] = None,
    ) -> AgentServiceResult:
        """处理数据库元数据查询 - 使用工具和 LLM 分析"""
        import time

        # Step 1: 调用数据库结构查询工具
        tool_start = time.time()
        try:
            from src.tools.plugins.database_schema_tool import DatabaseSchemaTool

            tool = DatabaseSchemaTool()
            tool_result = await tool.execute(action="get_overview")
            tool_time = int((time.time() - tool_start) * 1000)

            trace.append({
                "step_id": len(trace) + 1,
                "step_type": "tool",
                "agent_name": "DatabaseSchemaTool",
                "action": "get_overview",
                "reasoning": f"调用数据库结构查询工具: {tool_result.data.get('summary', 'OK') if tool_result.success else tool_result.error}",
                "duration_ms": tool_time,
                "status": "success" if tool_result.success else "failed",
            })

            if not tool_result.success:
                return AgentServiceResult(
                    success=False,
                    message=f"⚠️ 数据库查询失败: {tool_result.error}",
                    intent="database_schema",
                    confidence=0.3,
                )

            data = tool_result.data

            # Step 2: 使用 LLM 分析数据，生成自然语言回答
            analysis_start = time.time()
            try:
                gateway = get_llm_gateway()

                # 构建数据摘要
                regions_info = []
                for rd in data.get("regions", []):
                    regions_info.append(
                        f"- {rd['region']}: {rd['total_records']:,} 条记录, "
                        f"数据中心: {', '.join(rd['data_centers'][:3])}{'...' if len(rd['data_centers']) > 3 else ''}, "
                        f"时间: {rd['min_time']} ~ {rd['max_time']}"
                    )

                analysis_prompt = f"""你是一个网络测量数据系统的助手。用户问："{query}"

数据库查询结果：
- 总地区数: {data.get('total_regions', 0)}
- 总记录数: {data.get('total_records', 0):,}
- 各地区详情:
{chr(10).join(regions_info)}

请用自然、友好的语言回答用户的问题，包括：
1. 直接回答数据库中有哪些数据
2. 简要介绍每个地区的数据情况
3. 推荐几个用户可能感兴趣的查询方向

注意：用口语化的方式回答，不要用列表格式，像聊天一样自然。控制在 200 字以内。"""

                llm_result = await gateway.generate(
                    prompt=analysis_prompt,
                    config=LLMConfig(
                        provider=provider or "bupt",
                        model=model or "deepseek-chat",
                        max_tokens=500,
                    )
                )

                analysis_time = int((time.time() - analysis_start) * 1000)

                token_usage = {
                    "prompt_tokens": llm_result.usage.get("prompt_tokens", 0),
                    "completion_tokens": llm_result.usage.get("completion_tokens", 0),
                    "total_tokens": llm_result.usage.get("prompt_tokens", 0) + llm_result.usage.get("completion_tokens", 0),
                }

                trace.append({
                    "step_id": len(trace) + 1,
                    "step_type": "llm",
                    "agent_name": "ChatLLMAgent",
                    "action": "analyze_schema",
                    "reasoning": "使用 LLM 生成自然语言回答",
                    "duration_ms": analysis_time,
                    "status": "success",
                    "tokens": token_usage,
                })

                # 组合回答：LLM 分析 + 结构化数据摘要
                message = llm_result.content

                # 添加简洁的数据表格
                if data.get("regions"):
                    message += "\n\n📊 **数据详情**\n"
                    for rd in data["regions"][:3]:
                        message += f"\n**{rd['region']}**: {rd['total_records']:,} 条记录"
                        if rd.get("min_time"):
                            message += f" ({rd['min_time']} ~ {rd['max_time']})"

                return AgentServiceResult(
                    success=True,
                    message=message,
                    intent="database_schema",
                    confidence=0.9,
                    token_usage=token_usage,
                )

            except Exception as e:
                logger.error(f"LLM analysis failed: {e}")

                # LLM 失败时，返回工具结果的简洁版本
                return AgentServiceResult(
                    success=True,
                    message=f"📊 数据库中有 **{data.get('total_regions', 0)} 个地区** 的数据，共 **{data.get('total_records', 0):,} 条记录**。\n\n"
                    + "\n".join([
                        f"- **{rd['region']}**: {rd['total_records']:,} 条记录"
                        for rd in data.get("regions", [])[:5]
                    ]),
                    intent="database_schema",
                    confidence=0.8,
                )

        except Exception as e:
            logger.error(f"Database schema query failed: {e}")
            tool_time = int((time.time() - tool_start) * 1000)

            trace.append({
                "step_id": len(trace) + 1,
                "step_type": "tool",
                "agent_name": "DatabaseSchemaTool",
                "action": "get_overview",
                "reasoning": f"工具调用失败: {str(e)}",
                "duration_ms": tool_time,
                "status": "failed",
            })

            return AgentServiceResult(
                success=False,
                message=f"⚠️ 数据库查询失败: {str(e)}",
                intent="database_schema",
                confidence=0.3,
            )

    async def _handle_diagnosis(
        self,
        query: str,
        mode: str,
        trace: List[Dict],
    ) -> AgentServiceResult:
        """处理诊断请求"""
        import time

        # 构建 Agent 上下文
        context = AgentContext(
            session_id="default",
            query=query,
            intent="diagnosis",
        )

        # 映射模式
        mode_map = {
            "sequential": CollaborationMode.SEQUENTIAL,
            "parallel": CollaborationMode.PARALLEL,
            "hierarchical": CollaborationMode.HIERARCHICAL,
            "debate": CollaborationMode.DEBATE,
        }

        # 执行 Agent 编排 (使用 LLM 增强型 Agent)
        orch_start = time.time()
        result = await self.orchestrator.execute(
            context=context,
            mode=mode_map.get(mode, CollaborationMode.SEQUENTIAL),
            agent_names=["KnowledgeAgent", "AnalysisLLMAgent", "DiagnosisLLMAgent"],
        )
        orch_time = int((time.time() - orch_start) * 1000)

        # 添加追踪
        for i, agent_result in enumerate(result.agent_results):
            trace.append({
                "step_id": len(trace) + 1,
                "step_type": "agent",
                "agent_name": agent_result.agent_name,
                "action": "execute",
                "reasoning": f"执行 {agent_result.agent_name}",
                "duration_ms": agent_result.execution_time_ms,
                "status": "success" if agent_result.success else "failed",
            })

        # 构建响应
        knowledge = ""
        analysis = ""
        diagnosis = ""

        for agent_result in result.agent_results:
            if agent_result.success and agent_result.data:
                if agent_result.agent_name == "KnowledgeAgent":
                    knowledge = agent_result.data.get("knowledge", "")
                elif agent_result.agent_name == "AnalysisLLMAgent":
                    analysis = agent_result.data.get("content", "")
                elif agent_result.agent_name == "DiagnosisLLMAgent":
                    diagnosis = agent_result.data.get("diagnosis", "")

        message = diagnosis or analysis or "诊断完成，但未得出明确结论。"

        return AgentServiceResult(
            success=True,
            message=message,
            intent="diagnosis",
            knowledge=knowledge,
            analysis=analysis,
            diagnosis=diagnosis,
            confidence=result.agent_results[-1].confidence if result.agent_results else 0.5,
        )

    async def _analyze_for_skill(
        self,
        session_id: str,
        query: str,
        intent: str,
        trace: List[Dict],
        success: bool,
        duration_ms: int,
    ) -> Optional[Dict]:
        """
        分析执行流程，判断是否推荐保存为 Skill

        Args:
            session_id: 会话 ID
            query: 用户查询
            intent: 识别的意图
            trace: 执行轨迹
            success: 是否成功
            duration_ms: 总耗时

        Returns:
            Skill 推荐信息，或 None
        """
        try:
            from src.skill.analyzer import get_flow_analyzer, ExecutionTrace

            analyzer = get_flow_analyzer()

            # 构建执行轨迹
            execution_trace = ExecutionTrace(
                session_id=session_id,
                query=query,
                intent=intent,
                steps=[
                    {
                        "step_type": step.get("step_type", "agent"),
                        "name": step.get("agent_name", step.get("action", "unknown")),
                        "config": step.get("config", {}),
                        "duration_ms": step.get("duration_ms", 0),
                    }
                    for step in trace
                ],
                success=success,
                duration_ms=duration_ms,
            )

            # 记录轨迹
            analyzer.record_trace(execution_trace)

            # 分析是否值得保存为 Skill
            recommendation = await analyzer.analyze(execution_trace)

            if recommendation.recommended:
                logger.info(f"Skill recommendation: {recommendation.suggested_name}")
                return {
                    "recommended": True,
                    "reason": recommendation.reason,
                    "suggested_name": recommendation.suggested_name,
                    "suggested_description": recommendation.suggested_description,
                    "suggested_workflow": recommendation.suggested_workflow,
                    "suggested_trigger": recommendation.suggested_trigger,
                    "suggested_params": recommendation.suggested_params,
                    "confidence": recommendation.confidence,
                }

        except Exception as e:
            logger.warning(f"Failed to analyze for skill: {e}")

        return None


# 全局服务实例
_agent_service: Optional[AgentService] = None


def get_agent_service() -> AgentService:
    """获取 Agent 服务实例"""
    global _agent_service
    if _agent_service is None:
        _agent_service = AgentService()
    return _agent_service

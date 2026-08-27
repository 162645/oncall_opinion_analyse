"""
Skill 执行器
执行 Skill 工作流
"""

from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
import time
import logging
import re

from .models import Skill, SkillStep, SkillParam, SkillExecution
from src.runtime import PermissionLevel, ToolRuntime

logger = logging.getLogger(__name__)


@dataclass
class ExecutionContext:
    """执行上下文"""
    skill: Skill
    params: Dict[str, Any]
    variables: Dict[str, Any] = field(default_factory=dict)
    steps_executed: List[Dict[str, Any]] = field(default_factory=list)
    current_step: int = 0
    success: bool = True
    error: Optional[str] = None


class SkillExecutor:
    """
    Skill 执行器

    功能:
    1. 参数注入和替换
    2. 步骤执行
    3. 条件判断
    4. 错误处理
    """

    def __init__(self, tool_runtime: Optional[ToolRuntime] = None, agent_resolver: Optional[Callable[[str], Any]] = None):
        self.tool_runtime = tool_runtime or ToolRuntime()
        self.agent_resolver = agent_resolver
        self._step_handlers = {
            "agent": self._execute_agent_step,
            "tool": self._execute_tool_step,
            "retrieval": self._execute_retrieval_step,
            "condition": self._execute_condition_step,
            "output": self._execute_output_step,
        }

    async def execute(
        self,
        skill: Skill,
        params: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> SkillExecution:
        """
        执行 Skill

        Args:
            skill: 要执行的 Skill
            params: 执行参数
            context: 额外上下文

        Returns:
            SkillExecution
        """
        start_time = time.time()

        # 创建执行上下文
        exec_ctx = ExecutionContext(
            skill=skill,
            params=params,
            variables=context or {},
        )

        # 参数验证
        validation_error = self._validate_params(skill, params)
        if validation_error:
            return SkillExecution(
                skill_id=skill.id,
                user_id=context.get("user_id", "") if context else "",
                params=params,
                success=False,
                duration_ms=int((time.time() - start_time) * 1000),
                error=validation_error,
            )

        # 合并默认参数
        merged_params = self._merge_default_params(skill, params)
        exec_ctx.params = merged_params

        # 执行工作流
        try:
            for i, step in enumerate(skill.workflow):
                exec_ctx.current_step = i

                # 检查条件
                if step.condition and not self._evaluate_condition(step.condition, exec_ctx):
                    logger.info(f"Skipping step {step.name}: condition not met")
                    continue

                # 执行步骤
                step_result = await self._execute_step(step, exec_ctx)

                exec_ctx.steps_executed.append({
                    "step_name": step.name,
                    "step_type": step.step_type,
                    "success": step_result.get("success", True),
                    "result": step_result.get("result"),
                    "error": step_result.get("error"),
                    "duration_ms": step_result.get("duration_ms", 0),
                })

                if not step_result.get("success", True):
                    if step.on_failure == "stop":
                        exec_ctx.success = False
                        exec_ctx.error = step_result.get("error", "Step failed")
                        break
                    elif step.on_failure == "retry":
                        # 简单重试一次
                        step_result = await self._execute_step(step, exec_ctx)

        except Exception as e:
            exec_ctx.success = False
            exec_ctx.error = str(e)
            logger.error(f"Skill execution failed: {e}")

        # 构建最终结果
        result = self._build_result(exec_ctx)

        return SkillExecution(
            skill_id=skill.id,
            user_id=context.get("user_id", "") if context else "",
            params=params,
            success=exec_ctx.success,
            duration_ms=int((time.time() - start_time) * 1000),
            steps_executed=exec_ctx.steps_executed,
            result=result,
            error=exec_ctx.error,
        )

    def _validate_params(self, skill: Skill, params: Dict[str, Any]) -> Optional[str]:
        """验证参数"""
        for param in skill.parameters:
            if param.required and param.name not in params:
                return f"Missing required parameter: {param.name}"

            if param.name in params and not param.validate(params[param.name]):
                return f"Invalid parameter value: {param.name}"

        return None

    def _merge_default_params(self, skill: Skill, params: Dict[str, Any]) -> Dict[str, Any]:
        """合并默认参数"""
        merged = {}

        for param in skill.parameters:
            if param.name in params:
                merged[param.name] = params[param.name]
            elif param.default is not None:
                merged[param.name] = param.default

        return merged

    async def _execute_step(
        self,
        step: SkillStep,
        ctx: ExecutionContext,
    ) -> Dict[str, Any]:
        """执行单个步骤"""
        start_time = time.time()

        handler = self._step_handlers.get(step.step_type)
        if not handler:
            return {
                "success": False,
                "error": f"Unknown step type: {step.step_type}",
                "duration_ms": 0,
            }

        try:
            # 替换配置中的变量
            config = self._replace_variables(step.config, ctx)

            # 执行
            result = await handler(step, config, ctx)

            result["duration_ms"] = int((time.time() - start_time) * 1000)
            return result

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "duration_ms": int((time.time() - start_time) * 1000),
            }

    def _replace_variables(
        self,
        config: Dict[str, Any],
        ctx: ExecutionContext,
    ) -> Dict[str, Any]:
        """替换配置中的变量"""
        result = {}

        for key, value in config.items():
            if isinstance(value, str):
                # 替换 {param} 格式的变量
                result[key] = self._interpolate(value, ctx)
            elif isinstance(value, dict):
                result[key] = self._replace_variables(value, ctx)
            elif isinstance(value, list):
                result[key] = [
                    self._interpolate(item, ctx) if isinstance(item, str) else item
                    for item in value
                ]
            else:
                result[key] = value

        return result

    def _interpolate(self, text: str, ctx: ExecutionContext) -> str:
        """插值替换"""
        # 替换参数 {param_name}
        for name, value in ctx.params.items():
            text = text.replace(f"{{{name}}}", str(value))

        # 替换变量 {var_name}
        for name, value in ctx.variables.items():
            text = text.replace(f"{{{name}}}", str(value))

        return text

    def _evaluate_condition(self, condition: str, ctx: ExecutionContext) -> bool:
        """评估条件"""
        try:
            # 简单的条件评估
            # 支持: {var} == "value", {var} != "value"
            condition = self._interpolate(condition, ctx)

            # 基本比较
            if "==" in condition:
                left, right = condition.split("==")
                return left.strip() == right.strip().strip('"').strip("'")

            if "!=" in condition:
                left, right = condition.split("!=")
                return left.strip() != right.strip().strip('"').strip("'")

            # 默认真值判断
            return bool(condition.strip())

        except Exception:
            return True

    # ===== 步骤处理器 =====

    async def _execute_agent_step(
        self,
        step: SkillStep,
        config: Dict[str, Any],
        ctx: ExecutionContext,
    ) -> Dict[str, Any]:
        """执行 Agent 步骤"""
        from src.agents import AgentContext, AgentResult
        from src.agents.service import get_agent_service

        agent_name = config.get("agent", "ChatLLMAgent")
        prompt = config.get("prompt", ctx.params.get("query", ""))

        try:
            service = get_agent_service()

            # 构建 Agent 上下文
            agent_ctx = AgentContext(
                session_id=ctx.variables.get("session_id", "skill-execution"),
                query=prompt,
                metadata=ctx.variables,
            )

            agent = self.agent_resolver(agent_name) if self.agent_resolver else service.orchestrator._agents.get(agent_name)
            if agent is None:
                return {"success": False, "error": f"Agent not found: {agent_name}"}
            result = await agent.execute(agent_ctx)

            # 保存结果到变量
            ctx.variables[f"{step.name}_result"] = result.data

            return {
                "success": result.success,
                "result": result.data,
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _execute_tool_step(
        self,
        step: SkillStep,
        config: Dict[str, Any],
        ctx: ExecutionContext,
    ) -> Dict[str, Any]:
        """执行工具步骤"""
        tool_name = config.get("tool", "")

        try:
            permission = getattr(PermissionLevel, config.get("permission", "read").upper(), PermissionLevel.READ)
            result = await self.tool_runtime.execute(
                tool_name,
                config.get("arguments", {}),
                actor=ctx.variables.get("user_id", "skill"),
                granted_permission=permission,
                idempotency_key=config.get("idempotency_key"),
            )
            if not result.success:
                return {"success": False, "error": result.error}

            # 保存结果
            ctx.variables[f"{step.name}_result"] = result.data

            return {"success": True, "result": result.data}

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _execute_retrieval_step(
        self,
        step: SkillStep,
        config: Dict[str, Any],
        ctx: ExecutionContext,
    ) -> Dict[str, Any]:
        """执行检索步骤"""
        from src.knowledge.service import get_knowledge_service

        query_template = config.get("query_template", "")
        top_k = config.get("top_k", 5)

        try:
            service = get_knowledge_service()
            result = await service.search(query_template, top_k=top_k)

            knowledge = "\n".join([r.content for r in result.results])
            ctx.variables["knowledge"] = knowledge
            ctx.variables[f"{step.name}_result"] = knowledge

            return {
                "success": True,
                "result": knowledge,
                "count": len(result.results),
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _execute_condition_step(
        self,
        step: SkillStep,
        config: Dict[str, Any],
        ctx: ExecutionContext,
    ) -> Dict[str, Any]:
        """执行条件步骤"""
        condition = config.get("condition", "")
        result = self._evaluate_condition(condition, ctx)

        return {"success": True, "result": result}

    async def _execute_output_step(
        self,
        step: SkillStep,
        config: Dict[str, Any],
        ctx: ExecutionContext,
    ) -> Dict[str, Any]:
        """执行输出步骤"""
        template = config.get("template", "{result}")

        output = self._interpolate(template, ctx)
        ctx.variables["output"] = output

        return {"success": True, "result": output}

    def _build_result(self, ctx: ExecutionContext) -> str:
        """构建最终结果"""
        # 从变量中获取输出
        output = ctx.variables.get("output", "")

        if not output:
            # 尝试获取最后一个步骤的结果
            if ctx.steps_executed:
                last_step = ctx.steps_executed[-1]
                output = last_step.get("result", "")

        return output

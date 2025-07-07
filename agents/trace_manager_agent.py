from typing import Dict, Any, List
from core.base_agent import BaseAgent
from tools import ReasoningTraceLogger, PlanRevisionTool, StateManager
import json
import re
from datetime import datetime
import logging

# 로거 설정
logger = logging.getLogger(__name__)


class TraceManagerAgent(BaseAgent):
    """
    전체 추론 과정 기록 및 관리 Agent
    - 각 ReActExecutor의 reasoning trace 수집
    - 실패 지점 식별 및 재시도 로직
    - 성능 메트릭 수집
    """

    def __init__(self):
        super().__init__("TraceManagerAgent")
        self.trace_logger = ReasoningTraceLogger()
        self.plan_revision_tool = PlanRevisionTool()
        self.state_manager = StateManager()
        self.mcp_context = {
            "role": "trace_manager",
            "function": "reasoning_trace_management",
        }

    def preprocess(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        추론 과정 관리를 위한 전처리
        """
        # 전체 실행 상태 확인
        execution_status = self.state_manager.get_execution_status()
        inputs["execution_status"] = execution_status

        # 글로벌 추론 trace 수집
        global_trace = self.trace_logger.get_global_trace()
        inputs["global_trace"] = global_trace

        return inputs

    def _create_prompt(self, inputs: Dict[str, Any]) -> str:
        """
        추론 과정 분석 및 관리를 위한 프롬프트 생성
        """
        execution_results = inputs.get("execution_results", [])
        failed_steps = inputs.get("failed_steps", [])
        global_trace = inputs.get("global_trace", [])
        execution_status = inputs.get("execution_status", {})

        # 실패한 단계들 요약
        failure_summary = ""
        if failed_steps:
            failure_summary = "\n**실패한 단계들:**\n"
            for step in failed_steps:
                failure_summary += f"- {step.get('step_id', 'unknown')}: {step.get('error', 'Unknown error')}\n"

        # 추론 과정 요약
        trace_summary = ""
        if global_trace:
            total_thoughts = len(
                [t for t in global_trace if t["step_type"] == "thought"]
            )
            total_actions = len([t for t in global_trace if t["step_type"] == "action"])
            total_observations = len(
                [t for t in global_trace if t["step_type"] == "observation"]
            )

            trace_summary = f"""
**추론 과정 통계:**
- 총 Thought 단계: {total_thoughts}
- 총 Action 단계: {total_actions}
- 총 Observation 단계: {total_observations}
- 전체 추론 단계: {len(global_trace)}
"""

        prompt = f"""
당신은 클라우드 거버넌스 AI 시스템의 Trace Manager Agent입니다.
전체 워크플로우의 추론 과정을 분석하고 관리해야 합니다.

**실행 상태:**
- 총 Agent 수: {execution_status.get('total_agents', 0)}
- 완료된 Agent: {execution_status.get('completed_agents', [])}
- 실패한 Agent: {execution_status.get('failed_agents', [])}
- 활성 Agent: {execution_status.get('active_agents', [])}

{trace_summary}

{failure_summary}

**분석 목표:**
1. 전체 추론 과정의 품질 평가
2. 실패 지점 식별 및 원인 분석
3. 개선 가능한 부분 제안
4. 재시도 필요 여부 판단
5. 최종 성공 가능성 예측

**출력 형식 (JSON):**
{{
    "trace_analysis": {{
        "overall_quality": "excellent|good|fair|poor",
        "reasoning_coherence": 0.0-1.0,
        "goal_achievement_rate": 0.0-1.0,
        "efficiency_score": 0.0-1.0
    }},
    "failure_analysis": {{
        "has_failures": true/false,
        "failure_count": 0,
        "critical_failures": ["step_id1", "step_id2"],
        "failure_patterns": ["pattern1", "pattern2"],
        "root_causes": ["cause1", "cause2"]
    }},
    "recommendations": {{
        "retry_needed": true/false,
        "revision_type": "retry|modify|add_step|replan|none",
        "priority_actions": ["action1", "action2"],
        "expected_improvement": 0.0-1.0
    }},
    "performance_metrics": {{
        "total_execution_time": "추정 시간",
        "resource_efficiency": 0.0-1.0,
        "success_probability": 0.0-1.0,
        "reasoning_depth": "shallow|medium|deep"
    }},
    "final_assessment": {{
        "workflow_status": "success|partial_success|failure|needs_revision",
        "confidence": 0.0-1.0,
        "next_action": "complete|retry|revise|abort",
        "summary": "전체 실행 과정 요약"
    }}
}}

정확한 JSON 형식으로만 응답하세요.
"""
        return prompt

    def postprocess(self, outputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        추론 과정 분석 결과 후처리
        """
        try:
            # LLM 응답에서 JSON 파싱
            content = outputs.content if hasattr(outputs, "content") else str(outputs)
            json_match = re.search(r"\{.*\}", content, re.DOTALL)

            if json_match:
                result = json.loads(json_match.group())

                # 분석 결과를 바탕으로 후속 조치 결정
                next_action = result.get("final_assessment", {}).get(
                    "next_action", "complete"
                )

                if next_action == "retry":
                    # 재시도 권장 사항 생성
                    retry_plan = self._create_retry_plan(result)
                    result["retry_plan"] = retry_plan

                elif next_action == "revise":
                    # 계획 수정 권장 사항 생성
                    revision_suggestions = self._create_revision_suggestions(result)
                    result["revision_suggestions"] = revision_suggestions

                # MCP context 업데이트
                result["mcp_context"] = {
                    **self.mcp_context,
                    "status": "success",
                    "analysis_completed": True,
                    "next_action": next_action,
                    "workflow_status": result.get("final_assessment", {}).get(
                        "workflow_status", "unknown"
                    ),
                }

                # 최종 trace 요약 생성
                result["trace_summary"] = self.trace_logger.get_reasoning_summary()

                return result
            else:
                # JSON 파싱 실패 시 기본 응답
                return self._create_default_response("JSON 파싱 실패")

        except Exception as e:
            return self._create_default_response(f"처리 중 오류 발생: {str(e)}")

    def _create_retry_plan(self, analysis_result: Dict[str, Any]) -> Dict[str, Any]:
        """재시도 계획 생성"""
        failure_analysis = analysis_result.get("failure_analysis", {})
        critical_failures = failure_analysis.get("critical_failures", [])

        return {
            "retry_strategy": "focused_retry",
            "target_steps": critical_failures,
            "max_retry_attempts": 2,
            "retry_modifications": [
                "Increase timeout for long-running operations",
                "Use alternative tools for failed operations",
                "Add more detailed error handling",
            ],
            "success_criteria": {
                "min_success_rate": 0.8,
                "max_execution_time": "5 minutes",
            },
        }

    def _create_revision_suggestions(
        self, analysis_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """계획 수정 제안 생성"""
        recommendations = analysis_result.get("recommendations", {})
        revision_type = recommendations.get("revision_type", "modify")

        return {
            "revision_type": revision_type,
            "suggested_changes": [
                "Simplify complex steps into smaller sub-steps",
                "Add validation checkpoints between major steps",
                "Implement fallback mechanisms for critical operations",
            ],
            "priority_order": ["high", "medium", "low"],
            "implementation_effort": "medium",
            "expected_benefit": recommendations.get("expected_improvement", 0.5),
        }

    def _create_default_response(self, error_message: str) -> Dict[str, Any]:
        """기본 오류 응답 생성"""
        return {
            "trace_analysis": {
                "overall_quality": "poor",
                "reasoning_coherence": 0.0,
                "goal_achievement_rate": 0.0,
                "efficiency_score": 0.0,
            },
            "failure_analysis": {
                "has_failures": True,
                "failure_count": 1,
                "critical_failures": ["trace_analysis"],
                "failure_patterns": ["analysis_error"],
                "root_causes": [error_message],
            },
            "recommendations": {
                "retry_needed": True,
                "revision_type": "retry",
                "priority_actions": ["restart_analysis"],
                "expected_improvement": 0.5,
            },
            "final_assessment": {
                "workflow_status": "failure",
                "confidence": 0.1,
                "next_action": "retry",
                "summary": f"추론 과정 분석 실패: {error_message}",
            },
            "mcp_context": {
                **self.mcp_context,
                "status": "error",
                "message": error_message,
            },
        }

    def handle_failure_recovery(
        self, failed_step: Dict[str, Any], context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """실패 복구 처리"""
        # 실패 단계 분석
        failure_reason = failed_step.get("error", "Unknown error")
        step_id = failed_step.get("step_id", "unknown")

        logger.info(f"🔄 실패 복구 처리 중: {step_id}")

        # 계획 수정 도구 사용
        revision_result = self.plan_revision_tool.run(
            {
                "current_plan": context.get("execution_plan", []),
                "failed_step": failed_step,
                "failure_reason": failure_reason,
                "context": context,
                "revision_type": "modify",  # 기본 수정 전략
            }
        )

        if revision_result.get("status") == "success":
            logger.info(f"✅ 계획 수정 완료: {revision_result.get('revision_type')}")
            return {
                "recovery_status": "success",
                "revised_plan": revision_result.get("revised_plan", []),
                "recovery_strategy": revision_result.get("revision_type"),
                "changes_made": revision_result.get("changes_made", {}),
            }
        else:
            logger.error(
                f"❌ 계획 수정 실패: {revision_result.get('message', 'Unknown error')}"
            )
            return {
                "recovery_status": "failed",
                "error": revision_result.get("message", "Recovery failed"),
                "fallback_needed": True,
            }

    def get_comprehensive_report(self) -> Dict[str, Any]:
        """종합 실행 보고서 생성"""
        return {
            "execution_summary": self.state_manager.get_execution_status(),
            "reasoning_summary": self.trace_logger.get_reasoning_summary(),
            "revision_history": self.plan_revision_tool.get_revision_history(),
            "performance_metrics": {
                "total_agents": len(self.state_manager.agent_states),
                "successful_completions": len(
                    [
                        agent
                        for agent, state in self.state_manager.agent_states.items()
                        if state.get("current_status") == "completed"
                    ]
                ),
                "total_reasoning_steps": len(self.trace_logger.global_trace),
                "revision_count": len(self.plan_revision_tool.revision_history),
            },
            "recommendations_for_future": [
                "추론 과정에서 자주 실패하는 패턴 개선",
                "도구 선택 로직 최적화",
                "에러 처리 및 복구 메커니즘 강화",
            ],
        }

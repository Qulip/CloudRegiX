from typing import Dict, Any, List
from datetime import datetime
from core import BaseTool


class PlanRevisionTool(BaseTool):
    """
    실행 중 계획 수정 및 재계획을 수행하는 Tool
    실패 시나리오나 예상치 못한 상황에 대응
    """

    def __init__(self):
        self.revision_history = []  # 수정 이력 저장

    def run(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        계획 수정 실행

        Args:
            inputs: {
                "current_plan": List[Dict],
                "failed_step": Dict,
                "failure_reason": str,
                "context": Dict,
                "revision_type": "retry|modify|add_step|replan"
            }

        Returns:
            수정된 계획
        """
        try:
            current_plan = inputs.get("current_plan", [])
            failed_step = inputs.get("failed_step", {})
            failure_reason = inputs.get("failure_reason", "")
            context = inputs.get("context", {})
            revision_type = inputs.get("revision_type", "retry")

            # 수정 이력 기록
            revision_entry = {
                "timestamp": datetime.now().isoformat(),
                "revision_type": revision_type,
                "failure_reason": failure_reason,
                "failed_step": failed_step,
                "original_plan_length": len(current_plan),
            }

            if revision_type == "retry":
                revised_plan = self._retry_failed_step(current_plan, failed_step)

            elif revision_type == "modify":
                revised_plan = self._modify_step(current_plan, failed_step, context)

            elif revision_type == "add_step":
                revised_plan = self._add_recovery_step(
                    current_plan, failed_step, context
                )

            elif revision_type == "replan":
                revised_plan = self._create_new_plan(context, failure_reason)

            else:
                revised_plan = current_plan  # 기본값: 변경 없음

            # 수정 결과 기록
            revision_entry["revised_plan_length"] = len(revised_plan)
            revision_entry["revision_successful"] = True
            self.revision_history.append(revision_entry)

            return {
                "status": "success",
                "revised_plan": revised_plan,
                "revision_type": revision_type,
                "revision_id": len(self.revision_history),
                "changes_made": self._analyze_changes(current_plan, revised_plan),
            }

        except Exception as e:
            revision_entry = {
                "timestamp": datetime.now().isoformat(),
                "revision_type": revision_type,
                "failure_reason": failure_reason,
                "revision_successful": False,
                "error": str(e),
            }
            self.revision_history.append(revision_entry)

            return {"status": "error", "message": str(e), "original_plan": current_plan}

    def _retry_failed_step(
        self, current_plan: List[Dict], failed_step: Dict
    ) -> List[Dict]:
        """실패한 단계 재시도를 위한 계획 수정"""
        revised_plan = current_plan.copy()

        # 실패한 단계에 재시도 플래그 추가
        for i, step in enumerate(revised_plan):
            if step.get("step_id") == failed_step.get("step_id"):
                revised_plan[i] = {
                    **step,
                    "retry_count": step.get("retry_count", 0) + 1,
                    "retry_reason": failed_step.get(
                        "error", "Previous execution failed"
                    ),
                }
                break

        return revised_plan

    def _modify_step(
        self, current_plan: List[Dict], failed_step: Dict, context: Dict
    ) -> List[Dict]:
        """실패한 단계의 접근 방식 수정"""
        revised_plan = current_plan.copy()

        for i, step in enumerate(revised_plan):
            if step.get("step_id") == failed_step.get("step_id"):
                # 실패 원인에 따라 다른 접근 방식 적용
                failure_reason = failed_step.get("error", "")

                if "tool_not_found" in failure_reason.lower():
                    # 다른 도구로 대체
                    alternative_tools = self._get_alternative_tools(
                        step.get("required_tools", [])
                    )
                    revised_plan[i]["required_tools"] = alternative_tools

                elif "insufficient_data" in failure_reason.lower():
                    # 데이터 수집 단계 추가
                    revised_plan[i]["pre_steps"] = step.get("pre_steps", []) + [
                        "data_collection"
                    ]

                elif "timeout" in failure_reason.lower():
                    # 실행 시간 조정
                    revised_plan[i]["timeout"] = step.get("timeout", 30) * 2

                revised_plan[i]["modified"] = True
                revised_plan[i]["modification_reason"] = failure_reason
                break

        return revised_plan

    def _add_recovery_step(
        self, current_plan: List[Dict], failed_step: Dict, context: Dict
    ) -> List[Dict]:
        """복구 단계 추가"""
        revised_plan = current_plan.copy()

        # 실패한 단계 위치 찾기
        failed_index = -1
        for i, step in enumerate(revised_plan):
            if step.get("step_id") == failed_step.get("step_id"):
                failed_index = i
                break

        if failed_index >= 0:
            # 복구 단계 생성
            recovery_step = {
                "step_id": f"recovery_{failed_step.get('step_id', 'unknown')}",
                "step_type": "recovery",
                "description": f"Recover from failed step: {failed_step.get('description', 'Unknown')}",
                "required_tools": ["rag_retriever"],  # 기본 복구 도구
                "is_recovery": True,
                "original_failed_step": failed_step,
            }

            # 실패한 단계 직전에 복구 단계 삽입
            revised_plan.insert(failed_index, recovery_step)

        return revised_plan

    def _create_new_plan(self, context: Dict, failure_reason: str) -> List[Dict]:
        """완전히 새로운 계획 생성"""
        user_intent = context.get("intent", "question")
        user_input = context.get("user_input", "")

        # 기본 계획 템플릿
        if user_intent == "slide_generation":
            return [
                {
                    "step_id": "replan_data_collection",
                    "step_type": "data_collection",
                    "description": "Collect comprehensive data for slide generation",
                    "required_tools": ["rag_retriever"],
                    "priority": "high",
                },
                {
                    "step_id": "replan_content_analysis",
                    "step_type": "analysis",
                    "description": "Analyze collected data for slide content",
                    "required_tools": ["reasoning_trace_logger"],
                    "priority": "high",
                },
                {
                    "step_id": "replan_slide_creation",
                    "step_type": "generation",
                    "description": "Generate slide with simplified approach",
                    "required_tools": ["slide_formatter"],
                    "priority": "high",
                },
            ]
        else:
            return [
                {
                    "step_id": "replan_simple_search",
                    "step_type": "search",
                    "description": "Simple search for user query",
                    "required_tools": ["rag_retriever"],
                    "priority": "medium",
                },
                {
                    "step_id": "replan_answer_generation",
                    "step_type": "generation",
                    "description": "Generate answer from search results",
                    "required_tools": ["reasoning_trace_logger"],
                    "priority": "medium",
                },
            ]

    def _get_alternative_tools(self, failed_tools: List[str]) -> List[str]:
        """실패한 도구의 대체 도구 반환"""
        alternatives = {
            "slide_formatter": ["report_summary"],
            "report_summary": ["rag_retriever"],
            "rag_retriever": ["reasoning_trace_logger"],
        }

        alternative_tools = []
        for tool in failed_tools:
            if tool in alternatives:
                alternative_tools.extend(alternatives[tool])
            else:
                alternative_tools.append(tool)  # 대체 도구가 없으면 원래 도구 유지

        return list(set(alternative_tools))  # 중복 제거

    def _analyze_changes(
        self, original_plan: List[Dict], revised_plan: List[Dict]
    ) -> Dict[str, Any]:
        """계획 변경 사항 분석"""
        return {
            "steps_added": len(revised_plan) - len(original_plan),
            "steps_modified": sum(
                1 for step in revised_plan if step.get("modified", False)
            ),
            "steps_removed": max(0, len(original_plan) - len(revised_plan)),
            "major_revision": len(revised_plan) != len(original_plan),
            "revision_count": len(self.revision_history),
        }

    def get_revision_history(self) -> List[Dict[str, Any]]:
        """수정 이력 반환"""
        return self.revision_history

    def clear_history(self):
        """수정 이력 초기화"""
        self.revision_history = []

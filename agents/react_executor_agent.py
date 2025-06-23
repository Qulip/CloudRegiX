from typing import Dict, Any
from core import BaseAgent
from tools import ReasoningTraceLogger, StateManager
from mcp_client import get_mcp_client


class ReActExecutorAgent(BaseAgent):
    """
    ReAct 방식으로 개별 Plan Step을 실행하는 Agent
    Thought → Action → Observation 순환 실행
    """

    def __init__(self, executor_id: str = "react_executor"):
        super().__init__(f"ReActExecutorAgent_{executor_id}")
        self.executor_id = executor_id
        self.mcp_client = get_mcp_client()
        self.trace_logger = ReasoningTraceLogger()
        self.state_manager = StateManager()
        self.max_iterations = 5  # 최대 ReAct 반복 횟수

    def preprocess(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        ReAct 실행을 위한 전처리
        """
        # 실행 상태 초기화
        self.state_manager.run(
            {
                "action": "set_state",
                "agent_id": self.name,
                "data": {
                    "status": "starting",
                    "step_index": 0,
                    "current_action": "preprocessing",
                    "progress": 0.0,
                },
            }
        )

        return inputs

    def _create_prompt(self, inputs: Dict[str, Any]) -> str:
        """
        ReAct 실행을 위한 프롬프트 생성
        """
        plan_step = inputs.get("plan_step", {})
        context = inputs.get("context", {})
        iteration = inputs.get("iteration", 0)
        previous_thoughts = inputs.get("previous_thoughts", [])
        previous_actions = inputs.get("previous_actions", [])
        previous_observations = inputs.get("previous_observations", [])

        prompt = f"""
당신은 클라우드 거버넌스 AI 시스템의 ReAct Executor Agent입니다.
주어진 계획 단계를 ReAct (Reasoning and Acting) 방식으로 실행해야 합니다.

**현재 실행 중인 단계:**
- 단계 ID: {plan_step.get('step_id', 'unknown')}
- 단계 유형: {plan_step.get('step_type', 'general')}
- 설명: {plan_step.get('description', 'Execute the given step')}
- 현재 반복: {iteration + 1}/{self.max_iterations}

**출력 형식 (JSON):**
{{
    "thought": "현재 상황 분석 및 다음 행동 계획",
    "action": {{
        "tool_name": "rag_retriever|slide_formatter|report_summary",
        "tool_params": {{
            "query": "검색어",
            "content": "내용"
        }}
    }},
    "goal_achieved": true/false,
    "confidence": 0.0-1.0,
    "final_result": "목표 달성 시 최종 결과",
    "status": "success|partial_success|error"
}}

정확한 JSON 형식으로만 응답하세요.
"""
        return prompt

    def postprocess(self, outputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        ReAct 실행 결과 후처리
        """
        try:
            # LLM 응답에서 JSON 파싱 (다른 에이전트들과 동일한 방식)
            import json
            import re

            content = outputs.content if hasattr(outputs, "content") else str(outputs)

            # JSON 부분 추출
            json_match = re.search(r"\{.*\}", content, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())

                # 필수 필드 보완
                result["executor_id"] = self.executor_id
                result["agent_name"] = self.name
                result["status"] = result.get("status", "success")

                # 상태 업데이트
                self.state_manager.run(
                    {
                        "action": "set_state",
                        "agent_id": self.name,
                        "data": {
                            "status": "completed",
                            "final_result": result.get("final_result", ""),
                            "confidence": result.get("confidence", 0.5),
                            "goal_achieved": result.get("goal_achieved", False),
                        },
                    }
                )

                return result
            else:
                # JSON 파싱 실패 시 기본 응답
                return {
                    "status": "error",
                    "error": "JSON 파싱 실패",
                    "executor_id": self.executor_id,
                    "agent_name": self.name,
                    "confidence": 0.0,
                    "goal_achieved": False,
                    "final_result": "응답 파싱에 실패했습니다.",
                }

        except Exception as e:
            return {
                "status": "error",
                "error": f"후처리 중 오류 발생: {str(e)}",
                "executor_id": self.executor_id,
                "agent_name": self.name,
                "confidence": 0.0,
                "goal_achieved": False,
                "final_result": f"처리 중 오류가 발생했습니다: {str(e)}",
            }

from typing import Dict, Any
from core import BaseAgent


class PlannerAgent(BaseAgent):
    """
    Planner Agent
    Router Agent의 결과를 바탕으로 어떤 작업을 수행할지 결정
    Task Management Agent에 전달할 작업 타입 결정
    """

    def __init__(self):
        super().__init__("PlannerAgent")
        self.mcp_context = {"role": "planner", "function": "task_planning"}

    def _create_prompt(self, inputs: Dict[str, Any]) -> str:
        """
        작업 계획 수립을 위한 프롬프트 생성

        Args:
            inputs (Dict[str, Any]): Router Agent 결과 포함

        Returns:
            str: LLM용 프롬프트
        """
        # Router Agent 결과 추출
        intent = inputs.get("intent", "general")
        confidence = inputs.get("confidence", 0.0)
        key_entities = inputs.get("key_entities", [])
        user_input = inputs.get("user_input", "")

        prompt = f"""
당신은 클라우드 거버넌스 AI 시스템의 Planner Agent입니다.
Router Agent의 분석 결과를 바탕으로 적절한 작업 계획을 수립해야 합니다.

**Router Agent 분석 결과:**
- Intent: {intent}
- Confidence: {confidence}
- Key Entities: {key_entities}
- Original Input: {user_input}

**사용 가능한 처리 방식:**
1. "TaskManagementAgent" - 통합 작업 처리 (질문 응답, 슬라이드 생성, 보고서 요약)
2. "DirectAnswer" - 간단한 인사나 일반 대화 직접 처리

**계획 수립 규칙:**
- intent가 "question"이면 TaskManagementAgent 선택, task_type: "question"
- intent가 "slide_generation"이면 TaskManagementAgent 선택, task_type: "slide"
- intent가 "report"이면 TaskManagementAgent 선택, task_type: "report"
- intent가 "general"이면 DirectAnswer 선택
- confidence가 0.5 미만이면 추가 분석 필요

**출력 형식 (JSON):**
{{
    "selected_agent": "TaskManagementAgent|DirectAnswer",
    "reasoning": "선택 이유 설명",
    "parameters": {{
        "query": "실제 질문 내용",
        "task_type": "question|slide|report",
        "slide_type": "basic|detailed|comparison (슬라이드 생성 시)",
        "summary_type": "executive|technical|compliance (보고서 요약 시)",
        "priority": "high|medium|low"
    }},
    "mcp_context": {{"role": "planner", "status": "success"}}
}}

정확한 JSON 형식으로만 응답하세요.
"""
        return prompt

    def postprocess(self, outputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Planner Agent 출력 후처리

        Args:
            outputs (Dict[str, Any]): LLM 응답

        Returns:
            Dict[str, Any]: 후처리된 결과
        """
        try:
            # LLM 응답에서 JSON 파싱
            import json
            import re

            content = outputs.content if hasattr(outputs, "content") else str(outputs)

            # JSON 부분 추출
            json_match = re.search(r"\{.*\}", content, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group())

                # MCP context 업데이트
                result["mcp_context"] = {
                    **self.mcp_context,
                    "status": "success",
                    "selected_agent": result.get("selected_agent", "DirectAnswer"),
                    "planning_timestamp": self._get_timestamp(),
                }

                return result
            else:
                # JSON 파싱 실패 시 기본 응답
                return {
                    "selected_agent": "DirectAnswer",
                    "reasoning": "JSON 파싱 실패로 기본 처리",
                    "parameters": {
                        "query": "파싱 오류로 인한 기본 응답",
                        "priority": "low",
                    },
                    "mcp_context": {
                        **self.mcp_context,
                        "status": "error",
                        "message": "응답 파싱 실패",
                    },
                }

        except Exception as e:
            return {
                "selected_agent": "DirectAnswer",
                "reasoning": f"처리 중 오류 발생: {str(e)}",
                "parameters": {"query": "오류로 인한 기본 응답", "priority": "low"},
                "mcp_context": {
                    **self.mcp_context,
                    "status": "error",
                    "message": str(e),
                },
            }

    def _get_timestamp(self) -> str:
        """현재 타임스탬프 반환"""
        from datetime import datetime

        return datetime.now().isoformat()

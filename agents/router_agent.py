from typing import Dict, Any
from core import BaseAgent


class RouterAgent(BaseAgent):
    """
    Router Agent
    사용자 발화 분석 후 의도(intent) 추출하여 Planner Agent로 전달
    분기 처리 없이 intent만 추출하는 역할
    """

    def __init__(self):
        super().__init__("RouterAgent")
        self.mcp_context = {"role": "router", "function": "intent_extraction"}

    def _create_prompt(self, inputs: Dict[str, Any]) -> str:
        """
        사용자 입력 분석을 위한 프롬프트 생성

        Args:
            inputs (Dict[str, Any]): {"user_input": str}

        Returns:
            str: LLM용 프롬프트
        """
        user_input = inputs.get("user_input", "")

        prompt = f"""
당신은 클라우드 거버넌스 전문 AI 시스템의 Router Agent입니다.
사용자의 입력을 분석하여 의도(intent)를 정확히 파악해야 합니다.

**분석 대상 입력:**
{user_input}

**가능한 Intent 유형:**
1. "question" - 클라우드 거버넌스 관련 질문이나 정보 요청
2. "slide_generation" - 슬라이드나 프레젠테이션 자료 생성 요청
3. "report" - 보고서나 요약 자료 생성 요청
4. "general" - 일반적인 대화나 인사

**분석 기준:**
- 슬라이드, 프레젠테이션, PPT, 발표자료 등의 키워드가 있으면 "slide_generation"
- 보고서, 요약, 리포트, 분석서 등의 키워드가 있으면 "report"
- 질문문(?, 어떻게, 무엇, 왜 등)이나 정보 요청이면 "question"
- 그 외는 "general"

**출력 형식 (JSON):**
{{
    "intent": "question|slide_generation|report|general",
    "confidence": 0.0-1.0,
    "key_entities": ["추출된", "핵심", "키워드"],
    "analysis": "의도 분석 이유",
    "mcp_context": {{"role": "router", "status": "success"}}
}}

정확한 JSON 형식으로만 응답하세요.
"""
        return prompt

    def postprocess(self, outputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Router Agent 출력 후처리

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
                    "intent_detected": result.get("intent", "unknown"),
                    "confidence": result.get("confidence", 0.0),
                }

                return result
            else:
                # JSON 파싱 실패 시 기본 응답
                return {
                    "intent": "general",
                    "confidence": 0.3,
                    "key_entities": [],
                    "analysis": "JSON 파싱 실패로 기본 처리",
                    "mcp_context": {
                        **self.mcp_context,
                        "status": "error",
                        "message": "응답 파싱 실패",
                    },
                }

        except Exception as e:
            return {
                "intent": "general",
                "confidence": 0.0,
                "key_entities": [],
                "analysis": f"처리 중 오류 발생: {str(e)}",
                "mcp_context": {
                    **self.mcp_context,
                    "status": "error",
                    "message": str(e),
                },
            }

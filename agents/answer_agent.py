from typing import Dict, Any
from core import BaseAgent


class AnswerAgent(BaseAgent):
    """
    Answer Agent
    Task Management Agent의 결과를
    사용자 응답 형식으로 정제하여 반환하는 최종 에이전트
    """

    def __init__(self):
        super().__init__("AnswerAgent")
        self.mcp_context = {
            "role": "responder",
            "function": "final_response_formatting",
        }

    def _create_prompt(self, inputs: Dict[str, Any]) -> str:
        """
        하이브리드 실행 결과를 포함한 최종 사용자 응답 생성을 위한 프롬프트 생성

        Args:
            inputs (Dict[str, Any]): 하이브리드 실행 결과

        Returns:
            str: LLM용 프롬프트
        """
        # 하이브리드 실행 결과 추출
        execution_results = inputs.get("execution_results", [])
        reasoning_trace = inputs.get("reasoning_trace", [])
        trace_summary = inputs.get("trace_summary", {})
        overall_confidence = inputs.get("overall_confidence", 0.5)

        # 기존 호환성 유지
        agent_type = inputs.get("agent_type", "hybrid_execution")
        answer_content = inputs.get("answer_content", "")
        confidence = inputs.get("confidence", "medium")
        source_type = inputs.get("source_type", "hybrid_react")

        # 하이브리드 실행 결과 처리
        if agent_type == "hybrid_execution" or reasoning_trace:
            # 실행 결과 분석
            successful_results = []
            failed_results = []

            if execution_results:
                successful_results = [
                    r for r in execution_results if r.get("status") == "success"
                ]
                failed_results = [
                    r for r in execution_results if r.get("status") != "success"
                ]

            # 최종 결과 추출
            final_result_content = ""
            if successful_results:
                # 성공한 결과 중 가장 완전한 답변 찾기
                for result in successful_results:
                    if (
                        result.get("final_result")
                        and len(result.get("final_result", "")) > 50
                    ):
                        final_result_content = result.get("final_result", "")
                        break

                # 완전한 답변이 없으면 첫 번째 성공 결과 사용
                if not final_result_content and successful_results:
                    final_result_content = successful_results[0].get("final_result", "")

            # 답변 내용이 비어있거나 불충분한 경우 대체 내용 생성
            if not final_result_content or len(final_result_content.strip()) < 20:
                user_input = (
                    inputs.get("context", {}).get("user_input", "")
                    or answer_content
                    or ""
                )
                user_input_lower = user_input.lower() if user_input else ""

                if any(
                    keyword in user_input_lower for keyword in ["클라우드", "거버넌스"]
                ):
                    final_result_content = "클라우드 거버넌스는 클라우드 서비스의 효율적이고 안전한 사용을 위한 종합적인 관리 체계입니다."
                elif "보안" in user_input_lower:
                    final_result_content = "클라우드 보안은 클라우드 환경에서 데이터와 애플리케이션을 보호하는 포괄적인 보안 전략입니다."
                else:
                    final_result_content = (
                        "요청하신 내용에 대한 정보를 제공해드리겠습니다."
                    )

            # 추론 과정 요약
            reasoning_summary = ""
            if trace_summary:
                thought_count = trace_summary.get("thought_count", 0)
                action_count = trace_summary.get("action_count", 0)
                observation_count = trace_summary.get("observation_count", 0)

                reasoning_summary = f"""
**추론 과정 요약:**
- 사고 단계: {thought_count}개
- 행동 단계: {action_count}개  
- 관찰 단계: {observation_count}개
- 전체 신뢰도: {overall_confidence:.2f}
"""
            else:
                reasoning_summary = f"""
**추론 과정 요약:**
- 하이브리드 AI 시스템이 단계적으로 분석을 수행했습니다
- 전체 신뢰도: {overall_confidence:.2f}
"""

            # 실행 결과 요약
            results_summary = ""
            if execution_results:
                results_summary = f"""
**실행 결과:**
- 성공한 단계: {len(successful_results)}개
- 실패한 단계: {len(failed_results)}개
- 최종 결과: {final_result_content[:100]}{'...' if len(final_result_content) > 100 else ''}
"""
            else:
                results_summary = """
**실행 결과:**
- 시스템이 사용자 요청을 분석하여 적절한 답변을 준비했습니다
"""

            prompt = f"""
당신은 클라우드 거버넌스 전문 AI 어시스턴트입니다.
사용자에게 클라우드 거버넌스에 대한 완전하고 유용한 정보를 제공해야 합니다.

**실행된 하이브리드 프로세스:**
{reasoning_summary}

{results_summary}

**기본 답변 내용:**
{final_result_content}

**응답 작성 지침:**
1. 클라우드 거버넌스 관련 전문 지식을 활용하여 완전하고 실용적인 답변 제공
2. 핵심 정보를 명확하고 체계적으로 전달
3. 실제 적용 가능한 구체적인 방법들과 예시 포함
4. 전문적이면서도 이해하기 쉬운 설명
5. 추가 질문을 자연스럽게 유도

**출력 형식:**
자연스러운 한국어로 완성된 답변을 작성하되, 다음 구조를 포함하세요:

1. **결과 요약**: 핵심 답변 내용 (구체적이고 상세하게)
2. **주요 구성 요소**: 관련 세부 사항들을 체계적으로 설명
3. **실용적 조언**: 실제 적용 가능한 구체적인 방법들
4. **추가 안내**: "더 자세한 정보가 필요하시거나 특정 영역에 대해 더 알고 싶으시면 말씀해 주세요!" 등

전문적이면서도 친근한 어조를 유지하여 완전하고 유용한 답변을 제공하세요.
"""

        elif agent_type == "question":
            prompt = f"""
당신은 클라우드 거버넌스 AI 어시스턴트입니다.
Question Agent가 생성한 답변을 사용자에게 친근하고 이해하기 쉽게 전달해야 합니다.

**Question Agent 답변:**
{answer_content}

**답변 신뢰도:** {confidence}
**정보 출처:** {source_type}

**응답 작성 지침:**
1. 친근하고 전문적인 어조 유지
2. 핵심 정보를 명확하게 전달
3. 필요시 추가 질문을 유도
4. 클라우드 거버넌스 전문성 어필
5. 실행 가능한 조언 포함

**출력 형식:**
자연스러운 한국어로 완성된 답변을 작성하세요.
답변 마지막에는 "추가 궁금한 점이 있으시면 언제든 말씀해 주세요!" 등의 친근한 마무리 문구를 포함하세요.
"""

        elif agent_type == "slide_generation":
            slide_data = inputs.get("slide_data", {})
            slide_html = inputs.get("slide_html", "")

            prompt = f"""
당신은 클라우드 거버넌스 AI 어시스턴트입니다.
Task Management Agent가 생성한 슬라이드를 사용자에게 효과적으로 제시해야 합니다.

**Task Management Agent 결과:**
{answer_content}

**생성된 슬라이드 데이터:**
{slide_data}

**HTML 형식 슬라이드가 생성되었습니다:**
- 슬라이드는 HTML 형식으로 생성되어 브라우저에서 볼 수 있습니다
- 반응형 디자인으로 모바일에서도 잘 보입니다
- 아름다운 그라데이션과 애니메이션 효과가 적용되었습니다

**응답 작성 지침:**
1. 슬라이드 생성 완료를 명확하게 알림
2. 슬라이드의 핵심 내용 요약 제시
3. HTML 형식으로 생성되었음을 안내
4. 추가 수정이나 다른 형식 요청 가능함을 안내
5. 전문적이면서도 친근한 어조 유지

**출력 형식:**
"📊 클라우드 거버넌스 슬라이드가 HTML 형식으로 생성되었습니다!"로 시작하여,
슬라이드의 핵심 내용 HTML 형식으로 요약하고,
마지막에 "슬라이드 내용 수정이나 다른 형식을 원하시면 말씀해 주세요!" 등의 안내 문구를 포함하세요.
"""

        elif agent_type == "report_summary":
            report_data = inputs.get("report_data", {})
            report_html = inputs.get("report_html", "")

            prompt = f"""
당신은 클라우드 거버넌스 AI 어시스턴트입니다.
Task Management Agent가 생성한 보고서 요약을 사용자에게 효과적으로 제시해야 합니다.

**Task Management Agent 결과:**
{answer_content}

**생성된 보고서 요약 데이터:**
{report_data}

**HTML 형식 보고서 요약이 생성되었습니다:**
- 보고서 요약은 HTML 형식으로 생성되어 브라우저에서 볼 수 있습니다
- 구조화된 섹션과 시각적 요소가 포함되었습니다
- 핵심 발견사항과 권고사항이 명확하게 정리되었습니다

**응답 작성 지침:**
1. 보고서 요약 생성 완료를 명확하게 알림
2. 보고서의 핵심 내용 요약 제시
3. HTML 형식으로 생성되었음을 안내
4. 추가 분석이나 다른 형식 요청 가능함을 안내
5. 전문적이면서도 친근한 어조 유지

**출력 형식:**
"📋 클라우드 거버넌스 보고서 요약이 HTML 형식으로 생성되었습니다!"로 시작하여,
보고서의 핵심 내용을 요약하고,
마지막에 "보고서 내용 수정이나 추가 분석을 원하시면 말씀해 주세요!" 등의 안내 문구를 포함하세요.
"""

        else:
            # 일반적인 대화나 오류 처리
            prompt = f"""
당신은 클라우드 거버넌스 AI 어시스턴트입니다.
사용자와 자연스럽게 대화하며 도움을 제공해야 합니다.

**처리 결과:**
{answer_content}

**상황:** {agent_type} 타입 처리

**응답 작성 지침:**
1. 친근하고 도움이 되는 어조
2. 클라우드 거버넌스 관련 도움 제공 의지 표현
3. 구체적인 질문이나 요청을 유도
4. 전문성을 바탕으로 한 신뢰감 조성

**출력 형식:**
자연스러운 한국어로 완성된 응답을 작성하세요.
"""

        return prompt

    def postprocess(self, outputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Answer Agent 최종 출력 후처리

        Args:
            outputs (Dict[str, Any]): LLM 응답

        Returns:
            Dict[str, Any]: 최종 사용자 응답
        """
        try:
            content = outputs.content if hasattr(outputs, "content") else str(outputs)

            # 최종 응답 형식 구성
            result = {
                "final_answer": content,
                "timestamp": self._get_timestamp(),
                "mcp_context": {
                    **self.mcp_context,
                    "status": "completed",
                    "response_ready": True,
                    "final_processing": True,
                },
            }

            return result

        except Exception as e:
            return {
                "final_answer": f"죄송합니다. 응답 처리 중 오류가 발생했습니다: {str(e)}\n\n다시 시도해 주시거나 다른 방식으로 질문해 주세요.",
                "timestamp": self._get_timestamp(),
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

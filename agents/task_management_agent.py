from typing import Dict, Any
from core import BaseAgent
from mcp_client import get_mcp_client


class TaskManagementAgent(BaseAgent):
    """
    Task Management Agent
    클라우드 거버넌스 관련 모든 작업을 통합 처리하는 에이전트
    - 질문 응답
    - 슬라이드 생성
    - 보고서 요약
    MCP 프로토콜을 통해 필요한 도구들을 사용하여 작업 수행
    """

    def __init__(self):
        super().__init__("TaskManagementAgent")
        self.mcp_client = get_mcp_client()
        self.mcp_context = {
            "role": "task_manager",
            "function": "integrated_task_processing",
        }

    def preprocess(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        작업 처리를 위한 전처리

        Args:
            inputs (Dict[str, Any]): Planner Agent 결과

        Returns:
            Dict[str, Any]: 전처리된 입력
        """
        # Planner Agent의 parameters에서 정보 추출
        parameters = inputs.get("parameters", {})
        query = parameters.get("query", inputs.get("user_input", ""))
        task_type = parameters.get("task_type", "question")  # question, slide, report

        # 작업 유형에 따라 적절한 검색 수행
        try:
            if task_type in ["slide", "report"]:
                # 슬라이드나 보고서 생성시 더 많은 자료 수집
                rag_results = self.mcp_client.search_documents(query=query, top_k=8)
            else:
                # 일반 질문시 기본 검색
                rag_results = self.mcp_client.search_documents(query=query, top_k=5)
        except Exception as e:
            print(f"MCP 검색 실패: {str(e)}")
            rag_results = {
                "results": [],
                "mcp_context": {
                    "status": "error",
                    "message": f"MCP 검색 실패: {str(e)}",
                },
            }

        # 전처리된 정보 저장
        inputs["rag_results"] = rag_results
        inputs["processed_query"] = query
        inputs["task_type"] = task_type

        # 추가 매개변수 저장 (postprocess에서 사용)
        self._current_task_type = task_type
        self._current_slide_type = parameters.get("slide_type", "basic")

        return inputs

    def _create_prompt(self, inputs: Dict[str, Any]) -> str:
        """
        작업 유형에 따른 프롬프트 생성

        Args:
            inputs (Dict[str, Any]): RAG 결과 포함 입력

        Returns:
            str: LLM용 프롬프트
        """
        query = inputs.get("processed_query", "")
        task_type = inputs.get("task_type", "question")
        rag_results = inputs.get("rag_results", {})
        search_results = rag_results.get("results", [])

        # 검색 결과를 컨텍스트로 구성
        context = ""
        if search_results:
            context = "**관련 문서 정보:**\n"
            for i, result in enumerate(search_results[:5], 1):
                context += f"{i}. {result['content'][:500]}...\n"
                context += f"   (출처: {result['source']}, 관련도: {result['relevance_score']:.2f})\n\n"
        else:
            context = "**관련 문서를 찾을 수 없어 일반적인 클라우드 거버넌스 지식으로 답변합니다.**\n\n"

        if task_type == "slide":
            return self._create_slide_prompt(query, context, inputs)
        elif task_type == "report":
            return self._create_report_prompt(query, context, inputs)
        else:
            return self._create_question_prompt(query, context)

    def _create_question_prompt(self, query: str, context: str) -> str:
        """질문 응답용 프롬프트"""
        return f"""
당신은 클라우드 거버넌스 전문가입니다.
사용자의 질문에 대해 검색된 문서 정보를 바탕으로 정확하고 유용한 답변을 제공해야 합니다.

**사용자 질문:**
{query}

{context}

**답변 작성 지침:**
1. 검색된 문서 정보를 우선적으로 활용하세요
2. 클라우드 거버넌스의 핵심 원칙에 맞게 답변하세요
3. 구체적이고 실행 가능한 정보를 포함하세요
4. 필요시 단계별 설명을 제공하세요
5. 관련 법규나 컴플라이언스 사항이 있다면 언급하세요

**출력 형식:**
답변 내용을 자연스러운 한국어로 작성하되, 마지막에 다음 정보를 포함하세요:

**요약:**
- 핵심 포인트 1
- 핵심 포인트 2
- 핵심 포인트 3

**참고 사항:**
검색된 문서에서 얻은 정보임을 명시하고, 추가적인 상세 정보가 필요한 경우를 안내하세요.
"""

    def _create_slide_prompt(
        self, query: str, context: str, inputs: Dict[str, Any]
    ) -> str:
        """슬라이드 생성용 프롬프트"""
        slide_type = inputs.get("slide_type", "basic")

        return f"""
당신은 클라우드 거버넌스 전문가이며 효과적인 프레젠테이션 슬라이드를 제작해야 합니다.
주어진 주제에 대해 {slide_type} 형식의 슬라이드 내용을 구성하세요.

**슬라이드 주제:**
{query}

**슬라이드 타입:** {slide_type}

{context}

**슬라이드 작성 지침:**
1. 명확하고 이해하기 쉬운 제목 설정
2. 핵심 내용을 bullet point로 정리
3. 각 포인트는 간결하면서도 구체적으로 작성
4. 클라우드 거버넌스의 실무적 관점 반영
5. 청중이 실행할 수 있는 구체적인 가이드라인 포함

**출력 형식:**
다음 정보를 포함한 구조화된 텍스트로 작성하세요:

제목: [슬라이드 제목]

핵심 내용:
- [포인트 1: 구체적이고 실행 가능한 내용]
- [포인트 2: 관련 정책이나 절차]
- [포인트 3: 모니터링 및 관리 방안]
- [포인트 4: 컴플라이언스 고려사항]
- [포인트 5: 최적화 방안]

상세 설명:
[각 포인트에 대한 추가 설명이나 예시]

결론:
[핵심 메시지나 실행 방안 요약]

이 내용을 바탕으로 HTML 형식의 슬라이드로 변환할 예정입니다.
"""

    def _create_report_prompt(
        self, query: str, context: str, inputs: Dict[str, Any]
    ) -> str:
        """보고서 요약용 프롬프트"""
        return f"""
당신은 클라우드 거버넌스 전문가로서 상세한 보고서를 작성해야 합니다.
검색된 문서 정보를 바탕으로 종합적이고 체계적인 보고서를 작성하세요.

**보고서 주제:**
{query}

{context}

**보고서 작성 지침:**
1. 체계적이고 논리적인 구조로 작성
2. 검색된 문서의 핵심 내용을 통합하여 정리
3. 현황 분석, 문제점, 개선 방안을 포함
4. 구체적인 실행 계획과 성과 지표 제시
5. 관련 법규 및 컴플라이언스 고려사항 포함

**출력 형식:**
다음 구조로 보고서를 작성하세요:

# 보고서 제목

## 1. 개요
- 보고서 목적
- 범위 및 대상

## 2. 현황 분석
- 현재 상황 평가
- 주요 이슈 및 과제

## 3. 핵심 내용
- 주요 정책 및 절차
- 기술적 요구사항
- 관리 방안

## 4. 개선 방안
- 단기 개선 계획
- 중장기 로드맵
- 성과 지표

## 5. 결론 및 권고사항
- 핵심 메시지
- 실행 우선순위
- 향후 계획

이 내용을 바탕으로 구조화된 보고서 요약을 생성할 예정입니다.
"""

    def postprocess(self, outputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Task Management Agent 출력 후처리

        Args:
            outputs (Dict[str, Any]): LLM 응답

        Returns:
            Dict[str, Any]: Answer Agent로 전달할 형식
        """
        try:
            content = outputs.content if hasattr(outputs, "content") else str(outputs)
            task_type = getattr(self, "_current_task_type", "question")

            if task_type == "slide":
                return self._process_slide_output(content)
            elif task_type == "report":
                return self._process_report_output(content)
            else:
                return self._process_question_output(content)

        except Exception as e:
            return {
                "agent_type": "task_management",
                "answer_content": f"작업 처리 중 오류가 발생했습니다: {str(e)}",
                "source_type": "error",
                "confidence": "low",
                "mcp_context": {
                    **self.mcp_context,
                    "status": "error",
                    "message": str(e),
                },
            }

    def _process_question_output(self, content: str) -> Dict[str, Any]:
        """질문 응답 결과 처리"""
        return {
            "agent_type": "question",
            "answer_content": content,
            "source_type": "rag_based",
            "confidence": "high",
            "mcp_context": {
                **self.mcp_context,
                "status": "success",
                "task_type": "question",
                "processing_completed": True,
                "rag_sources_used": True,
                "mcp_enabled": True,
            },
        }

    def _process_slide_output(self, content: str) -> Dict[str, Any]:
        """슬라이드 생성 결과 처리"""
        slide_type = getattr(self, "_current_slide_type", "basic")

        # 제목 추출
        title = "클라우드 거버넌스"
        if "제목:" in content:
            title_line = content.split("제목:")[1].split("\n")[0].strip()
            if title_line:
                title = title_line

        # MCP 클라이언트를 통한 SlideFormatter Tool 호출 (HTML 형식)
        try:
            slide_result = self.mcp_client.format_slide(
                content=content,
                title=title,
                slide_type=slide_type,
                format_type="html",
            )
        except Exception as e:
            print(f"MCP 슬라이드 포맷팅 실패: {str(e)}")
            slide_result = {
                "slide": {},
                "html": "",
                "mcp_context": {
                    "status": "error",
                    "message": f"MCP 슬라이드 포맷팅 실패: {str(e)}",
                },
            }

        return {
            "agent_type": "slide_generation",
            "answer_content": content,
            "slide_data": slide_result.get("slide", {}),
            "slide_html": slide_result.get("html", ""),
            "source_type": "rag_based_slide",
            "confidence": "high",
            "mcp_context": {
                **self.mcp_context,
                "status": "success",
                "task_type": "slide",
                "slide_generated": True,
                "slide_type": slide_type,
                "formatter_status": slide_result.get("mcp_context", {}).get(
                    "status", "unknown"
                ),
                "mcp_enabled": True,
            },
        }

    def _process_report_output(self, content: str) -> Dict[str, Any]:
        """보고서 요약 결과 처리"""
        # 제목 추출
        title = "클라우드 거버넌스 보고서"
        if "# " in content:
            title_line = content.split("# ")[1].split("\n")[0].strip()
            if title_line:
                title = title_line

        # MCP 클라이언트를 통한 ReportSummary Tool 호출
        try:
            report_result = self.mcp_client.summarize_report(
                content=content,
                title=title,
                format_type="html",
            )
        except Exception as e:
            print(f"MCP 보고서 요약 실패: {str(e)}")
            report_result = {
                "summary": {},
                "html": "",
                "mcp_context": {
                    "status": "error",
                    "message": f"MCP 보고서 요약 실패: {str(e)}",
                },
            }

        return {
            "agent_type": "report_summary",
            "answer_content": content,
            "report_data": report_result.get("summary", {}),
            "report_html": report_result.get("html", ""),
            "source_type": "rag_based_report",
            "confidence": "high",
            "mcp_context": {
                **self.mcp_context,
                "status": "success",
                "task_type": "report",
                "report_generated": True,
                "formatter_status": report_result.get("mcp_context", {}).get(
                    "status", "unknown"
                ),
                "mcp_enabled": True,
            },
        }

from typing import Dict, List, Any
from core.base_tool import BaseTool
from core.settings import get_llm
import logging
import re


class SlideDraftTool(BaseTool):
    """
    슬라이드 초안 생성 도구
    RAG 검색 결과와 사용자 입력을 기반으로 슬라이드 초안 데이터를 생성
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.llm = get_llm()

    def run(self, inputs: Dict) -> Dict:
        """
        슬라이드 초안 생성 실행

        Args:
            inputs (Dict): {
                "search_results": List[Dict],
                "user_input": str
            }

        Returns:
            Dict: {"draft": Dict, "mcp_context": Dict}
        """
        try:
            search_results = inputs.get("search_results", [])
            user_input = inputs.get("user_input", "")

            self.logger.info(f"슬라이드 초안 생성 시작")

            # 검색 결과에서 핵심 내용 추출
            key_contents = self._extract_key_contents(search_results)

            # LLM을 사용한 슬라이드 초안 생성
            draft_data = self._generate_slide_draft(user_input, key_contents)

            self.logger.info(
                f"슬라이드 초안 생성 완료: 마크다운 형식 ({draft_data.get('format', 'unknown')})"
            )

            return {
                "draft": draft_data,
                "mcp_context": {
                    "role": "slide_drafter",
                    "status": "success",
                    "search_results_count": len(search_results),
                    "content_length": len(draft_data.get("markdown_content", "")),
                    "format": draft_data.get("format", "unknown"),
                },
            }

        except Exception as e:
            self.logger.error(f"슬라이드 초안 생성 실패: {str(e)}")
            return {
                "draft": {},
                "mcp_context": {
                    "role": "slide_drafter",
                    "status": "error",
                    "message": f"슬라이드 초안 생성 중 오류: {str(e)}",
                },
            }

    def _extract_key_contents(self, search_results: List[Dict]) -> List[str]:
        """검색 결과에서 핵심 내용 추출"""
        key_contents = []

        for result in search_results:
            content = result.get("content", "")
            if not content:
                continue

            # 문장 단위로 분할하여 핵심 내용 추출
            sentences = content.split(".")
            for sentence in sentences:
                sentence = sentence.strip()
                if len(sentence) > 30 and len(sentence) < 300:
                    # 핵심 키워드가 포함된 문장 우선 선별
                    keywords = [
                        "정책",
                        "컴플라이언스",
                        "모니터링",
                        "보안",
                        "관리",
                        "거버넌스",
                        "클라우드",
                        "구현",
                        "방안",
                        "요구사항",
                        "인증",
                        "규정",
                        "준수",
                        "위험",
                        "평가",
                        "감사",
                    ]
                    if any(keyword in sentence for keyword in keywords):
                        key_contents.append(sentence)

            # 최대 10개까지만 수집
            if len(key_contents) >= 10:
                break

        return key_contents[:10]

    def _generate_slide_draft(self, user_input: str, key_contents: List[str]) -> Dict:
        """LLM을 사용하여 슬라이드 초안 생성"""

        # 컨텍스트 구성
        context = (
            "\n".join(key_contents)
            if key_contents
            else "클라우드 거버넌스 관련 일반 정보"
        )

        prompt = f"""
**목표:** 주어진 내용을 분석하여 프레젠테이션 슬라이드 제작을 위한 상세 계획서를 작성합니다.

**세부 지침:**  
1.  **내용 분석:** 주어진 내용을 깊이 있게 분석하여 핵심 주제, 주요 주장, 근거 데이터, 결론 등을 파악합니다.
2.  **슬라이드 구성:** 분석된 내용을 바탕으로 논리적인 흐름(예: 서론 - 본론 - 결론, 문제 제기 - 해결 방안 제시 등)에 맞춰 전체 슬라이드를 구성합니다.
3.  **슬라이드별 계획:** 각 슬라이드에 포함될 내용을 구체적으로 계획합니다. 각 슬라이드 계획에는 다음 요소가 반드시 포함되어야 합니다.  
    *   **슬라이드 번호:** `# 슬라이드 N` 형식으로 표기합니다.  
    *   **주제:** 해당 슬라이드의 핵심 주제를 명료하게 작성합니다. (`주제: ...`)  
    *   **요약 내용:** 해당 슬라이드에서 전달할 핵심 메시지, 포함될 주요 내용, 데이터, 시각 자료 아이디어 등을 간결하게 요약합니다. (`요약 내용: ...`)  
4.  **답변 생성:** 위 계획을 마크다운 형식으로 답변합니다. 마크다운 형식 외 다른 설명은 제거해 주세요.

**출력 형식 예시:**  
```markdown  

# 슬라이드 1  

주제: 연구의 배경 및 필요성  

요약 내용: [연구 주제]가 왜 중요한지, 현재 어떤 문제 상황이 있는지 설명합니다. 관련 통계나 이전 연구를 간략히 언급하여 연구의 필요성을 강조합니다.  



# 슬라이드 2  

주제: 연구 목표 및 질문  

요약 내용: 본 연구를 통해 구체적으로 무엇을 밝히고자 하는지 명확한 목표를 제시합니다. 연구 질문을 1~2가지로 명료하게 제시합니다.  



# 슬라이드 3  

주제: 연구 방법론  

요약 내용: 연구 목표 달성을 위해 어떤 연구 방법을 사용했는지 설명합니다. (예: 설문조사, 문헌 연구, 실험 등). 데이터 수집 및 분석 과정을 간략하게 소개합니다.  

... (이하 생략) ...  



# 슬라이드 N  

주제: 결론 및 제언  

요약 내용: 연구 결과를 요약하고, 연구의 핵심 결론을 명확하게 전달합니다. 연구의 한계점과 향후 연구 방향 또는 실질적인 제언을 덧붙입니다.  



**추가 사항**
답변에는 총 3개의 슬라이드로 모든 필수적인 내용이 담기도록 구성해 주세요.

** 제공된 정보 **
- 사용자 요청 : {user_input}

** 참고 자료 **
{context}
"""

        try:
            # LLM 호출
            response = self.llm.invoke(prompt)

            # 응답에서 마크다운 텍스트 추출
            response_text = (
                response.content if hasattr(response, "content") else str(response)
            )

            # 마크다운 코드 블록 제거 (필요시)
            if "```markdown" in response_text:
                response_text = re.sub(r"```markdown\s*", "", response_text)
                response_text = re.sub(r"```\s*$", "", response_text)
            elif "```" in response_text:
                response_text = re.sub(r"```\s*", "", response_text)

            # 마크다운 형식 그대로 반환
            draft_data = {
                "markdown_content": response_text.strip(),
                "format": "markdown_raw",
            }

            return draft_data

        except Exception as e:
            self.logger.error(f"LLM 호출 실패: {str(e)}")
            # 폴백 초안 생성
            return self._create_fallback_draft(user_input)

    def _create_fallback_draft(self, user_input: str) -> Dict:
        """LLM 호출 실패 시 폴백 초안 생성"""

        # 사용자 입력에서 키워드 추출
        keywords = self._extract_keywords_from_input(user_input)

        # 마크다운 형식으로 폴백 초안 생성
        fallback_markdown = f"""# 슬라이드 1

주제: 개요 및 배경

요약 내용: 사용자 요청 '{user_input}'에 대한 개요와 배경을 설명합니다.

# 슬라이드 2

주제: 주요 내용

요약 내용: 핵심 키워드 '{', '.join(keywords)}'를 중심으로 한 주요 내용을 다룹니다.

# 슬라이드 3

주제: 결론 및 제언

요약 내용: 분석 결과를 바탕으로 한 결론과 향후 제언사항을 제시합니다."""

        return {"markdown_content": fallback_markdown, "format": "markdown_fallback"}

    def _extract_keywords_from_input(self, user_input: str) -> List[str]:
        """사용자 입력에서 키워드 추출"""
        import re

        # 불용어 제거
        stop_words = {
            "이",
            "그",
            "저",
            "것",
            "수",
            "등",
            "및",
            "또는",
            "그리고",
            "하는",
            "있는",
            "되는",
            "에서",
            "으로",
            "를",
            "을",
            "의",
            "가",
        }

        # 특수문자 제거 및 단어 분리
        cleaned_input = re.sub(r"[^\w\s]", " ", user_input)
        words = cleaned_input.split()

        # 키워드 필터링
        keywords = [word for word in words if len(word) >= 2 and word not in stop_words]

        return keywords[:5]  # 최대 5개까지

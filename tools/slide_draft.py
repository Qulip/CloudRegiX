from typing import Dict, List, Any
from core.base_tool import BaseTool
from core.settings import get_llm
import logging


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
                "user_input": str,
                "title": str
            }

        Returns:
            Dict: {"draft": Dict, "mcp_context": Dict}
        """
        try:
            search_results = inputs.get("search_results", [])
            user_input = inputs.get("user_input", "")
            title = inputs.get("title", "클라우드 거버넌스")

            self.logger.info(f"슬라이드 초안 생성 시작")

            # 검색 결과에서 핵심 내용 추출
            key_contents = self._extract_key_contents(search_results)

            # LLM을 사용한 슬라이드 초안 생성
            draft_data = self._generate_slide_draft(user_input, key_contents, title)

            self.logger.info(
                f"슬라이드 초안 생성 완료: {len(draft_data.get('bullets', []))}개 항목"
            )

            return {
                "draft": draft_data,
                "mcp_context": {
                    "role": "slide_drafter",
                    "status": "success",
                    "search_results_count": len(search_results),
                    "bullets_count": len(draft_data.get("bullets", [])),
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

    def _generate_slide_draft(
        self, user_input: str, key_contents: List[str], title: str
    ) -> Dict:
        """LLM을 사용하여 슬라이드 초안 생성"""

        # 컨텍스트 구성
        context = (
            "\n".join(key_contents)
            if key_contents
            else "클라우드 거버넌스 관련 일반 정보"
        )

        prompt = f"""
다음 정보를 바탕으로 기본 보고서 슬라이드의 초안을 작성해주세요.

- 사용자의 요청에 맞는 핵심 포인트 들이 포함되어야 합니다.
- 핵심 포인트는 3-5개로 구성하고, 각 포인트는 명확하고 간결하게 작성해주세요.
- 핵심 포인트는 사용자의 요청에 맞는 내용이어야 합니다.
- 핵심 포인트는 참고 자료에 포함된 내용이어야 합니다.

사용자 요청: {user_input}
제목: {title}
참고 자료: {context}

다음 JSON 형식으로 응답해주세요:
{{
    "title": "슬라이드 제목",
    "bullets": ["핵심 포인트 1", "핵심 포인트 2", "핵심 포인트 3", "핵심 포인트 4", "핵심 포인트 5"],
    "notes": "슬라이드 설명"
}}

핵심 포인트는 3-5개로 구성하고, 각 포인트는 명확하고 간결하게 작성해주세요.
"""

        try:
            # LLM 호출
            response = self.llm.invoke(prompt)

            # 응답에서 JSON 추출
            response_text = (
                response.content if hasattr(response, "content") else str(response)
            )

            # JSON 파싱 시도
            import json
            import re

            # JSON 블록 찾기
            json_match = re.search(r"\{.*\}", response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                draft_data = json.loads(json_str)
            else:
                # JSON을 찾지 못한 경우 기본 구조 생성
                draft_data = self._create_fallback_draft(user_input, title)

            return draft_data

        except Exception as e:
            self.logger.error(f"LLM 호출 실패: {str(e)}")
            # 폴백 초안 생성
            return self._create_fallback_draft(user_input, title)

    def _create_fallback_draft(self, user_input: str, title: str) -> Dict:
        """LLM 호출 실패 시 폴백 초안 생성"""

        # 사용자 입력에서 키워드 추출
        keywords = self._extract_keywords_from_input(user_input)

        return {
            "title": title,
            "bullets": [
                f"{title} 개요",
                f"{title} 주요 특징",
                f"{title} 적용 방안",
                f"{title} 기대 효과",
            ],
            "notes": "기본 슬라이드 초안",
        }

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

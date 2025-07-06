from typing import Dict, List, Any, Generator, Type
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field
import json
import logging
from core.settings import get_llm
from langchain_core.messages import HumanMessage, SystemMessage

# 로깅 설정
logger = logging.getLogger(__name__)


class SlideGeneratorInput(BaseModel):
    """슬라이드 생성기 입력 모델"""

    slide_draft: Dict[str, Any] = Field(description="슬라이드 초안 데이터")
    search_results: List[Dict[str, Any]] = Field(description="RAG 검색 결과 데이터")
    user_input: str = Field(description="사용자 입력")


class SlideGeneratorTool(BaseTool):
    """
    슬라이드 생성 LangChain 도구
    slide_draft 툴의 결과와 RAG 검색 결과를 기반으로 LLM을 활용한 HTML 슬라이드 생성
    """

    name: str = "slide_generator"
    description: str = (
        "슬라이드 생성 도구 - slide_draft와 RAG 검색 결과를 기반으로 LLM을 활용한 HTML 슬라이드 생성"
    )
    args_schema: Type[BaseModel] = SlideGeneratorInput

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._llm = None
        logger.info("SlideGeneratorTool 초기화 완료")

    @property
    def llm(self):
        """LLM 인스턴스를 lazy loading으로 가져옴"""
        if self._llm is None:
            self._llm = get_llm()
        return self._llm

    def _create_slide_content_with_llm(
        self,
        slide_draft: Dict,
        search_results: List[Dict],
        user_input: str,
    ) -> Dict:
        """LLM을 활용하여 슬라이드 콘텐츠 생성"""

        logger.info(f"LLM을 활용한 슬라이드 콘텐츠 생성 시작")

        # 검색 결과 요약
        search_content = "\n".join(
            [f"- {result.get('content', '')[:200]}..." for result in search_results[:5]]
        )

        # 시스템 메시지 정의
        system_message = SystemMessage(
            content="""
당신은 전문적인 클라우드 거버넌스 보고서 컨설턴트 AI 어시스턴트입니다.
주어진 정보를 바탕으로 보고서에 작성될 콘텐츠를 선정 및 정리해야 합니다.

반드시 JSON 형식으로 응답하며, 한국어로 작성해주세요.
"""
        )

        # 사용자 메시지 생성
        user_message = HumanMessage(
            content=f"""
다음 정보를 바탕으로 보고서에 포함되어야 하는 콘텐츠 내용들을 선정하고, 보고서 형식에 알맞게 문구를 변경해주세요:

**사용자 요청:**
{user_input}

**슬라이드 초안:**
{json.dumps(slide_draft, ensure_ascii=False, indent=2)}

**검색 결과 요약:**
{search_content}

** 필수 출력 형식 **
{{
    "title": "슬라이드 제목",
    "bullets": ["핵심 포인트 1", "핵심 포인트 2", ...],
    "sub_bullets": {{"point_1": {{"세부사항1": "세부사항1 내용", "세부사항2": "세부사항2 내용"}}, ...}},
    "conclusion": "결론",
    "notes": "추가 노트나 출처 정보"
}}

**요구사항:**
- 슬라이드 초안의 문구 핵심 포인트 들은 차용하되, 워딩은 수정 가능
- sub_bullets 는 핵심 포인트별 세부 사항 과 세부사항 별 슬라이드에 들어갈 내용(각 세부사항 별 슬라이드 생성 예정)
- 사용자의 요청에 맞는 내용
- 간결하고, 명확한 워딩 사용
"""
        )

        try:
            # LLM 호출
            logger.info("LLM 호출 시작")
            response = self.llm.invoke([system_message, user_message])
            logger.info("LLM 응답 수신 완료")

            # JSON 파싱
            content = response.content.strip()
            if content.startswith("```json"):
                content = content[7:-3].strip()
            elif content.startswith("```"):
                content = content[3:-3].strip()

            slide_content = json.loads(content)
            logger.info("슬라이드 콘텐츠 생성 완료")

            return slide_content

        except Exception as e:
            logger.error(f"LLM 슬라이드 콘텐츠 생성 실패: {str(e)}")
            # 폴백: 기본 구조 반환
            return self._create_fallback_content(slide_draft, search_results)

    def _create_fallback_content(
        self, slide_draft: Dict, search_results: List[Dict]
    ) -> Dict:
        """LLM 실패 시 폴백 콘텐츠 생성"""
        logger.info("폴백 콘텐츠 생성 시작")

        title = slide_draft.get("title", "클라우드 거버넌스 보고서")
        bullets = slide_draft.get("bullets", ["핵심 포인트를 생성할 수 없습니다."])

        # 검색 결과에서 간단한 포인트 추출
        if search_results:
            search_bullets = []
            for result in search_results[:3]:
                content = result.get("content", "")
                if content and len(content) > 20:
                    search_bullets.append(content[:100] + "...")
            if search_bullets:
                bullets.extend(search_bullets)

        return {
            "title": title,
            "bullets": bullets[:5],
            "notes": f"검색 결과 {len(search_results)}개 기반으로 생성",
        }

    def _generate_html_with_llm(self, slide_content: Dict, user_input: str) -> str:
        """LLM을 활용하여 HTML 생성"""

        logger.info("LLM을 활용한 HTML 생성 시작")

        system_message = SystemMessage(
            content="""
당신은 보고서에 포함될 내용들을 토대로 보고서 형식의 HTML 슬라이드를 생성해주는 AI 어시스턴스 입니다.
주어진 슬라이드 콘텐츠를 바탕으로 아름답고 전문적인 HTML 보고서를 생성해주세요.

요구사항:
- 반응형 디자인 (모바일 친화적)
- 현대적이고 전문적인 스타일
- 보고서에 적합한 색상 체계
- 가독성이 좋은 폰트와 레이아웃
- 적절한 아이콘과 시각적 요소
- 완전한 HTML 문서 (DOCTYPE, head, body 포함)
"""
        )

        user_message = HumanMessage(
            content=f"""
다음 보고서로 작성할 콘텐츠를 바탕으로 전문적인 HTML 보고서를 생성해주세요:

** 사용자 요청 ** {user_input}

** 보고서에 포함되야하는 내용 **
{json.dumps(slide_content, ensure_ascii=False, indent=2)}

    > 내용 설명
    - {{
        "title": "슬라이드 제목",
        "bullets": ["핵심 포인트 1", "핵심 포인트 2", ...],
        "sub_bullets": {{"point_1": {{"세부사항1": "세부사항1 내용", "세부사항2": "세부사항2 내용"}}, ...}},
        "conclusion": "결론",
        "notes": "추가 노트나 출처 정보"
    }}
    - sub_bullets 는 핵심 포인트별 세부 사항 과 세부사항 별 슬라이드에 들어갈 내용
    - 각 세부사항 별 슬라이드 생성 필요

** 요구사항 **
- 완전한 HTML 문서로 생성
- CSS는 인라인 스타일로 포함하여 작성
- 보고서에 적합한 전문적인 디자인 적용

** 답변 형식 **
- 답변은 반드시 완전한 HTML 문서로 생성
- HTML 내용 설명 등 HTML을 제외한 내용은 답변하지 않아도 됨
"""
        )

        try:
            logger.info("HTML 생성을 위한 LLM 호출 시작")
            response = self.llm.invoke([system_message, user_message])
            html_content = response.content.strip()

            # HTML 코드 블록 제거
            if html_content.startswith("```html"):
                html_content = html_content[7:-3].strip()
            elif html_content.startswith("```"):
                html_content = html_content[3:-3].strip()

            logger.info("HTML 생성 완료")
            return html_content

        except Exception as e:
            logger.error(f"LLM HTML 생성 실패: {str(e)}")
            # 폴백: 기본 HTML 템플릿 사용
            return self._create_fallback_html(slide_content)

    def _create_fallback_html(self, slide_content: Dict) -> str:
        """폴백 HTML 생성"""
        logger.info("폴백 HTML 생성 시작")

        title = slide_content.get("title", "보고서")

        html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        body {{
            font-family: 'Segoe UI', 'Malgun Gothic', Arial, sans-serif;
            line-height: 1.6;
            margin: 0;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #333;
            min-height: 100vh;
        }}
        .container {{
            max-width: 1000px;
            margin: 0 auto;
            background: white;
            border-radius: 15px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
            overflow: hidden;
        }}
        .header {{
            background: linear-gradient(135deg, #2c3e50 0%, #34495e 100%);
            color: white;
            padding: 40px;
            text-align: center;
        }}
        .header h1 {{
            margin: 0;
            font-size: 2.5rem;
            font-weight: 300;
        }}
        .content {{
            padding: 40px;
        }}
        .section {{
            margin-bottom: 30px;
        }}
        .section h2 {{
            color: #2c3e50;
            border-bottom: 2px solid #3498db;
            padding-bottom: 10px;
        }}
        .bullet-list {{
            list-style: none;
            padding: 0;
        }}
        .bullet-list li {{
            background: #f8f9fa;
            margin: 10px 0;
            padding: 15px;
            border-radius: 8px;
            border-left: 4px solid #3498db;
        }}
        .comparison {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
        }}
        .comparison-column {{
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
        }}
        .footer {{
            background: #ecf0f1;
            padding: 20px;
            text-align: center;
            color: #7f8c8d;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{title}</h1>
        </div>
        <div class="content">"""

        html += '<div class="section"><h2>핵심 포인트</h2><ul class="bullet-list">'
        for bullet in slide_content.get("bullets", []):
            html += f"<li>{bullet}</li>"
        html += "</ul></div>"

        if slide_content.get("notes"):
            html += (
                f'<div class="section"><p><em>{slide_content["notes"]}</em></p></div>'
            )

        html += """
        </div>
        <div class="footer">
            클라우드 거버넌스 AI 시스템에서 생성된 보고서입니다.
        </div>
    </div>
</body>
</html>"""

        return html

    def _run(
        self,
        slide_draft: Dict[str, Any],
        search_results: List[Dict[str, Any]],
        user_input: str,
    ) -> str:
        """LangChain Tool 실행 메서드"""
        logger.info(f"SlideGeneratorTool 실행 시작")

        inputs = {
            "slide_draft": slide_draft,
            "search_results": search_results,
            "user_input": user_input,
        }

        result = self.run(inputs)
        return json.dumps(result, ensure_ascii=False, indent=2)

    def run_streaming(self, inputs: Dict) -> Generator[Dict[str, Any], None, None]:
        """스트리밍 실행을 위한 메서드"""
        logger.info(f"스트리밍 슬라이드 생성 시작")

        try:
            # 진행 상황 스트리밍
            yield {
                "type": "progress",
                "stage": "analyzing_input",
                "message": "입력 데이터 분석 중...",
                "progress": 0.1,
            }

            # LLM으로 슬라이드 콘텐츠 생성
            yield {
                "type": "progress",
                "stage": "generating_content",
                "message": "LLM을 활용한 슬라이드 콘텐츠 생성 중...",
                "progress": 0.3,
            }

            slide_content = self._create_slide_content_with_llm(
                inputs.get("slide_draft", {}),
                inputs.get("search_results", []),
                inputs.get("user_input", ""),
            )

            yield {
                "type": "progress",
                "stage": "generating_html",
                "message": "HTML 슬라이드 생성 중...",
                "progress": 0.8,
            }

            # LLM으로 HTML 생성
            html = self._generate_html_with_llm(
                slide_content, inputs.get("user_input", "")
            )

            # 최종 결과
            final_result = {
                "slide": slide_content,
                "html": html,
                "langchain_context": {
                    "tool_name": "slide_generator",
                    "status": "success",
                    "generation_method": "llm_based",
                    "total_bullets": len(slide_content.get("bullets", [])),
                    "search_results_count": len(inputs.get("search_results", [])),
                },
            }

            yield {
                "type": "result",
                "stage": "completed",
                "message": "LLM 기반 슬라이드 생성 완료",
                "progress": 1.0,
                "data": final_result,
            }

        except Exception as e:
            logger.error(f"스트리밍 슬라이드 생성 실패: {str(e)}")
            yield {
                "type": "error",
                "stage": "error",
                "message": f"슬라이드 생성 중 오류: {str(e)}",
                "progress": 0.0,
                "error": str(e),
            }

    def run(self, inputs: Dict) -> Dict:
        """기존 방식과의 호환성을 위한 메서드"""

        logger.info(f"슬라이드 생성 시작")

        try:
            # LLM으로 슬라이드 콘텐츠 생성
            slide_content = self._create_slide_content_with_llm(
                inputs.get("slide_draft", {}),
                inputs.get("search_results", []),
                inputs.get("user_input", ""),
            )

            # LLM으로 HTML 생성
            html = self._generate_html_with_llm(
                slide_content, inputs.get("user_input", "")
            )

            result = {
                "slide": slide_content,
                "html": html,
                "langchain_context": {
                    "tool_name": "slide_generator",
                    "status": "success",
                    "generation_method": "llm_based",
                    "total_bullets": len(slide_content.get("bullets", [])),
                    "search_results_count": len(inputs.get("search_results", [])),
                },
            }

            logger.info("슬라이드 생성 완료")
            return result

        except Exception as e:
            logger.error(f"슬라이드 생성 실패: {str(e)}")
            return {
                "slide": {},
                "html": "",
                "markdown": "",
                "langchain_context": {
                    "tool_name": "slide_generator",
                    "status": "error",
                    "message": f"슬라이드 생성 중 오류: {str(e)}",
                    "generation_method": "llm_based",
                },
            }

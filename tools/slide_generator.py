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
    slide_type: str = Field(
        default="basic", description="슬라이드 유형 (basic, detailed, comparison)"
    )
    format_type: str = Field(default="html", description="출력 형식 (html, json)")


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
        slide_type: str,
    ) -> Dict:
        """LLM을 활용하여 슬라이드 콘텐츠 생성"""

        logger.info(f"LLM을 활용한 슬라이드 콘텐츠 생성 시작 - 타입: {slide_type}")

        # 검색 결과 요약
        search_content = "\n".join(
            [f"- {result.get('content', '')[:200]}..." for result in search_results[:5]]
        )

        # 시스템 메시지 정의
        system_message = SystemMessage(
            content="""
당신은 전문적인 보고서 슬라이드를 생성하는 AI 어시스턴트입니다.
주어진 정보를 바탕으로 구조화된 슬라이드 콘텐츠를 생성해야 합니다.

슬라이드 유형별 요구사항:
- basic: 제목, 핵심 포인트 5개, 간단한 노트
- detailed: 제목, 부제목, 핵심 포인트 3개, 각 포인트별 세부사항 3개, 결론
- comparison: 제목, 좌측 컬럼(현재 상황), 우측 컬럼(개선 방안), 각각 3-4개 항목

반드시 JSON 형식으로 응답하며, 한국어로 작성해주세요.
"""
        )

        # 사용자 메시지 생성
        user_message = HumanMessage(
            content=f"""
다음 정보를 바탕으로 '{slide_type}' 유형의 슬라이드 콘텐츠를 생성해주세요:

**사용자 요청:**
{user_input}

**슬라이드 초안:**
{json.dumps(slide_draft, ensure_ascii=False, indent=2)}

**검색 결과 요약:**
{search_content}

**요구사항:**
- 슬라이드 유형: {slide_type}
- 전문적이고 구조화된 보고서 형식
- 실용적이고 구체적인 내용
- 클라우드 거버넌스 맥락에 맞는 내용

다음 JSON 형식으로 응답해주세요:
{{
    "title": "슬라이드 제목",
    "subtitle": "부제목 (detailed 타입인 경우)",
    "bullets": ["핵심 포인트 1", "핵심 포인트 2", ...],
    "sub_bullets": {{"point_1": ["세부사항1", "세부사항2"], ...}} (detailed 타입인 경우),
    "left_column": {{"title": "좌측 제목", "items": ["항목1", "항목2", ...]}} (comparison 타입인 경우),
    "right_column": {{"title": "우측 제목", "items": ["항목1", "항목2", ...]}} (comparison 타입인 경우),
    "conclusion": "결론 (detailed 타입인 경우)",
    "notes": "추가 노트나 출처 정보"
}}
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
            return self._create_fallback_content(
                slide_draft, search_results, slide_type
            )

    def _create_fallback_content(
        self, slide_draft: Dict, search_results: List[Dict], slide_type: str
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

        if slide_type == "detailed":
            return {
                "title": title,
                "subtitle": "상세 분석",
                "bullets": bullets[:3],
                "sub_bullets": {
                    "point_1": ["구현 방안", "모니터링 방법", "최적화 전략"],
                    "point_2": ["현재 상황", "개선 필요사항", "기대 효과"],
                    "point_3": ["리스크 관리", "성과 측정", "지속적 개선"],
                },
                "conclusion": "체계적인 접근이 필요합니다.",
                "notes": f"검색 결과 {len(search_results)}개 기반으로 생성",
            }
        elif slide_type == "comparison":
            mid_point = len(bullets) // 2
            return {
                "title": title,
                "left_column": {
                    "title": "현재 상황",
                    "items": (
                        bullets[:mid_point]
                        if mid_point > 0
                        else ["현재 상황 분석 필요"]
                    ),
                },
                "right_column": {
                    "title": "개선 방안",
                    "items": (
                        bullets[mid_point:]
                        if mid_point > 0
                        else ["개선 방안 수립 필요"]
                    ),
                },
                "notes": f"검색 결과 {len(search_results)}개 기반으로 생성",
            }
        else:
            return {
                "title": title,
                "bullets": bullets[:5],
                "notes": f"검색 결과 {len(search_results)}개 기반으로 생성",
            }

    def _generate_html_with_llm(
        self, slide_content: Dict, slide_type: str, user_input: str
    ) -> str:
        """LLM을 활용하여 HTML 생성"""

        logger.info("LLM을 활용한 HTML 생성 시작")

        system_message = SystemMessage(
            content="""
당신은 전문적인 HTML 슬라이드를 생성하는 AI입니다.
주어진 슬라이드 콘텐츠를 바탕으로 아름답고 전문적인 HTML 보고서를 생성해주세요.

요구사항:
- 반응형 디자인 (모바일 친화적)
- 현대적이고 전문적인 스타일
- 클라우드 거버넌스에 적합한 색상 체계
- 가독성이 좋은 폰트와 레이아웃
- 적절한 아이콘과 시각적 요소
- 완전한 HTML 문서 (DOCTYPE, head, body 포함)
"""
        )

        user_message = HumanMessage(
            content=f"""
다음 슬라이드 콘텐츠를 바탕으로 전문적인 HTML 보고서를 생성해주세요:

**슬라이드 유형:** {slide_type}
**사용자 요청:** {user_input}

**슬라이드 콘텐츠:**
{json.dumps(slide_content, ensure_ascii=False, indent=2)}

완전한 HTML 문서를 생성해주세요. CSS는 인라인 스타일로 포함하고, 
보고서에 적합한 전문적인 디자인을 적용해주세요.
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
            return self._create_fallback_html(slide_content, slide_type)

    def _create_fallback_html(self, slide_content: Dict, slide_type: str) -> str:
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

        if slide_type == "comparison":
            html += '<div class="section"><h2>비교 분석</h2><div class="comparison">'
            html += f'<div class="comparison-column"><h3>{slide_content.get("left_column", {}).get("title", "좌측")}</h3><ul class="bullet-list">'
            for item in slide_content.get("left_column", {}).get("items", []):
                html += f"<li>{item}</li>"
            html += f'</ul></div><div class="comparison-column"><h3>{slide_content.get("right_column", {}).get("title", "우측")}</h3><ul class="bullet-list">'
            for item in slide_content.get("right_column", {}).get("items", []):
                html += f"<li>{item}</li>"
            html += "</ul></div></div></div>"
        else:
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
        slide_type: str = "basic",
        format_type: str = "html",
    ) -> str:
        """LangChain Tool 실행 메서드"""
        logger.info(f"SlideGeneratorTool 실행 시작 - 타입: {slide_type}")

        inputs = {
            "slide_draft": slide_draft,
            "search_results": search_results,
            "user_input": user_input,
            "slide_type": slide_type,
            "format_type": format_type,
        }

        result = self.run(inputs)
        return json.dumps(result, ensure_ascii=False, indent=2)

    def run_streaming(self, inputs: Dict) -> Generator[Dict[str, Any], None, None]:
        """스트리밍 실행을 위한 메서드"""
        slide_type = inputs.get("slide_type", "basic")
        logger.info(f"스트리밍 슬라이드 생성 시작 - 타입: {slide_type}")

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
                slide_type,
            )

            yield {
                "type": "progress",
                "stage": "generating_html",
                "message": "HTML 슬라이드 생성 중...",
                "progress": 0.6,
            }

            # LLM으로 HTML 생성
            html = self._generate_html_with_llm(
                slide_content, slide_type, inputs.get("user_input", "")
            )

            yield {
                "type": "progress",
                "stage": "generating_markdown",
                "message": "마크다운 형식 생성 중...",
                "progress": 0.8,
            }

            # 마크다운 생성
            markdown = self._convert_to_markdown(slide_content, slide_type)

            # 최종 결과
            final_result = {
                "slide": slide_content,
                "html": html,
                "markdown": markdown,
                "langchain_context": {
                    "tool_name": "slide_generator",
                    "status": "success",
                    "slide_type": slide_type,
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
        slide_type = inputs.get("slide_type", "basic")
        format_type = inputs.get("format_type", "html")

        logger.info(f"슬라이드 생성 시작 - 타입: {slide_type}, 형식: {format_type}")

        try:
            # LLM으로 슬라이드 콘텐츠 생성
            slide_content = self._create_slide_content_with_llm(
                inputs.get("slide_draft", {}),
                inputs.get("search_results", []),
                inputs.get("user_input", ""),
                slide_type,
            )

            # LLM으로 HTML 생성
            html = self._generate_html_with_llm(
                slide_content, slide_type, inputs.get("user_input", "")
            )

            # 마크다운 생성
            markdown = self._convert_to_markdown(slide_content, slide_type)

            result = {
                "slide": slide_content,
                "html": html,
                "markdown": markdown,
                "langchain_context": {
                    "tool_name": "slide_generator",
                    "status": "success",
                    "slide_type": slide_type,
                    "format": format_type,
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

    def _convert_to_markdown(self, slide_content: Dict, slide_type: str) -> str:
        """슬라이드 콘텐츠를 마크다운으로 변환"""
        markdown = f"# {slide_content.get('title', '제목 없음')}\n\n"

        if slide_type == "detailed" and slide_content.get("subtitle"):
            markdown += f"## {slide_content['subtitle']}\n\n"

        if slide_type == "comparison":
            left_col = slide_content.get("left_column", {})
            right_col = slide_content.get("right_column", {})

            markdown += f"## {left_col.get('title', '좌측')}\n"
            for item in left_col.get("items", []):
                markdown += f"- {item}\n"

            markdown += f"\n## {right_col.get('title', '우측')}\n"
            for item in right_col.get("items", []):
                markdown += f"- {item}\n"
        else:
            markdown += "## 핵심 포인트\n"
            for bullet in slide_content.get("bullets", []):
                markdown += f"- {bullet}\n"

            if slide_type == "detailed" and slide_content.get("sub_bullets"):
                markdown += "\n## 세부 사항\n"
                for key, sub_items in slide_content["sub_bullets"].items():
                    for sub_item in sub_items:
                        markdown += f"  - {sub_item}\n"

            if slide_content.get("conclusion"):
                markdown += f"\n## 결론\n{slide_content['conclusion']}\n"

        if slide_content.get("notes"):
            markdown += f"\n---\n*{slide_content['notes']}*\n"

        return markdown

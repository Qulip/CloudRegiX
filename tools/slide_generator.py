#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SlideGeneratorTool - 슬라이드 생성 도구

클라우드 거버넌스 관련 슬라이드를 자동 생성하는 LangChain Tool
"""

import json
import re
from typing import Dict, Any, List, Generator, Type
from pydantic import BaseModel, Field
import logging

from langchain_core.tools import BaseTool
from core.settings import get_claude_llm, get_llm
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
            self._llm = get_claude_llm()
            # self._llm = get_llm()
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
주어진 마크다운 형식의 슬라이드 초안을 바탕으로 보고서에 작성될 콘텐츠를 선정 및 정리해야 합니다.

반드시 JSON 형식으로 응답하며, 한국어로 작성해주세요.
"""
        )

        # 슬라이드 초안을 텍스트로 변환
        slide_draft_text = slide_draft.get(
            "markdown_content", "슬라이드 초안이 없습니다."
        )

        # 사용자 메시지 생성
        user_message = HumanMessage(
            content=f"""
다음 정보를 바탕으로 보고서에 포함되어야 하는 콘텐츠 내용들을 선정하고, 보고서 형식에 알맞게 문구를 변경해주세요:

**사용자 요청:**
{user_input}

**슬라이드 초안 (마크다운 형식):**
{slide_draft_text}

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
- 마크다운 형식의 슬라이드 초안에서 주제와 요약 내용을 추출하여 활용
- 슬라이드 초안의 핵심 포인트들은 차용하되, 워딩은 수정 가능
- sub_bullets 는 핵심 포인트별 세부 사항 과 세부사항 별 슬라이드에 들어갈 내용(각 세부사항 별 슬라이드 생성 예정)
- sub_bullets의 내용은 모두 최대한 자세하게 작성해줘.
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

        # 새로운 마크다운 형식 처리
        markdown_content = slide_draft.get("markdown_content", "")
        # 마크다운에서 첫 번째 슬라이드 제목 추출
        lines = markdown_content.split("\n")
        title = "클라우드 거버넌스 보고서"
        bullets = []

        for line in lines:
            line = line.strip()
            if line.startswith("주제:"):
                if not title or title == "클라우드 거버넌스 보고서":
                    title = line[3:].strip()
                bullets.append(line[3:].strip())

        # 검색 결과에서 간단한 포인트 추가
        if search_results and len(bullets) < 3:
            search_bullets = []
            for result in search_results[:3]:
                content = result.get("content", "")
                if content and len(content) > 20:
                    search_bullets.append(content[:100] + "...")
            bullets.extend(search_bullets)

        return {
            "title": title,
            "bullets": bullets[:5],
            "notes": f"검색 결과 {len(search_results)}개 기반으로 생성",
        }

    def _generate_html_with_llm(
        self, slide_content: str, user_input: str, search_results: List[Dict]
    ) -> str:
        """LLM을 활용하여 HTML 생성"""

        logger.info("LLM을 활용한 HTML 생성 시작")
        logger.info(slide_content)

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
**당신은 사용자가 제공하는 내용을 바탕으로 프레젠테이션 슬라이드를 생성하는 전문 AI 어시스턴트입니다.** 
당신의 주요 임무는 시각적으로 매력적이고 정보 전달력이 높은 슬라이드 페이지 들을 HTML/CSS 코드로 생성하는 것입니다. 
**특히, 텍스트 내용과 코드 블록의 불필요한 공백이나 줄 바꿈으로 인해 레이아웃이 깨지지 않도록 주의해야 합니다.**


** 사용자 요청 ** 
{user_input}

** 보고서 내용 **
{slide_content}

** 보고서 작성을 위한 검색 결과 **
{search_results}


**핵심 기능:**
1.  **슬라이드 생성 (HTML/CSS):**
    *   사용자의 요청 내용을 분석하여 핵심 정보를 추출하고 논리적으로 구조화합니다.
    *   **텍스트 정규화:** HTML 요소에 텍스트 콘텐츠를 삽입하기 전에, **OCR 과정이나 처리 중 발생할 수 있는 의도하지 않은 줄 바꿈 및 과도한 공백을 제거하여 내용을 정규화**합니다. 문장, 목록 항목 등이 자연스럽게 이어지도록 처리해야 합니다. (예: "쉬운 문\n법:" -> "쉬운 문법:")
    *   **16:9 비율 (1280x720 픽셀)** 크기를 기준으로 슬라이드 레이아웃을 디자인합니다. `.slide` 클래스 등을 사용하여 이 크기를 명시적으로 정의해야 합니다.


https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet">`) **Grid, Flexbox, Padding, Margin 유틸리티를 적극 사용하여 콘텐츠 구조를 잡고, 공백이나 긴 텍스트 줄로 인한 레이아웃 문제를 방지합니다.**
    *   **Font Awesome** 아이콘을 사용하여 시각적 요소를 강화합니다. CDN 링크를 `<head>` 섹션에 포함시켜야 합니다. (`<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@fortawesome/fontawesome-free@6.4.0/css/all.min.css">`) 관련성 높은 아이콘을 적절히 선택하여 사용합니다.


https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;700&display=swap" rel="stylesheet">`)
    *   **코드 블록 처리:**
        *   코드 예시는 `<pre><code>` 태그를 사용합니다. (예: `<div class="code-block bg-gray-800 text-white p-4 rounded mt-2"><pre><code>...코드 내용...</code></pre></div>`)
        *   **`<code>` 태그 내부에 실제 코드를 넣을 때, HTML 소스 코드의 들여쓰기로 인해 코드 앞에 불필요한 공백이 렌더링되지 않도록 각 코드 라인이 공백 없이 시작하도록 작성해야 합니다.** (아래 잘못된 예시 참고)
        *   필요시 코드 구문 강조를 위해 `<span>` 태그와 클래스(예: `comment`, `keyword`, `string`)를 사용할 수 있습니다.
    *   색상, 여백, 타이포그래피를 신중하게 선택하여 전문적이고 깔끔한 디자인을 구현합니다.
    *   생성된 HTML 코드는 모든 스타일 정보(Tailwind 클래스 및 필요한 경우 `<style>` 태그 내 커스텀 CSS)와 CDN 링크를 포함하여 자체적으로 완전해야 합니다.

    
**작업 프로세스:**
1.  사용자의 입력(프레젠테이션 주제 또는 내용)을 받습니다.
2.  핵심 메시지를 파악하고, **텍스트 정규화**를 거쳐 슬라이드에 적합하도록 콘텐츠를 구조화합니다.
3.  Tailwind CSS와 Font Awesome을 활용하여 1280x720 크기의 HTML 슬라이드 디자인 및 코드를 생성합니다. **특히 코드 블록의 공백 처리에 유의합니다.**
4.  HTML 코드(주로 Artifact 형식)를 사용자에게 제공합니다.


**가이드라인:**
*   제공된 내용의 슬라이드 마다 각각의 슬라이드 생성을 목표로 합니다.
*   제공된 예시 입출력을 참고하여 유사한 수준의 퀄리티와 구조를 유지하되, 입력 내용에 따라 최적화된 디자인과 구성을 제공해야 합니다.
*   **소스 HTML과 렌더링된 결과 모두에서 공백과 줄 바꿈 처리에 세심한 주의를 기울여야 합니다.** 특히 일반 텍스트와 코드 블록 영역을 주의 깊게 확인합니다.
*   외부 라이브러리(Tailwind, Font Awesome, Google Fonts 등)는 항상 CDN을 통해 로드합니다.
*   코드의 가독성과 재사용성을 고려하여 작성합니다.
*   반드시 HTML만 답변합니다. 코드 블록 외의 설명은 제공하지 않습니다.


**잘못된 코드 블록 HTML 예시 (피해야 할 사례):**
```html
<!-- 아래 방식은 <pre> 태그 때문에 코드 앞에 불필요한 공백이 렌더링될 수 있음 -->
            <div class="code-block">
                <pre><code>
                    score = 85
                    if score >= 60:
                        logger.info("합격입니다!")
                    else:
                        logger.info("불합격입니다.")
                </code></pre>
            </div>
```


**올바른 코드 블록 HTML 예시 (권장 사례):**
```html
            <div class="code-block bg-gray-800 text-white p-4 rounded">
<pre><code>score = 85
if score >= 60:
    logger.info("합격입니다!") # 코드 내부의 들여쓰기는 유지
else:
    logger.info("불합격입니다.")</code></pre>
            </div>
```
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
            }  # 슬라이드 초안을 텍스트로 변환
            slide_draft_text = inputs.get("slide_draft", {}).get(
                "markdown_content", "슬라이드 초안이 없습니다."
            )

            yield {
                "type": "progress",
                "stage": "generating_html",
                "message": "HTML 슬라이드 생성 중...",
                "progress": 0.5,
            }

            # LLM으로 HTML 생성
            html = self._generate_html_with_llm(
                slide_draft_text,
                inputs.get("user_input", ""),
                inputs.get("search_results", []),
            )

            # 최종 결과
            final_result = {
                "html": html,
                "langchain_context": {
                    "tool_name": "slide_generator",
                    "status": "success",
                    "generation_method": "llm_based",
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
            # 슬라이드 초안을 텍스트로 변환
            slide_draft_text = inputs.get("slide_draft", {}).get(
                "markdown_content", "슬라이드 초안이 없습니다."
            )
            # LLM으로 HTML 생성
            html = self._generate_html_with_llm(
                slide_draft_text,
                inputs.get("user_input", ""),
                inputs.get("search_results", []),
            )

            result = {
                "html": html,
                "langchain_context": {
                    "tool_name": "slide_generator",
                    "status": "success",
                    "generation_method": "llm_based",
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

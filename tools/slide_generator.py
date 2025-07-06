from typing import Dict, List, Any, Generator, Type
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field
import json


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
    slide_draft 툴의 결과와 RAG 검색 결과를 기반으로 HTML 슬라이드 생성
    """

    name: str = "slide_generator"
    description: str = (
        "슬라이드 생성 도구 - slide_draft와 RAG 검색 결과를 기반으로 HTML 슬라이드 생성"
    )
    args_schema: Type[BaseModel] = SlideGeneratorInput

    @property
    def slide_templates(self) -> Dict:
        """슬라이드 템플릿 정의"""
        return {
            "basic": {"title": "", "bullets": [], "notes": ""},
            "detailed": {
                "title": "",
                "subtitle": "",
                "bullets": [],
                "sub_bullets": {},
                "conclusion": "",
                "notes": "",
            },
            "comparison": {
                "title": "",
                "left_column": {"title": "", "items": []},
                "right_column": {"title": "", "items": []},
                "notes": "",
            },
        }

    def _extract_key_points_from_search_results(
        self, search_results: List[Dict], max_points: int = 5
    ) -> List[str]:
        """검색 결과에서 핵심 포인트 추출"""
        key_points = []

        for result in search_results:
            content = result.get("content", "")
            if not content:
                continue

            # 문장 분할 및 핵심 내용 추출
            sentences = content.split(".")
            for sentence in sentences:
                sentence = sentence.strip()
                if len(sentence) > 20 and len(sentence) < 200:
                    # 핵심 키워드가 포함된 문장 우선
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
                    ]
                    if any(keyword in sentence for keyword in keywords):
                        key_points.append(sentence)
                        if len(key_points) >= max_points:
                            break

            if len(key_points) >= max_points:
                break

        return key_points[:max_points]

    def _create_slide_from_draft_and_search(
        self, slide_draft: Dict, search_results: List[Dict], slide_type: str
    ) -> Dict:
        """slide_draft와 검색 결과를 기반으로 슬라이드 생성"""

        # slide_draft에서 기본 정보 추출
        title = slide_draft.get("title", "클라우드 거버넌스")
        subtitle = slide_draft.get("subtitle", "")
        draft_bullets = slide_draft.get("bullets", [])

        # 검색 결과에서 추가 정보 추출
        search_bullets = self._extract_key_points_from_search_results(search_results)

        # 두 소스의 정보를 결합
        combined_bullets = draft_bullets + search_bullets

        # 중복 제거 및 정제
        unique_bullets = []
        seen = set()
        for bullet in combined_bullets:
            if bullet not in seen and len(bullet) > 10:
                unique_bullets.append(bullet)
                seen.add(bullet)

        if slide_type == "detailed":
            # 세부 슬라이드 생성
            sub_bullets = {}
            for i, bullet in enumerate(unique_bullets[:3]):
                sub_bullets[f"point_{i+1}"] = [
                    f"{bullet}의 구현 방법",
                    f"{bullet}의 모니터링 방안",
                    f"{bullet}의 최적화 전략",
                ]

            return {
                "title": title,
                "subtitle": subtitle or "핵심 요소 및 구현 방안",
                "bullets": unique_bullets[:3],
                "sub_bullets": sub_bullets,
                "conclusion": slide_draft.get(
                    "conclusion", "체계적인 클라우드 거버넌스 구현이 필요합니다."
                ),
                "notes": f"총 {len(search_results)}개의 검색 결과를 기반으로 생성됨",
            }

        elif slide_type == "comparison":
            # 비교 슬라이드 생성
            mid_point = len(unique_bullets) // 2
            return {
                "title": title,
                "left_column": {
                    "title": slide_draft.get("left_title", "현재 상황"),
                    "items": unique_bullets[:mid_point],
                },
                "right_column": {
                    "title": slide_draft.get("right_title", "개선 방안"),
                    "items": unique_bullets[mid_point:],
                },
                "notes": f"총 {len(search_results)}개의 검색 결과를 기반으로 생성됨",
            }

        else:
            # 기본 슬라이드 생성
            return {
                "title": title,
                "bullets": unique_bullets[:5],
                "notes": f"총 {len(search_results)}개의 검색 결과를 기반으로 생성됨",
            }

    def _run(
        self,
        slide_draft: Dict[str, Any],
        search_results: List[Dict[str, Any]],
        user_input: str,
        slide_type: str = "basic",
        format_type: str = "html",
    ) -> str:
        """
        LangChain Tool 실행 메서드

        Args:
            slide_draft: 슬라이드 초안 데이터
            search_results: RAG 검색 결과
            user_input: 사용자 입력
            slide_type: 슬라이드 유형
            format_type: 출력 형식

        Returns:
            JSON 문자열로 변환된 슬라이드 데이터
        """
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
        """
        스트리밍 실행을 위한 메서드

        Args:
            inputs: 입력 데이터

        Yields:
            스트리밍 청크 데이터
        """
        slide_type = inputs.get("slide_type", "basic")

        try:
            # 진행 상황 스트리밍
            yield {
                "type": "progress",
                "stage": "analyzing_draft",
                "message": "슬라이드 초안 분석 중...",
                "progress": 0.2,
            }

            # 슬라이드 데이터 생성
            slide_data = self._create_slide_from_draft_and_search(
                inputs.get("slide_draft", {}),
                inputs.get("search_results", []),
                slide_type,
            )

            yield {
                "type": "progress",
                "stage": "generating_structure",
                "message": "슬라이드 구조 생성 중...",
                "progress": 0.5,
            }

            # HTML 생성
            html = self._convert_to_html(slide_data, slide_type)

            yield {
                "type": "progress",
                "stage": "formatting_html",
                "message": "HTML 형식 변환 중...",
                "progress": 0.8,
            }

            # 마크다운 생성
            markdown = self._convert_to_markdown(slide_data, slide_type)

            # 최종 결과
            final_result = {
                "slide": slide_data,
                "html": html,
                "markdown": markdown,
                "langchain_context": {
                    "tool_name": "slide_generator",
                    "status": "success",
                    "slide_type": slide_type,
                    "total_bullets": len(slide_data.get("bullets", [])),
                    "search_results_count": len(inputs.get("search_results", [])),
                },
            }

            yield {
                "type": "result",
                "stage": "completed",
                "message": "슬라이드 생성 완료",
                "progress": 1.0,
                "data": final_result,
            }

        except Exception as e:
            yield {
                "type": "error",
                "stage": "error",
                "message": f"슬라이드 생성 중 오류: {str(e)}",
                "progress": 0.0,
                "error": str(e),
            }

    def run(self, inputs: Dict) -> Dict:
        """
        기존 방식과의 호환성을 위한 메서드

        Args:
            inputs: 입력 데이터

        Returns:
            슬라이드 생성 결과
        """
        slide_type = inputs.get("slide_type", "basic")
        format_type = inputs.get("format_type", "html")

        try:
            # 슬라이드 데이터 생성
            slide_data = self._create_slide_from_draft_and_search(
                inputs.get("slide_draft", {}),
                inputs.get("search_results", []),
                slide_type,
            )

            # HTML 및 마크다운 형식 생성
            html = self._convert_to_html(slide_data, slide_type)
            markdown = self._convert_to_markdown(slide_data, slide_type)

            return {
                "slide": slide_data,
                "html": html,
                "markdown": markdown,
                "langchain_context": {
                    "tool_name": "slide_generator",
                    "status": "success",
                    "slide_type": slide_type,
                    "format": format_type,
                    "total_bullets": len(slide_data.get("bullets", [])),
                    "search_results_count": len(inputs.get("search_results", [])),
                },
            }

        except Exception as e:
            return {
                "slide": {},
                "html": "",
                "markdown": "",
                "langchain_context": {
                    "tool_name": "slide_generator",
                    "status": "error",
                    "message": f"슬라이드 생성 중 오류: {str(e)}",
                },
            }

    def _convert_to_html(self, slide_data: Dict, slide_type: str) -> str:
        """슬라이드 데이터를 HTML로 변환"""
        title = slide_data.get("title", "제목 없음")

        html = f"""
<!DOCTYPE html>
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
        .slide-container {{
            max-width: 1000px;
            margin: 0 auto;
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1);
            overflow: hidden;
            position: relative;
        }}
        .slide-header {{
            background: linear-gradient(135deg, #2c3e50 0%, #34495e 100%);
            color: white;
            padding: 40px;
            text-align: center;
            position: relative;
        }}
        .slide-header::before {{
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: url('data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><defs><pattern id="grain" width="100" height="100" patternUnits="userSpaceOnUse"><circle cx="20" cy="20" r="1" fill="rgba(255,255,255,0.1)"/><circle cx="80" cy="40" r="1" fill="rgba(255,255,255,0.1)"/><circle cx="50" cy="70" r="1" fill="rgba(255,255,255,0.1)"/></pattern></defs><rect width="100" height="100" fill="url(%23grain)"/></svg>');
            opacity: 0.3;
        }}
        .slide-header h1 {{
            margin: 0;
            font-size: 2.5rem;
            font-weight: 300;
            letter-spacing: -1px;
            position: relative;
            z-index: 1;
        }}
        .slide-header .subtitle {{
            margin-top: 15px;
            opacity: 0.9;
            font-size: 1.2rem;
            position: relative;
            z-index: 1;
        }}
        .slide-content {{
            padding: 50px;
        }}
        .section {{
            margin-bottom: 40px;
        }}
        .section h2 {{
            color: #2c3e50;
            margin-bottom: 25px;
            font-size: 1.8rem;
            font-weight: 600;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
        }}
        .bullet-list {{
            list-style: none;
            padding: 0;
        }}
        .bullet-list li {{
            background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
            margin: 15px 0;
            padding: 20px;
            border-radius: 12px;
            border-left: 5px solid #3498db;
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.05);
            transition: transform 0.2s ease, box-shadow 0.2s ease;
            position: relative;
        }}
        .bullet-list li:hover {{
            transform: translateY(-2px);
            box-shadow: 0 8px 16px rgba(0, 0, 0, 0.1);
        }}
        .bullet-list li::before {{
            content: '▶';
            color: #3498db;
            font-weight: bold;
            margin-right: 10px;
        }}
        .comparison-container {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 30px;
            margin-top: 20px;
        }}
        .comparison-column {{
            background: #f8f9fa;
            padding: 25px;
            border-radius: 12px;
            border-top: 4px solid #e74c3c;
        }}
        .comparison-column:last-child {{
            border-top-color: #27ae60;
        }}
        .comparison-column h3 {{
            margin-top: 0;
            color: #2c3e50;
            font-size: 1.3rem;
        }}
        .sub-bullets {{
            margin-left: 20px;
            margin-top: 15px;
        }}
        .sub-bullets li {{
            background: #ffffff;
            border-left-color: #95a5a6;
            padding: 12px 15px;
            font-size: 0.9rem;
        }}
        .conclusion {{
            background: linear-gradient(135deg, #3498db 0%, #2980b9 100%);
            color: white;
            padding: 30px;
            border-radius: 15px;
            text-align: center;
            font-size: 1.1rem;
            font-weight: 500;
            margin-top: 30px;
        }}
        .slide-footer {{
            background: #ecf0f1;
            padding: 20px;
            text-align: center;
            color: #7f8c8d;
            font-style: italic;
        }}
        .search-info {{
            background: #e8f4f8;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 20px;
            border-left: 4px solid #3498db;
        }}
        .search-info h3 {{
            margin: 0 0 10px 0;
            color: #2c3e50;
            font-size: 1.1rem;
        }}
        .search-info p {{
            margin: 0;
            color: #7f8c8d;
            font-size: 0.9rem;
        }}
        @media (max-width: 768px) {{
            .slide-container {{
                margin: 10px;
                border-radius: 10px;
            }}
            .slide-header {{
                padding: 20px;
            }}
            .slide-header h1 {{
                font-size: 1.8rem;
            }}
            .slide-content {{
                padding: 25px;
            }}
            .comparison-container {{
                grid-template-columns: 1fr;
                gap: 20px;
            }}
        }}
    </style>
</head>
<body>
    <div class="slide-container">
        <div class="slide-header">
            <h1>{title}</h1>
            <div class="subtitle">AI 기반 클라우드 거버넌스 슬라이드</div>
        </div>
        <div class="slide-content">
"""

        # 검색 결과 정보 표시
        if slide_data.get("notes"):
            html += f"""
            <div class="search-info">
                <h3>📊 데이터 기반 정보</h3>
                <p>{slide_data["notes"]}</p>
            </div>
            """

        if slide_type == "detailed" and slide_data.get("subtitle"):
            html += f'<div class="section"><h2>{slide_data["subtitle"]}</h2></div>'

        if slide_type == "comparison":
            html += '<div class="section"><h2>비교 분석</h2>'
            html += '<div class="comparison-container">'
            html += f'<div class="comparison-column"><h3>{slide_data["left_column"]["title"]}</h3><ul class="bullet-list">'
            for item in slide_data["left_column"]["items"]:
                html += f"<li>{item}</li>"
            html += f'</ul></div><div class="comparison-column"><h3>{slide_data["right_column"]["title"]}</h3><ul class="bullet-list">'
            for item in slide_data["right_column"]["items"]:
                html += f"<li>{item}</li>"
            html += "</ul></div></div></div>"
        else:
            html += (
                '<div class="section"><h2>📋 핵심 포인트</h2><ul class="bullet-list">'
            )
            for bullet in slide_data.get("bullets", []):
                html += f"<li>{bullet}</li>"
            html += "</ul></div>"

            if slide_type == "detailed" and slide_data.get("sub_bullets"):
                html += '<div class="section"><h2>🔍 세부 사항</h2>'
                for key, sub_items in slide_data["sub_bullets"].items():
                    html += '<ul class="bullet-list sub-bullets">'
                    for sub_item in sub_items:
                        html += f"<li>{sub_item}</li>"
                    html += "</ul>"
                html += "</div>"

            if slide_data.get("conclusion"):
                html += f'<div class="conclusion">💡 {slide_data["conclusion"]}</div>'

        html += "</div>"

        html += '<div class="slide-footer">클라우드 거버넌스 AI 시스템에서 생성된 슬라이드입니다.</div>'

        html += """
    </div>
</body>
</html>
"""
        return html

    def _convert_to_markdown(self, slide_data: Dict, slide_type: str) -> str:
        """슬라이드 데이터를 마크다운으로 변환 (호환성을 위해 유지)"""
        markdown = f"# {slide_data.get('title', '제목 없음')}\n\n"

        if slide_type == "detailed" and slide_data.get("subtitle"):
            markdown += f"## {slide_data['subtitle']}\n\n"

        if slide_type == "comparison":
            markdown += f"## {slide_data['left_column']['title']}\n"
            for item in slide_data["left_column"]["items"]:
                markdown += f"- {item}\n"
            markdown += f"\n## {slide_data['right_column']['title']}\n"
            for item in slide_data["right_column"]["items"]:
                markdown += f"- {item}\n"
        else:
            markdown += "## 핵심 포인트\n"
            for bullet in slide_data.get("bullets", []):
                markdown += f"- {bullet}\n"

            if slide_type == "detailed" and slide_data.get("sub_bullets"):
                markdown += "\n## 세부 사항\n"
                for key, sub_items in slide_data["sub_bullets"].items():
                    for sub_item in sub_items:
                        markdown += f"  - {sub_item}\n"

            if slide_data.get("conclusion"):
                markdown += f"\n## 결론\n{slide_data['conclusion']}\n"

        if slide_data.get("notes"):
            markdown += f"\n---\n*{slide_data['notes']}*\n"

        return markdown

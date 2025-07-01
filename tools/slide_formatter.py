from typing import Dict, List, Any, Generator, Type
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field
import json


class SlideFormatterInput(BaseModel):
    """슬라이드 포맷터 입력 모델"""

    content: str = Field(description="슬라이드로 변환할 텍스트 내용")
    title: str = Field(default="클라우드 거버넌스", description="슬라이드 제목")
    slide_type: str = Field(
        default="basic", description="슬라이드 유형 (basic, detailed, comparison)"
    )
    subtitle: str = Field(
        default="", description="슬라이드 부제목 (detailed 타입에서 사용)"
    )
    format_type: str = Field(default="json", description="출력 형식 (json, markdown)")


class SlideFormatterTool(BaseTool):
    """
    슬라이드 포맷팅 LangChain 도구
    스트리밍을 지원하는 JSON 또는 마크다운 슬라이드 포맷 생성
    """

    name: str = "slide_formatter"
    description: str = "슬라이드 포맷팅 도구 - 텍스트 내용을 HTML 슬라이드로 변환"
    args_schema: Type[BaseModel] = SlideFormatterInput

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

    def _extract_key_points(self, content: str, max_points: int = 5) -> List[str]:
        """텍스트에서 핵심 포인트 추출"""
        # 간단한 문장 분할 및 핵심 내용 추출
        sentences = content.split(".")
        key_points = []

        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) > 20 and len(sentence) < 200:  # 적절한 길이의 문장
                # 핵심 키워드가 포함된 문장 우선
                keywords = [
                    "정책",
                    "컴플라이언스",
                    "모니터링",
                    "보안",
                    "관리",
                    "거버넌스",
                    "클라우드",
                ]
                if any(keyword in sentence for keyword in keywords):
                    key_points.append(sentence)
                elif len(key_points) < max_points:
                    key_points.append(sentence)

        return key_points[:max_points]

    def _create_basic_slide(self, inputs: Dict) -> Dict:
        """기본 슬라이드 형식 생성"""
        content = inputs.get("content", "")
        title = inputs.get("title", "클라우드 거버넌스")

        bullets = self._extract_key_points(content)

        return {
            "title": title,
            "bullets": bullets,
            "notes": f"총 {len(bullets)}개의 핵심 포인트",
        }

    def _create_detailed_slide(self, inputs: Dict) -> Dict:
        """상세 슬라이드 형식 생성"""
        content = inputs.get("content", "")
        title = inputs.get("title", "클라우드 거버넌스 상세")
        subtitle = inputs.get("subtitle", "핵심 요소 및 구현 방안")

        bullets = self._extract_key_points(content, max_points=3)

        # 각 bullet에 대한 세부 사항 생성
        sub_bullets = {}
        for i, bullet in enumerate(bullets):
            sub_bullets[f"point_{i+1}"] = [
                f"{bullet}의 구현 방법",
                f"{bullet}의 모니터링",
                f"{bullet}의 최적화",
            ]

        return {
            "title": title,
            "subtitle": subtitle,
            "bullets": bullets,
            "sub_bullets": sub_bullets,
            "conclusion": "체계적인 클라우드 거버넌스 구현이 필요합니다.",
            "notes": "상세 내용은 각 포인트별로 구분하여 설명",
        }

    def _create_comparison_slide(self, inputs: Dict) -> Dict:
        """비교 슬라이드 형식 생성"""
        content = inputs.get("content", "")
        title = inputs.get("title", "클라우드 거버넌스 비교")

        # 간단한 before/after 또는 pros/cons 구조
        points = self._extract_key_points(content, max_points=6)
        mid_point = len(points) // 2

        return {
            "title": title,
            "left_column": {"title": "현재 상황", "items": points[:mid_point]},
            "right_column": {"title": "개선 방안", "items": points[mid_point:]},
            "notes": "현재 상황과 개선 방안의 비교",
        }

    def _run(
        self,
        content: str,
        title: str = "클라우드 거버넌스",
        slide_type: str = "basic",
        subtitle: str = "",
        format_type: str = "json",
    ) -> str:
        """
        LangChain Tool 실행 메서드

        Args:
            content: 슬라이드로 변환할 텍스트 내용
            title: 슬라이드 제목
            slide_type: 슬라이드 유형
            subtitle: 슬라이드 부제목
            format_type: 출력 형식

        Returns:
            JSON 문자열로 변환된 슬라이드 데이터
        """
        inputs = {
            "content": content,
            "title": title,
            "slide_type": slide_type,
            "subtitle": subtitle,
            "format": format_type,
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
                "stage": "analyzing_content",
                "message": "콘텐츠 분석 중...",
                "progress": 0.2,
            }

            # 슬라이드 타입에 따른 생성
            if slide_type == "detailed":
                slide_data = self._create_detailed_slide(inputs)
            elif slide_type == "comparison":
                slide_data = self._create_comparison_slide(inputs)
            else:
                slide_data = self._create_basic_slide(inputs)

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
                    "tool_name": "slide_formatter",
                    "status": "success",
                    "slide_type": slide_type,
                    "total_bullets": len(slide_data.get("bullets", [])),
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
            슬라이드 포맷팅 결과
        """
        slide_type = inputs.get("slide_type", "basic")
        format_type = inputs.get("format", "json")

        try:
            # 슬라이드 타입에 따른 생성
            if slide_type == "detailed":
                slide_data = self._create_detailed_slide(inputs)
            elif slide_type == "comparison":
                slide_data = self._create_comparison_slide(inputs)
            else:
                slide_data = self._create_basic_slide(inputs)

            # HTML 및 마크다운 형식 생성
            html = self._convert_to_html(slide_data, slide_type)
            markdown = self._convert_to_markdown(slide_data, slide_type)

            return {
                "slide": slide_data,
                "html": html,
                "markdown": markdown,
                "langchain_context": {
                    "tool_name": "slide_formatter",
                    "status": "success",
                    "slide_type": slide_type,
                    "format": format_type,
                    "total_bullets": len(slide_data.get("bullets", [])),
                },
            }

        except Exception as e:
            return {
                "slide": {},
                "html": "",
                "markdown": "",
                "langchain_context": {
                    "tool_name": "slide_formatter",
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
            <div class="subtitle">클라우드 거버넌스 프레젠테이션</div>
        </div>
        <div class="slide-content">
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

        if slide_data.get("notes"):
            html += f'<div class="slide-footer">{slide_data["notes"]}</div>'
        else:
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

from typing import Dict, List, Any
from core.base_tool import BaseTool


class ReportSummaryTool(BaseTool):
    """
    보고서 요약 도구
    MCP Tool Protocol을 통해 HTML 형식의 보고서 요약 생성
    """

    def __init__(self):
        self.report_templates = {
            "executive": {
                "sections": ["개요", "핵심 발견사항", "권고사항", "다음 단계"],
                "focus": "경영진 대상 요약",
            },
            "technical": {
                "sections": [
                    "기술 현황",
                    "시스템 분석",
                    "기술적 권고사항",
                    "구현 계획",
                ],
                "focus": "기술진 대상 상세 분석",
            },
            "compliance": {
                "sections": [
                    "컴플라이언스 현황",
                    "갭 분석",
                    "리스크 평가",
                    "개선 방안",
                ],
                "focus": "컴플라이언스 중심 분석",
            },
        }

    def _extract_sections(self, content: str) -> Dict[str, str]:
        """보고서 내용에서 섹션별로 내용 추출"""
        sections = {}

        # 마크다운 헤더를 기준으로 섹션 분리
        lines = content.split("\n")
        current_section = "개요"
        current_content = []

        for line in lines:
            if line.startswith("## "):
                # 이전 섹션 저장
                if current_content:
                    sections[current_section] = "\n".join(current_content).strip()
                    current_content = []

                # 새 섹션 시작
                current_section = line[3:].strip()
            elif line.startswith("# "):
                # 제목은 별도 처리
                sections["title"] = line[2:].strip()
            else:
                current_content.append(line)

        # 마지막 섹션 저장
        if current_content:
            sections[current_section] = "\n".join(current_content).strip()

        return sections

    def _create_executive_summary(self, sections: Dict[str, str]) -> Dict[str, Any]:
        """경영진용 요약 생성"""
        summary = {
            "title": sections.get("title", "클라우드 거버넌스 보고서"),
            "type": "executive",
            "key_points": [],
            "recommendations": [],
            "priorities": [],
        }

        # 핵심 포인트 추출
        for section_name, content in sections.items():
            if (
                "핵심" in section_name
                or "주요" in section_name
                or "현황" in section_name
            ):
                points = self._extract_bullet_points(content)
                summary["key_points"].extend(points[:3])  # 상위 3개만

        # 권고사항 추출
        for section_name, content in sections.items():
            if (
                "개선" in section_name
                or "권고" in section_name
                or "방안" in section_name
            ):
                recommendations = self._extract_bullet_points(content)
                summary["recommendations"].extend(recommendations[:3])

        # 우선순위 설정
        summary["priorities"] = ["단기 실행 과제", "중기 개선 방안", "장기 전략 수립"]

        return summary

    def _create_technical_summary(self, sections: Dict[str, str]) -> Dict[str, Any]:
        """기술진용 요약 생성"""
        summary = {
            "title": sections.get("title", "클라우드 거버넌스 기술 보고서"),
            "type": "technical",
            "technical_findings": [],
            "implementation_steps": [],
            "technical_requirements": [],
        }

        # 기술적 발견사항 추출
        for section_name, content in sections.items():
            if "기술" in section_name or "시스템" in section_name:
                findings = self._extract_bullet_points(content)
                summary["technical_findings"].extend(findings)

        # 구현 단계 추출
        for section_name, content in sections.items():
            if "구현" in section_name or "계획" in section_name:
                steps = self._extract_bullet_points(content)
                summary["implementation_steps"].extend(steps)

        # 기술 요구사항 추출
        summary["technical_requirements"] = [
            "클라우드 인프라 설정",
            "보안 정책 구현",
            "모니터링 시스템 구축",
            "자동화 도구 도입",
        ]

        return summary

    def _extract_bullet_points(self, content: str) -> List[str]:
        """텍스트에서 bullet point 추출"""
        points = []
        lines = content.split("\n")

        for line in lines:
            line = line.strip()
            if line.startswith("- ") or line.startswith("• "):
                points.append(line[2:].strip())
            elif line.startswith("* "):
                points.append(line[2:].strip())
            elif len(line) > 20 and len(line) < 150 and "." in line:
                # 문장 형태의 중요한 내용
                points.append(line)

        return points[:5]  # 최대 5개까지

    def _convert_to_html(self, summary_data: Dict[str, Any]) -> str:
        """요약 데이터를 HTML로 변환"""
        title = summary_data.get("title", "보고서 요약")
        summary_type = summary_data.get("type", "executive")

        html = f"""
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        body {{
            font-family: 'Segoe UI', Arial, sans-serif;
            line-height: 1.6;
            margin: 0;
            padding: 20px;
            background-color: #f5f7fa;
            color: #333;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            overflow: hidden;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }}
        .header h1 {{
            margin: 0;
            font-size: 2.2rem;
            font-weight: 300;
        }}
        .header .subtitle {{
            margin-top: 10px;
            opacity: 0.9;
            font-size: 1.1rem;
        }}
        .content {{
            padding: 40px;
        }}
        .section {{
            margin-bottom: 35px;
            padding: 25px;
            background: #f8f9fa;
            border-radius: 8px;
            border-left: 4px solid #667eea;
        }}
        .section h2 {{
            color: #2c3e50;
            margin-top: 0;
            margin-bottom: 20px;
            font-size: 1.4rem;
            font-weight: 600;
        }}
        .points-list {{
            list-style: none;
            padding: 0;
        }}
        .points-list li {{
            background: white;
            margin: 10px 0;
            padding: 15px;
            border-radius: 6px;
            border-left: 3px solid #3498db;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
        }}
        .priority-badge {{
            display: inline-block;
            background: #e74c3c;
            color: white;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.85rem;
            margin-right: 10px;
        }}
        .technical-badge {{
            display: inline-block;
            background: #27ae60;
            color: white;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.85rem;
            margin-right: 10px;
        }}
        .footer {{
            background: #ecf0f1;
            padding: 20px;
            text-align: center;
            color: #7f8c8d;
            font-size: 0.9rem;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{title}</h1>
            <div class="subtitle">클라우드 거버넌스 보고서 요약</div>
        </div>
        <div class="content">
"""

        if summary_type == "executive":
            html += self._add_executive_sections(summary_data)
        elif summary_type == "technical":
            html += self._add_technical_sections(summary_data)
        else:
            html += self._add_general_sections(summary_data)

        html += """
        </div>
        <div class="footer">
            클라우드 거버넌스 AI 시스템에서 생성된 보고서 요약입니다.
        </div>
    </div>
</body>
</html>
"""
        return html

    def _add_executive_sections(self, summary_data: Dict[str, Any]) -> str:
        """경영진용 섹션 추가"""
        html = ""

        # 핵심 포인트
        if summary_data.get("key_points"):
            html += '<div class="section">'
            html += "<h2>🎯 핵심 발견사항</h2>"
            html += '<ul class="points-list">'
            for point in summary_data["key_points"]:
                html += f'<li><span class="priority-badge">핵심</span>{point}</li>'
            html += "</ul></div>"

        # 권고사항
        if summary_data.get("recommendations"):
            html += '<div class="section">'
            html += "<h2>📋 주요 권고사항</h2>"
            html += '<ul class="points-list">'
            for rec in summary_data["recommendations"]:
                html += f"<li>{rec}</li>"
            html += "</ul></div>"

        # 우선순위
        if summary_data.get("priorities"):
            html += '<div class="section">'
            html += "<h2>⭐ 실행 우선순위</h2>"
            html += '<ul class="points-list">'
            for i, priority in enumerate(summary_data["priorities"], 1):
                html += (
                    f'<li><span class="priority-badge">{i}순위</span>{priority}</li>'
                )
            html += "</ul></div>"

        return html

    def _add_technical_sections(self, summary_data: Dict[str, Any]) -> str:
        """기술진용 섹션 추가"""
        html = ""

        # 기술적 발견사항
        if summary_data.get("technical_findings"):
            html += '<div class="section">'
            html += "<h2>🔧 기술적 발견사항</h2>"
            html += '<ul class="points-list">'
            for finding in summary_data["technical_findings"]:
                html += f'<li><span class="technical-badge">기술</span>{finding}</li>'
            html += "</ul></div>"

        # 구현 단계
        if summary_data.get("implementation_steps"):
            html += '<div class="section">'
            html += "<h2>⚙️ 구현 단계</h2>"
            html += '<ul class="points-list">'
            for step in summary_data["implementation_steps"]:
                html += f"<li>{step}</li>"
            html += "</ul></div>"

        # 기술 요구사항
        if summary_data.get("technical_requirements"):
            html += '<div class="section">'
            html += "<h2>📊 기술 요구사항</h2>"
            html += '<ul class="points-list">'
            for req in summary_data["technical_requirements"]:
                html += f'<li><span class="technical-badge">필수</span>{req}</li>'
            html += "</ul></div>"

        return html

    def _add_general_sections(self, summary_data: Dict[str, Any]) -> str:
        """일반 섹션 추가"""
        html = '<div class="section">'
        html += "<h2>📄 보고서 요약</h2>"
        html += "<p>요약 정보를 표시할 수 없습니다. 원본 보고서를 참조해주세요.</p>"
        html += "</div>"
        return html

    def run(self, inputs: Dict) -> Dict:
        """
        MCP Tool Protocol을 통한 보고서 요약 실행

        Args:
            inputs (Dict): {
                "content": str,
                "title": str,
                "summary_type": str,  # "executive", "technical", "compliance"
                "format": str  # "html", "json"
            }

        Returns:
            Dict: {"summary": Dict, "html": str, "mcp_context": Dict}
        """
        try:
            content = inputs.get("content", "")
            title = inputs.get("title", "클라우드 거버넌스 보고서")
            summary_type = inputs.get("summary_type", "executive")
            format_type = inputs.get("format", "html")

            # 섹션별 내용 추출
            sections = self._extract_sections(content)
            sections["title"] = title

            # 요약 타입에 따른 처리
            if summary_type == "technical":
                summary_data = self._create_technical_summary(sections)
            else:
                summary_data = self._create_executive_summary(sections)

            # HTML 변환
            html_output = self._convert_to_html(summary_data)

            return {
                "summary": summary_data,
                "html": html_output,
                "mcp_context": {
                    "role": "report_summarizer",
                    "status": "success",
                    "summary_type": summary_type,
                    "format": format_type,
                    "sections_processed": len(sections),
                },
            }

        except Exception as e:
            return {
                "summary": {},
                "html": "",
                "mcp_context": {
                    "role": "report_summarizer",
                    "status": "error",
                    "message": f"보고서 요약 중 오류: {str(e)}",
                },
            }

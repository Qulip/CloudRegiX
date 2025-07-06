from typing import Dict, List, Any
from core.base_tool import BaseTool


class ReportSummaryTool(BaseTool):
    """
    보고서 요약 도구
    클라우드 전환 제안서 구조에 맞는 요약 생성
    """

    def __init__(self):
        self.proposal_structure = {
            "overview": "제안 개요 및 목적",
            "necessity": "고객 Pain Point, 산업 동향, 정책 변화 기반 제안 필요성",
            "target_systems": "시스템 전환 대상 정의",
            "strategy": "전환 전략 및 방법론",
            "roadmap": "단계별 로드맵",
            "methodology": "자체 방법론 적용",
            "automation": "자동화 도구 활용 계획",
            "architecture": "인프라 및 보안 아키텍처 설계",
            "operations": "운영 방안 (SLA 기반)",
            "compliance": "규제 대응 전략",
            "project_management": "프로젝트 관리 체계 (PMO)",
            "exit_plan": "Exit Plan",
            "resource_plan": "인력 투입 계획",
            "benefits": "기대효과 및 경쟁력",
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

    def _create_proposal_summary(self, sections: Dict[str, str]) -> Dict[str, Any]:
        """클라우드 전환 제안서 구조에 맞는 요약 생성"""
        summary = {
            "title": sections.get("title", "클라우드 전환 제안서"),
            "structure_summary": "✅ 보고서 전체 구조 요약",
            "sections": {},
        }

        # 제안 개요 및 목적
        summary["sections"]["overview"] = self._extract_overview(sections)

        # 제안 필요성
        summary["sections"]["necessity"] = self._extract_necessity(sections)

        # 시스템 전환 대상
        summary["sections"]["target_systems"] = self._extract_target_systems(sections)

        # 전환 전략 및 방법론
        summary["sections"]["strategy"] = self._extract_strategy(sections)

        # 단계별 로드맵
        summary["sections"]["roadmap"] = self._extract_roadmap(sections)

        # 자체 방법론 적용
        summary["sections"]["methodology"] = self._extract_methodology(sections)

        # 자동화 도구 활용
        summary["sections"]["automation"] = self._extract_automation(sections)

        # 인프라 및 보안 아키텍처
        summary["sections"]["architecture"] = self._extract_architecture(sections)

        # 운영 방안
        summary["sections"]["operations"] = self._extract_operations(sections)

        # 규제 대응 전략
        summary["sections"]["compliance"] = self._extract_compliance(sections)

        # 프로젝트 관리 체계
        summary["sections"]["project_management"] = self._extract_project_management(
            sections
        )

        # Exit Plan
        summary["sections"]["exit_plan"] = self._extract_exit_plan(sections)

        # 인력 투입 계획
        summary["sections"]["resource_plan"] = self._extract_resource_plan(sections)

        # 기대효과 및 경쟁력
        summary["sections"]["benefits"] = self._extract_benefits(sections)

        # 핵심 포인트 요약
        summary["key_points"] = self._extract_key_points(sections)

        return summary

    def _extract_overview(self, sections: Dict[str, str]) -> str:
        """제안 개요 및 목적 추출"""
        overview_keywords = ["제안 개요", "개요", "목적", "배경", "서론", "소개"]
        return self._find_section_by_keywords(
            sections, overview_keywords, "클라우드 전환을 통한 디지털 혁신 달성"
        )

    def _extract_necessity(self, sections: Dict[str, str]) -> str:
        """제안 필요성 추출"""
        necessity_keywords = ["필요성", "pain point", "문제점", "현황", "동향", "정책"]
        return self._find_section_by_keywords(
            sections, necessity_keywords, "고객 Pain Point 해결 및 정책 변화 대응"
        )

    def _extract_target_systems(self, sections: Dict[str, str]) -> str:
        """시스템 전환 대상 추출"""
        target_keywords = [
            "전환 대상",
            "시스템 전환",
            "대상",
            "시스템",
            "범위",
            "분류",
            "수량",
        ]
        return self._find_section_by_keywords(
            sections, target_keywords, "클라우드 전환 대상 시스템 분류 및 범위 정의"
        )

    def _extract_strategy(self, sections: Dict[str, str]) -> str:
        """전환 전략 및 방법론 추출"""
        strategy_keywords = ["전략", "방법론", "접근법", "방안"]
        return self._find_section_by_keywords(
            sections, strategy_keywords, "체계적인 클라우드 전환 전략 및 방법론"
        )

    def _extract_roadmap(self, sections: Dict[str, str]) -> str:
        """단계별 로드맵 추출"""
        roadmap_keywords = ["로드맵", "단계", "일정", "계획", "스케줄"]
        return self._find_section_by_keywords(
            sections, roadmap_keywords, "단계별 클라우드 전환 로드맵"
        )

    def _extract_methodology(self, sections: Dict[str, str]) -> str:
        """자체 방법론 적용 추출"""
        methodology_keywords = ["방법론", "way4u", "프레임워크", "모델"]
        return self._find_section_by_keywords(
            sections, methodology_keywords, "LG CNS Way4U 방법론 적용"
        )

    def _extract_automation(self, sections: Dict[str, str]) -> str:
        """자동화 도구 활용 추출"""
        automation_keywords = ["자동화", "도구", "툴", "automation"]
        return self._find_section_by_keywords(
            sections, automation_keywords, "자동화 도구 활용 계획"
        )

    def _extract_architecture(self, sections: Dict[str, str]) -> str:
        """인프라 및 보안 아키텍처 추출"""
        architecture_keywords = [
            "인프라 아키텍처",
            "보안 아키텍처",
            "아키텍처",
            "인프라",
            "보안",
            "랜딩존",
            "네트워크",
            "dr",
            "백업",
        ]
        return self._find_section_by_keywords(
            sections,
            architecture_keywords,
            "랜딩존, 네트워크, DR, 백업, DevSecOps 구성",
        )

    def _extract_operations(self, sections: Dict[str, str]) -> str:
        """운영 방안 추출"""
        operations_keywords = ["운영 방안", "운영", "sla", "모니터링", "장애", "cmp"]
        return self._find_section_by_keywords(
            sections, operations_keywords, "운영조직, CMP 도구, 모니터링/장애 대응"
        )

    def _extract_compliance(self, sections: Dict[str, str]) -> str:
        """규제 대응 전략 추출"""
        compliance_keywords = ["규제", "금감원", "csp", "보안성", "심의"]
        return self._find_section_by_keywords(
            sections,
            compliance_keywords,
            "금감원 보고, CSP 안정성 평가, 보안성 심의 대응",
        )

    def _extract_project_management(self, sections: Dict[str, str]) -> str:
        """프로젝트 관리 체계 추출"""
        pmo_keywords = [
            "프로젝트 관리",
            "pmo",
            "프로젝트",
            "관리",
            "조직도",
            "품질",
            "위험",
            "이슈",
        ]
        return self._find_section_by_keywords(
            sections, pmo_keywords, "조직도, 일정계획, 품질/위험/이슈 관리"
        )

    def _extract_exit_plan(self, sections: Dict[str, str]) -> str:
        """Exit Plan 추출"""
        exit_keywords = ["exit", "계약", "종료", "이관", "데이터"]
        return self._find_section_by_keywords(
            sections, exit_keywords, "계약 종료 시 데이터/시스템/운영 이관 전략"
        )

    def _extract_resource_plan(self, sections: Dict[str, str]) -> str:
        """인력 투입 계획 추출"""
        resource_keywords = ["인력 계획", "인력", "투입", "자격", "구성", "일정"]
        return self._find_section_by_keywords(
            sections, resource_keywords, "인력 구성, 자격 보유 현황, 투입 일정"
        )

    def _extract_benefits(self, sections: Dict[str, str]) -> str:
        """기대효과 및 경쟁력 추출"""
        benefits_keywords = [
            "기대효과",
            "경쟁력",
            "효과",
            "비용",
            "절감",
            "안정성",
            "실적",
            "차별성",
        ]
        return self._find_section_by_keywords(
            sections, benefits_keywords, "비용절감, 운영 안정성, 실적, 도구 차별성"
        )

    def _find_section_by_keywords(
        self, sections: Dict[str, str], keywords: List[str], default: str
    ) -> str:
        """키워드를 통해 관련 섹션 찾기"""
        # 1순위: 섹션 이름에 키워드가 정확히 매칭되는 경우
        for section_name, content in sections.items():
            for keyword in keywords:
                if keyword.lower() in section_name.lower():
                    return content[:200] + "..." if len(content) > 200 else content

        # 2순위: 내용에 키워드가 포함되는 경우
        for section_name, content in sections.items():
            for keyword in keywords:
                if keyword.lower() in content.lower():
                    return content[:200] + "..." if len(content) > 200 else content

        return default

    def _extract_key_points(self, sections: Dict[str, str]) -> Dict[str, str]:
        """핵심 포인트 요약"""
        return {
            "전략성": "고객 맞춤형 접근과 해결 방안 제시",
            "시각화": "구조도, 조직도, 일정표 등 다이어그램 활용",
            "정량성": "SLA 지표, 인력 수, 일정 등 수치 기반으로 제시",
            "규제 대응": "금융감독기관 보고 체계/보안 요건 적극 반영",
            "차별화": "도구, 인력, 실적, 방법론 등 자사 강점 강조",
        }

    def run(self, inputs: Dict) -> Dict:
        """
        클라우드 전환 제안서 요약 실행

        Args:
            inputs (Dict): {
                "content": str,
                "title": str
            }

        Returns:
            Dict: {"summary": Dict, "mcp_context": Dict}
        """
        try:
            content = inputs.get("content", "")
            title = inputs.get("title", "클라우드 전환 제안서")

            # 섹션별 내용 추출
            sections = self._extract_sections(content)
            sections["title"] = title

            # 제안서 구조에 맞는 요약 생성
            summary_data = self._create_proposal_summary(sections)

            return {
                "summary": summary_data,
                "mcp_context": {
                    "role": "report_summarizer",
                    "status": "success",
                    "sections_processed": len(sections),
                    "structure": "cloud_transformation_proposal",
                },
            }

        except Exception as e:
            return {
                "summary": {},
                "mcp_context": {
                    "role": "report_summarizer",
                    "status": "error",
                    "message": f"보고서 요약 중 오류: {str(e)}",
                },
            }

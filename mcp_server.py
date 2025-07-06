#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
클라우드 거버넌스 AI 서비스 FastMCP 서버

RAG 검색 및 보고서 요약 도구들을 MCP 프로토콜로 제공합니다.
"""

import sys
import os
from typing import Dict, Any, List
import logging

# 현재 디렉토리를 Python 패스에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from fastmcp import FastMCP
from tools import RAGRetrieverTool, ReportSummaryTool, SlideDraftTool

# FastMCP 서버 초기화
mcp = FastMCP("cloud-governance-tools")

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 도구 인스턴스들
rag_retriever = None
report_summary = None
slide_draft = None


def startup():
    """MCP 서버 시작 시 도구들 초기화"""
    global rag_retriever, report_summary, slide_draft
    try:
        logger.info("🔧 MCP 도구 서버 초기화 중...")

        # RAG Retriever 초기화
        rag_retriever = RAGRetrieverTool()
        logger.info("✅ RAG Retriever 도구 초기화 완료")

        # Report Summary 초기화
        report_summary = ReportSummaryTool()
        logger.info("✅ Report Summary 도구 초기화 완료")

        # Slide Draft 초기화
        slide_draft = SlideDraftTool()
        logger.info("✅ Slide Draft 도구 초기화 완료")

        logger.info("🎉 모든 MCP 도구 초기화 완료")

    except Exception as e:
        logger.error(f"❌ MCP 도구 초기화 실패: {str(e)}")
        raise


@mcp.tool
async def search_documents(query: str, top_k: int = 5) -> Dict[str, Any]:
    """
    RAG 기반 문서 검색 도구

    Args:
        query: 검색할 질문이나 키워드
        top_k: 반환할 최대 결과 개수 (기본값: 5)

    Returns:
        검색 결과 및 관련 메타데이터
    """
    try:
        logger.info(f"📄 문서 검색 요청: {query[:50]}...")

        if not rag_retriever:
            return {
                "results": [],
                "mcp_context": {
                    "role": "retriever",
                    "status": "error",
                    "message": "RAG Retriever가 초기화되지 않았습니다.",
                },
            }

        # RAG 검색 실행
        result = rag_retriever.run({"query": query, "top_k": top_k})

        logger.info(f"✅ 문서 검색 완료: {len(result.get('results', []))}개 결과")
        return result

    except Exception as e:
        logger.error(f"❌ 문서 검색 실패: {str(e)}")
        return {
            "results": [],
            "mcp_context": {
                "role": "retriever",
                "status": "error",
                "message": f"문서 검색 중 오류: {str(e)}",
            },
        }


@mcp.tool
async def summarize_report(
    content: str,
    title: str = "클라우드 거버넌스 보고서",
    summary_type: str = "executive",
    format_type: str = "html",
) -> Dict[str, Any]:
    """
    보고서 요약 도구

    Args:
        content: 요약할 보고서 내용
        title: 보고서 제목 (기본값: "클라우드 거버넌스 보고서")
        summary_type: 요약 유형 ("executive", "technical", "compliance")
        format_type: 출력 형식 ("html", "json")

    Returns:
        요약된 보고서 데이터
    """
    try:
        logger.info(f"📊 보고서 요약 요청: {summary_type} 타입")

        if not report_summary:
            return {
                "summary": {},
                "html": "",
                "mcp_context": {
                    "role": "report_summarizer",
                    "status": "error",
                    "message": "Report Summary가 초기화되지 않았습니다.",
                },
            }

        # 보고서 요약 실행
        result = report_summary.run(
            {
                "content": content,
                "title": title,
                "summary_type": summary_type,
                "format": format_type,
            }
        )

        logger.info(f"✅ 보고서 요약 완료: {summary_type} 타입")
        return result

    except Exception as e:
        logger.error(f"❌ 보고서 요약 실패: {str(e)}")
        return {
            "summary": {},
            "html": "",
            "mcp_context": {
                "role": "report_summarizer",
                "status": "error",
                "message": f"보고서 요약 중 오류: {str(e)}",
            },
        }


@mcp.tool
async def create_slide_draft(
    search_results: List[Dict[str, Any]],
    user_input: str,
    slide_type: str = "basic",
    title: str = "클라우드 거버넌스",
) -> Dict[str, Any]:
    """
    슬라이드 초안 생성 도구

    Args:
        search_results: RAG 검색 결과 리스트
        user_input: 사용자 입력 텍스트
        slide_type: 슬라이드 유형 ("basic", "detailed", "comparison")
        title: 슬라이드 제목

    Returns:
        슬라이드 초안 데이터
    """
    try:
        logger.info(f"📝 슬라이드 초안 생성 요청: {slide_type} 타입")

        if not slide_draft:
            return {
                "draft": {},
                "mcp_context": {
                    "role": "slide_drafter",
                    "status": "error",
                    "message": "Slide Draft가 초기화되지 않았습니다.",
                },
            }

        # 슬라이드 초안 생성 실행
        result = slide_draft.run(
            {
                "search_results": search_results,
                "user_input": user_input,
                "slide_type": slide_type,
                "title": title,
            }
        )

        logger.info(f"✅ 슬라이드 초안 생성 완료: {slide_type} 타입")
        return result

    except Exception as e:
        logger.error(f"❌ 슬라이드 초안 생성 실패: {str(e)}")
        return {
            "draft": {},
            "mcp_context": {
                "role": "slide_drafter",
                "status": "error",
                "message": f"슬라이드 초안 생성 중 오류: {str(e)}",
            },
        }


@mcp.tool
async def get_tool_status() -> Dict[str, Any]:
    """
    MCP 도구 서버 상태 확인

    Returns:
        도구 서버의 현재 상태 정보
    """
    try:
        status = {
            "server_name": "cloud-governance-tools",
            "version": "1.0.0",
            "status": "running",
            "tools": {
                "rag_retriever": "available" if rag_retriever else "unavailable",
                "report_summary": "available" if report_summary else "unavailable",
                "slide_draft": "available" if slide_draft else "unavailable",
            },
            "timestamp": get_timestamp(),
        }

        logger.info("📊 도구 상태 조회 완료")
        return status

    except Exception as e:
        logger.error(f"❌ 도구 상태 조회 실패: {str(e)}")
        return {
            "status": "error",
            "message": f"상태 조회 중 오류: {str(e)}",
            "timestamp": get_timestamp(),
        }


def get_timestamp() -> str:
    """현재 타임스탬프 반환"""
    from datetime import datetime

    return datetime.now().isoformat()


if __name__ == "__main__":
    print("=" * 60)
    print("🛠️  클라우드 거버넌스 MCP 도구 서버 시작")
    print("=" * 60)
    print("📄 사용 가능한 도구:")
    print("   • search_documents: RAG 기반 문서 검색")
    print("   • summarize_report: 보고서 요약 (HTML 형식)")
    print("   • create_slide_draft: 슬라이드 초안 생성")
    print("   • get_tool_status: 도구 상태 확인")
    print("=" * 60)

    startup()  # 도구들 초기화

    try:
        mcp.run(transport="streamable-http", host="127.0.0.1", port=8001, path="/tools")
    except KeyboardInterrupt:
        print("\n🛑 사용자에 의해 중단됨")
    except Exception as e:
        print(f"\n❌ 서버 실행 중 오류: {str(e)}")
    finally:
        print("✅ 모든 서버가 종료되었습니다.")

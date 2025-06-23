#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MCP 클라이언트 모듈

FastMCP 서버와 Model Context Protocol을 통해 통신하는 클라이언트
"""

import logging
from typing import Dict, Any
import httpx
import asyncio

logger = logging.getLogger(__name__)


class MCPClient:
    """MCP 서버와 통신하는 클라이언트"""

    def __init__(self, mcp_server_url: str = "http://localhost:8001"):
        """
        MCP 클라이언트 초기화

        Args:
            mcp_server_url: MCP 서버 URL
        """
        self.mcp_server_url = mcp_server_url.rstrip("/")
        self.client = httpx.AsyncClient(timeout=30.0)

    async def __aenter__(self):
        """비동기 컨텍스트 매니저 시작"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """비동기 컨텍스트 매니저 종료"""
        await self.client.aclose()

    async def call_tool(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        """
        MCP 도구 호출

        Args:
            tool_name: 호출할 도구 이름
            **kwargs: 도구에 전달할 매개변수

        Returns:
            도구 실행 결과
        """
        try:
            logger.info(f"🔧 MCP 도구 호출: {tool_name}")

            # MCP 도구 호출 엔드포인트 URL
            url = f"{self.mcp_server_url}/tools/{tool_name}"

            # 매개변수 준비
            payload = kwargs

            # POST 요청으로 도구 호출
            response = await self.client.post(
                url, json=payload, headers={"Content-Type": "application/json"}
            )

            if response.status_code == 200:
                result = response.json()
                logger.info(f"✅ MCP 도구 호출 성공: {tool_name}")
                return result
            else:
                logger.error(f"❌ MCP 도구 호출 실패: {response.status_code}")
                return {
                    "error": f"HTTP {response.status_code}: {response.text}",
                    "mcp_context": {"status": "error", "tool_name": tool_name},
                }

        except Exception as e:
            logger.error(f"❌ MCP 도구 호출 예외: {str(e)}")
            return {
                "error": f"도구 호출 실패: {str(e)}",
                "mcp_context": {"status": "error", "tool_name": tool_name},
            }

    async def search_documents(self, query: str, top_k: int = 5) -> Dict[str, Any]:
        """
        문서 검색 도구 호출

        Args:
            query: 검색 질의
            top_k: 반환할 최대 결과 수

        Returns:
            검색 결과
        """
        return await self.call_tool("search_documents", query=query, top_k=top_k)

    async def format_slide(
        self,
        content: str,
        title: str = "클라우드 거버넌스",
        slide_type: str = "basic",
        subtitle: str = "",
        format_type: str = "json",
    ) -> Dict[str, Any]:
        """
        슬라이드 포맷팅 도구 호출

        Args:
            content: 슬라이드 내용
            title: 슬라이드 제목
            slide_type: 슬라이드 유형
            subtitle: 부제목
            format_type: 출력 형식

        Returns:
            포맷팅된 슬라이드
        """
        return await self.call_tool(
            "format_slide",
            content=content,
            title=title,
            slide_type=slide_type,
            subtitle=subtitle,
            format_type=format_type,
        )

    async def summarize_report(
        self,
        content: str,
        title: str = "클라우드 거버넌스 보고서",
        summary_type: str = "executive",
        format_type: str = "html",
    ) -> Dict[str, Any]:
        """
        보고서 요약 도구 호출

        Args:
            content: 요약할 보고서 내용
            title: 보고서 제목
            summary_type: 요약 유형 ("executive", "technical", "compliance")
            format_type: 출력 형식

        Returns:
            요약된 보고서
        """
        return await self.call_tool(
            "summarize_report",
            content=content,
            title=title,
            summary_type=summary_type,
            format_type=format_type,
        )

    async def get_tool_status(self) -> Dict[str, Any]:
        """
        MCP 도구 서버 상태 확인

        Returns:
            서버 상태 정보
        """
        return await self.call_tool("get_tool_status")

    async def health_check(self) -> bool:
        """
        MCP 서버 헬스 체크

        Returns:
            서버가 정상인지 여부
        """
        try:
            response = await self.client.get(f"{self.mcp_server_url}/health")
            return response.status_code == 200
        except Exception:
            return False


class SyncMCPClient:
    """동기 MCP 클라이언트 래퍼"""

    def __init__(self, mcp_server_url: str = "http://localhost:8001"):
        self.mcp_server_url = mcp_server_url

    def _run_async(self, coro):
        """비동기 함수를 동기적으로 실행"""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(coro)

    def search_documents(self, query: str, top_k: int = 5) -> Dict[str, Any]:
        """동기식 문서 검색"""

        async def _search():
            async with MCPClient(self.mcp_server_url) as client:
                return await client.search_documents(query, top_k)

        return self._run_async(_search())

    def format_slide(
        self,
        content: str,
        title: str = "클라우드 거버넌스",
        slide_type: str = "basic",
        subtitle: str = "",
        format_type: str = "json",
    ) -> Dict[str, Any]:
        """동기식 슬라이드 포맷팅"""

        async def _format():
            async with MCPClient(self.mcp_server_url) as client:
                return await client.format_slide(
                    content, title, slide_type, subtitle, format_type
                )

        return self._run_async(_format())

    def summarize_report(
        self,
        content: str,
        title: str = "클라우드 거버넌스 보고서",
        summary_type: str = "executive",
        format_type: str = "html",
    ) -> Dict[str, Any]:
        """동기식 보고서 요약"""

        async def _summarize():
            async with MCPClient(self.mcp_server_url) as client:
                return await client.summarize_report(
                    content, title, summary_type, format_type
                )

        return self._run_async(_summarize())

    def get_tool_status(self) -> Dict[str, Any]:
        """동기식 도구 상태 확인"""

        async def _status():
            async with MCPClient(self.mcp_server_url) as client:
                return await client.get_tool_status()

        return self._run_async(_status())

    def health_check(self) -> bool:
        """동기식 헬스 체크"""

        async def _health():
            async with MCPClient(self.mcp_server_url) as client:
                return await client.health_check()

        return self._run_async(_health())


# 전역 MCP 클라이언트 인스턴스
_mcp_client = None


def get_mcp_client() -> SyncMCPClient:
    """글로벌 MCP 클라이언트 인스턴스 반환"""
    global _mcp_client
    if _mcp_client is None:
        _mcp_client = SyncMCPClient()
    return _mcp_client

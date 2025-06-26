#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MCP 클라이언트 모듈 (langchain-mcp-adapters 사용)

FastMCP 서버와 Model Context Protocol을 통해 통신하는 클라이언트
langchain-mcp-adapters 라이브러리를 사용하여 올바른 MCP 프로토콜로 통신
"""

import logging
from typing import Dict, Any
import asyncio
from langchain_mcp_adapters.client import MultiServerMCPClient
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

logger = logging.getLogger(__name__)


class MCPClient:
    """langchain-mcp-adapters를 통한 MCP 서버와 통신하는 클라이언트"""

    def __init__(self, mcp_server_url: str = "http://localhost:8001/tools"):
        """
        MCP 클라이언트 초기화

        Args:
            mcp_server_url: MCP 서버 URL
        """
        self.mcp_server_url = mcp_server_url
        self.session = None
        self.read_stream = None
        self.write_stream = None
        self.client_session = None

    async def __aenter__(self):
        """비동기 컨텍스트 매니저 시작"""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """비동기 컨텍스트 매니저 종료"""
        await self.disconnect()

    async def connect(self):
        """MCP 서버에 연결"""
        try:
            logger.info(f"🔗 MCP 서버에 연결 중: {self.mcp_server_url}")

            # streamablehttp_client를 사용하여 연결
            self.read_stream, self.write_stream, _ = await streamablehttp_client(
                self.mcp_server_url
            ).__aenter__()
            self.client_session = ClientSession(self.read_stream, self.write_stream)
            await self.client_session.__aenter__()

            # 연결 초기화
            await self.client_session.initialize()
            logger.info("✅ MCP 서버 연결 성공")

        except Exception as e:
            logger.error(f"❌ MCP 서버 연결 실패: {str(e)}")
            raise

    async def disconnect(self):
        """MCP 서버 연결 해제"""
        try:
            if self.client_session:
                await self.client_session.__aexit__(None, None, None)
            if self.read_stream and self.write_stream:
                # streamablehttp_client 정리는 자동으로 처리됨
                pass
            logger.info("🔌 MCP 서버 연결 해제")
        except Exception as e:
            logger.error(f"❌ 연결 해제 중 오류: {str(e)}")

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
            if not self.client_session:
                raise RuntimeError("MCP 클라이언트가 연결되지 않았습니다")

            logger.info(f"🔧 MCP 도구 호출: {tool_name}")
            logger.info(f"📋 매개변수: {kwargs}")

            # MCP 프로토콜을 통해 도구 호출
            result = await self.client_session.call_tool(tool_name, arguments=kwargs)

            if result.isError:
                logger.error(f"❌ MCP 도구 호출 실패: {result.content[0].text}")
                return {
                    "error": result.content[0].text,
                    "mcp_context": {"status": "error", "tool_name": tool_name},
                }
            else:
                logger.info(f"✅ MCP 도구 호출 성공: {tool_name}")
                # MCP 결과를 파싱하여 반환
                if result.content and len(result.content) > 0:
                    content = result.content[0]
                    if hasattr(content, "text"):
                        # 텍스트 결과인 경우
                        return {"result": content.text, "status": "success"}
                    else:
                        # 다른 형태의 결과인 경우
                        return {"result": str(content), "status": "success"}
                else:
                    return {"result": "도구 실행 완료", "status": "success"}

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
            if not self.client_session:
                return False

            # 간단한 도구 목록 조회로 헬스 체크
            tools_response = await self.client_session.list_tools()
            return True
        except Exception:
            return False


class SyncMCPClient:
    """동기 MCP 클라이언트 래퍼 (langchain-mcp-adapters 기반)"""

    def __init__(self, mcp_server_url: str = "http://localhost:8001/tools"):
        """
        동기 MCP 클라이언트 초기화

        Args:
            mcp_server_url: MCP 서버 URL
        """
        self.mcp_server_url = mcp_server_url
        self.multi_client = MultiServerMCPClient(
            {"default": {"url": mcp_server_url, "transport": "streamable_http"}}
        )

    def _run_async(self, coro):
        """비동기 함수를 동기적으로 실행"""
        try:
            # 현재 실행 중인 이벤트 루프가 있는지 확인
            loop = asyncio.get_running_loop()
            # 이미 실행 중인 루프가 있으면 새 스레드에서 실행
            import concurrent.futures
            import threading

            def run_in_thread():
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                try:
                    return new_loop.run_until_complete(coro)
                finally:
                    new_loop.close()

            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(run_in_thread)
                return future.result()

        except RuntimeError:
            # 실행 중인 이벤트 루프가 없으면 새로 생성
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(coro)
            finally:
                loop.close()

    def search_documents(self, query: str, top_k: int = 5) -> Dict[str, Any]:
        """동기식 문서 검색"""

        async def _search():
            try:
                # MultiServerMCPClient를 사용하여 도구 가져오기
                tools = await self.multi_client.get_tools()

                # search_documents 도구 찾기
                search_tool = None
                for tool in tools:
                    if tool.name == "search_documents":
                        search_tool = tool
                        break

                if not search_tool:
                    return {"error": "search_documents 도구를 찾을 수 없습니다"}

                # 도구 실행
                result = await search_tool.ainvoke({"query": query, "top_k": top_k})
                return {"result": result, "status": "success"}

            except Exception as e:
                return {"error": f"검색 실패: {str(e)}"}

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
            try:
                tools = await self.multi_client.get_tools()

                format_tool = None
                for tool in tools:
                    if tool.name == "format_slide":
                        format_tool = tool
                        break

                if not format_tool:
                    return {"error": "format_slide 도구를 찾을 수 없습니다"}

                result = await format_tool.ainvoke(
                    {
                        "content": content,
                        "title": title,
                        "slide_type": slide_type,
                        "subtitle": subtitle,
                        "format_type": format_type,
                    }
                )
                return {"result": result, "status": "success"}

            except Exception as e:
                return {"error": f"슬라이드 포맷팅 실패: {str(e)}"}

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
            try:
                tools = await self.multi_client.get_tools()

                summary_tool = None
                for tool in tools:
                    if tool.name == "summarize_report":
                        summary_tool = tool
                        break

                if not summary_tool:
                    return {"error": "summarize_report 도구를 찾을 수 없습니다"}

                result = await summary_tool.ainvoke(
                    {
                        "content": content,
                        "title": title,
                        "summary_type": summary_type,
                        "format_type": format_type,
                    }
                )
                return {"result": result, "status": "success"}

            except Exception as e:
                return {"error": f"보고서 요약 실패: {str(e)}"}

        return self._run_async(_summarize())

    def get_tool_status(self) -> Dict[str, Any]:
        """동기식 도구 상태 확인"""

        async def _status():
            try:
                tools = await self.multi_client.get_tools()

                status_tool = None
                for tool in tools:
                    if tool.name == "get_tool_status":
                        status_tool = tool
                        break

                if not status_tool:
                    return {"error": "get_tool_status 도구를 찾을 수 없습니다"}

                result = await status_tool.ainvoke({})
                return {"result": result, "status": "success"}

            except Exception as e:
                return {"error": f"상태 확인 실패: {str(e)}"}

        return self._run_async(_status())

    def health_check(self) -> bool:
        """동기식 헬스 체크"""

        async def _health():
            try:
                tools = await self.multi_client.get_tools()
                return len(tools) > 0
            except Exception:
                return False

        return self._run_async(_health())


# 전역 MCP 클라이언트 인스턴스
_mcp_client = None


def get_mcp_client() -> SyncMCPClient:
    """글로벌 MCP 클라이언트 인스턴스 반환"""
    global _mcp_client
    if _mcp_client is None:
        _mcp_client = SyncMCPClient("http://localhost:8001/tools")
    return _mcp_client

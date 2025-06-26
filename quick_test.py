#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
langchain-mcp-adapters를 사용한 MCP 도구 호출 테스트
"""

import sys
import os
import asyncio

# 현재 디렉토리를 Python 패스에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from langchain_mcp_adapters.client import MultiServerMCPClient


async def test_mcp_tools():
    """langchain-mcp-adapters를 사용하여 MCP 도구 테스트"""
    print("🧪 langchain-mcp-adapters MCP 도구 테스트")
    print("=" * 70)

    try:
        # MultiServerMCPClient 설정
        print("📋 1. MCP 클라이언트 초기화...")
        client = MultiServerMCPClient(
            {
                "cloud_governance_tools": {
                    "url": "http://localhost:8001/tools",
                    "transport": "streamable_http",
                }
            }
        )
        print("✅ 클라이언트 초기화 완료")

        # 사용 가능한 도구 확인
        print(f"\n📋 2. 사용 가능한 도구 확인...")
        tools = await client.get_tools()
        print(f"   발견된 도구 수: {len(tools)}")

        for i, tool in enumerate(tools):
            print(f"   {i+1}. {tool.name}: {tool.description[:100]}...")

        if len(tools) == 0:
            print("❌ 사용 가능한 도구가 없습니다. MCP 서버가 실행 중인지 확인하세요.")
            return False

        # 첫 번째 도구 테스트 (보통 search_documents)
        if len(tools) > 0:
            test_tool = tools[0]
            print(f"\n📋 3. 도구 테스트: {test_tool.name}")

            try:
                if test_tool.name == "search_documents":
                    result = await test_tool.ainvoke(
                        {"query": "클라우드 보안 정책", "top_k": 3}
                    )
                elif test_tool.name == "format_slide":
                    result = await test_tool.ainvoke(
                        {
                            "content": "클라우드 거버넌스의 중요성",
                            "title": "테스트 슬라이드",
                            "slide_type": "basic",
                        }
                    )
                elif test_tool.name == "get_tool_status":
                    result = await test_tool.ainvoke({})
                else:
                    print(f"   알려지지 않은 도구 유형: {test_tool.name}")
                    return False

                print(f"   ✅ 도구 실행 성공!")
                print(f"   📊 결과 타입: {type(result)}")
                print(f"   📊 결과 길이: {len(str(result))} 문자")

                # 결과 일부 출력 (너무 길면 잘라서)
                result_str = str(result)
                if len(result_str) > 500:
                    print(f"   📄 결과 미리보기: {result_str[:500]}...")
                else:
                    print(f"   📄 결과: {result_str}")

                return True

            except Exception as tool_error:
                print(f"   ❌ 도구 실행 실패: {str(tool_error)}")
                import traceback

                traceback.print_exc()
                return False

    except Exception as e:
        print(f"❌ 테스트 실행 중 예외 발생: {str(e)}")
        import traceback

        traceback.print_exc()
        return False


def main():
    """메인 테스트 실행"""
    print("🚀 langchain-mcp-adapters MCP 도구 테스트")
    print("=" * 80)
    print("📌 이 테스트는 다음을 확인합니다:")
    print("   • MCP 서버 연결")
    print("   • 사용 가능한 도구 목록")
    print("   • 도구 실행 테스트")
    print("=" * 80)

    try:
        # 비동기 테스트 실행
        result = asyncio.run(test_mcp_tools())

        print("\n" + "=" * 80)
        if result:
            print("🎉 MCP 도구 테스트가 성공했습니다!")
            print("   langchain-mcp-adapters를 통한 MCP 통신이 정상 작동합니다.")
            return 0
        else:
            print("⚠️  MCP 도구 테스트가 실패했습니다.")
            print("   • MCP 서버가 실행되고 있는지 확인하세요: python mcp_server.py")
            print("   • 서버 URL이 올바른지 확인하세요: http://localhost:8001/tools")
            return 1

    except Exception as e:
        print(f"\n❌ 메인 테스트 실행 중 예외: {str(e)}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)

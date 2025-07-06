#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CloudRegiX 시스템 통합 테스트 (langchain-mcp-adapters 사용)
"""

import sys
import os
import asyncio

# 현재 디렉토리를 Python 패스에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from agents import ReActExecutorAgent
from langchain_mcp_adapters.client import MultiServerMCPClient


async def test_mcp_connection():
    """MCP 서버 연결 테스트"""
    print("🔗 MCP 서버 연결 테스트")
    print("-" * 50)

    try:
        client = MultiServerMCPClient(
            {
                "cloud_governance": {
                    "url": "http://localhost:8001/tools",
                    "transport": "streamable_http",
                }
            }
        )

        tools = await client.get_tools()
        print(f"✅ MCP 연결 성공: {len(tools)}개 도구 발견")

        for tool in tools:
            print(f"   • {tool.name}")

        return True

    except Exception as e:
        print(f"❌ MCP 연결 실패: {str(e)}")
        return False


def test_react_executor():
    """ReActExecutorAgent 테스트"""
    print("\n🤖 ReActExecutorAgent 테스트")
    print("-" * 50)

    try:
        executor = ReActExecutorAgent("test_executor")
        print("✅ ReActExecutorAgent 초기화 완료")

        # 간단한 검색 테스트
        test_step = {
            "step_id": "test_search",
            "step_type": "data_collection",
            "description": "클라우드 보안 정보 검색",
            "required_tools": ["search_documents"],
            "timeout": 30,
        }

        test_context = {"user_query": "클라우드 보안 정책에 대해 알려주세요"}

        print("📋 테스트 단계 실행 중...")
        result = executor.execute_step(test_step, test_context)

        print(f"📊 실행 결과:")
        print(f"   상태: {result.get('status', 'unknown')}")
        print(f"   신뢰도: {result.get('confidence', 0)}")
        print(f"   목표 달성: {result.get('goal_achieved', False)}")

        return (
            result.get("status") == "success"
            or result.get("status") == "partial_success"
        )

    except Exception as e:
        print(f"❌ ReActExecutorAgent 테스트 실패: {str(e)}")
        import traceback

        traceback.print_exc()
        return False


def test_slide_generation():
    """슬라이드 생성 테스트"""
    print("\n🎨 슬라이드 생성 테스트")
    print("-" * 50)

    try:
        executor = ReActExecutorAgent("slide_executor")

        test_step = {
            "step_id": "test_slide",
            "step_type": "generating",
            "description": "클라우드 거버넌스 슬라이드 생성",
            "required_tools": ["format_slide"],
            "timeout": 30,
        }

        test_context = {"user_query": "클라우드 거버넌스 개요 슬라이드를 만들어주세요"}

        print("📋 슬라이드 생성 중...")
        result = executor.execute_step(test_step, test_context)

        print(f"📊 생성 결과:")
        print(f"   상태: {result.get('status', 'unknown')}")
        print(f"   목표 달성: {result.get('goal_achieved', False)}")

        return result.get("goal_achieved", False)

    except Exception as e:
        print(f"❌ 슬라이드 생성 테스트 실패: {str(e)}")
        return False


async def main():
    """메인 테스트 실행"""
    print("🚀 CloudRegiX 시스템 통합 테스트")
    print("=" * 80)
    print("📌 langchain-mcp-adapters 기반 MCP 통신 테스트")
    print("=" * 80)

    # 테스트 목록
    tests = [
        ("MCP 서버 연결", test_mcp_connection, True),  # 비동기
        ("ReActExecutorAgent", test_react_executor, False),  # 동기
        ("슬라이드 생성", test_slide_generation, False),  # 동기
    ]

    passed = 0
    total = len(tests)

    for test_name, test_func, is_async in tests:
        print(f"\n🧪 {test_name} 테스트 실행 중...")

        try:
            if is_async:
                result = await test_func()
            else:
                result = test_func()

            if result:
                passed += 1
                print(f"✅ {test_name} 테스트 통과")
            else:
                print(f"❌ {test_name} 테스트 실패")

        except Exception as e:
            print(f"💥 {test_name} 테스트 실행 중 예외: {str(e)}")

    # 최종 결과
    print("\n" + "=" * 80)
    print(f"📊 테스트 결과: {passed}/{total} 통과")

    if passed == total:
        print("🎉 모든 테스트가 성공했습니다!")
        print("   ✅ MCP 서버 연결 정상")
        print("   ✅ ReActExecutorAgent 정상 작동")
        print("   ✅ 도구 호출 성공")
        print("\n💡 시스템이 정상적으로 작동하고 있습니다.")
        return 0
    else:
        print("⚠️  일부 테스트가 실패했습니다.")
        print("\n🔧 확인사항:")
        print("   • MCP 서버가 실행 중인지 확인: python mcp_server.py")
        print("   • 포트 8001이 사용 가능한지 확인")
        print("   • 네트워크 연결 상태 확인")
        return 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n🛑 사용자에 의해 중단됨")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 시스템 테스트 실행 중 예외: {str(e)}")
        import traceback

        traceback.print_exc()
        sys.exit(1)

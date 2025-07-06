#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
langchain-mcp-adapters를 사용한 MCP 도구 호출 테스트
"""

import sys
import os
import asyncio
import json
import logging
from tools.slide_generator import SlideGeneratorTool

# 현재 디렉토리를 Python 패스에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from langchain_mcp_adapters.client import MultiServerMCPClient

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


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


def test_slide_generator():
    """SlideGeneratorTool 테스트"""
    print("=== SlideGeneratorTool 테스트 시작 ===")

    # 테스트 데이터 준비
    test_slide_draft = {
        "title": "클라우드 보안 거버넌스 전략",
        "subtitle": "AI 기반 보안 관리 방안",
        "bullets": [
            "클라우드 보안 정책 수립",
            "접근 제어 및 인증 강화",
            "데이터 암호화 및 백업 전략",
        ],
    }

    test_search_results = [
        {
            "content": "클라우드 환경에서의 보안 거버넌스는 조직의 디지털 전환 과정에서 핵심적인 역할을 합니다. 효과적인 보안 정책을 통해 위험을 최소화하고 컴플라이언스를 확보할 수 있습니다.",
            "source": "보안 가이드라인 문서",
        },
        {
            "content": "AI 기반 보안 모니터링 시스템은 실시간으로 위협을 탐지하고 대응할 수 있는 능력을 제공합니다. 머신러닝 알고리즘을 활용하여 비정상적인 패턴을 식별하고 자동화된 대응 체계를 구축할 수 있습니다.",
            "source": "AI 보안 솔루션 백서",
        },
        {
            "content": "제로 트러스트 보안 모델은 모든 네트워크 트래픽을 신뢰하지 않는 것을 전제로 하여 지속적인 검증과 최소 권한 원칙을 적용합니다. 이는 클라우드 환경에서 특히 중요한 보안 접근 방식입니다.",
            "source": "제로 트러스트 가이드",
        },
    ]

    test_user_input = "클라우드 보안 거버넌스를 위한 종합적인 전략을 수립하고 싶습니다. AI 기반 보안 모니터링과 제로 트러스트 모델을 포함한 실용적인 방안을 제시해주세요."

    try:
        # SlideGeneratorTool 인스턴스 생성
        slide_tool = SlideGeneratorTool()

        # 기본 슬라이드 생성 테스트
        print("\n--- 기본 슬라이드 생성 테스트 ---")
        basic_inputs = {
            "slide_draft": test_slide_draft,
            "search_results": test_search_results,
            "user_input": test_user_input,
            "slide_type": "basic",
            "format_type": "html",
        }

        basic_result = slide_tool.run(basic_inputs)
        print(f"기본 슬라이드 생성 성공: {basic_result['langchain_context']['status']}")
        print(f"생성된 제목: {basic_result['slide'].get('title', 'N/A')}")
        print(f"핵심 포인트 수: {len(basic_result['slide'].get('bullets', []))}")

        # 상세 슬라이드 생성 테스트
        print("\n--- 상세 슬라이드 생성 테스트 ---")
        detailed_inputs = {
            "slide_draft": test_slide_draft,
            "search_results": test_search_results,
            "user_input": test_user_input,
            "slide_type": "detailed",
            "format_type": "html",
        }

        detailed_result = slide_tool.run(detailed_inputs)
        print(
            f"상세 슬라이드 생성 성공: {detailed_result['langchain_context']['status']}"
        )
        print(f"생성된 제목: {detailed_result['slide'].get('title', 'N/A')}")
        print(f"부제목: {detailed_result['slide'].get('subtitle', 'N/A')}")
        print(f"결론: {detailed_result['slide'].get('conclusion', 'N/A')}")

        # 비교 슬라이드 생성 테스트
        print("\n--- 비교 슬라이드 생성 테스트 ---")
        comparison_inputs = {
            "slide_draft": test_slide_draft,
            "search_results": test_search_results,
            "user_input": test_user_input,
            "slide_type": "comparison",
            "format_type": "html",
        }

        comparison_result = slide_tool.run(comparison_inputs)
        print(
            f"비교 슬라이드 생성 성공: {comparison_result['langchain_context']['status']}"
        )
        print(f"생성된 제목: {comparison_result['slide'].get('title', 'N/A')}")
        left_col = comparison_result["slide"].get("left_column", {})
        right_col = comparison_result["slide"].get("right_column", {})
        print(
            f"좌측 컬럼: {left_col.get('title', 'N/A')} ({len(left_col.get('items', []))}개 항목)"
        )
        print(
            f"우측 컬럼: {right_col.get('title', 'N/A')} ({len(right_col.get('items', []))}개 항목)"
        )

        # HTML 파일 저장 테스트
        print("\n--- HTML 파일 저장 테스트 ---")
        with open("test_slide_basic.html", "w", encoding="utf-8") as f:
            f.write(basic_result["html"])
        print("기본 슬라이드 HTML 파일 저장 완료: test_slide_basic.html")

        with open("test_slide_detailed.html", "w", encoding="utf-8") as f:
            f.write(detailed_result["html"])
        print("상세 슬라이드 HTML 파일 저장 완료: test_slide_detailed.html")

        with open("test_slide_comparison.html", "w", encoding="utf-8") as f:
            f.write(comparison_result["html"])
        print("비교 슬라이드 HTML 파일 저장 완료: test_slide_comparison.html")

        print("\n=== SlideGeneratorTool 테스트 완료 ===")
        return True

    except Exception as e:
        logger.error(f"SlideGeneratorTool 테스트 실패: {str(e)}")
        return False


def test_streaming_slide_generator():
    """SlideGeneratorTool 스트리밍 테스트"""
    print("\n=== SlideGeneratorTool 스트리밍 테스트 시작 ===")

    test_slide_draft = {
        "title": "클라우드 비용 최적화 전략",
        "bullets": [
            "리소스 사용량 모니터링",
            "자동 스케일링 구현",
            "비용 분석 및 예측",
        ],
    }

    test_search_results = [
        {
            "content": "클라우드 비용 최적화를 위해서는 지속적인 모니터링과 분석이 필요합니다. 사용하지 않는 리소스를 식별하고 제거하여 비용을 절감할 수 있습니다.",
            "source": "비용 최적화 가이드",
        }
    ]

    test_user_input = (
        "클라우드 비용을 효율적으로 관리하고 최적화하는 방법을 알려주세요."
    )

    try:
        slide_tool = SlideGeneratorTool()

        inputs = {
            "slide_draft": test_slide_draft,
            "search_results": test_search_results,
            "user_input": test_user_input,
            "slide_type": "basic",
            "format_type": "html",
        }

        print("스트리밍 슬라이드 생성 중...")
        for chunk in slide_tool.run_streaming(inputs):
            if chunk["type"] == "progress":
                print(f"진행률: {chunk['progress']*100:.1f}% - {chunk['message']}")
            elif chunk["type"] == "result":
                print(f"완료: {chunk['message']}")
                result = chunk["data"]
                print(f"생성된 제목: {result['slide'].get('title', 'N/A')}")

                # 스트리밍 결과 HTML 저장
                with open("test_slide_streaming.html", "w", encoding="utf-8") as f:
                    f.write(result["html"])
                print(
                    "스트리밍 슬라이드 HTML 파일 저장 완료: test_slide_streaming.html"
                )

            elif chunk["type"] == "error":
                print(f"오류: {chunk['message']}")
                return False

        print("=== SlideGeneratorTool 스트리밍 테스트 완료 ===")
        return True

    except Exception as e:
        logger.error(f"스트리밍 테스트 실패: {str(e)}")
        return False


def main():
    """메인 테스트 실행"""
    print("🚀 CloudRegiX 시스템 테스트")
    print("=" * 80)
    print("📌 이 테스트는 다음을 확인합니다:")
    print("   • SlideGeneratorTool 기능 테스트")
    print("   • LLM 기반 슬라이드 생성")
    print("   • MCP 서버 연결")
    print("   • 사용 가능한 도구 목록")
    print("=" * 80)

    success_count = 0
    total_tests = 3

    try:
        # SlideGeneratorTool 테스트
        print("\n=== SlideGeneratorTool Test ===")
        try:
            success1 = test_slide_generator()
            success2 = test_streaming_slide_generator()

            if success1 and success2:
                print("\n✅ SlideGeneratorTool 테스트가 성공적으로 완료되었습니다!")
                success_count += 1
            else:
                print("\n❌ SlideGeneratorTool 테스트가 실패했습니다.")
        except Exception as e:
            print(f"SlideGeneratorTool 테스트 실패: {e}")

        # MCP 도구 테스트
        print("\n=== MCP Tools Test ===")
        try:
            result = asyncio.run(test_mcp_tools())
            if result:
                print("✅ MCP 도구 테스트가 성공했습니다!")
                success_count += 1
            else:
                print("❌ MCP 도구 테스트가 실패했습니다.")
        except Exception as e:
            print(f"MCP 도구 테스트 실패: {e}")

        print("\n" + "=" * 80)
        print(f"📊 테스트 결과: {success_count}/{total_tests} 성공")

        if success_count == total_tests:
            print("🎉 모든 테스트가 성공했습니다!")
            print("   CloudRegiX 시스템이 정상 작동합니다.")
            return 0
        else:
            print("⚠️  일부 테스트가 실패했습니다.")
            print("   • 실패한 테스트를 확인하고 문제를 해결하세요.")
            return 1

    except Exception as e:
        print(f"\n❌ 메인 테스트 실행 중 예외: {str(e)}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)

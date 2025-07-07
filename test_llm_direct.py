#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SlideGenerator LLM 직접 테스트
"""

import sys
import os

# 현재 디렉토리를 Python 패스에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from tools.slide_generator import SlideGeneratorTool
import logging

# 로깅 설정
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


def test_slide_generator_direct():
    """SlideGenerator를 직접 테스트"""

    print("🔍 SlideGenerator LLM 직접 테스트 시작...")

    # SlideGenerator 인스턴스 생성
    slide_generator = SlideGeneratorTool()

    # 테스트 입력 데이터
    test_inputs = {
        "slide_draft": {
            "markdown_content": """
# 클라우드 보안 정책

## 주요 내용
- 클라우드 거버넌스의 중요성
- 보안 정책 수립 방안
- 모니터링 체계 구축

## 핵심 포인트
- 데이터 보호가 최우선
- 지속적인 보안 감사 필요
- 직원 교육의 중요성
            """,
            "format": "markdown",
        },
        "search_results": [
            {
                "content": "클라우드 보안 정책은 조직의 클라우드 환경을 보호하기 위한 핵심 요소입니다.",
                "source": "테스트 문서",
            }
        ],
        "user_input": "클라우드 보안 정책에 대한 슬라이드를 만들어주세요",
    }

    try:
        print("📊 SlideGenerator 실행 중...")
        result = slide_generator.run(test_inputs)

        if "html" in result and result["html"]:
            html = result["html"]
            print(f"✅ HTML 생성 성공!")
            print(f"📄 HTML 전체 길이: {len(html):,} 문자")

            # HTML 시작 부분
            print(f"\n🔍 HTML 시작 (처음 300자):")
            print("-" * 60)
            print(html[:300])
            print("-" * 60)

            # HTML 끝 부분
            print(f"\n🔍 HTML 끝 (마지막 300자):")
            print("-" * 60)
            print(html[-300:])
            print("-" * 60)

            # HTML 완전성 확인
            if html.strip().endswith("</html>"):
                print("\n✅ HTML 완전성 검증: 정상 (</html>로 끝남)")
            else:
                print("\n⚠️ HTML 완전성 검증: 비정상 (</html>로 끝나지 않음)")
                print(f"실제 끝: {html[-100:]}")

            # HTML 파일로 저장
            with open("test_output.html", "w", encoding="utf-8") as f:
                f.write(html)
            print("\n💾 HTML을 test_output.html 파일로 저장했습니다.")

            return True
        else:
            print("❌ HTML 생성 실패 - 결과에 HTML이 없습니다.")
            print(f"결과: {result}")
            return False

    except Exception as e:
        print(f"❌ 테스트 중 오류 발생: {str(e)}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_slide_generator_direct()
    sys.exit(0 if success else 1)

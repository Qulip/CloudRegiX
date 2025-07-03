#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Streamlit 웹 앱 실행 스크립트
"""

import subprocess
import sys
import os


def main():
    """Streamlit 앱 실행"""
    print("=" * 60)
    print("🚀 클라우드 거버넌스 AI 웹 앱 시작")
    print("=" * 60)
    print("📌 웹 앱 URL: http://localhost:8501")
    print("💡 API 서버가 실행 중인지 확인하세요 (http://localhost:8000)")
    print("🛑 종료하려면 Ctrl+C를 누르세요")
    print("=" * 60)

    # Streamlit 앱 실행
    try:
        subprocess.run(
            [
                sys.executable,
                "-m",
                "streamlit",
                "run",
                "main.py",
                "--server.port=8501",
                "--server.address=0.0.0.0",
                "--browser.gatherUsageStats=false",
            ],
            cwd=os.path.dirname(os.path.abspath(__file__)),
        )
    except KeyboardInterrupt:
        print("\n🛑 웹 앱이 종료되었습니다.")
    except Exception as e:
        print(f"❌ 웹 앱 실행 실패: {str(e)}")


if __name__ == "__main__":
    main()

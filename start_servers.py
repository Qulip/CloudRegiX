#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
클라우드 거버넌스 AI 서비스 통합 실행 스크립트

FastAPI 서버와 MCP 서버를 동시에 실행합니다.
"""

import subprocess
import sys
import time
import signal
import os
from concurrent.futures import ThreadPoolExecutor


class ServerManager:
    """서버 실행 관리 클래스"""

    def __init__(self):
        self.processes = []
        self.running = True

    def run_mcp_server(self):
        """MCP 서버 실행"""
        try:
            print("🛠️  MCP 도구 서버 시작 중... (포트 8001)")
            process = subprocess.Popen(
                [sys.executable, "mcp_server.py"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                cwd=os.path.dirname(os.path.abspath(__file__)),
            )
            self.processes.append(process)

            # 실시간 로그 출력
            for line in iter(process.stdout.readline, ""):
                if self.running:
                    print(f"[MCP] {line.strip()}")
                else:
                    break

        except Exception as e:
            print(f"❌ MCP 서버 실행 실패: {str(e)}")

    def run_api_server(self):
        """API 서버 실행"""
        try:
            # MCP 서버가 시작될 시간을 줌
            time.sleep(3)

            print("🚀 FastAPI 서버 시작 중... (포트 8000)")
            process = subprocess.Popen(
                [sys.executable, "api_server.py"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                cwd=os.path.dirname(os.path.abspath(__file__)),
            )
            self.processes.append(process)

            # 실시간 로그 출력
            for line in iter(process.stdout.readline, ""):
                if self.running:
                    print(f"[API] {line.strip()}")
                else:
                    break

        except Exception as e:
            print(f"❌ API 서버 실행 실패: {str(e)}")

    def signal_handler(self, signum, frame):
        """시그널 핸들러 (Ctrl+C 처리)"""
        print("\n🛑 서버 종료 신호 수신...")
        self.stop_servers()
        sys.exit(0)

    def stop_servers(self):
        """모든 서버 중지"""
        self.running = False
        print("🔄 서버들을 종료하는 중...")

        for process in self.processes:
            if process.poll() is None:  # 프로세스가 아직 실행 중인 경우
                try:
                    process.terminate()
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()

        print("✅ 모든 서버가 종료되었습니다.")

    def run(self):
        """서버들 실행"""
        # 시그널 핸들러 등록
        signal.signal(signal.SIGINT, self.signal_handler)

        print("=" * 60)
        print("🚀 클라우드 거버넌스 AI 서비스 시작")
        print("=" * 60)
        print("📌 실행 중인 서버:")
        print("   • MCP 도구 서버: http://localhost:8001")
        print("   • FastAPI 서버: http://localhost:8000")
        print()
        print("💡 API 테스트:")
        print("   curl -X POST http://localhost:8000/chat \\")
        print("        -H 'Content-Type: application/json' \\")
        print('        -d \'{"query": "클라우드 보안 정책에 대해 알려주세요"}\'')
        print()
        print("🛑 종료하려면 Ctrl+C를 누르세요")
        print("=" * 60)

        # 스레드풀로 서버들 동시 실행
        with ThreadPoolExecutor(max_workers=2) as executor:
            try:
                # MCP 서버 먼저 시작
                mcp_future = executor.submit(self.run_mcp_server)
                # API 서버는 조금 늦게 시작
                api_future = executor.submit(self.run_api_server)

                # 두 서버가 모두 완료될 때까지 대기
                mcp_future.result()
                api_future.result()

            except KeyboardInterrupt:
                print("\n🛑 사용자에 의해 중단됨")
            except Exception as e:
                print(f"\n❌ 서버 실행 중 오류: {str(e)}")
            finally:
                self.stop_servers()


def check_dependencies():
    """의존성 확인"""
    try:
        import fastapi
        import uvicorn
        import httpx
        from fastmcp import FastMCP

        print("✅ 모든 의존성이 설치되어 있습니다.")
        return True
    except ImportError as e:
        print(f"❌ 의존성 누락: {str(e)}")
        print("🔧 해결 방법: pip install -r requirements.txt")
        return False


def check_environment():
    """환경 설정 확인"""
    required_vars = ["AOAI_API_KEY", "AOAI_ENDPOINT", "AOAI_API_VERSION"]
    missing_vars = []

    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)

    if missing_vars:
        print(f"❌ 환경 변수 누락: {', '.join(missing_vars)}")
        print("🔧 해결 방법: .env 파일을 생성하고 Azure OpenAI 설정을 입력하세요.")
        return False

    print("✅ 환경 설정이 완료되어 있습니다.")
    return True


def main():
    """메인 실행 함수"""
    print("🔍 시스템 사전 확인 중...")

    # 의존성 확인
    if not check_dependencies():
        return 1

    # 환경 설정 확인
    if not check_environment():
        return 1

    # 서버 실행
    manager = ServerManager()
    manager.run()

    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)

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
import logging

from core import get_llm


# 로깅 설정
def setup_server_logging():
    """서버 시작 스크립트 로깅 설정"""
    # 로그 디렉토리 확인
    log_dir = "log"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # 로그 파일 경로
    log_file_path = os.path.join(log_dir, "start_servers.log")

    # 서버 시작 시마다 로그 파일 초기화
    if os.path.exists(log_file_path):
        with open(log_file_path, "w", encoding="utf-8") as f:
            f.write("")  # 파일 내용 비우기

    # 로깅 설정
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.FileHandler(log_file_path, encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )


setup_server_logging()
logger = logging.getLogger(__name__)


class ServerManager:
    """서버 실행 관리 클래스"""

    def __init__(self):
        self.processes = []
        self.running = True

    def run_mcp_server(self):
        """MCP 서버 실행"""
        try:
            logger.info("🛠️  MCP 도구 서버 시작 중... (포트 8001)")
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
                    logger.info(f"[MCP] {line.strip()}")
                else:
                    break

        except Exception as e:
            logger.error(f"❌ MCP 서버 실행 실패: {str(e)}")

    def run_api_server(self):
        """API 서버 실행"""
        try:
            # MCP 서버가 시작될 시간을 줌
            time.sleep(3)

            logger.info("🚀 FastAPI 서버 시작 중... (포트 8000)")
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
                    logger.info(f"[API] {line.strip()}")
                else:
                    break

        except Exception as e:
            logger.error(f"❌ API 서버 실행 실패: {str(e)}")

    def signal_handler(self, signum, frame):
        """시그널 핸들러 (Ctrl+C 처리)"""
        logger.info("\n🛑 서버 종료 신호 수신...")
        self.stop_servers()
        sys.exit(0)

    def stop_servers(self):
        """모든 서버 중지"""
        self.running = False
        logger.info("🔄 서버들을 종료하는 중...")

        for process in self.processes:
            if process.poll() is None:  # 프로세스가 아직 실행 중인 경우
                try:
                    process.terminate()
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()

        logger.info("✅ 모든 서버가 종료되었습니다.")

    def run(self):
        """서버들 실행"""
        # 시그널 핸들러 등록
        signal.signal(signal.SIGINT, self.signal_handler)

        logger.info("=" * 60)
        logger.info("🚀 클라우드 거버넌스 AI 서비스 시작")
        logger.info("=" * 60)
        logger.info("📌 실행 중인 서버:")
        logger.info("   • MCP 도구 서버: http://localhost:8001")
        logger.info("   • FastAPI 서버: http://localhost:8000")
        logger.info("")
        logger.info("💡 API 테스트:")
        logger.info("   curl -X POST http://localhost:8000/chat \\")
        logger.info("        -H 'Content-Type: application/json' \\")
        logger.info('        -d \'{"query": "클라우드 보안 정책에 대해 알려주세요"}\'')
        logger.info("")
        logger.info("🛑 종료하려면 Ctrl+C를 누르세요")
        logger.info("=" * 60)

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
                logger.info("\n🛑 사용자에 의해 중단됨")
            except Exception as e:
                logger.error(f"\n❌ 서버 실행 중 오류: {str(e)}")
            finally:
                self.stop_servers()


def check_dependencies():
    """의존성 확인"""
    try:
        import fastapi
        import uvicorn
        import httpx
        from fastmcp import FastMCP

        logger.info("✅ 모든 의존성이 설치되어 있습니다.")
        return True
    except ImportError as e:
        logger.error(f"❌ 의존성 누락: {str(e)}")
        logger.info("🔧 해결 방법: pip install -r requirements.txt")
        return False


def check_environment():
    """환경 설정 확인"""
    required_vars = ["AOAI_API_KEY", "AOAI_ENDPOINT", "AOAI_API_VERSION"]
    missing_vars = []

    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)

    if missing_vars:
        logger.error(f"❌ 환경 변수 누락: {', '.join(missing_vars)}")
        logger.info(
            "🔧 해결 방법: .env 파일을 생성하고 Azure OpenAI 설정을 입력하세요."
        )
        return False

    logger.info("✅ 환경 설정이 완료되어 있습니다.")
    return True


def check_aoai():
    try:
        llm = get_llm()
        logger.info("✅ LLM 인스턴스 생성 성공")

        # 간단한 테스트 호출
        response = llm.invoke("안녕하세요")
        logger.info("✅ LLM 호출 성공")
        logger.info(f"응답 타입: {type(response)}")
        logger.info(f"응답 내용: {response.content[:50]}...")

        return True

    except Exception as e:
        logger.error(f"LLM 연결 오류: {e}")
        import traceback

        traceback.print_exc()

        return False


def main():
    """메인 실행 함수"""
    logger.info("🔍 시스템 사전 확인 중...")

    # 의존성 확인
    if not check_dependencies():
        return 1
    # 환경 설정 확인
    if not check_environment():
        return 1

    if not check_aoai():
        return 1

    # 서버 실행
    manager = ServerManager()
    manager.run()

    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
클라우드 거버넌스 AI 서비스 FastAPI 서버

사용자 입력을 받아 처리하는 API 엔드포인트를 제공합니다.
"""

import sys
import os
from typing import Dict, Any, Generator
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from watchfiles import DefaultFilter
import logging
from contextlib import asynccontextmanager
import json
from uvicorn import Config, Server

# 현재 디렉토리를 Python 패스에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from orchestrator import CloudGovernanceOrchestrator

# 로그 디렉토리 생성
log_dir = "log"
if not os.path.exists(log_dir):
    os.makedirs(log_dir)


# 로깅 설정 강화
def setup_logging():
    """로깅 설정"""
    # 로그 파일 경로
    log_file_path = os.path.join(log_dir, "api_server.log")

    # 서버 시작 시마다 로그 파일 초기화
    if os.path.exists(log_file_path):
        with open(log_file_path, "w", encoding="utf-8") as f:
            f.write("")  # 파일 내용 비우기

    # 루트 로거 설정
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    # 기존 핸들러 제거
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # 로그 포맷 설정
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # 파일 핸들러 추가
    file_handler = logging.FileHandler(log_file_path, encoding="utf-8")
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)

    # 콘솔 핸들러 추가
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    # 루트 로거에 핸들러 추가
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)


# 로깅 설정 실행
setup_logging()
logger = logging.getLogger(__name__)

# 오케스트레이터 인스턴스 (전역)
orchestrator = None


class IgnoreLogsFilter(DefaultFilter):
    def __call__(self, change, path):
        # logs 디렉토리 내 파일은 감시 제외
        if "/logs/" in path or path.endswith(".log"):
            return False
        return super().__call__(change, path)


class UserInput(BaseModel):
    """사용자 입력 요청 모델"""

    query: str
    options: Dict[str, Any] = {}


def startup_event():
    """서버 시작 시 초기화"""
    global orchestrator
    try:
        logger.info("🔧 클라우드 거버넌스 AI 시스템 초기화 중...")
        orchestrator = CloudGovernanceOrchestrator()
        logger.info("✅ 시스템 초기화 완료")
    except Exception as e:
        logger.error(f"❌ 시스템 초기화 실패: {str(e)}")
        raise


@asynccontextmanager
async def lifespan(app: FastAPI):
    startup_event()
    yield


# FastAPI 앱 초기화
app = FastAPI(
    title="클라우드 거버넌스 AI 서비스",
    description="클라우드 거버넌스 관련 질문 답변 및 슬라이드 생성 AI 서비스",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS 미들웨어 추가
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 모든 origin 허용 (개발용)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """루트 엔드포인트"""
    return {
        "message": "클라우드 거버넌스 AI 서비스",
        "version": "1.0.0",
        "status": "running",
    }


@app.get("/health")
async def health_check():
    """헬스 체크 엔드포인트"""
    try:
        status = orchestrator.get_system_status()
        return {
            "status": "healthy",
            "system_status": status,
            "timestamp": get_timestamp(),
        }
    except Exception as e:
        logger.error(f"헬스 체크 실패: {str(e)}")
        raise HTTPException(status_code=500, detail="시스템 상태 확인 실패")


@app.post("/chat")
async def process_user_input(user_input: UserInput):
    """
    사용자 입력 처리 엔드포인트 (스트리밍 응답)

    모든 요청을 스트리밍 방식으로 처리합니다.
    """
    try:
        logger.info(f"📨 사용자 요청 수신: {user_input.query[:50]}...")

        if not user_input.query.strip():
            raise HTTPException(status_code=400, detail="질문을 입력해주세요.")

        # RouterAgent를 통해 의도 먼저 분석
        router_result = orchestrator.router_agent({"user_input": user_input.query})
        intent = router_result.get("intent", "general")

        logger.info(f"🎯 감지된 의도: {intent}")
        logger.info("📊 스트리밍 응답으로 처리")

        def generate_streaming_response() -> Generator[str, None, None]:
            try:
                # 스트리밍 처리 시작 신호
                start_chunk = {
                    "type": "start",
                    "message": "요청 처리를 시작합니다...",
                    "timestamp": get_timestamp(),
                    "intent": intent,
                }
                yield f"data: {json.dumps(start_chunk, ensure_ascii=False)}\n\n"

                # 오케스트레이터를 통한 스트리밍 처리
                for chunk in orchestrator.process_request_streaming(user_input.query):
                    chunk_data = {"timestamp": get_timestamp(), "chunk": chunk}
                    yield f"data: {json.dumps(chunk_data, ensure_ascii=False)}\n\n"

                # 스트림 종료 신호
                final_chunk = {
                    "type": "stream_end",
                    "message": "처리가 완료되었습니다.",
                    "timestamp": get_timestamp(),
                }
                yield f"data: {json.dumps(final_chunk, ensure_ascii=False)}\n\n"

            except Exception as e:
                error_chunk = {
                    "type": "error",
                    "message": f"스트리밍 처리 중 오류: {str(e)}",
                    "error": str(e),
                    "timestamp": get_timestamp(),
                }
                yield f"data: {json.dumps(error_chunk, ensure_ascii=False)}\n\n"

        return StreamingResponse(
            generate_streaming_response(),
            media_type="text/plain",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Content-Type": "text/plain; charset=utf-8",
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 요청 처리 실패: {str(e)}")

        def generate_error_stream():
            error_response = {
                "type": "error",
                "message": f"요청 처리 중 오류가 발생했습니다: {str(e)}",
                "error": str(e),
                "timestamp": get_timestamp(),
            }
            yield f"data: {json.dumps(error_response, ensure_ascii=False)}\n\n"

        return StreamingResponse(
            generate_error_stream(),
            media_type="text/plain",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Content-Type": "text/plain; charset=utf-8",
            },
        )


@app.get("/system/status")
async def get_system_status():
    """시스템 상태 조회 엔드포인트"""
    try:
        status = orchestrator.get_system_status()
        return {"success": True, "data": status, "timestamp": get_timestamp()}
    except Exception as e:
        logger.error(f"시스템 상태 조회 실패: {str(e)}")
        raise HTTPException(status_code=500, detail="시스템 상태 조회 실패")


def get_timestamp() -> str:
    """현재 타임스탬프 반환"""
    from datetime import datetime

    return datetime.now().isoformat()


if __name__ == "__main__":

    logger.info("=" * 60)
    logger.info("🚀 클라우드 거버넌스 AI FastAPI 서버 시작")
    logger.info("=" * 60)
    logger.info("📊 사용 가능한 엔드포인트:")
    logger.info("   • POST /chat: 통합 질문 답변 및 스트리밍 응답")
    logger.info("   • GET /health: 헬스 체크")
    logger.info("   • GET /system/status: 시스템 상태")
    logger.info("=" * 60)
    logger.info("💡 모든 요청이 스트리밍 방식으로 처리됩니다.")
    logger.info("=" * 60)

    config = Config(
        "api_server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        reload_excludes=["log/*"],
        log_level="info",
    )
    server = Server(config)
    server.run()

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
import logging
from contextlib import asynccontextmanager
import json

# 현재 디렉토리를 Python 패스에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from orchestrator import CloudGovernanceOrchestrator

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 오케스트레이터 인스턴스 (전역)
orchestrator = None


class UserInput(BaseModel):
    """사용자 입력 요청 모델"""

    query: str
    options: Dict[str, Any] = {}
    stream: bool = False  # 스트리밍 응답 요청 여부


class ApiResponse(BaseModel):
    """API 응답 모델"""

    success: bool
    data: Dict[str, Any] = {}
    message: str = ""
    timestamp: str


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
    사용자 입력 처리 엔드포인트 (스트리밍 및 일반 응답 지원)

    슬라이드 생성 요청이거나 stream=True인 경우 스트리밍 응답을 제공합니다.
    """
    try:
        logger.info(f"📨 사용자 요청 수신: {user_input.query[:50]}...")

        if not user_input.query.strip():
            raise HTTPException(status_code=400, detail="질문을 입력해주세요.")

        # RouterAgent를 통해 의도 먼저 분석
        router_result = orchestrator.router_agent({"user_input": user_input.query})
        intent = router_result.get("intent", "general")

        logger.info(f"🎯 감지된 의도: {intent}")

        # 슬라이드 생성 요청이거나 명시적으로 스트리밍을 요청한 경우
        if intent == "slide_generation" or user_input.stream:
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
                    for chunk in orchestrator.process_request_streaming(
                        user_input.query
                    ):
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

        else:
            # 일반 요청의 경우 기존 동기 방식으로 처리
            logger.info("💬 일반 응답으로 처리")
            result = orchestrator.process_request(user_input.query)

            logger.info("✅ 요청 처리 완료")

            return ApiResponse(
                success=True,
                data=result,
                message="요청이 성공적으로 처리되었습니다.",
                timestamp=get_timestamp(),
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 요청 처리 실패: {str(e)}")

        # 스트리밍 요청에서 오류가 발생한 경우
        try:
            router_intent = (
                router_result.get("intent")
                if "router_result" in locals()
                else "unknown"
            )
        except:
            router_intent = "unknown"

        if user_input.stream or router_intent == "slide_generation":

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
        else:
            return ApiResponse(
                success=False,
                data={},
                message=f"요청 처리 중 오류가 발생했습니다: {str(e)}",
                timestamp=get_timestamp(),
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
    import uvicorn

    print("=" * 60)
    print("🚀 클라우드 거버넌스 AI FastAPI 서버 시작")
    print("=" * 60)
    print("📊 사용 가능한 엔드포인트:")
    print("   • POST /chat: 통합 질문 답변 및 스트리밍 슬라이드 생성")
    print("   • GET /health: 헬스 체크")
    print("   • GET /system/status: 시스템 상태")
    print("=" * 60)
    print("💡 슬라이드 생성 요청 시 자동으로 스트리밍 응답으로 처리됩니다.")
    print("💡 stream=true 옵션으로 강제 스트리밍 응답도 가능합니다.")
    print("=" * 60)

    uvicorn.run(
        "api_server:app", host="0.0.0.0", port=8000, reload=True, log_level="info"
    )

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
클라우드 거버넌스 AI 서비스 FastAPI 서버

사용자 입력을 받아 처리하는 API 엔드포인트를 제공합니다.
"""

import sys
import os
from typing import Dict, Any
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import logging

# 현재 디렉토리를 Python 패스에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from orchestrator import CloudGovernanceOrchestrator

# FastAPI 앱 초기화
app = FastAPI(
    title="클라우드 거버넌스 AI 서비스",
    description="클라우드 거버넌스 관련 질문 답변 및 슬라이드 생성 AI 서비스",
    version="1.0.0",
)

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 오케스트레이터 인스턴스 (전역)
orchestrator = None


class UserInput(BaseModel):
    """사용자 입력 요청 모델"""

    query: str
    options: Dict[str, Any] = {}


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


@app.post("/chat", response_model=ApiResponse)
async def process_user_input(user_input: UserInput):
    """사용자 입력 처리 엔드포인트"""
    try:
        logger.info(f"📨 사용자 요청 수신: {user_input.query[:50]}...")

        if not user_input.query.strip():
            raise HTTPException(status_code=400, detail="질문을 입력해주세요.")

        # 오케스트레이터를 통한 요청 처리
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
    startup_event()

    uvicorn.run(
        "api_server:app", host="0.0.0.0", port=8000, reload=True, log_level="info"
    )

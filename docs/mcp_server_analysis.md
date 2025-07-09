# 📘 클라우드 거버넌스 AI Tool 서비스 기술 문서 (Fast MCP 기반)

## 1. 서비스 개요

클라우드 거버넌스 AI Tool 서비스는 **Fast MCP(Model Context Protocol)** 기반으로 구축된 AI 도구 서버입니다. 이 서버는 다양한 AI Agent들이 클라우드 거버넌스 관련 작업을 수행할 수 있도록 다음과 같은 핵심 기능들을 MCP 프로토콜을 통해 제공합니다:

- **RAG 기반 문서 검색**: 클라우드 거버넌스 관련 질문에 대한 벡터 검색 및 하이브리드 검색
- **보고서 요약**: 클라우드 전환 제안서 구조에 맞는 체계적인 요약 생성
- **슬라이드 초안 생성**: RAG 검색 결과를 기반으로 한 프레젠테이션 슬라이드 초안 작성
- **상태 관리**: AI Agent들의 실행 상태 및 공유 데이터 관리

AI Agent들은 MCP 클라이언트를 통해 이 서버의 도구들을 호출하여 슬라이드 생성, 거버넌스 질의 응답, 보고서 작성 등의 복합적인 작업을 수행할 수 있습니다.

## 2. Tool 구조 및 역할

`mcp_server.py`에서 등록되어 사용되는 모든 MCP Tool들의 상세 기능은 다음과 같습니다:

### 🛠 Tool: `search_documents` (RAGRetrieverTool)

- **목적**: ChromaDB 기반 RAG 검색을 통한 클라우드 거버넌스 관련 문서 검색
- **입력값**:
  - `query` (string): 검색할 질문이나 키워드
  - `top_k` (int, 기본값: 5): 반환할 최대 결과 개수
- **출력값**: 검색 결과 리스트와 관련 메타데이터
- **주요 기능**:
  - 벡터 검색, 키워드 검색, 하이브리드 검색 지원
  - 적응형 검색 방법 자동 선택
  - 도메인 특화 키워드 사전 활용
- **사용 시나리오**: 슬라이드 생성 또는 질의 응답의 기반 자료 추출

### 🛠 Tool: `summarize_report` (ReportSummaryTool)

- **목적**: 클라우드 전환 제안서 구조에 맞는 체계적인 보고서 요약 생성
- **입력값**:
  - `content` (string): 요약할 보고서 내용
  - `title` (string, 기본값: "클라우드 전환 제안서"): 보고서 제목
- **출력값**: 14개 섹션으로 구조화된 제안서 요약 데이터
- **주요 구조**:
  - 제안 개요, 필요성, 대상 시스템, 전환 전략
  - 단계별 로드맵, 방법론, 자동화 계획
  - 아키텍처 설계, 운영 방안, 규제 대응
  - 프로젝트 관리, Exit Plan, 인력 계획, 기대효과
- **사용 시나리오**: 복잡한 클라우드 전환 프로젝트 제안서의 체계적 정리

### 🛠 Tool: `create_slide_draft` (SlideDraftTool)

- **목적**: RAG 검색 결과와 사용자 입력을 기반으로 한 슬라이드 초안 생성
- **입력값**:
  - `search_results` (List[Dict]): RAG 검색 결과 리스트
  - `user_input` (string): 사용자 입력 텍스트
- **출력값**: 마크다운 형식의 슬라이드 초안 데이터
- **주요 기능**:
  - 검색 결과에서 핵심 내용 자동 추출
  - LLM을 활용한 논리적 슬라이드 구성
  - 5개 슬라이드로 구성된 완전한 프레젠테이션 초안
- **사용 시나리오**: 클라우드 거버넌스 관련 프레젠테이션 자료 준비

### 🛠 Tool: `get_tool_status`

- **목적**: MCP 도구 서버의 현재 상태 확인
- **입력값**: 없음
- **출력값**: 서버 상태 정보 (도구 가용성, 버전, 타임스탬프 등)
- **사용 시나리오**: 서버 모니터링 및 헬스체크

## 3. 주요 파일 및 모듈 설명

### 핵심 서버 파일

- **`mcp_server.py`**: Fast MCP 서버의 메인 파일로 모든 도구들을 MCP 프로토콜로 노출

### 도구 구현 파일들 (`tools/` 디렉토리)

- **`rag_retriever.py`**: ChromaDB 기반 RAG 검색 도구의 핵심 로직

  - 벡터/키워드/하이브리드 검색 알고리즘 구현
  - 쿼리 분석 및 적응형 검색 방법 선택
  - 관련성 점수 계산 및 결과 최적화

- **`report_summary.py`**: 클라우드 전환 제안서 요약 기능

  - 14개 섹션별 내용 분석 및 추출
  - 키워드 기반 섹션 매칭 알고리즘
  - 구조화된 제안서 포맷 생성

- **`slide_draft.py`**: 슬라이드 초안 생성 기능

  - 검색 결과에서 핵심 내용 추출
  - LLM 기반 슬라이드 구성 및 내용 생성
  - 마크다운 형식 출력 처리

- **`slide_generator.py`**: HTML 슬라이드 생성 도구 (Python 기반)

  - LLM을 활용한 완전한 HTML 슬라이드 생성
  - slide_draft 결과를 기반으로 시각적 슬라이드 제작
  - MCP 도구가 아닌 Python 기반 독립 도구

- **`reasoning_trace_logger.py`**: ReAct 추론 과정 추적 도구

  - Agent별 Thought-Action-Observation 추적
  - 글로벌 워크플로우 trace 관리
  - 추론 과정 요약 및 분석

- **`plan_revision_tool.py`**: 실행 계획 수정 도구

  - 실패한 단계에 대한 대안 계획 생성
  - 복구 단계 추가 및 도구 대체
  - 실행 이력 관리

- **`state_manager.py`**: Agent 상태 및 공유 데이터 관리
  - 병렬 실행 시 상태 동기화
  - Agent 간 의존성 관리
  - 공유 데이터 저장소 제공

### 핵심 모듈 (`core/` 디렉토리)

- **`base_tool.py`**: 모든 도구의 기본 인터페이스

  - 추상 클래스로 `run(inputs: dict) -> dict` 메서드 정의
  - 모든 도구가 상속받는 기본 구조

- **`settings.py`**: 설정 및 LLM/임베딩 모델 관리

  - Azure OpenAI와 Claude LLM 설정
  - 임베딩 모델 (text-embedding-3-small) 설정
  - 환경변수 기반 설정 관리

- **`search_engine.py`**: 검색 엔진 핵심 로직 (RAG 도구에서 활용)

## 4. Tool 등록 및 MCP 구조 흐름

### MCP Tool 등록 과정

```
1. 도구 인스턴스 생성
   rag_retriever = RAGRetrieverTool()
   report_summary = ReportSummaryTool()
   slide_draft = SlideDraftTool()
        ↓
2. FastMCP 데코레이터를 통한 함수 등록
   @mcp.tool
   async def search_documents(query: str, top_k: int = 5):
        ↓
3. Fast MCP 서버 시작
   mcp.run(transport="streamable-http", host="127.0.0.1", port=8001)
        ↓
4. HTTP 엔드포인트로 노출
   http://127.0.0.1:8001/tools
```

### 호출 흐름도

```
AI Agent (MCP Client)
        ↓ HTTP Request
Fast MCP Server (mcp_server.py)
        ↓ Function Call
Tool Wrapper Functions (@mcp.tool)
        ↓ Method Call
Tool Instances (RAGRetrieverTool, etc.)
        ↓ Core Logic
BaseTool.run(inputs) Implementation
        ↓ External Services
ChromaDB / LLM APIs / File System
        ↓ Response
JSON Result with mcp_context
```

### 상세 실행 흐름

1. **초기화 단계** (`startup()` 함수)

   - 각 도구 인스턴스 생성 및 초기화
   - ChromaDB 연결 확인
   - LLM 및 임베딩 모델 설정 검증

2. **요청 수신**

   - AI Agent가 HTTP POST 요청으로 도구 호출
   - FastMCP가 요청을 파싱하고 해당 함수로 라우팅

3. **도구 실행**

   - 래퍼 함수가 도구 인스턴스의 `run()` 메서드 호출
   - 각 도구별 비즈니스 로직 실행
   - 오류 처리 및 로깅

4. **응답 반환**
   - 표준화된 JSON 형식으로 결과 반환
   - `mcp_context` 메타데이터 포함

## 5. 사용 예시

### 예시 1: RAG 기반 문서 검색

```python
# 입력
{
    "query": "클라우드 보안 정책 수립 방안",
    "top_k": 3
}

# 처리 흐름
1. 쿼리 분석 → 복잡도 평가 → 검색 방법 선택 (하이브리드)
2. ChromaDB에서 벡터 검색 + 키워드 검색 병행
3. 관련성 점수 재계산 → 최적 결과 선별

# 출력
{
    "results": [
        {
            "content": "클라우드 보안 정책은...",
            "metadata": {"source": "governance_policy.pdf"},
            "score": 0.92
        }
    ],
    "mcp_context": {
        "role": "retriever",
        "status": "success",
        "search_method": "hybrid"
    }
}
```

### 예시 2: 슬라이드 초안 생성

```python
# 입력
{
    "search_results": [검색 결과 리스트],
    "user_input": "클라우드 거버넌스 프레임워크 소개"
}

# 처리 흐름
1. 검색 결과에서 핵심 내용 추출 (키워드 필터링)
2. LLM 프롬프트 구성 → Claude/GPT-4o 호출
3. 마크다운 형식 슬라이드 초안 생성

# 출력
{
    "draft": {
        "markdown_content": "# 슬라이드 1\n주제: 거버넌스 개요\n내용: ...",
        "format": "markdown_raw"
    },
    "mcp_context": {
        "role": "slide_drafter",
        "status": "success",
        "content_length": 1500
    }
}
```

### 예시 3: 보고서 요약

```python
# 입력
{
    "content": "클라우드 전환 프로젝트 상세 내용...",
    "title": "AWS 클라우드 전환 제안서"
}

# 처리 흐름
1. 마크다운 헤더 기준 섹션 분리
2. 14개 표준 섹션별 키워드 매칭
3. 각 섹션별 핵심 내용 추출 및 요약

# 출력
{
    "summary": {
        "overview": "AWS 클라우드 전환을 통한...",
        "necessity": "기존 인프라의 확장성 한계...",
        "target_systems": "웹 서비스, 데이터베이스...",
        ...
    },
    "mcp_context": {
        "role": "report_summarizer",
        "status": "success"
    }
}
```

## 6. 기술적 특징

### MCP 프로토콜 기반 설계

- **표준화된 인터페이스**: 모든 도구가 동일한 MCP 프로토콜을 통해 노출
- **언어 독립적**: Python 외 다른 언어로 작성된 Agent도 HTTP API로 접근 가능
- **확장성**: 새로운 도구 추가 시 `@mcp.tool` 데코레이터만으로 간단히 등록

### 로깅 및 모니터링

- **구조화된 로깅**: 각 도구별 상세 실행 로그 기록
- **파일 기반 로깅**: `log/mcp_server.log`에 모든 활동 기록
- **성능 메트릭**: 검색 시간, 캐시 히트율 등 통계 수집

### 오류 처리

- **단계별 예외 처리**: 초기화, 실행, 응답 각 단계별 오류 처리
- **Graceful Degradation**: 일부 도구 실패 시에도 서버 전체는 정상 동작
- **표준화된 오류 응답**: `mcp_context`에 오류 정보 포함

이 문서는 Fast MCP 기반 클라우드 거버넌스 AI Tool 서비스의 전체 아키텍처와 각 컴포넌트의 역할을 상세히 설명하여, 개발자들이 시스템을 이해하고 확장할 수 있도록 구성되었습니다.

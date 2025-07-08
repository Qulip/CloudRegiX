# CloudRegiX - 클라우드 거버넌스 AI 시스템

![CloudRegiX Logo](https://img.shields.io/badge/CloudRegiX-v1.0-blue.svg)
![Python](https://img.shields.io/badge/Python-3.12+-green.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

## 🌟 프로젝트 개요

**CloudRegiX**는 클라우드 거버넌스를 위한 하이브리드 AI 시스템입니다. Plan & Execute와 ReAct(Reasoning and Acting) 방식을 결합하여 복잡한 클라우드 거버넌스 질문에 답변하고, 프레젠테이션 자료를 생성합니다.

## 🎯 핵심 특징

- **🔄 하이브리드 AI**: Plan & Execute + ReAct 방식 결합
- **🤖 멀티 에이전트**: 5개 전문 에이전트의 협업
- **⚡ 풀링 처리**: ReAct Executor 풀을 통한 효율적 작업 관리 (최대 5개)
- **🛡️ 자동 복구**: 실패 상황 감지 및 복구
- **📊 실시간 추적**: 전체 추론 과정 로깅 및 분석
- **🔗 MCP 프로토콜**: FastMCP 기반 도구 통합

## 📁 프로젝트 구조

```
CloudRegiX/
├── agents/                     # AI 에이전트 모음
│   ├── router_agent.py         # 사용자 의도 분석
│   ├── planner_agent.py        # 실행 계획 수립
│   ├── react_executor_agent.py # ReAct 방식 실행
│   ├── trace_manager_agent.py  # 추론 과정 분석
│   └── answer_agent.py         # 최종 응답 생성
├── core/                       # 기본 클래스 및 설정
│   ├── base_agent.py          # 에이전트 기본 클래스
│   ├── base_tool.py           # 도구 기본 클래스
│   ├── settings.py            # 시스템 설정
│   ├── search_engine.py       # 검색 엔진 코어
│   ├── stream_agent.py        # 스트리밍 에이전트
│   └── standalone_vectorization.py # 독립 벡터화
├── tools/                      # 시스템 도구 모음
│   ├── state_manager.py       # 상태 관리
│   ├── reasoning_trace_logger.py # 추론 로거
│   ├── plan_revision_tool.py  # 계획 수정
│   ├── rag_retriever.py       # RAG 기반 정보 검색
│   ├── report_summary.py      # 보고서 생성 및 요약
│   ├── slide_generator.py     # LangChain 슬라이드 생성
│   └── slide_draft.py         # MCP 슬라이드 초안
├── streamlit/                  # 웹 UI
│   └── main.py                # Streamlit 앱
├── data/                       # 데이터 저장소
│   └── vectorstore/           # ChromaDB 벡터 저장소
├── docs/                       # 기술 문서
│   ├── api_server_analysis.md
│   └── mcp_server_analysis.md
├── orchestrator.py            # 메인 오케스트레이터
├── api_server.py              # FastAPI 서버
├── mcp_server.py              # FastMCP 서버
├── mcp_client.py              # MCP 클라이언트
├── start_servers.py           # 서버 통합 실행
└── requirements.txt           # 종속성
```

### 폴더별 역할

#### 📂 `agents/` - AI 에이전트

- **RouterAgent**: 사용자 의도 분석 및 분류 (question/slide_generation/general)
- **PlannerAgent**: 하이브리드 실행 계획 수립 및 단계 분해
- **ReActExecutorAgent**: ReAct 방식으로 개별 단계 실행 (풀링 방식 관리)
- **TraceManagerAgent**: 전체 실행 과정 추론 분석 및 평가
- **AnswerAgent**: 최종 사용자 응답 생성 및 포맷팅

#### 📂 `core/` - 기본 구조

- **BaseAgent**: 모든 에이전트의 추상 기본 클래스
- **BaseTool**: 도구들의 기본 인터페이스
- **settings**: Azure OpenAI 및 Claude LLM, 임베딩 설정 관리
- **search_engine**: ChromaDB 기반 검색 엔진
- **stream_agent**: 스트리밍 응답 처리

#### 📂 `tools/` - 지원 도구

- **StateManager**: 시스템 상태 추적 및 관리
- **ReasoningTraceLogger**: 추론 과정 로깅
- **PlanRevisionTool**: 실행 계획 동적 수정
- **RAGRetriever**: ChromaDB 기반 하이브리드 문서 검색
- **ReportSummary**: 클라우드 전환 제안서 생성 및 요약
- **SlideGenerator**: LangChain 기반 HTML 슬라이드 생성
- **SlideDraft**: MCP 도구 기반 슬라이드 초안 생성

#### 📂 `streamlit/` - 웹 인터페이스

- 통합된 사용자 친화적인 웹 UI 제공
- 실시간 스트리밍으로 슬라이드 생성
- API 서버와 연동하여 원활한 사용자 경험 제공

## 🤖 에이전트 아키텍처

### 전체 시스템 구조

```mermaid
graph TB
    subgraph "사용자 인터페이스"
        UI[Streamlit UI]
        API[FastAPI]
        Direct[Direct API]
    end

    subgraph "CloudGovernanceOrchestrator"
        Orchestrator[메인 오케스트레이터]
    end

    subgraph "AI 에이전트"
        Router[RouterAgent<br/>의도 분석]
        Planner[PlannerAgent<br/>계획 수립]
        ExecutorPool[ReActExecutor Pool<br/>최대 5개 풀링]
        TraceManager[TraceManagerAgent<br/>추론 분석]
        Answer[AnswerAgent<br/>응답 생성]
    end

    subgraph "도구 계층"
        StateManager[상태 관리]
        Logger[추론 로거]
        Revision[계획 수정]
        RAG[RAG 검색]
        Report[보고서 생성]
        Slide[슬라이드 생성]
    end

    subgraph "FastMCP 서버"
        MCP[FastMCP Tools Server]
    end

    subgraph "데이터 저장소"
        ChromaDB[ChromaDB<br/>벡터 저장소]
    end

    UI --> Orchestrator
    API --> Orchestrator
    Direct --> Orchestrator

    Orchestrator --> Router
    Router --> Planner
    Planner --> ExecutorPool
    ExecutorPool --> TraceManager
    TraceManager --> Answer

    ExecutorPool --> StateManager
    ExecutorPool --> Logger
    ExecutorPool --> RAG
    ExecutorPool --> Report
    ExecutorPool --> Slide

    TraceManager --> Revision

    RAG --> MCP
    Report --> MCP
    Slide --> MCP
    RAG --> ChromaDB
```

### 하이브리드 처리 흐름

```mermaid
flowchart TD
    Start[사용자 요청] --> Router[RouterAgent<br/>의도 분석]

    Router --> |intent, confidence| Planner[PlannerAgent<br/>실행 계획 수립]

    Planner --> |execution_steps| Strategy{실행 전략}

    Strategy --> |hybrid_react| Hybrid[하이브리드 실행]
    Strategy --> |legacy| Legacy[레거시 처리]

    Hybrid --> Pool[ReActExecutor Pool<br/>풀링 관리]

    subgraph "ReAct 사이클"
        Pool --> Think[Think<br/>상황 분석]
        Think --> Act[Act<br/>도구 실행]
        Act --> Observe[Observe<br/>결과 관찰]
        Observe --> Check{목표 달성?}
        Check -->|No, <5회| Think
        Check -->|Yes| Complete[실행 완료]
    end

    Complete --> Trace[TraceManagerAgent<br/>추론 분석]
    Legacy --> Trace

    Trace --> Assess{성공 여부}

    Assess -->|Success| Final[AnswerAgent<br/>최종 응답]
    Assess -->|Retry| Recovery[실패 복구]
    Assess -->|Revise| Revision[계획 수정]

    Recovery --> Pool
    Revision --> Planner

    Final --> End[사용자 응답]
```

### 에이전트 데이터 흐름

```mermaid
sequenceDiagram
    participant U as 사용자
    participant O as Orchestrator
    participant R as Router
    participant P as Planner
    participant E as Executor Pool
    participant T as TraceManager
    participant A as Answer

    U->>O: 사용자 입력
    O->>R: 의도 분석 요청
    R->>R: NLP 처리
    R-->>O: {intent, confidence, entities}

    O->>P: 계획 수립 요청
    P->>P: 단계 분해 및 의존성 분석
    P-->>O: {execution_steps, strategy}

    O->>E: 풀링 방식 실행 시작
    loop ReAct 반복 (최대 5회)
        E->>E: Think (상황 분석)
        E->>E: Act (도구 실행)
        E->>E: Observe (결과 관찰)
    end
    E-->>O: {execution_results}

    O->>T: 추론 과정 분석
    T->>T: 성공/실패 분석
    T-->>O: {trace_analysis, recommendations}

    alt 실패 복구 필요
        O->>E: 재실행
        E-->>O: 복구 결과
    end

    O->>A: 최종 응답 생성
    A->>A: 결과 종합 및 포맷팅
    A-->>O: {final_response}
    O-->>U: 완성된 응답
```

## 🚀 시작하기

### 필요 조건

```bash
Python 3.12+
```

### 설치 및 실행

```bash
# 저장소 클론
git clone <repository-url>
cd CloudRegiX

# 종속성 설치
pip install -r requirements.txt

# 환경 변수 설정 (.env 파일 생성)
AOAI_API_KEY=your_azure_openai_api_key
AOAI_ENDPOINT=your_azure_openai_endpoint
AOAI_API_VERSION=2024-10-01-preview
ANTHROPIC_API_KEY=your_anthropic_api_key

# 1. 백엔드 서버 시작 (필수)
python start_servers.py

# 2. 웹 UI 시작 (별도 터미널에서)
cd streamlit
python run_streamlit.py

# 또는 개별 실행
python api_server.py              # FastAPI 서버 (8000번 포트)
python mcp_server.py              # FastMCP 서버 (8001번 포트)
streamlit run streamlit/main.py   # Streamlit UI (8501번 포트)
```

## 🔧 사용법

### 웹 UI

1. 브라우저에서 `http://localhost:8501` 접속
2. **통합 홈페이지**: 전반적인 서비스 소개 및 질의응답
   - 슬라이드 생성: "슬라이드 만들어줘", "프레젠테이션 자료" 등
   - 일반 질문: 클라우드 거버넌스 관련 질의응답
   - 실시간 진행 상황 표시
   - 완성된 슬라이드 미리보기 및 다운로드

### REST API

```bash
curl -X POST "http://localhost:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{"query": "클라우드 보안 정책에 대해 설명해주세요"}'
```

### 직접 API 호출

```python
from orchestrator import CloudGovernanceOrchestrator

orchestrator = CloudGovernanceOrchestrator()
result = orchestrator.process_request_streaming("클라우드 거버넌스 슬라이드를 만들어주세요")
for chunk in result:
    print(chunk)
```

## 🧪 테스트

```bash
# LLM 연결 테스트
python test_llm_direct.py

# 벡터 데이터베이스 독립 실행
python core/standalone_vectorization.py
```

## 🛠️ 기술 스택

- **AI Framework**: LangChain, OpenAI GPT-4o, Claude Sonnet-4
- **벡터 검색**: ChromaDB (하이브리드 검색 지원)
- **웹 Framework**: FastAPI, Streamlit
- **프로토콜**: FastMCP (Model Context Protocol)
- **임베딩**: Azure OpenAI text-embedding-3-small (1536차원)
- **언어**: Python 3.12+

## 📊 주요 기능

### 지원하는 요청 유형

1. **질문 답변**: 클라우드 거버넌스 관련 질문
2. **슬라이드 생성**: HTML 형식의 프레젠테이션 자료 생성
3. **일반 대화**: 기본적인 상호작용

### 처리 성능

- **평균 응답 시간**: 3-20초 (복잡도에 따라)
- **풀링 처리**: 최대 5개 ReAct Executor 풀링 관리
- **자동 복구**: 실패 시 최대 5회 재시도
- **벡터 검색**: ChromaDB 기반 하이브리드 검색

## 📝 라이선스

MIT 라이선스

## 🤝 기여하기

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

_CloudRegiX - 클라우드 거버넌스를 위한 지능형 AI 시스템_ 🚀

# 클라우드 거버넌스 자동화 AI - 웹 인터페이스

클라우드 거버넌스 자동화 AI의 웹 인터페이스입니다. API 서버와 연동하여 실시간 스트리밍으로 슬라이드를 생성할 수 있습니다.

## ✨ 주요 기능

- **홈페이지**: 전반적인 서비스 소개 및 간단한 질의응답
- **AI 슬라이드**: 실시간 스트리밍으로 슬라이드 생성
  - 사용자 요청에 따른 자동 슬라이드 생성
  - 실시간 진행 상황 표시
  - 생성된 슬라이드 미리보기 및 다운로드
- **AI 거버넌스**: 거버넌스 관련 기능 (예정)

## 📋 요구사항

```txt
streamlit==1.45.1
requests==2.31.0
```

## 🛠️ 설치 및 실행

### 1. 전체 시스템 실행 (권장)

루트 디렉토리에서 백엔드 API 서버를 먼저 실행:

```bash
# 의존성 설치
pip install -r requirements.txt

# API 서버 실행 (MCP 서버 포함)
python start_servers.py
```

별도 터미널에서 웹 앱 실행:

```bash
cd streamlit
python run_streamlit.py
```

### 2. 웹 앱만 실행

```bash
cd streamlit
streamlit run main.py --server.port=8501
```

### 3. 접속 방법

- **웹 앱**: http://localhost:8501
- **API 서버**: http://localhost:8000 (백엔드)

## 🎯 사용 방법

### AI 슬라이드 생성

1. **홈페이지에서**: "슬라이드" 키워드가 포함된 질문 입력 → 자동으로 AI 슬라이드 페이지로 이동
2. **AI 슬라이드 페이지에서**: 직접 슬라이드 요청 입력

**예시 질문:**

- "클라우드 보안 정책에 대한 슬라이드를 만들어줘"
- "AWS 거버넌스 프레임워크 슬라이드 생성"
- "컴플라이언스 체크리스트 발표 자료"

### 스트리밍 기능

- 실시간 진행 상황 표시
- 단계별 처리 과정 확인
- 완료 즉시 슬라이드 미리보기

## 📁 프로젝트 구조

```
streamlit/
├── main.py                    # 메인 Streamlit 애플리케이션
├── run_streamlit.py          # 실행 스크립트
├── README.md                 # 이 파일
└── .streamlit/
    └── config.toml           # Streamlit 설정
```

## 🔧 API 연동

웹 앱은 다음 API와 연동됩니다:

- `POST /chat`: 통합 질문 답변 및 스트리밍 슬라이드 생성
- `GET /health`: 서버 상태 확인
- `GET /system/status`: 시스템 상태 조회

## 🐛 문제 해결

### API 서버 연결 오류

```bash
# API 서버가 실행 중인지 확인
curl http://localhost:8000/health
```

### 패키지 설치 오류

```bash
# 가상환경 생성 후 설치
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r ../requirements.txt
```

### CORS 오류

API 서버에서 CORS가 활성화되어 있어야 합니다 (이미 설정됨).

## 📝 개발자 노트

- Streamlit의 실시간 업데이트를 위해 `st.empty()` placeholder 사용
- API 스트리밍 응답을 `requests.post(..., stream=True)`로 처리
- 세션 상태를 통한 페이지 간 데이터 전달

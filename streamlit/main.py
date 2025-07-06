import streamlit as st
import requests
import json
import time
import asyncio
import uuid
from typing import Dict, Any

# 페이지 설정
st.set_page_config(
    page_title="클라우드 거버넌스 자동화 AI",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# 세션 상태 초기화
if "slide_content" not in st.session_state:
    st.session_state.slide_content = ""
if "slide_html" not in st.session_state:
    st.session_state.slide_html = ""
if "is_processing" not in st.session_state:
    st.session_state.is_processing = False
if "progress" not in st.session_state:
    st.session_state.progress = 0.0
if "status_message" not in st.session_state:
    st.session_state.status_message = ""
if "slide_query" not in st.session_state:
    st.session_state.slide_query = ""
if "general_response" not in st.session_state:
    st.session_state.general_response = ""
if "chat_response" not in st.session_state:
    st.session_state.chat_response = ""
if "response_intent" not in st.session_state:
    st.session_state.response_intent = ""

# API 서버 URL 설정
API_BASE_URL = "http://localhost:8000"


def check_api_server():
    """API 서버 상태 확인"""
    try:
        url = f"{API_BASE_URL}/health"
        print(f"[DEBUG] API 서버 상태 확인 URL: {url}")

        response = requests.get(url, timeout=5)
        print(f"[DEBUG] 서버 상태 확인 응답: {response.status_code}")

        if response.status_code == 200:
            print(f"[DEBUG] 서버 정상 응답: {response.text[:200]}")
            return True
        else:
            print(f"[DEBUG] 서버 오류 응답: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"[DEBUG] 서버 연결 실패: {str(e)}")
        return False


# 커스텀 CSS
st.markdown(
    """
<style>
    /* 전체 배경 */
    .stApp {
        background-color: #1a1a1a;
    }
    
    /* 메인 컨테이너 */
    .main .block-container {
        padding-top: 2rem;
        padding-left: 2rem;
        padding-right: 2rem;
        max-width: none;
    }
    
    /* 사이드바 스타일 */
    .css-1d391kg {
        background-color: #1a1a1a;
        border-right: 1px solid #333;
    }
    
    .css-1lcbmhc {
        background-color: #1a1a1a;
    }
    
    /* 사이드바 메뉴 항목 */
    .sidebar-item {
        display: flex;
        align-items: center;
        padding: 12px 16px;
        margin: 4px 0;
        border-radius: 8px;
        color: #b3b3b3;
        cursor: pointer;
        transition: all 0.2s ease;
        text-decoration: none;
    }
    
    .sidebar-item:hover {
        background-color: #2a2a2a;
        color: #ffffff;
    }
    
    .sidebar-item.active {
        background-color: #333;
        color: #ffffff;
    }
    
    .sidebar-item .icon {
        margin-right: 12px;
        font-size: 16px;
    }
    
    /* 메인 타이틀 */
    .main-title {
        color: #ffffff;
        font-size: 2.5rem;
        font-weight: 600;
        text-align: center;
        margin: 3rem 0 2rem 0;
    }
    
    /* 메인 페이지 설명 텍스트 */
    .main-description {
        color: #b3b3b3;
        font-size: 1.2rem;
        text-align: center;
        margin: 2rem 0 3rem 0;
        line-height: 1.6;
    }
    
    /* 입력 영역 */
    .input-container {
        display: flex;
        justify-content: center;
        margin: 2rem 0;
    }
    
    .input-container-fixed {
        position: fixed;
        bottom: 2rem;
        left: 50%;
        transform: translateX(-50%);
        width: 90%;
        max-width: 800px;
        z-index: 1000;
    }
    
    .input-box {
        background-color: #2a2a2a;
        border: 1px solid #404040;
        border-radius: 12px;
        padding: 16px 20px;
        color: #ffffff;
        width: 100%;
        max-width: 600px;
        font-size: 16px;
        outline: none;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
    }
    
    .input-box::placeholder {
        color: #888888;
    }
    
    .input-box:focus {
        border-color: #666666;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.5);
    }
    
    /* 오른쪽 미리보기 영역 */
    .preview-container {
        background-color: #2a2a2a;
        border-radius: 12px;
        padding: 1.5rem;
        height: 60vh;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        border: 1px solid #404040;
    }
    
    .preview-title {
        color: #ffffff;
        font-size: 1.2rem;
        font-weight: 500;
        margin-bottom: 1rem;
    }
    
    .preview-icon {
        font-size: 3rem;
        color: #666666;
        margin-bottom: 1rem;
    }
    
    .preview-text {
        color: #888888;
        font-size: 0.9rem;
        text-align: center;
        line-height: 1.5;
    }
    
    /* 로고 영역 */
    .logo-container {
        display: flex;
        align-items: center;
        padding: 1rem 1rem 1.5rem 1rem;
        border-bottom: 1px solid #333;
        margin-bottom: 1rem;
    }
    
    .logo-text {
        color: #ffffff;
        font-size: 1.2rem;
        font-weight: 600;
        margin-left: 0.5rem;
    }
    
    /* 하단 액션 버튼들 */
    .action-buttons {
        display: flex;
        align-items: center;
        gap: 12px;
        margin-left: 12px;
    }
    
    .action-btn {
        background: none;
        border: none;
        color: #888888;
        padding: 8px;
        border-radius: 6px;
        cursor: pointer;
        transition: all 0.2s ease;
    }
    
    .action-btn:hover {
        background-color: #2a2a2a;
        color: #ffffff;
    }
    
    /* 전송 버튼 */
    .send-btn {
        background-color: #333;
        border: none;
        color: #ffffff;
        padding: 8px 12px;
        border-radius: 6px;
        cursor: pointer;
        margin-left: auto;
        transition: all 0.2s ease;
    }
    
    .send-btn:hover {
        background-color: #444;
    }
    
    /* 폼 버튼 높이 조정 및 정렬 */
    .stForm button {
        height: 2.5rem;
        margin-top: 1.5rem;
    }
    
    /* 입력창과 버튼 정렬 */
    .stForm [data-testid="column"] {
        display: flex;
        align-items: end;
    }
    
    /* Streamlit 기본 요소 숨기기 */
    #MainMenu {visibility: hidden;}
    .stDeployButton {display:none;}
    footer {visibility: hidden;}
    .stApp > header {visibility: hidden;}
    
    /* 사이드바 닫기 버튼 숨기기 */
    .css-1rs6os .css-17lntkn {
        display: none;
    }
    
    /* 사이드바 토글 버튼 스타일 */
    .css-1rs6os .css-1lsmgbg {
        background-color: #333;
        color: #ffffff;
    }
    
    /* 사이드바 내 버튼 스타일 */
    .css-1d391kg button[data-testid="baseButton-secondary"] {
        background: none;
        border: none;
        color: #b3b3b3;
        padding: 12px 16px;
        margin: 4px 0;
        border-radius: 8px;
        width: 100%;
        text-align: left;
        transition: all 0.2s ease;
        font-size: 14px;
        font-weight: normal;
    }
    
    .css-1d391kg button[data-testid="baseButton-secondary"]:hover {
        background-color: #2a2a2a;
        color: #ffffff;
    }
    
    .css-1d391kg button[data-testid="baseButton-secondary"]:focus {
        box-shadow: none;
        outline: none;
    }
</style>
""",
    unsafe_allow_html=True,
)

# 사이드바 구성
with st.sidebar:
    st.markdown(
        """
    <div class="logo-container">
        <span style="font-size: 1.5rem;">🤖</span>
        <span class="logo-text">클라우드 거버넌스 자동화 AI</span>
    </div>
    """,
        unsafe_allow_html=True,
    )

    # 홈 메뉴만 표시
    st.markdown(
        """
        <div class="sidebar-item active">
            <span class="icon">🏠</span>
            <span>홈</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


# 메인 페이지 함수 (AI 슬라이드 기능 통합)
def show_main_page():
    # placeholder 변수들을 먼저 선언 (None으로 초기화)
    chat_response_placeholder = None
    slide_preview_placeholder = None

    # 메인 타이틀
    st.markdown(
        """
    <div class="main-title">
        클라우드 거버넌스 자동화 AI
    </div>
    """,
        unsafe_allow_html=True,
    )

    # 초기 안내 텍스트 placeholder
    guide_text_placeholder = st.empty()

    # 초기 안내 텍스트 (응답이나 슬라이드가 없을 때만 표시)
    if (
        not st.session_state.chat_response
        and not st.session_state.slide_html
        and not st.session_state.is_processing
    ):
        with guide_text_placeholder.container():
            st.markdown(
                """
            <div class="main-description">
                AI 기반 클라우드 거버넌스 자동화 솔루션입니다.<br>
                슬라이드 생성, 거버넌스 관리 등 다양한 기능을 제공합니다.<br>
                아래 입력창에 원하시는 작업을 입력해주세요.
            </div>
            """,
                unsafe_allow_html=True,
            )

    # API 서버 상태 표시 (연결 실패시만)
    server_status = check_api_server()
    if not server_status:
        st.error(f"❌ API 서버 연결 안됨 ({API_BASE_URL})")

    # 홈에서 넘어온 질문이 있으면 기본값으로 설정
    default_value = ""
    if hasattr(st.session_state, "slide_query") and st.session_state.slide_query:
        default_value = st.session_state.slide_query
        st.session_state.slide_query = ""  # 사용 후 초기화

    # 슬라이드 미리보기 영역 (상단)
    slide_preview_placeholder = st.empty()

    # 현재 슬라이드가 있으면 표시
    if st.session_state.slide_html:
        with slide_preview_placeholder.container():
            st.markdown("### 📊 슬라이드 미리보기")
            # HTML 슬라이드 표시
            st.components.v1.html(
                st.session_state.slide_html, height=600, scrolling=True
            )

            # 다운로드 버튼
            st.download_button(
                label="📥 HTML 다운로드",
                data=st.session_state.slide_html,
                file_name="slide.html",
                mime="text/html",
                key=f"slide_download_main_{int(time.time())}",
            )

    # 채팅 응답 표시 영역 (슬라이드 아래)
    chat_response_placeholder = st.empty()

    # 현재 채팅 응답이 있으면 표시
    if st.session_state.chat_response:
        with chat_response_placeholder.container():
            st.markdown("### 💬 응답")
            st.info(st.session_state.chat_response)

    # 진행 상황 표시용 placeholder
    progress_placeholder = st.empty()
    status_placeholder = st.empty()

    # 현재 상태 표시
    if st.session_state.is_processing:
        progress_placeholder.progress(st.session_state.progress)
        status_placeholder.info(st.session_state.status_message)
    elif st.session_state.status_message:
        if "오류" in st.session_state.status_message:
            status_placeholder.error(st.session_state.status_message)
        elif "완료" in st.session_state.status_message:
            status_placeholder.success(st.session_state.status_message)
        else:
            status_placeholder.info(st.session_state.status_message)

    # 공백으로 여백 생성
    st.markdown("<br>" * 2, unsafe_allow_html=True)

    # 입력 폼 (하단에 위치)
    st.markdown("### 💭 질문하기")
    with st.form(key="main_form", clear_on_submit=True):
        col_input, col_btn = st.columns([5, 1])

        with col_input:
            user_input = st.text_input(
                "질문을 입력하세요",
                value=default_value,
                placeholder="무엇을 도와드릴까요? (예: 슬라이드 생성, 거버넌스 설정 등)",
                key="main_input",
                label_visibility="collapsed",
            )

        with col_btn:
            submit_button = st.form_submit_button(
                "전송", type="primary", use_container_width=True
            )

    # 폼 제출 처리
    if submit_button:
        if not user_input.strip():
            st.error("질문을 입력해주세요.")
        elif st.session_state.is_processing:
            st.warning("이미 처리 중입니다. 잠시만 기다려주세요.")
        else:
            # API 서버 상태 확인
            if not check_api_server():
                st.error(
                    f"🚨 API 서버에 연결할 수 없습니다. 서버가 실행 중인지 확인해주세요.\n서버 URL: {API_BASE_URL}"
                )
            else:
                # 폼 제출 직후 바로 처리 시작
                handle_slide_request(
                    user_input,
                    progress_placeholder,
                    status_placeholder,
                    slide_preview_placeholder,
                    chat_response_placeholder,
                    guide_text_placeholder,
                )


# API 호출 함수들
def send_chat_request(query: str, stream: bool = True) -> Dict[str, Any]:
    """
    API 서버에 채팅 요청을 보내는 함수

    Args:
        query: 사용자 질문
        stream: 스트리밍 응답 여부

    Returns:
        API 응답 결과
    """
    try:
        url = f"{API_BASE_URL}/chat"
        payload = {"query": query, "stream": stream, "options": {}}

        # 디버깅을 위한 로깅
        print(f"[DEBUG] API 요청 URL: {url}")
        print(f"[DEBUG] API 요청 데이터: {payload}")

        if stream:
            # 스트리밍 요청
            response = requests.post(
                url,
                json=payload,
                stream=True,
                headers={"Content-Type": "application/json"},
                timeout=60,
            )
            print(f"[DEBUG] 응답 상태 코드: {response.status_code}")
            print(f"[DEBUG] 응답 헤더: {dict(response.headers)}")

            # 응답 상태 확인
            if response.status_code != 200:
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}: {response.text}",
                }

            return {"success": True, "response": response}
        else:
            # 일반 요청
            response = requests.post(
                url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=30,
            )
            print(f"[DEBUG] 응답 상태 코드: {response.status_code}")

            # 응답 상태 확인
            if response.status_code != 200:
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}: {response.text}",
                }

            return {"success": True, "data": response.json()}

    except Exception as e:
        print(f"[DEBUG] API 요청 오류: {str(e)}")
        return {"success": False, "error": str(e)}


def process_streaming_response(
    response,
    progress_placeholder,
    status_placeholder,
    slide_placeholder=None,
    chat_placeholder=None,
    guide_placeholder=None,
) -> None:
    """
    스트리밍 응답을 처리하는 함수

    Args:
        response: requests 응답 객체
        progress_placeholder: 진행률 표시용 placeholder
        status_placeholder: 상태 메시지 표시용 placeholder
        slide_placeholder: 슬라이드 즉시 표시용 placeholder (선택적)
        chat_placeholder: 채팅 응답 즉시 표시용 placeholder (선택적)
        guide_placeholder: 초기 안내 텍스트 placeholder (선택적)
    """
    try:
        slide_data = None
        chat_answer = ""
        intent = ""
        line_count = 0

        def display_slide(html_content):
            """슬라이드 표시 함수"""
            if html_content and slide_placeholder:
                # 기본 안내 텍스트 숨기기
                if guide_placeholder:
                    guide_placeholder.empty()

                # 슬라이드 표시
                with slide_placeholder.container():
                    st.markdown("### 📊 슬라이드 미리보기")
                    st.components.v1.html(
                        html_content,
                        height=600,
                        scrolling=True,
                    )
                    st.download_button(
                        label="📥 HTML 다운로드",
                        data=html_content,
                        file_name="slide.html",
                        mime="text/html",
                        key=f"slide_download_{uuid.uuid4().hex[:8]}",
                    )
                print(f"[DEBUG] 슬라이드 화면 표시 완료")

        def extract_slide_html(data):
            """다양한 데이터 구조에서 슬라이드 HTML 추출"""
            if not data:
                return None

            # 직접 html 키가 있는 경우
            if isinstance(data, dict) and "html" in data:
                return data["html"]

            # 중첩된 구조에서 html 찾기
            if isinstance(data, dict):
                for key in ["data", "result", "final_result", "content"]:
                    if key in data:
                        nested_data = data[key]
                        if isinstance(nested_data, dict) and "html" in nested_data:
                            return nested_data["html"]
                        elif isinstance(nested_data, str):
                            try:
                                parsed = json.loads(nested_data)
                                if isinstance(parsed, dict) and "html" in parsed:
                                    return parsed["html"]
                            except:
                                pass

            return None

        print(f"[DEBUG] 스트리밍 응답 처리 시작")
        for line in response.iter_lines(decode_unicode=True):
            line_count += 1
            if line_count <= 5:  # 처음 5줄만 출력
                print(f"[DEBUG] 응답 라인 {line_count}: {line[:100]}")

            if line and line.startswith("data: "):
                try:
                    json_data = json.loads(line[6:])  # "data: " 제거
                    data_type = json_data.get("type", "unknown")
                    print(f"[DEBUG] 파싱된 JSON 데이터 타입: {data_type}")
                    if data_type in ["answer", "result"]:
                        print(f"[DEBUG] 상세 데이터: {json_data}")

                    # 시작 신호에서 intent 파악
                    if json_data.get("type") == "start":
                        intent = json_data.get("intent", "")
                        st.session_state.response_intent = intent
                        print(f"[DEBUG] 감지된 의도: {intent}")

                    # 진행 상황 업데이트 (직접 타입)
                    if json_data.get("type") == "progress":
                        progress = json_data.get("progress", 0.0)
                        message = json_data.get("message", "")
                        st.session_state.progress = progress
                        st.session_state.status_message = message

                        # 실시간 UI 업데이트
                        progress_placeholder.progress(progress)
                        status_placeholder.info(message)
                        time.sleep(0.1)

                    # chunk 내 진행 상황 업데이트
                    elif (
                        "chunk" in json_data
                        and json_data["chunk"].get("type") == "progress"
                    ):
                        chunk_data = json_data["chunk"]
                        progress = chunk_data.get("progress", 0.0)
                        message = chunk_data.get("message", "")
                        st.session_state.progress = progress
                        st.session_state.status_message = message

                        # 실시간 UI 업데이트
                        progress_placeholder.progress(progress)
                        status_placeholder.info(message)
                        time.sleep(0.1)

                    # chunk 데이터 내에서 결과 처리
                    elif "chunk" in json_data:
                        chunk_data = json_data.get("chunk", {})

                        # 답변 텍스트 처리
                        if chunk_data.get("type") == "answer":
                            answer_text = chunk_data.get("content", "")
                            if answer_text:
                                chat_answer = answer_text
                                st.session_state.chat_response = chat_answer
                                print(
                                    f"[DEBUG] 답변 텍스트 저장: {answer_text[:100]}..."
                                )

                                # 기본 안내 텍스트 숨기기
                                if guide_placeholder:
                                    guide_placeholder.empty()

                                # 채팅 응답을 즉시 표시
                                if chat_placeholder:
                                    with chat_placeholder.container():
                                        st.markdown("### 💬 응답")
                                        st.info(answer_text)
                                    print(f"[DEBUG] 답변 즉시 화면 표시 완료")

                        # 결과 데이터 처리
                        elif chunk_data.get("type") == "result":
                            chunk_result = chunk_data.get("data", {})
                            if chunk_result:
                                slide_data = chunk_result
                                print(
                                    f"[DEBUG] 결과 데이터 저장: {str(chunk_result)[:100]}..."
                                )

                                # HTML 추출 및 즉시 표시
                                slide_html = extract_slide_html(chunk_result)
                                if slide_html:
                                    st.session_state.slide_html = slide_html
                                    st.session_state.slide_content = str(chunk_result)
                                    print(f"[DEBUG] 슬라이드 HTML 즉시 저장 완료")
                                    display_slide(slide_html)

                        # 도구 실행 결과 처리
                        elif (
                            chunk_data.get("type") == "tool_execution"
                            and "chunk_data" in chunk_data
                        ):
                            nested_chunk = chunk_data.get("chunk_data", {})
                            if nested_chunk.get("type") == "result":
                                nested_result = nested_chunk.get("data", {})
                                if nested_result:
                                    slide_data = nested_result
                                    print(
                                        f"[DEBUG] 도구 실행 결과 저장: {str(nested_result)[:100]}..."
                                    )

                                    # HTML 추출 및 즉시 표시
                                    slide_html = extract_slide_html(nested_result)
                                    if slide_html:
                                        st.session_state.slide_html = slide_html
                                        st.session_state.slide_content = str(
                                            nested_result
                                        )
                                        print(
                                            f"[DEBUG] 도구 실행 결과에서 슬라이드 HTML 즉시 저장 완료"
                                        )
                                        display_slide(slide_html)
                            elif nested_chunk.get("type") == "progress":
                                message = nested_chunk.get("message", "")
                                st.session_state.status_message = message
                                status_placeholder.info(message)
                                time.sleep(0.1)

                    # 도구 실행 결과 (직접 타입)
                    elif json_data.get("type") == "tool_execution":
                        chunk_data = json_data.get("chunk_data", {})
                        if chunk_data.get("type") == "result":
                            result_data = chunk_data.get("data", {})
                            if result_data:
                                slide_data = result_data
                                # HTML 추출 및 즉시 표시
                                slide_html = extract_slide_html(result_data)
                                if slide_html:
                                    st.session_state.slide_html = slide_html
                                    st.session_state.slide_content = str(result_data)
                                    print(
                                        f"[DEBUG] 직접 도구 실행 결과에서 슬라이드 HTML 저장 완료"
                                    )
                                    display_slide(slide_html)
                        elif chunk_data.get("type") == "progress":
                            message = chunk_data.get("message", "")
                            st.session_state.status_message = message
                            status_placeholder.info(message)
                            time.sleep(0.1)

                    # 최종 결과
                    elif json_data.get("type") == "result":
                        final_data = json_data.get("data", {})
                        if final_data:
                            slide_data = final_data
                            # HTML 추출 및 즉시 표시
                            slide_html = extract_slide_html(final_data)
                            if slide_html:
                                st.session_state.slide_html = slide_html
                                st.session_state.slide_content = str(final_data)
                                print(f"[DEBUG] 최종 결과에서 슬라이드 HTML 저장 완료")
                                display_slide(slide_html)
                            else:
                                # 슬라이드가 아닌 일반 답변인 경우
                                if isinstance(final_data, str):
                                    chat_answer = final_data
                                elif isinstance(final_data, dict):
                                    # 딕셔너리에서 답변 추출
                                    chat_answer = final_data.get("final_answer")
                                else:
                                    chat_answer = str(final_data)

                                if chat_answer:
                                    st.session_state.chat_response = chat_answer
                                    print(
                                        f"[DEBUG] 일반 답변 저장: {chat_answer[:100]}..."
                                    )

                                    # 기본 안내 텍스트 숨기기
                                    if guide_placeholder:
                                        guide_placeholder.empty()

                                    # 채팅 응답을 즉시 표시
                                    if chat_placeholder:
                                        with chat_placeholder.container():
                                            st.markdown("### 💬 응답")
                                            st.info(chat_answer)
                                        print(f"[DEBUG] 일반 답변 즉시 화면 표시 완료")

                    # 직접 답변 타입 처리
                    elif json_data.get("type") == "answer":
                        answer_content = json_data.get("content", "") or json_data.get(
                            "message", ""
                        )
                        if answer_content:
                            chat_answer = answer_content
                            st.session_state.chat_response = chat_answer
                            print(f"[DEBUG] 직접 답변 저장: {answer_content[:100]}...")

                            # 기본 안내 텍스트 숨기기
                            if guide_placeholder:
                                guide_placeholder.empty()

                            # 채팅 응답을 즉시 표시
                            if chat_placeholder:
                                with chat_placeholder.container():
                                    st.markdown("### 💬 응답")
                                    st.info(answer_content)
                                print(f"[DEBUG] 직접 답변 즉시 화면 표시 완료")

                    # 오류 처리
                    elif json_data.get("type") == "error":
                        error_msg = f"오류: {json_data.get('message', 'Unknown error')}"
                        st.session_state.status_message = error_msg
                        st.session_state.is_processing = False
                        status_placeholder.error(error_msg)
                        return

                except json.JSONDecodeError:
                    continue

        # 최종 처리
        print(
            f"[DEBUG] 최종 처리 - intent: {intent}, chat_answer: {chat_answer[:100] if chat_answer else 'None'}, slide_data: {slide_data is not None}"
        )

        # 슬라이드 데이터 최종 처리 (스트리밍 중에 표시되지 않은 경우)
        if slide_data and not st.session_state.slide_html:
            print(f"[DEBUG] 최종 슬라이드 데이터 처리: {slide_data}")

            # HTML 추출
            slide_html = extract_slide_html(slide_data)
            if slide_html:
                st.session_state.slide_html = slide_html
                st.session_state.slide_content = str(slide_data)
                print(f"[DEBUG] 최종 슬라이드 HTML 저장 완료")
                display_slide(slide_html)
            else:
                print(
                    f"[DEBUG] 슬라이드 HTML을 찾을 수 없음 - 데이터 구조: {list(slide_data.keys()) if isinstance(slide_data, dict) else type(slide_data)}"
                )

        # 채팅 답변 처리
        if chat_answer:
            st.session_state.chat_response = chat_answer
            print(f"[DEBUG] 채팅 답변 저장 완료")

            # 기본 안내 텍스트 숨기기
            if guide_placeholder:
                guide_placeholder.empty()

            # 채팅 응답을 즉시 표시
            if chat_placeholder:
                with chat_placeholder.container():
                    st.markdown("### 💬 응답")
                    st.info(chat_answer)
                print(f"[DEBUG] 채팅 응답 즉시 화면 표시 완료")

        elif slide_data:
            # 슬라이드 생성 시에도 답변 텍스트 저장
            answer_text = None
            if isinstance(slide_data, str):
                answer_text = slide_data
            elif isinstance(slide_data, dict):
                # 다양한 키에서 답변 추출
                answer_text = (
                    slide_data.get("final_answer")
                    or slide_data.get("answer")
                    or slide_data.get("response")
                    or slide_data.get("content")
                    or slide_data.get("message")
                )
                # 슬라이드가 없는 일반 응답인 경우에만 전체 데이터 사용
                if not answer_text and not st.session_state.slide_html:
                    answer_text = str(slide_data)
            else:
                answer_text = str(slide_data)

            if answer_text:
                st.session_state.chat_response = answer_text
                print(f"[DEBUG] 답변 텍스트 저장 완료")

                # 기본 안내 텍스트 숨기기
                if guide_placeholder:
                    guide_placeholder.empty()

                # 답변을 즉시 표시
                if chat_placeholder:
                    with chat_placeholder.container():
                        st.markdown("### 💬 응답")
                        st.info(answer_text)
                    print(f"[DEBUG] 답변 즉시 화면 표시 완료")

        st.session_state.progress = 1.0

        # 응답 유형에 따른 완료 메시지
        if st.session_state.slide_html:
            st.session_state.status_message = "슬라이드 생성이 완료되었습니다!"
            completion_message = "슬라이드 생성이 완료되었습니다!"
        elif st.session_state.chat_response:
            st.session_state.status_message = "응답이 완료되었습니다!"
            completion_message = "응답이 완료되었습니다!"
        else:
            # 답변이 없는 경우에도 적절한 메시지 표시
            st.session_state.status_message = "처리가 완료되었습니다!"
            completion_message = "처리가 완료되었습니다!"

            # 답변이 전혀 없는 경우 기본 메시지 표시
            if not chat_answer and not slide_data:
                default_message = "요청을 처리했지만 응답을 받지 못했습니다."
                st.session_state.chat_response = default_message

                # 기본 안내 텍스트 숨기기
                if guide_placeholder:
                    guide_placeholder.empty()

                if chat_placeholder:
                    with chat_placeholder.container():
                        st.markdown("### 💬 응답")
                        st.warning(default_message)
                    print(f"[DEBUG] 기본 메시지 표시 완료")

        st.session_state.is_processing = False

        # 최종 UI 업데이트
        progress_placeholder.progress(1.0)
        status_placeholder.success(completion_message)

        print(f"[DEBUG] 스트리밍 처리 완료")

    except Exception as e:
        error_msg = f"스트리밍 처리 중 오류: {str(e)}"
        st.session_state.status_message = error_msg
        st.session_state.is_processing = False
        status_placeholder.error(error_msg)


def handle_slide_request(
    query: str,
    progress_placeholder,
    status_placeholder,
    slide_placeholder=None,
    chat_placeholder=None,
    guide_placeholder=None,
) -> None:
    """
    슬라이드 요청을 처리하는 함수

    Args:
        query: 사용자 질문
        progress_placeholder: 진행률 표시용 placeholder
        status_placeholder: 상태 메시지 표시용 placeholder
        slide_placeholder: 슬라이드 즉시 표시용 placeholder (선택적)
        chat_placeholder: 채팅 응답 즉시 표시용 placeholder (선택적)
        guide_placeholder: 초기 안내 텍스트 placeholder (선택적)
    """
    if not query.strip():
        status_placeholder.error("질문을 입력해주세요.")
        return

    # 상태 초기화
    st.session_state.is_processing = True
    st.session_state.progress = 0.0
    st.session_state.status_message = "요청을 처리하고 있습니다..."
    st.session_state.slide_html = ""
    st.session_state.slide_content = ""
    st.session_state.chat_response = ""
    st.session_state.response_intent = ""

    # 초기 상태 표시
    progress_placeholder.progress(0.0)
    status_placeholder.info("요청을 처리하고 있습니다...")

    try:
        # API 요청 보내기
        result = send_chat_request(query, stream=True)

        if result["success"]:
            # 스트리밍 응답 처리
            process_streaming_response(
                result["response"],
                progress_placeholder,
                status_placeholder,
                slide_placeholder,
                chat_placeholder,
                guide_placeholder,
            )
        else:
            error_msg = f"API 요청 실패: {result['error']}"
            st.session_state.status_message = error_msg
            st.session_state.is_processing = False
            status_placeholder.error(error_msg)
    except Exception as e:
        error_msg = f"요청 처리 중 예상치 못한 오류: {str(e)}"
        st.session_state.status_message = error_msg
        st.session_state.is_processing = False
        status_placeholder.error(error_msg)


# 메인 페이지 표시
show_main_page()

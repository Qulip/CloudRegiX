import streamlit as st
import requests
import json
import time
import asyncio
from typing import Dict, Any

# 페이지 설정
st.set_page_config(
    page_title="클라우드 거버넌스 자동화 AI",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# 세션 상태 초기화
if "current_page" not in st.session_state:
    st.session_state.current_page = "홈"
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


# 페이지 네비게이션 함수
def navigate_to_page(page_name):
    st.session_state.current_page = page_name
    st.rerun()


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

    # 메뉴 항목들
    menu_items = [
        ("🏠", "홈"),
        ("📊", "AI 슬라이드"),
        ("🌐", "AI 거버넌스"),
    ]

    for item in menu_items:
        is_active = st.session_state.current_page == item[1]
        if is_active:
            st.markdown(
                f"""
            <div class="sidebar-item active">
                <span class="icon">{item[0]}</span>
                <span>{item[1]}</span>
            </div>
            """,
                unsafe_allow_html=True,
            )
        else:
            # 클릭 가능한 메뉴 항목
            if st.button(
                f"{item[0]} {item[1]}",
                key=f"nav_{item[1]}",
                use_container_width=True,
                type="secondary",
            ):
                navigate_to_page(item[1])


# 메인 페이지 함수
def show_main_page():
    # 메인 타이틀
    st.markdown(
        """
    <div class="main-title">
        클라우드 거버넌스 자동화 AI
    </div>
    """,
        unsafe_allow_html=True,
    )

    # 설명 텍스트
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

    # 입력 폼
    with st.form(key="main_form", clear_on_submit=True):
        col1, col2, col3 = st.columns([1, 6, 1])
        with col2:
            col_input, col_btn = st.columns([5, 1])

            with col_input:
                user_input = st.text_input(
                    "질문을 입력하세요",
                    placeholder="무엇을 도와드릴까요? (예: 슬라이드 생성, 거버넌스 설정 등)",
                    key="main_input",
                    label_visibility="collapsed",
                )

            with col_btn:
                submit_button = st.form_submit_button(
                    "전송", type="primary", use_container_width=True
                )

    # 폼 제출 처리 - 슬라이드 관련 요청이면 슬라이드 페이지로 이동
    if submit_button and user_input:
        # 간단한 의도 분석
        slide_keywords = ["슬라이드", "발표", "프레젠테이션", "slide", "presentation"]
        if any(keyword in user_input.lower() for keyword in slide_keywords):
            st.session_state.current_page = "AI 슬라이드"
            st.session_state.slide_query = user_input  # 질문을 저장
            st.rerun()
        else:
            # 일반 질문은 간단한 답변 표시
            st.info(
                f"'{user_input}' 질문을 받았습니다. 해당 기능은 곧 추가될 예정입니다. 슬라이드 생성을 원하시면 '슬라이드'라는 키워드를 포함해주세요."
            )

    # 공백 추가
    st.markdown("<br>" * 3, unsafe_allow_html=True)


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
    response, progress_placeholder, status_placeholder
) -> None:
    """
    스트리밍 응답을 처리하는 함수

    Args:
        response: requests 응답 객체
        progress_placeholder: 진행률 표시용 placeholder
        status_placeholder: 상태 메시지 표시용 placeholder
    """
    try:
        slide_data = None
        line_count = 0

        print(f"[DEBUG] 스트리밍 응답 처리 시작")
        for line in response.iter_lines(decode_unicode=True):
            line_count += 1
            if line_count <= 5:  # 처음 5줄만 출력
                print(f"[DEBUG] 응답 라인 {line_count}: {line[:100]}")

            if line and line.startswith("data: "):
                try:
                    json_data = json.loads(line[6:])  # "data: " 제거
                    print(f"[DEBUG] 파싱된 JSON 데이터: {json_data}")

                    # 진행 상황 업데이트 (직접 타입)
                    if json_data.get("type") == "progress":
                        progress = json_data.get("progress", 0.0)
                        message = json_data.get("message", "")
                        st.session_state.progress = progress
                        st.session_state.status_message = message

                        # 실시간 UI 업데이트
                        progress_placeholder.progress(progress)
                        status_placeholder.info(message)
                        # 강제로 UI 업데이트
                        time.sleep(0.1)  # 작은 딜레이로 UI 업데이트 시간 확보

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

                    # 도구 실행 결과
                    elif json_data.get("type") == "tool_execution":
                        chunk_data = json_data.get("chunk_data", {})
                        if chunk_data.get("type") == "result":
                            result_data = chunk_data.get("data", {})
                            if not slide_data and result_data:
                                slide_data = result_data
                        elif chunk_data.get("type") == "progress":
                            message = chunk_data.get("message", "")
                            st.session_state.status_message = message
                            status_placeholder.info(message)
                            time.sleep(0.1)

                    # 최종 결과
                    elif json_data.get("type") == "result":
                        final_data = json_data.get("data", {})
                        if not slide_data and final_data:
                            slide_data = final_data

                    # chunk 데이터 내에서 결과 처리
                    elif "chunk" in json_data:
                        chunk_data = json_data.get("chunk", {})
                        if chunk_data.get("type") == "result":
                            chunk_result = chunk_data.get("data", {})
                            if not slide_data and chunk_result:
                                slide_data = chunk_result
                        elif (
                            chunk_data.get("type") == "tool_execution"
                            and "chunk_data" in chunk_data
                        ):
                            # 중첩된 tool_execution 처리
                            nested_chunk = chunk_data.get("chunk_data", {})
                            if nested_chunk.get("type") == "result":
                                nested_result = nested_chunk.get("data", {})
                                if not slide_data and nested_result:
                                    slide_data = nested_result

                    # 오류 처리
                    elif json_data.get("type") == "error":
                        error_msg = f"오류: {json_data.get('message', 'Unknown error')}"
                        st.session_state.status_message = error_msg
                        st.session_state.is_processing = False
                        status_placeholder.error(error_msg)
                        return

                except json.JSONDecodeError:
                    continue

        # 응답 데이터 처리
        if slide_data:
            print(f"[DEBUG] 최종 slide_data: {slide_data}")

            # 슬라이드 HTML이 있는지 확인
            if "html" in slide_data:
                st.session_state.slide_html = slide_data["html"]
                st.session_state.slide_content = str(slide_data)
                st.session_state.general_response = ""  # 일반 응답 초기화
            elif "data" in slide_data and "html" in slide_data["data"]:
                st.session_state.slide_html = slide_data["data"]["html"]
                st.session_state.slide_content = str(slide_data)
                st.session_state.general_response = ""  # 일반 응답 초기화
            else:
                # 슬라이드가 아닌 일반 응답인 경우
                if "final_answer" in slide_data:
                    st.session_state.general_response = slide_data["final_answer"]
                elif "answer" in slide_data:
                    st.session_state.general_response = slide_data["answer"]
                elif "response" in slide_data:
                    st.session_state.general_response = slide_data["response"]
                else:
                    st.session_state.general_response = str(slide_data)
                st.session_state.slide_html = ""  # 슬라이드 초기화
                st.session_state.slide_content = ""

        st.session_state.progress = 1.0

        # 응답 유형에 따른 완료 메시지
        if st.session_state.slide_html:
            st.session_state.status_message = "슬라이드 생성이 완료되었습니다!"
            completion_message = "슬라이드 생성이 완료되었습니다!"
        elif st.session_state.general_response:
            st.session_state.status_message = "응답이 완료되었습니다!"
            completion_message = "응답이 완료되었습니다!"
        else:
            st.session_state.status_message = "처리가 완료되었습니다!"
            completion_message = "처리가 완료되었습니다!"

        st.session_state.is_processing = False

        # 최종 UI 업데이트
        progress_placeholder.progress(1.0)
        status_placeholder.success(completion_message)

        # 응답이 완료되었으면 페이지 새로고침하여 결과 표시
        if st.session_state.slide_html or st.session_state.general_response:
            time.sleep(1)  # 메시지를 잠깐 보여줌
            st.rerun()

    except Exception as e:
        error_msg = f"스트리밍 처리 중 오류: {str(e)}"
        st.session_state.status_message = error_msg
        st.session_state.is_processing = False
        status_placeholder.error(error_msg)


def handle_slide_request(query: str, progress_placeholder, status_placeholder) -> None:
    """
    슬라이드 요청을 처리하는 함수

    Args:
        query: 사용자 질문
        progress_placeholder: 진행률 표시용 placeholder
        status_placeholder: 상태 메시지 표시용 placeholder
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
    st.session_state.general_response = ""

    # 초기 상태 표시
    progress_placeholder.progress(0.0)
    status_placeholder.info("요청을 처리하고 있습니다...")

    try:
        # API 요청 보내기
        result = send_chat_request(query, stream=True)

        if result["success"]:
            # 스트리밍 응답 처리
            process_streaming_response(
                result["response"], progress_placeholder, status_placeholder
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


# AI 슬라이드 페이지 함수
def show_ai_slide_page():
    col1, col2 = st.columns([3, 1])

    with col1:
        # 메인 타이틀
        st.markdown(
            """
        <div class="main-title">
            슬라이드를 만들 준비가 되셨나요?
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

        # 일반 응답 표시 영역 (상단)
        if st.session_state.general_response:
            st.markdown("### 💬 응답")
            st.info(st.session_state.general_response)
            st.markdown("---")

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
        st.markdown("<br>" * 3, unsafe_allow_html=True)

        # 입력 폼 (하단에 위치)
        st.markdown("### 💭 질문하기")
        with st.form(key="slide_form", clear_on_submit=True):
            col_input, col_btn = st.columns([5, 1])

            with col_input:
                user_input = st.text_input(
                    "질문을 입력하세요",
                    value=default_value,
                    placeholder="예: 클라우드 보안 정책에 대한 슬라이드를 만들어줘",
                    key="slide_input",
                    label_visibility="collapsed",
                )

            with col_btn:
                submit_button = st.form_submit_button(
                    "생성", type="primary", use_container_width=True
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
                        user_input, progress_placeholder, status_placeholder
                    )

    with col2:
        # 슬라이드 미리보기 영역
        if st.session_state.slide_html:
            st.markdown("### 슬라이드 미리보기")
            # HTML 슬라이드 표시
            st.components.v1.html(
                st.session_state.slide_html, height=800, scrolling=True
            )

            # 다운로드 버튼
            st.download_button(
                label="HTML 다운로드",
                data=st.session_state.slide_html,
                file_name="slide.html",
                mime="text/html",
            )

        else:
            # 기본 미리보기 영역
            st.markdown(
                """
            <div class="preview-container">
                <div class="preview-icon">📄</div>
                <div class="preview-title">슬라이드 미리보기</div>
                <div class="preview-text">
                    여기서 생성된 슬라이드를<br>
                    미리 확인할 수 있습니다
                </div>
            </div>
            """,
                unsafe_allow_html=True,
            )


# AI 거버넌스 페이지 함수
def show_ai_governance_page():
    st.markdown(
        """
    <div class="main-title">
        AI 거버넌스
    </div>
    """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
    <div class="main-description">
        AI 거버넌스 기능이 곧 제공될 예정입니다.
    </div>
    """,
        unsafe_allow_html=True,
    )


# 현재 페이지에 따라 컨텐츠 표시
if st.session_state.current_page == "홈":
    show_main_page()
elif st.session_state.current_page == "AI 슬라이드":
    show_ai_slide_page()
elif st.session_state.current_page == "AI 거버넌스":
    show_ai_governance_page()

import streamlit as st

# 페이지 설정
st.set_page_config(
    page_title="클라우드 거버넌스 자동화 AI",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

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
    
    /* 입력 영역 */
    .input-container {
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

    # 메뉴 항목들
    menu_items = [
        ("🏠", "홈"),
        ("📊", "AI 슬라이드", True),  # 현재 활성화된 메뉴
        ("🌐", "AI 거버넌스"),
    ]

    for item in menu_items:
        if len(item) == 3 and item[2]:  # 활성화된 메뉴
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
            st.markdown(
                f"""
            <div class="sidebar-item">
                <span class="icon">{item[0]}</span>
                <span>{item[1]}</span>
            </div>
            """,
                unsafe_allow_html=True,
            )

# 메인 컨텐츠 영역
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

    # 공백 추가 (하단 입력창을 위한 공간)
    st.markdown("<br>" * 10, unsafe_allow_html=True)

with col2:
    # 슬라이드 미리보기 영역
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

# 하단 입력 영역 (고정 위치)
st.markdown(
    """
<div class="input-container">
    <div style="display: flex; align-items: center; background-color: #2a2a2a; border: 1px solid #404040; border-radius: 12px; padding: 12px 16px;">
        <div class="action-buttons">
            <button class="action-btn">📎</button>
        </div>
        <input 
            type="text" 
            placeholder="슬라이드 요청을 여기에 입력하세요" 
            style="flex: 1; background: none; border: none; color: #ffffff; font-size: 16px; outline: none; margin: 0 12px;"
        />
        <div style="display: flex; align-items: center; gap: 8px;">
            <button class="action-btn">🎤</button>
            <button class="send-btn">↑</button>
        </div>
    </div>
</div>
""",
    unsafe_allow_html=True,
)

# JavaScript로 입력창 기능 추가
st.markdown(
    """
<script>
document.addEventListener('DOMContentLoaded', function() {
    const input = document.querySelector('.input-container input');
    const sendBtn = document.querySelector('.send-btn');
    
    if (input && sendBtn) {
        input.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                handleSend();
            }
        });
        
        sendBtn.addEventListener('click', function() {
            handleSend();
        });
    }
    
    function handleSend() {
        const value = input.value.trim();
        if (value) {
            // 여기에 슬라이드 생성 로직 추가 가능
            console.log('Slide request:', value);
            input.value = '';
        }
    }
});
</script>
""",
    unsafe_allow_html=True,
)

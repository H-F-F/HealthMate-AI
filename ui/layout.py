import streamlit as st


BASE_STYLES = """
<style>
.main .block-container {
    max-width: 700px;
    padding-top: 0.8rem;
    padding-bottom: 6.2rem;
}
.hma-header {
    background: linear-gradient(120deg, #f6fff8 0%, #eef7ff 100%);
    border: 1px solid #d9f3e4;
    border-radius: 14px;
    padding: 0.95rem 1.2rem;
    margin-bottom: 1rem;
    text-align: center;
}
.hma-muted {
    color: #596973;
    font-size: 0.95rem;
}
.hma-card {
    border: 1px solid #e8edf2;
    border-radius: 12px;
    padding: 0.7rem 0.9rem;
    background: #ffffff;
}
div[data-testid="stToolbar"] {
    display: none;
}
div[data-testid="stDecoration"] {
    display: none;
}
div[data-testid="stStatusWidget"] {
    display: none;
}
footer {
    display: none;
}
div[data-testid="stChatInput"] {
    position: fixed;
    left: 50%;
    transform: translateX(-50%);
    bottom: 0.9rem;
    width: min(700px, calc(100vw - 2rem));
    z-index: 1000;
    background: #ffffff;
    border-radius: 12px;
    box-shadow: 0 8px 26px rgba(15, 23, 42, 0.12);
    padding: 0.2rem 0.35rem;
}
button[data-baseweb="tab"] {
    font-size: 1.08rem;
    font-weight: 600;
}
</style>
"""


def apply_base_styles() -> None:
    st.markdown(BASE_STYLES, unsafe_allow_html=True)


def render_header() -> None:
    st.markdown(
        """
<div class="hma-header">
    <h2 style="margin: 0;">🏥 HealthMate-AI</h2>
    <div class="hma-muted" style="margin-top: 0.25rem;">你的健康问答与习惯管理助手</div>
</div>
""",
        unsafe_allow_html=True,
    )

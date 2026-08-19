# 导入与路径配置
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

from services.conversation_service import (
    build_default_conversation_store,
    create_new_conversation,
    ensure_conversation_store_shape,
    get_conversation_by_id,
    load_conversation_store,
    save_conversation_store,
    set_current_conversation,
    update_conversation_messages,
)
from services.defaults import (
    build_default_daily_metrics,
    build_default_diet_log,
    build_default_messages,
    build_default_weight_plan,
)
from services.profile_service import load_user_profile, save_user_profile
from services.weather_service import build_default_weather_state
from ui.auth_panel import render_auth_panel
from ui.chat_tab import render_chat_tab
from ui.conversation_sidebar import render_conversation_sidebar
from ui.health_tab import render_health_tab
from ui.layout import apply_base_styles, render_header
from ui.weather_tab import render_weather_tab

USER_DATA_DIR = Path("data/user_profiles")
CONVERSATION_DATA_DIR = Path("data/conversations")
USER_AUTH_FILE = Path("data/users.json")

load_dotenv()


# Streamlit 全局配置
st.set_page_config(page_title="HealthMate-AI", page_icon="🏥", layout="centered")
apply_base_styles()


# 把对话列表加载到 st.session_state,让页面读取最新的对话数据
def _apply_conversation_store_to_session(store: dict) -> None:
    normalized_store = ensure_conversation_store_shape(store)
    st.session_state.conversations = normalized_store["conversations"]
    st.session_state.current_conversation_id = normalized_store["current_conversation_id"]
    current = get_conversation_by_id(normalized_store, normalized_store["current_conversation_id"])
    # 登录、刷新或切换侧边栏会话后，需要把当前展示的消息列表
    # 同步到被选中的会话，避免页面内容和会话状态错位。
    st.session_state.messages = current["messages"] if current else build_default_messages()


# 获取当前所有对话的结构（标准化）
def _current_conversation_store() -> dict:
    return ensure_conversation_store_shape(
        {
            "current_conversation_id": st.session_state.get("current_conversation_id"),
            "conversations": st.session_state.get("conversations", []),
        }
    )


# 重置所有用户数据为默认值
def _reset_user_state_to_defaults() -> None:
    st.session_state.weight_plan = build_default_weight_plan()
    st.session_state.diet_log = build_default_diet_log()
    st.session_state.daily_metrics = build_default_daily_metrics()
    st.session_state.weather_state = build_default_weather_state()
    _apply_conversation_store_to_session(build_default_conversation_store())


# 保存用户的健康数据到本地 JSON
def _save_current_user_profile() -> bool:
    user_id = st.session_state.get("current_user")
    if not user_id:
        return False

    return save_user_profile(
        USER_DATA_DIR,
        user_id,
        weight_plan=st.session_state.get("weight_plan", {}),
        weather_state=st.session_state.get("weather_state", {}),
        diet_log=st.session_state.get("diet_log", {}),
        daily_metrics=st.session_state.get("daily_metrics", {}),
    )


# 保存用户的聊天记录到本地 JSON
def _save_current_user_conversations() -> bool:
    user_id = st.session_state.get("current_user")
    if not user_id:
        return False

    current_store = _current_conversation_store()
    # 先把内存里的最新聊天消息写回当前会话，再整体落盘，
    # 这样切换会话或重新登录时才能恢复到最新状态。
    store = update_conversation_messages(
        current_store,
        str(current_store.get("current_conversation_id", "")),
        st.session_state.get("messages", build_default_messages()),
    )
    _apply_conversation_store_to_session(store)
    return save_conversation_store(CONVERSATION_DATA_DIR, user_id, store)


# 登录时加载用户健康数据
def _load_profile_into_session(user_id: str) -> bool:
    payload = load_user_profile(USER_DATA_DIR, user_id)
    if not payload:
        return False

    if isinstance(payload.get("weight_plan"), dict):
        st.session_state.weight_plan = payload["weight_plan"]
    if isinstance(payload.get("weather_state"), dict):
        st.session_state.weather_state = payload["weather_state"]
    if isinstance(payload.get("diet_log"), dict):
        st.session_state.diet_log = payload["diet_log"]
    if isinstance(payload.get("daily_metrics"), dict):
        st.session_state.daily_metrics = payload["daily_metrics"]
    return True


# 登录时加载历史对话
def _load_conversations_into_session(user_id: str) -> bool:
    store = load_conversation_store(CONVERSATION_DATA_DIR, user_id)
    if not store:
        return False
    _apply_conversation_store_to_session(store)
    return True


# 新建对话 → 保存 → 刷新页面
def _create_new_conversation() -> None:
    _save_current_user_conversations()
    store = create_new_conversation(_current_conversation_store())
    _apply_conversation_store_to_session(store)
    _save_current_user_conversations()
    st.rerun()


# 切换历史对话 → 自动保存上一个 → 加载新的
def _switch_conversation(conversation_id: str) -> None:
    if not conversation_id:
        return
    _save_current_user_conversations()
    store = set_current_conversation(_current_conversation_store(), conversation_id)
    _apply_conversation_store_to_session(store)
    _save_current_user_conversations()
    st.rerun()


# 状态初始化函数
def _init_state() -> None:
    # Streamlit 每次交互都会整页重跑，因此要先稳定初始化
    # session_state，后续页面逻辑才能在同一套状态约定上运行。
    if "agent" not in st.session_state:
        st.session_state.agent = None
    if "agent_error" not in st.session_state:
        st.session_state.agent_error = None
    if "current_user" not in st.session_state:
        st.session_state.current_user = None
    if "auth_name_input" not in st.session_state:
        st.session_state.auth_name_input = ""
    if "auth_password_input" not in st.session_state:
        st.session_state.auth_password_input = ""
    if "auth_mode" not in st.session_state:
        st.session_state.auth_mode = "登录"
    if (
        "messages" not in st.session_state
        or "conversations" not in st.session_state
        or "current_conversation_id" not in st.session_state
    ):
        _apply_conversation_store_to_session(build_default_conversation_store())
    if "weather_state" not in st.session_state:
        st.session_state.weather_state = build_default_weather_state()
    if "weight_plan" not in st.session_state:
        st.session_state.weight_plan = build_default_weight_plan()
    if "diet_log" not in st.session_state:
        st.session_state.diet_log = build_default_diet_log()
    if "daily_metrics" not in st.session_state:
        st.session_state.daily_metrics = build_default_daily_metrics()


# 主渲染流程
_init_state()
render_header()
render_auth_panel(
    auth_file=USER_AUTH_FILE,
    on_save_profile=_save_current_user_profile,
    on_save_conversations=_save_current_user_conversations,
    on_reset_state=_reset_user_state_to_defaults,
    on_load_profile=_load_profile_into_session,
    on_load_conversations=_load_conversations_into_session,
)

if not st.session_state.current_user:
    st.stop()

render_conversation_sidebar(
    conversations=st.session_state.get("conversations", []),
    current_conversation_id=str(st.session_state.get("current_conversation_id", "")),
    on_new_conversation=_create_new_conversation,
    on_select_conversation=_switch_conversation,
)

current_conversation = get_conversation_by_id(_current_conversation_store(), str(st.session_state.get("current_conversation_id", "")))
current_conversation_title = str((current_conversation or {}).get("title", "新对话"))

tab_chat, tab_plan, tab_weather = st.tabs(["💬 智能问答", "📊 健康管理", "🌤️ 实时天气"])

with tab_chat:
    render_chat_tab(
        on_messages_changed=_save_current_user_conversations,
        on_new_conversation=_create_new_conversation,
        conversation_title=current_conversation_title,
    )
with tab_plan:
    render_health_tab(on_save_profile=_save_current_user_profile)
with tab_weather:
    render_weather_tab(on_save_profile=_save_current_user_profile)

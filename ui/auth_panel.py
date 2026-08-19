from pathlib import Path
from typing import Callable

import streamlit as st

from services.auth_service import is_valid_user_id, register_user, safe_user_id, verify_user


def render_auth_panel(
    *,
    auth_file: Path,
    on_save_profile: Callable[[], bool],
    on_save_conversations: Callable[[], bool],
    on_reset_state: Callable[[], None],
    on_load_profile: Callable[[str], bool],
    on_load_conversations: Callable[[str], bool],
) -> None:
    if st.session_state.current_user:
        c1, c2 = st.columns([8, 2])
        with c1:
            st.caption(f"当前用户：{st.session_state.current_user}")
            st.caption("数据已自动保存")
        with c2:
            if st.button("退出登录", use_container_width=True):
                st.session_state.current_user = None
                st.rerun()
        return

    st.markdown("<div style='height: 0.4rem;'></div>", unsafe_allow_html=True)
    _, center, _ = st.columns([2, 4, 2])
    with center:
        st.markdown("### 登录 / 注册")
        mode = st.radio("模式", ["登录", "注册"], horizontal=True, key="auth_mode")
        name = st.text_input(
            "用户名",
            key="auth_name_input",
            placeholder="仅支持中文、英文字母、数字（1-40位）",
            help="用户名只能包含中文、英文字母、数字，长度 1-40 位。",
        )
        password = st.text_input("密码", type="password", key="auth_password_input", placeholder="至少 6 位")
        btn_label = "登录" if mode == "登录" else "注册并登录"
        if st.button(btn_label, use_container_width=True):
            user_id = safe_user_id(name)
            if not is_valid_user_id(user_id):
                st.warning("用户名仅支持中文、英文字母、数字，长度 1-40 位。")
                return
            if not password:
                st.warning("请输入密码")
                return

            if mode == "注册":
                ok, msg = register_user(auth_file, user_id, password)
                if not ok:
                    st.warning(msg)
                    return
                st.toast(msg)
                st.session_state.current_user = user_id
                on_reset_state()
                on_save_profile()
                on_save_conversations()
                st.toast("已创建默认资料，并根据定位初始化天气")
            else:
                if not verify_user(auth_file, user_id, password):
                    st.error("用户名或密码错误")
                    return
                st.session_state.current_user = user_id
                on_reset_state()
                profile_loaded = on_load_profile(user_id)
                conversations_loaded = on_load_conversations(user_id)
                if profile_loaded or conversations_loaded:
                    if not profile_loaded:
                        on_save_profile()
                    if not conversations_loaded:
                        on_save_conversations()
                    st.toast("已加载历史数据")
                else:
                    on_save_profile()
                    on_save_conversations()
                    st.toast("未找到历史资料，已使用默认资料")

            st.rerun()

from typing import Callable

import streamlit as st

from agent.react_agent import create_health_agent
from services.assistant_service import build_service_unavailable_response, generate_health_response


# 确保 AI 大脑已创建成功
def _ensure_agent() -> None:
    if st.session_state.agent is not None or st.session_state.agent_error is not None:
        return
    try:
        st.session_state.agent = create_health_agent()
    except Exception as exc:
        st.session_state.agent_error = str(exc)


# 渲染整个聊天页面 + 处理消息发送 + 展示回答
def render_chat_tab(
    *,
    on_messages_changed: Callable[[], bool],
    on_new_conversation: Callable[[], None],
    conversation_title: str = "新对话",
) -> None:
    header_left, header_right = st.columns([7, 2])
    with header_left:
        st.subheader("💬 智能问答")
        st.caption(f"当前对话：{conversation_title}")
    with header_right:
        st.markdown("<div style='height: 0.6rem;'></div>", unsafe_allow_html=True)
        if st.button("＋ 新对话", key="chat_tab_new_conversation", use_container_width=True):
            on_new_conversation()

    prompt = st.chat_input("输入你的健康问题...", key="chat_input_bottom")
    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})
        on_messages_changed()
        _ensure_agent()
        if st.session_state.agent_error:
            response = build_service_unavailable_response(st.session_state.agent_error)
        else:
            try:
                with st.spinner("正在分析..."):
                    history = [
                        {"role": message["role"], "content": message["content"]}
                        for message in st.session_state.messages
                        if message["role"] in {"user", "assistant"}
                    ]
                    response = generate_health_response(
                        messages=history,
                        agent=st.session_state.agent,
                    )
            except Exception as exc:
                response = build_service_unavailable_response(str(exc))

        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": response.answer,
                "structured": response.to_dict(),
            }
        )
        on_messages_changed()
        st.rerun()

    message_box = st.container(height=520, border=False)
    with message_box:
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
                structured = message.get("structured")
                if message["role"] == "assistant" and isinstance(structured, dict):
                    risk_level = str(structured.get("risk_level", "low")).upper()
                    triage_reason = str(structured.get("triage_reason", "")).strip()
                    safety_notice = str(structured.get("safety_notice", "")).strip()
                    follow_ups = structured.get("follow_up_questions") or []
                    used_tools = structured.get("used_tools") or []
                    latency_ms = structured.get("latency_ms", 0)
                    tokens_used = structured.get("tokens_used", 0)

                    meta_parts = [f"风险等级：`{risk_level}`"]
                    if used_tools:
                        meta_parts.append(f"工具：`{', '.join(used_tools)}`")
                    if latency_ms:
                        meta_parts.append(f"耗时：`{latency_ms} ms`")
                    if tokens_used:
                        meta_parts.append(f"Token：`{tokens_used}`")
                    st.caption(" | ".join(meta_parts))

                    if triage_reason:
                        st.info(f"判断依据：{triage_reason}")
                    if safety_notice:
                        st.warning(safety_notice)
                    if follow_ups:
                        st.markdown("**建议继续确认**")
                        for item in follow_ups:
                            st.markdown(f"- {item}")

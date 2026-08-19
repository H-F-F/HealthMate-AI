from datetime import datetime
from typing import Callable

import streamlit as st


def _format_updated_at(value: str) -> str:
    try:
        return datetime.fromisoformat(value).strftime("%m-%d %H:%M")
    except Exception:
        return value


def render_conversation_sidebar(
    *,
    conversations: list[dict],
    current_conversation_id: str,
    on_new_conversation: Callable[[], None],
    on_select_conversation: Callable[[str], None],
) -> None:
    with st.sidebar:
        st.markdown("### 对话历史")
        st.button("＋ 新对话", use_container_width=True, on_click=on_new_conversation)
        st.caption("重新登录后会保留历史对话")
        st.markdown("---")

        if not conversations:
            st.caption("暂无历史对话")
            return

        for item in conversations:
            title = str(item.get("title", "")).strip() or "新对话"
            updated_at = _format_updated_at(str(item.get("updated_at", "")))
            is_current = item.get("id") == current_conversation_id
            label = f"{'● ' if is_current else ''}{title}"
            if st.button(
                label,
                key=f"conversation-{item.get('id')}",
                use_container_width=True,
                type="primary" if is_current else "secondary",
            ):
                on_select_conversation(str(item.get("id", "")))
            if updated_at:
                st.caption(updated_at)

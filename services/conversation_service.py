import json
from copy import deepcopy
from datetime import datetime
from pathlib import Path
import re
from uuid import uuid4

from services.defaults import build_default_messages


DEFAULT_CONVERSATION_TITLE = "新对话"
TITLE_MAX_LENGTH = 18
TITLE_PATTERNS = (
    ("胸痛与呼吸困难", ("胸痛", "呼吸困难")),
    ("持续高烧处理", ("持续高烧", "高烧", "发烧")),
    ("BMI计算", ("bmi", "身高", "体重")),
    ("饮水建议", ("喝多少水", "饮水", "喝水")),
    ("步数目标", ("步数", "走多少步")),
    ("失眠调整", ("失眠", "入睡慢", "白天犯困")),
    ("减脂建议", ("减肥", "减脂", "体重下降")),
    ("腹泻处理", ("腹泻", "拉肚子")),
    ("头痛处理", ("头痛", "头疼")),
    ("胃痛处理", ("胃痛", "腹痛")),
    ("压力与焦虑", ("压力大", "焦虑", "心烦")),
    ("早餐建议", ("早餐",)),
    ("午餐建议", ("午餐",)),
    ("晚餐建议", ("晚餐",)),
    ("运动建议", ("运动", "跑步", "锻炼")),
    ("睡眠建议", ("睡眠",)),
)


# 生成当前时间字符串，用于记录创建 / 更新时间
def _now_iso(now: datetime | None = None) -> str:
    current = now or datetime.now()
    return current.isoformat(timespec="seconds")


# 清洗消息
def _normalize_messages(messages: list[dict] | None) -> list[dict]:
    normalized: list[dict] = []
    for message in messages or []:
        if not isinstance(message, dict):
            continue
        role = str(message.get("role", "")).strip()
        content = str(message.get("content", "")).strip()
        if role not in {"assistant", "user"} or not content:
            continue
        item = {"role": role, "content": content}
        structured = message.get("structured")
        if isinstance(structured, dict):
            item["structured"] = deepcopy(structured)
        normalized.append(item)
    return normalized


# 生成用户对话文件路径：data/conversations/用户ID.json
def conversation_store_path(conversation_data_dir: Path, user_id: str) -> Path:
    return conversation_data_dir / f"{user_id}.json"


# 清理标题文本：去掉符号、多余空格
def _clean_title_text(text: str) -> str:
    cleaned = re.sub(r"\s+", " ", text or "").strip()
    cleaned = re.sub(r"[，。！？；：、“”\"'（）()\[\]【】<>《》]", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


# 根据用户问题匹配预设标题
def _extract_title_keywords(text: str) -> str:
    lowered = (text or "").lower()
    for title, patterns in TITLE_PATTERNS:
        if any(pattern.lower() in lowered for pattern in patterns):
            return title
    return ""


# 生成对话标题
def generate_conversation_title(messages: list[dict], default_title: str = DEFAULT_CONVERSATION_TITLE) -> str:
    first_user_message = next((str(item.get("content", "")).strip() for item in messages if item.get("role") == "user"), "")
    if not first_user_message:
        return default_title

    keyword_title = _extract_title_keywords(first_user_message)
    if keyword_title:
        return keyword_title

    compact = _clean_title_text(first_user_message)
    if len(compact) <= TITLE_MAX_LENGTH:
        return compact
    return compact[:TITLE_MAX_LENGTH].rstrip() + "..."


# 创建一条新对话
# 包含：
#   id
#   标题
#   创建时间
#   更新时间
#   消息列表
def create_conversation(
    *,
    title: str | None = None,
    messages: list[dict] | None = None,
    conversation_id: str | None = None,
    now: datetime | None = None,
) -> dict:
    normalized_messages = _normalize_messages(messages or build_default_messages())
    timestamp = _now_iso(now)
    resolved_title = (title or "").strip() or generate_conversation_title(normalized_messages)
    return {
        "id": conversation_id or uuid4().hex,
        "title": resolved_title,
        "created_at": timestamp,
        "updated_at": timestamp,
        "messages": normalized_messages,
    }


# 初始化默认对话结构
#   新建一个对话
#   设为当前对话
def build_default_conversation_store(now: datetime | None = None) -> dict:
    conversation = create_conversation(now=now)
    return {
        "current_conversation_id": conversation["id"],
        "conversations": [conversation],
    }


# 对话按更新时间排序，最新的排在最上面
def _sort_conversations(conversations: list[dict]) -> list[dict]:
    return sorted(
        conversations,
        key=lambda item: str(item.get("updated_at", "")),
        reverse=True,
    )


# 格式校验 + 数据修复
# 不管读取的旧数据多乱，都整理成标准结构
def ensure_conversation_store_shape(payload: dict | None) -> dict:
    if not isinstance(payload, dict):
        return build_default_conversation_store()

    # 把磁盘中的会话数据统一整理成当前结构，
    # 避免旧版本文件或不完整数据影响页面恢复。
    normalized_items: list[dict] = []
    for item in payload.get("conversations", []) or []:
        if not isinstance(item, dict):
            continue
        conversation_id = str(item.get("id", "")).strip() or uuid4().hex
        messages = _normalize_messages(item.get("messages", []))
        created_at = str(item.get("created_at", "")).strip() or _now_iso()
        updated_at = str(item.get("updated_at", "")).strip() or created_at
        title = str(item.get("title", "")).strip() or generate_conversation_title(messages)
        normalized_items.append(
            {
                "id": conversation_id,
                "title": title,
                "created_at": created_at,
                "updated_at": updated_at,
                "messages": messages or build_default_messages(),
            }
        )

    if not normalized_items:
        return build_default_conversation_store()

    sorted_items = _sort_conversations(normalized_items)
    current_conversation_id = str(payload.get("current_conversation_id", "")).strip()
    if not current_conversation_id or not any(item["id"] == current_conversation_id for item in sorted_items):
        current_conversation_id = sorted_items[0]["id"]

    return {
        "current_conversation_id": current_conversation_id,
        "conversations": sorted_items,
    }


# 加载用户的对话文件
def load_conversation_store(conversation_data_dir: Path, user_id: str) -> dict | None:
    path = conversation_store_path(conversation_data_dir, user_id)
    if not path.exists():
        return None

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None

    return ensure_conversation_store_shape(payload)


# 保存用户对话到本地文件
def save_conversation_store(conversation_data_dir: Path, user_id: str, store: dict) -> bool:
    if not user_id:
        return False

    conversation_data_dir.mkdir(parents=True, exist_ok=True)
    normalized_store = ensure_conversation_store_shape(store)
    conversation_store_path(conversation_data_dir, user_id).write_text(
        json.dumps(normalized_store, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return True


# 根据 ID 查找某一条对话
def get_conversation_by_id(store: dict, conversation_id: str) -> dict | None:
    normalized_store = ensure_conversation_store_shape(store)
    return next((item for item in normalized_store["conversations"] if item["id"] == conversation_id), None)


# 更新某条对话的消息
def update_conversation_messages(store: dict, conversation_id: str, messages: list[dict], *, now: datetime | None = None) -> dict:
    normalized_store = ensure_conversation_store_shape(store)
    normalized_messages = _normalize_messages(messages)
    timestamp = _now_iso(now)
    updated_items: list[dict] = []
    matched = False

    for item in normalized_store["conversations"]:
        if item["id"] != conversation_id:
            updated_items.append(item)
            continue

        matched = True
        title = item.get("title", DEFAULT_CONVERSATION_TITLE)
        # 只有默认占位标题才会被首条真实用户消息替换，
        # 已经生成好的标题不再反复改名。
        if title == DEFAULT_CONVERSATION_TITLE or not str(title).strip():
            title = generate_conversation_title(normalized_messages)
        updated_items.append(
            {
                **item,
                "title": title,
                "updated_at": timestamp,
                "messages": normalized_messages or build_default_messages(),
            }
        )

    if not matched:
        updated_items.append(
            create_conversation(
                title=generate_conversation_title(normalized_messages),
                messages=normalized_messages or build_default_messages(),
                conversation_id=conversation_id,
                now=now,
            )
        )

    return {
        "current_conversation_id": conversation_id,
        "conversations": _sort_conversations(updated_items),
    }


# 创建一个新对话加到列表最前面，并设为当前对话
def create_new_conversation(store: dict | None = None, *, now: datetime | None = None) -> dict:
    normalized_store = ensure_conversation_store_shape(store)
    conversation = create_conversation(now=now)
    conversations = [conversation, *normalized_store["conversations"]]
    return {
        "current_conversation_id": conversation["id"],
        "conversations": _sort_conversations(conversations),
    }


# 切换当前选中的对话
def set_current_conversation(store: dict, conversation_id: str) -> dict:
    normalized_store = ensure_conversation_store_shape(store)
    if any(item["id"] == conversation_id for item in normalized_store["conversations"]):
        normalized_store["current_conversation_id"] = conversation_id
    return normalized_store

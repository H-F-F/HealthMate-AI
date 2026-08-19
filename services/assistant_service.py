import json
import re
import time
from dataclasses import asdict, dataclass, field
from typing import Any

from services.triage_service import TriageResult, assess_symptom_risk


ALLOWED_RISK_LEVELS = {"low", "medium", "high", "urgent"}


# 数据结构 StructuredHealthResponse
# 统一响应结构体，确保前端永远收到固定格式
# 作用：最终返回给前端的标准格式。
# 包含字段：
#   answer：给用户看的回答
#   risk_level：风险等级
#   triage_reason：为什么是这个风险
#   safety_notice：安全提醒
#   follow_up_questions：后续追问
#   used_tools：调用了哪些工具（地图 / 搜索等）
#   route：从哪条路由来的
#   latency_ms：耗时
#   tokens_used：token 消耗
@dataclass
class StructuredHealthResponse:
    answer: str
    risk_level: str
    triage_reason: str
    safety_notice: str
    follow_up_questions: list[str] = field(default_factory=list)
    used_tools: list[str] = field(default_factory=list)
    route: str = "agent_structured"
    structure_source: str = "fallback"
    latency_ms: int = 0
    tokens_used: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# 提示词模板,让 AI 把自由文本 → 变成标准 JSON
STRUCTURE_PROMPT_TEMPLATE = """你是健康助手的结构化输出整理器。

你会收到：
1. 用户最后一条问题
2. 助手原始回答
3. 风险等级和分流原因
4. 已调用工具列表

请严格输出 JSON，不要输出任何额外说明。JSON 字段必须是：
{{
  "answer": "给用户看的最终回答，4-8句，清晰、具体、不要重复",
  "risk_level": "low|medium|high|urgent",
  "triage_reason": "一句话说明风险判断依据",
  "safety_notice": "一句话安全提醒",
  "follow_up_questions": ["最多3条后续追问，每条不超过20字"],
  "used_tools": ["工具名列表"]
}}

要求：
- `risk_level` 只能使用提供的等级，不要改写。
- `answer` 里不要写 JSON、不要写字段名。
- `answer` 默认使用详细版回答：尽量包含原因判断、可执行建议、注意事项；如果适合，可以分成短段落。
- `follow_up_questions` 最多 3 条，适合继续追问用户获取关键信息。
- 如果用户问题主要是计算或日常管理，`follow_up_questions` 可以为空数组。

用户问题：
{user_prompt}

助手原始回答：
{raw_answer}

风险等级：
{risk_level}

风险说明：
{triage_reason}

安全提醒：
{safety_notice}

已调用工具：
{used_tools}
"""


# 服务不可用时的兜底返回
def build_service_unavailable_response(error_message: str) -> StructuredHealthResponse:
    return StructuredHealthResponse(
        answer="当前模型服务未就绪，请检查 `.env` 中 `DASHSCOPE_API_KEY` 配置后重试。",
        risk_level="medium",
        triage_reason="当前无法调用模型服务，因此只能返回兜底提示。",
        safety_notice=f"错误详情：{error_message}",
        follow_up_questions=[],
        used_tools=[],
        route="service_unavailable",
        structure_source="fallback",
    )


# 紧急情况响应（高危症状）
def build_urgent_triage_response(user_prompt: str, triage: TriageResult) -> StructuredHealthResponse:
    follow_up_questions = []
    if "胸" in user_prompt or "呼吸" in user_prompt:
        follow_up_questions = ["症状持续多久了？", "是否伴随冷汗或头晕？"]
    elif "高烧" in user_prompt:
        follow_up_questions = ["体温最高到多少度？", "是否已持续超过24小时？"]

    return StructuredHealthResponse(
        answer=(
            "你描述的情况包含危险信号，现阶段不适合只做线上健康建议。"
            "请立即前往急诊或呼叫急救；如果身边有人，尽量让对方陪同。"
        ),
        risk_level="urgent",
        triage_reason=triage.reason,
        safety_notice=triage.immediate_action,
        follow_up_questions=follow_up_questions,
        used_tools=[],
        route="rule_triage",
        structure_source="rule",
    )


# 清洗追问问题,最多3条
def _sanitize_follow_up_questions(items: Any) -> list[str]:
    if not isinstance(items, list):
        return []
    questions: list[str] = []
    for item in items:
        text = str(item).strip()
        if text and text not in questions:
            questions.append(text[:20])
        if len(questions) == 3:
            break
    return questions


# 自动生成默认追问
def _default_follow_up_questions(user_prompt: str, risk_level: str) -> list[str]:
    if risk_level in {"high", "urgent"}:
        return ["症状持续多久了？", "是否正在加重？"]
    if any(keyword in user_prompt for keyword in ("睡眠", "失眠", "熬夜")):
        return ["这种情况持续几天了？", "最近作息是否固定？"]
    if any(keyword in user_prompt for keyword in ("减肥", "饮食", "热量")):
        return ["你最近一周怎么吃？", "有没有固定运动？"]
    if any(keyword in user_prompt for keyword in ("运动", "步数", "锻炼")):
        return ["最近每周运动几次？"]
    return []


# 从 AI 返回中提取 JSON
def _extract_first_json_object(text: str) -> dict[str, Any] | None:
    if not text:
        return None

    cleaned = text.strip()
    cleaned = cleaned.replace("```json", "```").replace("```JSON", "```")
    # 格式化模型不一定只返回纯 JSON，先尝试提取代码块里的 JSON，
    # 再退回到响应中第一个结构完整的对象。
    fence_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", cleaned, flags=re.S)
    if fence_match:
        candidate = fence_match.group(1)
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

    start = cleaned.find("{")
    if start == -1:
        return None

    depth = 0
    for index in range(start, len(cleaned)):
        char = cleaned[index]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                candidate = cleaned[start : index + 1]
                try:
                    return json.loads(candidate)
                except json.JSONDecodeError:
                    return None
    return None


# 获取 AI 最终回答,从对话记录里找到最后一条 AI 消息
def _final_ai_answer(result_messages: list[Any]) -> str:
    for message in reversed(result_messages):
        if getattr(message, "type", None) == "ai":
            content = getattr(message, "content", "")
            if isinstance(content, str) and content.strip():
                return content.strip()
    return ""


# 收集调用过的工具
def _collect_used_tools(result_messages: list[Any]) -> list[str]:
    tool_names: list[str] = []
    for message in result_messages:
        if getattr(message, "type", None) == "tool":
            name = getattr(message, "name", None)
            if name and name not in tool_names:
                tool_names.append(str(name))
    return tool_names


# 统计 token 消耗
def _collect_token_usage(result_messages: list[Any]) -> int:
    total_tokens = 0
    for message in result_messages:
        metadata = getattr(message, "response_metadata", {}) or {}
        usage = metadata.get("token_usage") or {}
        total_tokens += int(usage.get("total_tokens", 0) or 0)
    return total_tokens


# 清理回答文本格式,去掉多余空行，让回答更干净
def _normalize_answer_text(text: str) -> str:
    cleaned = (text or "").strip()
    if not cleaned:
        return ""
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned


# 快速结构化
def _build_fast_structured_response(
    *,
    user_prompt: str,
    raw_answer: str,
    triage: TriageResult,
    used_tools: list[str],
) -> StructuredHealthResponse:
    answer = _normalize_answer_text(raw_answer) or "我暂时无法回答这个问题，请稍后再试。"
    follow_up_questions = _default_follow_up_questions(user_prompt, triage.risk_level)
    return StructuredHealthResponse(
        answer=answer,
        risk_level=triage.risk_level,
        triage_reason=triage.reason,
        safety_notice=triage.immediate_action,
        follow_up_questions=follow_up_questions,
        used_tools=used_tools,
        structure_source="fast_local",
    )


# 清洗、校验、修复 AI 返回的 JSON
def _sanitize_structured_payload(
    payload: dict[str, Any] | None,
    *,
    raw_answer: str,
    triage: TriageResult,
    used_tools: list[str],
    user_prompt: str,
) -> StructuredHealthResponse:
    if not payload:
        return StructuredHealthResponse(
            answer=raw_answer or "我暂时无法生成结构化回答，请稍后再试。",
            risk_level=triage.risk_level,
            triage_reason=triage.reason,
            safety_notice=triage.immediate_action,
            follow_up_questions=_default_follow_up_questions(user_prompt, triage.risk_level),
            used_tools=used_tools,
            structure_source="fallback",
        )

    answer = str(payload.get("answer") or raw_answer or "").strip() or "我暂时无法生成结构化回答，请稍后再试。"
    risk_level = str(payload.get("risk_level") or triage.risk_level).strip().lower()
    if risk_level not in ALLOWED_RISK_LEVELS:
        risk_level = triage.risk_level

    triage_reason = str(payload.get("triage_reason") or triage.reason).strip() or triage.reason
    safety_notice = str(payload.get("safety_notice") or triage.immediate_action).strip() or triage.immediate_action
    follow_up_questions = _sanitize_follow_up_questions(payload.get("follow_up_questions"))
    if not follow_up_questions:
        follow_up_questions = _default_follow_up_questions(user_prompt, risk_level)

    raw_used_tools = payload.get("used_tools")
    if isinstance(raw_used_tools, list):
        normalized_tools = []
        for tool_name in raw_used_tools:
            name = str(tool_name).strip()
            if name and name not in normalized_tools:
                normalized_tools.append(name)
        if normalized_tools:
            used_tools = normalized_tools

    return StructuredHealthResponse(
        answer=answer,
        risk_level=risk_level,
        triage_reason=triage_reason,
        safety_notice=safety_notice,
        follow_up_questions=follow_up_questions,
        used_tools=used_tools,
        structure_source="model_json",
    )


# 双模式结构化
# 格式化响应（对外接口）
def format_structured_response(
    *,
    user_prompt: str,
    raw_answer: str,
    triage: TriageResult,
    used_tools: list[str],
    formatter_model: Any | None = None,
    formatter_strategy: str = "fast",
) -> StructuredHealthResponse:
    # 默认走本地快速结构化，避免用户链路再多一次模型调用；
    # 更严格的模型格式化只保留为可选模式。
    if formatter_strategy != "model":
        return _build_fast_structured_response(
            user_prompt=user_prompt,
            raw_answer=raw_answer,
            triage=triage,
            used_tools=used_tools,
        )

    model = formatter_model
    if model is None:
        return _build_fast_structured_response(
            user_prompt=user_prompt,
            raw_answer=raw_answer,
            triage=triage,
            used_tools=used_tools,
        )

    prompt = STRUCTURE_PROMPT_TEMPLATE.format(
        user_prompt=user_prompt,
        raw_answer=raw_answer,
        risk_level=triage.risk_level,
        triage_reason=triage.reason,
        safety_notice=triage.immediate_action,
        used_tools=", ".join(used_tools) if used_tools else "无",
    )

    try:
        response = model.invoke(prompt)
        content = getattr(response, "content", "")
        if isinstance(content, list):
            content = "\n".join(str(item) for item in content)
        payload = _extract_first_json_object(str(content))
    except Exception:
        payload = None

    return _sanitize_structured_payload(
        payload,
        raw_answer=raw_answer,
        triage=triage,
        used_tools=used_tools,
        user_prompt=user_prompt,
    )


# 主入口函数 generate_health_response
# 内部流程:
#   取最近 12 条对话（防止太长）
#   获取用户最新问题
#   风险分诊：高危直接返回急诊
#   调用 AI agent 获取回答
#   记录耗时、token、工具调用
#   结构化整理回答
#   返回标准格式给前端
def generate_health_response(
    *,
    messages: list[dict[str, str]],
    agent: Any,
    formatter_model: Any | None = None,
    formatter_strategy: str = "fast",
) -> StructuredHealthResponse:
    # 只保留最近一段对话，既控制上下文长度，
    # 又能保留多轮追问所需的核心信息。
    recent_messages = messages[-12:]
    user_prompt = next((msg["content"] for msg in reversed(recent_messages) if msg["role"] == "user"), "")
    triage = assess_symptom_risk(user_prompt)
    if triage.requires_immediate_care:
        return build_urgent_triage_response(user_prompt, triage)

    started = time.perf_counter()
    result = agent.invoke({"messages": recent_messages})
    latency_ms = int((time.perf_counter() - started) * 1000)

    result_messages = result.get("messages", [])
    raw_answer = _final_ai_answer(result_messages)
    used_tools = _collect_used_tools(result_messages)
    tokens_used = _collect_token_usage(result_messages)
    structured = format_structured_response(
        user_prompt=user_prompt,
        raw_answer=raw_answer or "我暂时无法回答这个问题，请稍后再试。",
        triage=triage,
        used_tools=used_tools,
        formatter_model=formatter_model,
        formatter_strategy=formatter_strategy,
    )
    structured.used_tools = used_tools or structured.used_tools
    structured.route = "agent_structured"
    structured.latency_ms = latency_ms
    structured.tokens_used = tokens_used
    return structured

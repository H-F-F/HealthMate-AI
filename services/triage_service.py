from dataclasses import dataclass, field


# 定义单条分诊规则模板：风险等级 + 触发关键词 + 判断原因 + 就医建议
@dataclass
class TriageRule:
    risk_level: str
    keywords: tuple[str, ...]
    reason: str
    immediate_action: str


# 定义风险检测最终返回结果，附带匹配词语、路由类型
@dataclass
class TriageResult:
    risk_level: str
    reason: str
    immediate_action: str
    matched_terms: list[str] = field(default_factory=list)
    route: str = "normal"

    @property
    def requires_immediate_care(self) -> bool:
        return self.risk_level == "urgent"


# 提前写好的全套风险关键词规则库，分紧急、高危、中等三级病症
TRIAGE_RULES = (
    TriageRule(
        risk_level="urgent",
        keywords=(
            "胸痛",
            "胸口疼",
            "呼吸困难",
            "喘不过气",
            "意识模糊",
            "昏迷",
            "抽搐",
            "口角歪斜",
            "单侧无力",
            "呕血",
            "便血",
            "黑便",
            "大出血",
            "高烧不退",
            "持续高烧",
            "39.5",
            "40度",
            "剧烈腹痛",
            "过敏性休克",
            "轻生",
            "自杀",
            "胸闷加重",
        ),
        reason="检测到需要优先排除急症的危险信号。",
        immediate_action="请立即线下就医或呼叫急救，不要仅依赖线上建议。",
    ),
    TriageRule(
        risk_level="high",
        keywords=(
            "发烧三天",
            "持续呕吐",
            "脱水",
            "心悸",
            "血压很高",
            "血糖很高",
            "咳血",
            "剧烈头痛",
            "无法进食",
        ),
        reason="症状提示需要尽快线下评估，避免延误。",
        immediate_action="建议尽快线下就医，最好当天完成评估。",
    ),
    TriageRule(
        risk_level="medium",
        keywords=(
            "失眠",
            "胃痛",
            "腹泻",
            "头晕",
            "咳嗽",
            "喉咙痛",
            "头疼",
            "减肥",
            "焦虑",
            "压力大",
        ),
        reason="问题适合先做健康管理建议，但需要关注是否持续或加重。",
        immediate_action="如果症状持续、反复或加重，建议线下就医。",
    ),
)


# 风险优先级排序，用户同时多个症状时，只按最高危险等级处理
RISK_PRIORITY = {
    "low": 0,
    "medium": 1,
    "high": 2,
    "urgent": 3,
}


# 接收用户症状文字
#   文本归一化处理
#   遍历匹配关键词
#   选取最高风险规则
#   返回最终分诊结果
#   没匹配到任何危险词 → 默认低风险 low
def assess_symptom_risk(text: str) -> TriageResult:
    normalized = (text or "").strip().lower()
    best_rule: TriageRule | None = None
    matched_terms: list[str] = []

    for rule in TRIAGE_RULES:
        current_matches = [keyword for keyword in rule.keywords if keyword.lower() in normalized]
        if not current_matches:
            continue
        if best_rule is None or RISK_PRIORITY[rule.risk_level] > RISK_PRIORITY[best_rule.risk_level]:
            best_rule = rule
            matched_terms = current_matches

    if best_rule is None:
        return TriageResult(
            risk_level="low",
            reason="未识别到明显危险信号，适合先给出日常健康管理建议。",
            immediate_action="以下建议仅供健康管理参考，不能替代医生面诊。",
            matched_terms=[],
            route="normal",
        )

    route = "rule_triage" if best_rule.risk_level == "urgent" else "normal"
    return TriageResult(
        risk_level=best_rule.risk_level,
        reason=best_rule.reason,
        immediate_action=best_rule.immediate_action,
        matched_terms=matched_terms,
        route=route,
    )

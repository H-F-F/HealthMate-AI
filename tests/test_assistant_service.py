import unittest

from services.assistant_service import format_structured_response
from services.triage_service import TriageResult


class FakeModelResponse:
    def __init__(self, content: str) -> None:
        self.content = content


class FakeFormatterModel:
    def __init__(self, content: str) -> None:
        self.content = content

    def invoke(self, prompt: str) -> FakeModelResponse:
        return FakeModelResponse(self.content)


class AssistantServiceTests(unittest.TestCase):
    def test_format_structured_response_uses_fast_local_mode_by_default(self) -> None:
        triage = TriageResult(
            risk_level="medium",
            reason="问题可能持续，需要观察。",
            immediate_action="若加重建议就医。",
        )

        response = format_structured_response(
            user_prompt="我最近总是失眠，怎么调整？",
            raw_answer="建议固定起床时间，睡前减少屏幕刺激，并观察两周变化。",
            triage=triage,
            used_tools=[],
        )

        self.assertEqual(response.risk_level, "medium")
        self.assertIn("固定起床时间", response.answer)
        self.assertEqual(response.structure_source, "fast_local")
        self.assertGreaterEqual(len(response.follow_up_questions), 1)

    def test_format_structured_response_parses_json_payload(self) -> None:
        triage = TriageResult(
            risk_level="medium",
            reason="问题可能持续，需要观察。",
            immediate_action="若加重建议就医。",
        )
        model = FakeFormatterModel(
            """```json
            {
              "answer": "建议先补充水分并观察 24 小时。",
              "risk_level": "medium",
              "triage_reason": "当前没有急症信号，但需要继续观察。",
              "safety_notice": "若发热或腹痛加重，请尽快就医。",
              "follow_up_questions": ["有没有发热？", "症状持续多久了？"],
              "used_tools": ["get_water_goal_tool"]
            }
            ```"""
        )

        response = format_structured_response(
            user_prompt="我今天有点腹泻，要注意什么？",
            raw_answer="建议补充水分并清淡饮食。",
            triage=triage,
            used_tools=["get_water_goal_tool"],
            formatter_model=model,
            formatter_strategy="model",
        )

        self.assertEqual(response.risk_level, "medium")
        self.assertIn("补充水分", response.answer)
        self.assertEqual(response.used_tools, ["get_water_goal_tool"])
        self.assertEqual(len(response.follow_up_questions), 2)
        self.assertEqual(response.structure_source, "model_json")

    def test_format_structured_response_falls_back_when_json_invalid(self) -> None:
        triage = TriageResult(
            risk_level="high",
            reason="症状需要尽快线下评估。",
            immediate_action="建议尽快就医。",
        )
        model = FakeFormatterModel("这不是 JSON")

        response = format_structured_response(
            user_prompt="我头痛得厉害，还一直想吐。",
            raw_answer="建议尽快线下就医。",
            triage=triage,
            used_tools=[],
            formatter_model=model,
            formatter_strategy="model",
        )

        self.assertEqual(response.risk_level, "high")
        self.assertEqual(response.answer, "建议尽快线下就医。")
        self.assertEqual(response.structure_source, "fallback")
        self.assertGreaterEqual(len(response.follow_up_questions), 1)

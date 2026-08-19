import unittest

from services.triage_service import assess_symptom_risk


class TriageServiceTests(unittest.TestCase):
    def test_assess_symptom_risk_marks_urgent_cases(self) -> None:
        result = assess_symptom_risk("我现在胸痛，还呼吸困难，怎么办？")
        self.assertEqual(result.risk_level, "urgent")
        self.assertTrue(result.requires_immediate_care)
        self.assertEqual(result.route, "rule_triage")

    def test_assess_symptom_risk_marks_high_cases(self) -> None:
        result = assess_symptom_risk("我已经持续呕吐一天了，吃什么都吐。")
        self.assertEqual(result.risk_level, "high")
        self.assertFalse(result.requires_immediate_care)

    def test_assess_symptom_risk_defaults_to_low(self) -> None:
        result = assess_symptom_risk("我想知道每天喝多少水比较合适。")
        self.assertEqual(result.risk_level, "low")

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from agent.react_agent import create_health_agent
from model.factory import get_chat_model
from services.assistant_service import StructuredHealthResponse, generate_health_response
from services.triage_service import assess_symptom_risk


def _safe_console_text(text: str) -> str:
    encoding = sys.stdout.encoding or "utf-8"
    return str(text).encode(encoding, errors="replace").decode(encoding, errors="replace")


def load_cases(dataset_path: Path) -> list[dict]:
    return json.loads(dataset_path.read_text(encoding="utf-8"))


def evaluate_case(case: dict, *, mode: str, agent=None, formatter_model=None, formatter_strategy: str = "fast") -> dict:
    prompt = str(case["prompt"])
    expected_risk = str(case.get("expected_risk_level", "low"))
    expected_tools = list(case.get("expected_tools", []))
    expected_route = str(case.get("expected_route", "agent_structured"))

    if mode == "triage":
        triage = assess_symptom_risk(prompt)
        response = StructuredHealthResponse(
            answer=triage.immediate_action,
            risk_level=triage.risk_level,
            triage_reason=triage.reason,
            safety_notice=triage.immediate_action,
            follow_up_questions=[],
            used_tools=[],
            route=triage.route,
            structure_source="rule",
        )
    else:
        response = generate_health_response(
            messages=[{"role": "user", "content": prompt}],
            agent=agent,
            formatter_model=formatter_model,
            formatter_strategy=formatter_strategy,
        )

    actual_tools = response.used_tools
    risk_match = response.risk_level == expected_risk
    if mode == "triage":
        tool_match = True
        route_match = response.route == "rule_triage" if expected_risk == "urgent" else True
    else:
        tool_match = all(tool_name in actual_tools for tool_name in expected_tools)
        route_match = response.route == expected_route
    passed = risk_match and tool_match and route_match

    return {
        "id": case["id"],
        "passed": passed,
        "risk_match": risk_match,
        "tool_match": tool_match,
        "route_match": route_match,
        "expected_risk": expected_risk,
        "actual_risk": response.risk_level,
        "expected_tools": expected_tools,
        "actual_tools": actual_tools,
        "expected_route": expected_route,
        "actual_route": response.route,
        "latency_ms": response.latency_ms,
        "tokens_used": response.tokens_used,
        "answer_preview": response.answer[:80],
    }


def print_report(results: list[dict], *, mode: str) -> None:
    passed_count = sum(1 for item in results if item["passed"])
    risk_match_count = sum(1 for item in results if item["risk_match"])
    tool_match_count = sum(1 for item in results if item["tool_match"])
    route_match_count = sum(1 for item in results if item["route_match"])
    total_latency = sum(int(item["latency_ms"]) for item in results)
    total_tokens = sum(int(item["tokens_used"]) for item in results)
    total = max(len(results), 1)

    print(_safe_console_text(f"Mode: {mode}"))
    print(_safe_console_text(f"Cases: {len(results)}"))
    print(_safe_console_text(f"Overall pass rate: {passed_count}/{len(results)} = {passed_count / total:.1%}"))
    print(_safe_console_text(f"Risk match rate: {risk_match_count}/{len(results)} = {risk_match_count / total:.1%}"))
    print(_safe_console_text(f"Tool match rate: {tool_match_count}/{len(results)} = {tool_match_count / total:.1%}"))
    print(_safe_console_text(f"Route match rate: {route_match_count}/{len(results)} = {route_match_count / total:.1%}"))
    if mode == "live":
        print(_safe_console_text(f"Average latency: {total_latency / total:.1f} ms"))
        print(_safe_console_text(f"Average tokens: {total_tokens / total:.1f}"))
    print(_safe_console_text("-" * 80))

    for item in results:
        status = "PASS" if item["passed"] else "FAIL"
        print(
            _safe_console_text(
                f"[{status}] {item['id']} | risk {item['actual_risk']} | "
                f"tools {item['actual_tools']} | route {item['actual_route']} | "
                f"latency {item['latency_ms']} ms"
            )
        )
        if not item["passed"]:
            print(
                _safe_console_text(
                    f"  expected risk={item['expected_risk']} tools={item['expected_tools']} "
                    f"route={item['expected_route']}"
                )
            )
        print(_safe_console_text(f"  answer: {item['answer_preview']}"))


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate HealthMate-AI assistant behavior.")
    parser.add_argument(
        "--dataset",
        default=str(ROOT / "data" / "evals" / "health_eval_cases.json"),
        help="Path to evaluation dataset JSON file.",
    )
    parser.add_argument(
        "--mode",
        choices=["triage", "live"],
        default="triage",
        help="triage 只跑危险分流；live 会调用真实模型和工具。",
    )
    parser.add_argument("--max-cases", type=int, default=0, help="Limit the number of cases to evaluate.")
    parser.add_argument(
        "--formatter-strategy",
        choices=["fast", "model"],
        default="fast",
        help="fast 为本地快速结构化；model 为二次模型整理。",
    )
    args = parser.parse_args()

    dataset_path = Path(args.dataset)
    cases = load_cases(dataset_path)
    if args.max_cases > 0:
        cases = cases[: args.max_cases]

    agent = None
    formatter_model = None
    if args.mode == "live":
        agent = create_health_agent()
        if args.formatter_strategy == "model":
            formatter_model = get_chat_model()

    results = [
        evaluate_case(
            case,
            mode=args.mode,
            agent=agent,
            formatter_model=formatter_model,
            formatter_strategy=args.formatter_strategy,
        )
        for case in cases
    ]
    print_report(results, mode=args.mode)


if __name__ == "__main__":
    main()

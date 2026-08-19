import json
from pathlib import Path


def user_profile_path(user_data_dir: Path, user_id: str) -> Path:
    return user_data_dir / f"{user_id}.json"


def build_profile_payload(
    *,
    weight_plan: dict,
    weather_state: dict,
    diet_log: dict,
    daily_metrics: dict,
) -> dict:
    return {
        "weight_plan": weight_plan,
        "weather_state": weather_state,
        "diet_log": diet_log,
        "daily_metrics": daily_metrics,
    }


def save_user_profile(
    user_data_dir: Path,
    user_id: str,
    *,
    weight_plan: dict,
    weather_state: dict,
    diet_log: dict,
    daily_metrics: dict,
) -> bool:
    if not user_id:
        return False

    user_data_dir.mkdir(parents=True, exist_ok=True)
    payload = build_profile_payload(
        weight_plan=weight_plan,
        weather_state=weather_state,
        diet_log=diet_log,
        daily_metrics=daily_metrics,
    )
    user_profile_path(user_data_dir, user_id).write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return True


def load_user_profile(user_data_dir: Path, user_id: str) -> dict | None:
    path = user_profile_path(user_data_dir, user_id)
    if not path.exists():
        return None

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None

    return payload if isinstance(payload, dict) else None

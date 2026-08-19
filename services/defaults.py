def build_default_messages() -> list[dict[str, str]]:
    return [
        {
            "role": "assistant",
            "content": "你好，我是 HealthMate-AI。你可以问我睡眠、饮食、运动、压力管理等问题。",
        }
    ]


def build_default_weight_plan() -> dict[str, float | int | str]:
    return {
        "current": 70.0,
        "target": 60.0,
        "months": 2,
        "lost": 2.8,
        "age": 28,
        "height": 170.0,
        "sex": "女",
    }


def build_default_diet_log() -> dict[str, object]:
    return {
        "breakfast": "燕麦粥 30g + 水煮蛋 1个 + 苹果 1个",
        "lunch": "鸡胸肉 150g + 糙米饭 半碗 + 蔬菜沙拉",
        "dinner": "清蒸鱼 150g + 西兰花 + 小米粥 小碗",
        "done": {"breakfast": True, "lunch": True, "dinner": True},
        "calories": {"breakfast": 320, "lunch": 520, "dinner": 430},
        "macros": {"protein": 65, "carbs": 180, "fat": 38},
    }


def build_default_daily_metrics() -> dict[str, int | float]:
    return {
        "steps_done": 4200,
        "water_done": 800,
        "sleep_hours": 7.2,
    }

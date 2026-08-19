from datetime import date, timedelta


MEAL_NAMES = ("breakfast", "lunch", "dinner")


def bmi_tag(bmi: float) -> str:
    if bmi < 18.5:
        return "偏瘦"
    if bmi < 24:
        return "正常"
    if bmi < 28:
        return "超重"
    return "肥胖"


def safe_ratio(value: float, total: float) -> float:
    if total <= 0:
        return 0.0
    return max(0.0, min(value / total, 1.0))


def diet_summary(log: dict) -> dict[str, int]:
    done = log.get("done", {})
    calories = log.get("calories", {})
    macros = log.get("macros", {})

    total_calories = 0
    for meal_name in MEAL_NAMES:
        if bool(done.get(meal_name, False)):
            total_calories += int(calories.get(meal_name, 0) or 0)

    return {
        "total_calories": total_calories,
        "protein": int(macros.get("protein", 0) or 0),
        "carbs": int(macros.get("carbs", 0) or 0),
        "fat": int(macros.get("fat", 0) or 0),
    }


def macro_status(value: int, target: int, tolerance: float = 0.1) -> str:
    low = int(target * (1 - tolerance))
    high = int(target * (1 + tolerance))
    if value < low:
        return f"偏低（目标 {target}g）"
    if value > high:
        return f"偏高（目标 {target}g）"
    return f"达标（目标 {target}g）"


def build_macro_targets(weight: float, target_calories: int) -> dict[str, int]:
    protein = max(int(round(weight * 1.6)), 60)
    fat = max(int(round(weight * 0.8)), 35)
    remaining_calories = max(target_calories - protein * 4 - fat * 9, 320)
    carbs = max(int(round(remaining_calories / 4)), 80)
    return {
        "protein": protein,
        "carbs": carbs,
        "fat": fat,
    }


def build_daily_meal_plan(
    *,
    bmi: float,
    calorie_gap: int,
    sleep_hours: float,
    steps_done: int,
    step_goal: int,
    water_done: int,
    water_goal: int,
    target_calories: int,
) -> dict[str, object]:
    breakfast = ["燕麦 35g", "鸡蛋 1个", "无糖酸奶 120g"]
    lunch = ["鸡胸肉 150g", "糙米饭 半碗", "蔬菜 2拳"]
    dinner = ["鱼虾或豆腐 150g", "绿叶菜 2拳", "杂粮 半碗"]
    note = "三餐尽量固定时间，先吃蛋白质和蔬菜。"

    if sleep_hours < 6.5:
        breakfast = ["燕麦 40g", "鸡蛋 2个（1全蛋+1蛋白）", "香蕉 1根"]
        note = "睡眠不足当天更容易饥饿，优先高蛋白早餐并减少甜食。"

    if bmi >= 28:
        lunch[1] = "糙米饭 1/3碗"
        dinner[2] = "杂粮 1/3碗"
    elif bmi < 18.5:
        lunch[1] = "糙米饭 1碗"
        dinner[2] = "杂粮 3/4碗"

    if calorie_gap < -150:
        dinner = ["清蒸鱼 120g", "蔬菜 2-3拳", "不额外加主食或仅 1/4碗"]
    elif calorie_gap > 250:
        lunch.append("加红薯 100g")
        dinner.append("加豆制品 80g")

    if steps_done < int(step_goal * 0.6):
        dinner[2] = "主食减至 1/3-1/2碗"

    if water_done < int(water_goal * 0.7):
        note += " 今天饮水偏少，下午和晚间分次补水。"

    breakfast_cal = int(target_calories * 0.28)
    lunch_cal = int(target_calories * 0.40)
    dinner_cal = int(target_calories * 0.32)
    if calorie_gap < -150:
        dinner_cal = int(dinner_cal * 0.85)
    if steps_done >= step_goal and calorie_gap > 100:
        breakfast_cal = int(breakfast_cal * 1.05)
        lunch_cal = int(lunch_cal * 1.05)

    total_cal = breakfast_cal + lunch_cal + dinner_cal

    return {
        "breakfast": breakfast,
        "lunch": lunch,
        "dinner": dinner,
        "breakfast_calories": breakfast_cal,
        "lunch_calories": lunch_cal,
        "dinner_calories": dinner_cal,
        "total_calories": total_cal,
        "calories": target_calories,
        "note": note,
    }


def build_daily_exercise_plan(
    *,
    bmi: float,
    sleep_hours: float,
    steps_done: int,
    step_goal: int,
    water_goal: int,
    weather_temp: int,
) -> list[str]:
    step_gap = max(step_goal - steps_done, 0)
    outdoor_ok = weather_temp < 32

    if sleep_hours < 6.5:
        return [
            f"低强度恢复日：轻松步行 {max(step_gap, 4000)} 步（20-40 分钟）",
            "拉伸 + 呼吸训练 15 分钟，避免高强度间歇",
            f"饮水至少 {water_goal} ml，分 6-8 次补充",
        ]

    cardio = (
        f"户外快走/慢跑 {max(step_gap, 5000)} 步（35-50 分钟）"
        if outdoor_ok
        else f"室内单车/椭圆机 30-40 分钟，补齐约 {max(step_gap, 5000)} 步活动量"
    )

    if bmi >= 28:
        strength = "低冲击力量训练 20 分钟（深蹲、臀桥、平板支撑）"
    elif bmi < 18.5:
        strength = "基础抗阻 25 分钟（弹力带划船、深蹲、俯卧撑）"
    else:
        strength = "全身力量训练 20-25 分钟（下肢+核心）"

    return [
        cardio,
        strength,
        f"训练后拉伸 8-10 分钟；全天饮水目标 {water_goal} ml",
    ]


def estimate_plan_timeline(current_weight: float, target_weight: float, months: int, lost_weight: float) -> dict[str, object]:
    delta = max(current_weight - target_weight, 0.0)
    progress = 0.0 if delta == 0 else safe_ratio(lost_weight, delta)
    remaining = max(delta - lost_weight, 0.0)
    eta_date = date.today() + timedelta(days=months * 30)
    weekly_target = delta / max(months * 4, 1)
    spent_weeks = lost_weight / weekly_target if weekly_target > 0 else 0
    remaining_weeks = max(int(months * 4 - spent_weeks), 0)
    return {
        "delta": delta,
        "progress": progress,
        "remaining": remaining,
        "eta_date": eta_date,
        "weekly_target": weekly_target,
        "remaining_weeks": remaining_weeks,
    }

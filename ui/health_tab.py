from typing import Callable

import streamlit as st

from services.defaults import build_default_daily_metrics, build_default_diet_log, build_default_weight_plan
from services.health_plans import (
    bmi_tag,
    build_daily_exercise_plan,
    build_daily_meal_plan,
    build_macro_targets,
    diet_summary,
    estimate_plan_timeline,
    macro_status,
    safe_ratio,
)
from utils.health_utils import calculate_bmi, get_step_goal, get_water_goal


# 保证体重计划数据格式正确
def _ensure_weight_plan_shape(plan: dict) -> dict:
    defaults = build_default_weight_plan()
    merged = defaults.copy()
    merged.update({key: value for key, value in plan.items() if key in merged})
    return merged


# 保证每日步数、饮水、睡眠数据格式正确
def _ensure_daily_metrics_shape(daily: dict) -> dict:
    defaults = build_default_daily_metrics()
    merged = defaults.copy()
    merged.update({key: value for key, value in daily.items() if key in merged})
    return merged


# 保证饮食记录（早中晚、热量、蛋白质）格式正确
def _ensure_diet_log_shape(diet_log: dict) -> dict:
    defaults = build_default_diet_log()
    merged = {
        "breakfast": str(diet_log.get("breakfast", defaults["breakfast"])),
        "lunch": str(diet_log.get("lunch", defaults["lunch"])),
        "dinner": str(diet_log.get("dinner", defaults["dinner"])),
        "done": defaults["done"].copy(),
        "calories": defaults["calories"].copy(),
        "macros": defaults["macros"].copy(),
    }

    merged["done"].update(
        {
            meal_name: bool(diet_log.get("done", {}).get(meal_name, defaults["done"][meal_name]))
            for meal_name in defaults["done"]
        }
    )
    merged["calories"].update(
        {
            meal_name: int(diet_log.get("calories", {}).get(meal_name, defaults["calories"][meal_name]) or 0)
            for meal_name in defaults["calories"]
        }
    )
    merged["macros"].update(
        {
            macro_name: int(diet_log.get("macros", {}).get(macro_name, defaults["macros"][macro_name]) or 0)
            for macro_name in defaults["macros"]
        }
    )
    return merged


# 渲染【饮食记录表单】
def _render_diet_log_editor(diet_log: dict) -> dict:
    st.markdown("**今日饮食记录**")
    c1, c2, c3 = st.columns(3)
    with c1:
        breakfast_done = st.checkbox("早餐已记录", value=diet_log["done"]["breakfast"])
        breakfast = st.text_area("早餐内容", value=diet_log["breakfast"], height=96)
        breakfast_cal = st.number_input("早餐热量", min_value=0, max_value=2000, value=diet_log["calories"]["breakfast"], step=10)
    with c2:
        lunch_done = st.checkbox("午餐已记录", value=diet_log["done"]["lunch"])
        lunch = st.text_area("午餐内容", value=diet_log["lunch"], height=96)
        lunch_cal = st.number_input("午餐热量", min_value=0, max_value=2500, value=diet_log["calories"]["lunch"], step=10)
    with c3:
        dinner_done = st.checkbox("晚餐已记录", value=diet_log["done"]["dinner"])
        dinner = st.text_area("晚餐内容", value=diet_log["dinner"], height=96)
        dinner_cal = st.number_input("晚餐热量", min_value=0, max_value=2000, value=diet_log["calories"]["dinner"], step=10)

    m1, m2, m3 = st.columns(3)
    with m1:
        protein = st.number_input("蛋白质 (g)", min_value=0, max_value=400, value=diet_log["macros"]["protein"], step=5)
    with m2:
        carbs = st.number_input("碳水 (g)", min_value=0, max_value=600, value=diet_log["macros"]["carbs"], step=5)
    with m3:
        fat = st.number_input("脂肪 (g)", min_value=0, max_value=300, value=diet_log["macros"]["fat"], step=5)

    return {
        "breakfast": breakfast.strip(),
        "lunch": lunch.strip(),
        "dinner": dinner.strip(),
        "done": {
            "breakfast": breakfast_done,
            "lunch": lunch_done,
            "dinner": dinner_done,
        },
        "calories": {
            "breakfast": int(breakfast_cal),
            "lunch": int(lunch_cal),
            "dinner": int(dinner_cal),
        },
        "macros": {
            "protein": int(protein),
            "carbs": int(carbs),
            "fat": int(fat),
        },
    }


# 核心主函数：整个健康管理页面全流程
def render_health_tab(*, on_save_profile: Callable[[], bool]) -> None:
    st.subheader("📊 健康管理")

    plan = _ensure_weight_plan_shape(st.session_state.get("weight_plan", {}))
    daily = _ensure_daily_metrics_shape(st.session_state.get("daily_metrics", {}))
    diet_log = _ensure_diet_log_shape(st.session_state.get("diet_log", {}))

    st.markdown("**我的身体数据**")
    c1, c2 = st.columns(2)
    with c1:
        plan["height"] = st.number_input("身高 (cm)", 120.0, 220.0, float(plan["height"]), 0.5)
    with c2:
        plan["current"] = st.number_input("当前体重 (kg)", 35.0, 180.0, float(plan["current"]), 0.1)

    bmi = calculate_bmi(float(plan["current"]), float(plan["height"]))
    b1, b2, b3 = st.columns(3)
    with b1:
        st.metric("身高", f"{plan['height']:.1f} cm")
    with b2:
        st.metric("体重", f"{plan['current']:.1f} kg")
    with b3:
        st.metric("BMI", f"{bmi:.1f}", bmi_tag(bmi))

    st.markdown("**我的减脂计划**")
    st.markdown('<div class="hma-card">', unsafe_allow_html=True)
    st.markdown("目标设定")
    p1, p2, p3, p4 = st.columns(4)
    with p1:
        plan["target"] = st.number_input("🎯 目标体重 (kg)", 35.0, 180.0, float(plan["target"]), 0.1)
    with p2:
        plan["months"] = st.number_input("⏱️ 减脂周期 (月)", min_value=1, value=int(plan["months"]), step=1)
    with p3:
        plan["age"] = st.number_input("🎂 年龄", 10, 100, int(plan["age"]))
    with p4:
        plan["sex"] = st.selectbox("性别", ["女", "男"], index=0 if plan["sex"] == "女" else 1)

    timeline = estimate_plan_timeline(
        current_weight=float(plan["current"]),
        target_weight=float(plan["target"]),
        months=int(plan["months"]),
        lost_weight=float(min(plan.get("lost", 0.0), max(float(plan["current"]) - float(plan["target"]), 0.1))),
    )
    max_lost = max(float(timeline["delta"]), 0.1)
    plan["lost"] = st.slider("已减重 (kg)", 0.0, max_lost, min(float(plan.get("lost", 0.0)), max_lost), 0.1)
    timeline = estimate_plan_timeline(
        current_weight=float(plan["current"]),
        target_weight=float(plan["target"]),
        months=int(plan["months"]),
        lost_weight=float(plan["lost"]),
    )
    target_bmi = calculate_bmi(float(plan["target"]), float(plan["height"]))

    st.markdown("减重进度")
    st.caption(f"当前 {plan['current']:.1f} kg  →  目标 {plan['target']:.1f} kg")
    st.progress(float(timeline["progress"]), text=f"进度 {float(timeline['progress']) * 100:.0f}%")
    st.caption(
        f"已减 {plan['lost']:.1f} kg · 还需 {float(timeline['remaining']):.1f} kg · 进度 {float(timeline['progress']) * 100:.0f}%"
    )

    weekly_target = float(timeline["weekly_target"])
    speed_state = "✅ 健康速度" if 0 < weekly_target <= 1.5 else "⚠️ 建议放缓"
    k1, k2, k3 = st.columns(3)
    with k1:
        st.metric("📊 目标BMI", f"{target_bmi:.1f}", bmi_tag(target_bmi))
    with k2:
        st.metric("⚡ 建议速度", f"{weekly_target:.2f} kg/周", speed_state)
    with k3:
        st.metric("📅 预计达成", timeline["eta_date"].isoformat(), f"还剩 {int(timeline['remaining_weeks'])} 周")

    st.info("💡 减脂小贴士：每周固定 1 次晨起空腹称重；偶尔偏离计划，第二天回归即可。")
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("**今日身体记录**")
    st.markdown('<div class="hma-card">', unsafe_allow_html=True)
    d1, d2, d3 = st.columns(3)
    with d1:
        steps_done = st.slider("今日步数", 0, 30000, int(daily.get("steps_done", 4200)), 100)
    with d2:
        water_done = st.slider("今日饮水 (ml)", 0, 6000, int(daily.get("water_done", 800)), 100)
    with d3:
        sleep_hours = st.slider("昨晚睡眠 (h)", 0.0, 12.0, float(daily.get("sleep_hours", 7.2)), 0.1)

    daily = {
        "steps_done": int(steps_done),
        "water_done": int(water_done),
        "sleep_hours": float(sleep_hours),
    }
    st.session_state.daily_metrics = daily

    st.session_state.diet_log = _render_diet_log_editor(diet_log)
    summary = diet_summary(st.session_state.diet_log)

    target_calories = int(max(1200, float(plan["current"]) * 30 - 500))
    macro_targets = build_macro_targets(float(plan["current"]), target_calories)
    weather_state = st.session_state.get("weather_state", {})
    weather_temp = int(weather_state.get("temp", 25) or 25)
    water_goal = int(get_water_goal(float(plan["current"]), weather_temp))
    step_goal = get_step_goal(int(plan["age"]))
    calorie_gap = target_calories - summary["total_calories"]
    sleep_ratio = safe_ratio(float(sleep_hours), 8.0)

    meal_plan = build_daily_meal_plan(
        bmi=bmi,
        calorie_gap=calorie_gap,
        sleep_hours=float(sleep_hours),
        steps_done=int(steps_done),
        step_goal=step_goal,
        water_done=int(water_done),
        water_goal=water_goal,
        target_calories=target_calories,
    )
    exercise_plan = build_daily_exercise_plan(
        bmi=bmi,
        sleep_hours=float(sleep_hours),
        steps_done=int(steps_done),
        step_goal=step_goal,
        water_goal=water_goal,
        weather_temp=weather_temp,
    )

    intake1, intake2, intake3, intake4 = st.columns(4)
    with intake1:
        st.metric("已记录热量", f"{summary['total_calories']} 千卡", f"目标 {target_calories}")
    with intake2:
        st.metric("蛋白质", f"{summary['protein']} g", macro_status(summary["protein"], macro_targets["protein"]))
    with intake3:
        st.metric("碳水", f"{summary['carbs']} g", macro_status(summary["carbs"], macro_targets["carbs"]))
    with intake4:
        st.metric("脂肪", f"{summary['fat']} g", macro_status(summary["fat"], macro_targets["fat"]))

    r1, r2, r3 = st.columns(3)
    with r1:
        step_progress = safe_ratio(int(steps_done), step_goal)
        st.metric("🚶 今日步数", f"{int(steps_done):,} 步", f"目标 {step_goal}")
        st.progress(step_progress, text=f"{step_progress * 100:.0f}%")
    with r2:
        water_progress = safe_ratio(int(water_done), water_goal)
        st.metric("💧 今日饮水", f"{int(water_done)} ml", f"目标 {water_goal}")
        st.progress(water_progress, text=f"{water_progress * 100:.0f}%")
    with r3:
        st.metric("😴 昨晚睡眠", f"{float(sleep_hours):.1f} 小时", "目标 7-9 小时")
        st.progress(sleep_ratio, text=f"{sleep_ratio * 100:.0f}%")

    st.markdown("**今日饮食推荐**")
    m1, m2, m3 = st.columns(3)
    with m1:
        st.markdown(
            "<div class='hma-card'><b>🌅 早餐</b><br/>"
            + "<br/>".join(meal_plan["breakfast"])
            + f"<br/><span class='hma-muted'>热量：{meal_plan['breakfast_calories']} 千卡</span></div>",
            unsafe_allow_html=True,
        )
    with m2:
        st.markdown(
            "<div class='hma-card'><b>🌞 午餐</b><br/>"
            + "<br/>".join(meal_plan["lunch"])
            + f"<br/><span class='hma-muted'>热量：{meal_plan['lunch_calories']} 千卡</span></div>",
            unsafe_allow_html=True,
        )
    with m3:
        st.markdown(
            "<div class='hma-card'><b>🌙 晚餐</b><br/>"
            + "<br/>".join(meal_plan["dinner"])
            + f"<br/><span class='hma-muted'>热量：{meal_plan['dinner_calories']} 千卡</span></div>",
            unsafe_allow_html=True,
        )
    st.caption(f"🔥 推荐总热量：{meal_plan['total_calories']} 千卡")

    st.markdown("**今日运动推荐**")
    st.markdown(
        f"""
<div class="hma-card" style="margin-top: 0.5rem;">
  1) {exercise_plan[0]}<br/>
  2) {exercise_plan[1]}<br/>
  3) {exercise_plan[2]}
</div>
""",
        unsafe_allow_html=True,
    )

    tips = []
    if calorie_gap < -150:
        tips.append("今日摄入偏高，晚餐主食减半并取消含糖饮料。")
    elif calorie_gap > 250:
        tips.append("今日摄入偏低，可增加全谷物和优质蛋白。")
    else:
        tips.append("热量控制合理，继续保持。")
    if int(steps_done) < step_goal:
        tips.append("步数未达标，晚间补走 20-30 分钟。")
    if int(water_done) < water_goal:
        tips.append("饮水偏少，分次补水至目标。")
    if not 7 <= float(sleep_hours) <= 9:
        tips.append("睡眠建议保持 7-9 小时。")

    action = f"今日行动：{meal_plan['note']}"
    st.info("📝 个性化建议：" + " ".join(tips[:3]) + " " + action)
    st.markdown("</div>", unsafe_allow_html=True)

    st.session_state.weight_plan = plan
    on_save_profile()

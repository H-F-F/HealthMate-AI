from langchain.tools import tool

from utils.health_utils import calculate_bmi, get_step_goal, get_water_goal


@tool
def calculate_bmi_tool(weight: float, height: float) -> str:
    """根据身高体重计算BMI，并给出体重区间判断。"""
    bmi = calculate_bmi(weight, height)
    if bmi < 18.5:
        category = "偏瘦"
    elif bmi < 24:
        category = "正常"
    elif bmi < 28:
        category = "超重"
    else:
        category = "肥胖"
    return f"您的BMI为 {bmi:.1f}，属于{category}范围。健康BMI建议保持在18.5-24。"


@tool
def get_water_goal_tool(weight: float, temperature: int = 25) -> str:
    """根据体重和气温推荐每日饮水量。"""
    total_ml = get_water_goal(weight, temperature)
    return f"建议每日饮水约 {int(total_ml)} 毫升（约 {total_ml / 1000:.1f} 升）。"


@tool
def get_step_goal_tool(age: int) -> str:
    """根据年龄给出每日步数建议。"""
    goal = get_step_goal(age)
    return f"根据您的年龄，建议每日步数目标为 {goal} 步。"


HEALTH_TOOLS = [
    calculate_bmi_tool,
    get_water_goal_tool,
    get_step_goal_tool,
]

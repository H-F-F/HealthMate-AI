def _normalize_height_cm(height_value: float) -> float:
    """Accept height in either centimeters or meters and normalize to centimeters."""
    if 0 < height_value < 10:
        return height_value * 100
    return height_value


def calculate_bmi(weight: float, height_cm: float) -> float:
    normalized_height_cm = _normalize_height_cm(height_cm)
    if weight <= 0 or normalized_height_cm <= 0:
        raise ValueError("体重和身高必须大于 0")
    return weight / ((normalized_height_cm / 100) ** 2)


def get_water_goal(weight: float, temperature: int = 25) -> float:
    if weight <= 0:
        raise ValueError("体重必须大于 0")
    base = weight * 30
    if temperature > 30:
        extra = 500
    elif temperature < 10:
        extra = -200
    else:
        extra = 0
    return max(base + extra, 1000)


def get_step_goal(age: int) -> int:
    if age < 0:
        raise ValueError("年龄不能为负数")
    if age < 18:
        return 10000
    if age < 65:
        return 8000
    return 6000

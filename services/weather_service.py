import json
import os
from datetime import date, timedelta
from urllib.parse import quote
from urllib.request import urlopen

import streamlit as st


def build_mock_weather_by_city(province: str = "", city: str = "", district: str = "") -> dict:
    province = province.strip()
    city = city.strip() or "汉中"
    district = district.strip()
    location = f"{province}{city}{district}"
    seed = sum((idx + 1) * ord(ch) for idx, ch in enumerate(location))

    weather_options = ["晴", "多云", "小雨", "阴"]
    weather = weather_options[seed % len(weather_options)]
    temp = 18 + seed % 15
    wind_power = f"{1 + seed % 4}级"
    humidity = 35 + seed % 45
    pressure = 996 + seed % 31
    uv = "较强" if weather == "晴" and temp >= 28 else ("中等" if weather in {"晴", "多云"} else "弱")
    air = "优" if humidity < 55 else ("良" if humidity < 75 else "轻度污染")
    icon_map = {"晴": "☀️", "多云": "⛅", "小雨": "🌧️", "阴": "☁️"}
    wind_direction = "北风"

    return {
        "province": province,
        "city": city,
        "district": district,
        "weather": weather,
        "icon": icon_map[weather],
        "temp": temp,
        "feels_like": temp + (1 if humidity > 60 else -1),
        "humidity": humidity,
        "wind_direction": wind_direction,
        "wind_power": wind_power,
        "wind": f"{wind_direction}{wind_power}",
        "uv": uv,
        "air": air,
        "pressure": pressure,
        "date": date.today().strftime("%Y-%m-%d"),
        "weather_date": date.today().isoformat(),
    }


def build_mock_forecast(weather_state: dict) -> list[dict[str, object]]:
    base_temp = int(weather_state.get("temp", 24) or 24)
    weather = str(weather_state.get("weather", "多云") or "多云")
    icon = str(weather_state.get("icon", "⛅") or "⛅")
    forecast = []

    for index in range(3):
        current_day = date.today() + timedelta(days=index + 1)
        high_temp = base_temp + (1 - index)
        low_temp = max(base_temp - 8 - index * 2, -10)
        forecast.append(
            {
                "date": current_day.isoformat(),
                "week_label": ["周一", "周二", "周三", "周四", "周五", "周六", "周日"][current_day.weekday()],
                "dayweather": weather,
                "nightweather": weather,
                "icon": icon,
                "daytemp": high_temp,
                "nighttemp": low_temp,
            }
        )

    return forecast


def _get_amap_key() -> str:
    return os.getenv("AMAP_API_KEY", "").strip()


@st.cache_data(ttl=3600)
def detect_location_by_ip() -> dict | None:
    try:
        key = _get_amap_key()
        if not key:
            return None

        ip_url = f"https://restapi.amap.com/v3/ip?key={key}&output=json"
        with urlopen(ip_url, timeout=8) as response:
            payload = json.loads(response.read().decode("utf-8"))

        if str(payload.get("status")) != "1":
            return None

        province = str(payload.get("province") or "").strip()
        city_data = payload.get("city")
        city = city_data if isinstance(city_data, str) else ""
        if not city and isinstance(city_data, list) and city_data:
            city = str(city_data[0])
        city = city.strip()
        adcode = str(payload.get("adcode") or "").strip()
        if not city and not adcode:
            return None

        return {"province": province, "city": city, "district": "", "adcode": adcode}
    except Exception:
        return None


@st.cache_data(ttl=86400)
def get_district_children(keyword: str) -> list[dict]:
    key = _get_amap_key()
    if not key:
        return []

    query = quote((keyword or "中国").strip())
    try:
        url = (
            "https://restapi.amap.com/v3/config/district"
            f"?key={key}&keywords={query}&subdistrict=1&extensions=base&output=json"
        )
        with urlopen(url, timeout=8) as response:
            payload = json.loads(response.read().decode("utf-8"))
        if str(payload.get("status")) != "1":
            return []

        top = (payload.get("districts") or [{}])[0]
        return top.get("districts") or []
    except Exception:
        return []


@st.cache_data(ttl=86400)
def get_district_info(keyword: str) -> dict | None:
    key = _get_amap_key()
    if not key:
        return None

    query = quote((keyword or "").strip())
    if not query:
        return None

    try:
        url = (
            "https://restapi.amap.com/v3/config/district"
            f"?key={key}&keywords={query}&subdistrict=0&extensions=base&output=json"
        )
        with urlopen(url, timeout=8) as response:
            payload = json.loads(response.read().decode("utf-8"))
        if str(payload.get("status")) != "1":
            return None

        districts = payload.get("districts") or []
        return districts[0] if districts else None
    except Exception:
        return None


@st.cache_data(ttl=86400)
def get_province_options() -> list[dict]:
    provinces = get_district_children("中国")
    return [item for item in provinces if item.get("level") == "province"]


@st.cache_data(ttl=86400)
def get_city_options(province_adcode: str) -> list[dict]:
    cities = get_district_children(province_adcode)
    return [item for item in cities if item.get("level") == "city"]


@st.cache_data(ttl=86400)
def get_district_options(city_adcode: str) -> list[dict]:
    districts = get_district_children(city_adcode)
    return [item for item in districts if item.get("level") in {"district", "street", "biz_area"} or item.get("adcode")]


@st.cache_data(ttl=600)
def fetch_realtime_weather_by_adcode(
    adcode: str,
    province: str = "",
    city: str = "",
    district: str = "",
) -> dict | None:
    adcode = (adcode or "").strip()
    if not adcode:
        return None

    try:
        key = _get_amap_key()
        if not key:
            return None

        weather_url = (
            "https://restapi.amap.com/v3/weather/weatherInfo"
            f"?key={key}&city={adcode}&extensions=base&output=json"
        )
        with urlopen(weather_url, timeout=8) as response:
            payload = json.loads(response.read().decode("utf-8"))
        if str(payload.get("status")) != "1":
            return None

        lives = payload.get("lives") or []
        if not lives:
            return None

        live = lives[0]
        weather = str(live.get("weather") or "阴")
        if "雨" in weather:
            icon = "🌧️"
        elif "云" in weather:
            icon = "⛅"
        elif "晴" in weather:
            icon = "☀️"
        elif "雪" in weather:
            icon = "🌨️"
        elif "雷" in weather:
            icon = "⛈️"
        else:
            icon = "☁️"

        report_time = str(live.get("reporttime") or "")
        weather_date = report_time.split(" ")[0] if report_time else date.today().isoformat()
        # Keep the user-selected province/city when available.
        # District-level AMap weather queries may return the district name in `city`,
        # which breaks province/city/district selector restoration on next login.
        display_province = province.strip() or str(live.get("province") or "").strip()
        display_city = city.strip() or str(live.get("city") or "").strip()
        display_district = district.strip()
        wind_direction = str(live.get("winddirection") or "风")
        raw_wind_power = str(live.get("windpower") or "").strip()
        wind_power = f"{raw_wind_power}级" if raw_wind_power else "1级"

        return {
            "province": display_province,
            "city": display_city,
            "district": display_district,
            "adcode": adcode,
            "weather": weather,
            "icon": icon,
            "temp": int(float(live.get("temperature", 0) or 0)),
            "feels_like": int(float(live.get("temperature", 0) or 0)),
            "humidity": int(float(live.get("humidity", 0) or 0)),
            "wind_direction": wind_direction,
            "wind_power": wind_power or "1级",
            "wind": f"{wind_direction}{wind_power or '1级'}",
            "uv": "中等",
            "air": "良",
            "pressure": 1013,
            "date": weather_date,
            "weather_date": weather_date,
        }
    except Exception:
        return None


@st.cache_data(ttl=600)
def fetch_forecast_by_adcode(adcode: str) -> list[dict[str, object]]:
    adcode = (adcode or "").strip()
    if not adcode:
        return []

    key = _get_amap_key()
    if not key:
        return []

    try:
        url = (
            "https://restapi.amap.com/v3/weather/weatherInfo"
            f"?key={key}&city={adcode}&extensions=all&output=json"
        )
        with urlopen(url, timeout=8) as response:
            payload = json.loads(response.read().decode("utf-8"))
        if str(payload.get("status")) != "1":
            return []

        forecasts = payload.get("forecasts") or []
        if not forecasts:
            return []

        cast_list = forecasts[0].get("casts") or []
        week_map = {
            "1": "周一",
            "2": "周二",
            "3": "周三",
            "4": "周四",
            "5": "周五",
            "6": "周六",
            "7": "周日",
        }
        items: list[dict[str, object]] = []
        for cast in cast_list[:3]:
            day_weather = str(cast.get("dayweather") or "阴")
            if "雨" in day_weather:
                icon = "🌧️"
            elif "云" in day_weather:
                icon = "⛅"
            elif "晴" in day_weather:
                icon = "☀️"
            elif "雪" in day_weather:
                icon = "🌨️"
            else:
                icon = "☁️"

            items.append(
                {
                    "date": str(cast.get("date") or ""),
                    "week_label": week_map.get(str(cast.get("week") or ""), ""),
                    "dayweather": day_weather,
                    "nightweather": str(cast.get("nightweather") or day_weather),
                    "daytemp": int(float(cast.get("daytemp", 0) or 0)),
                    "nighttemp": int(float(cast.get("nighttemp", 0) or 0)),
                    "icon": icon,
                }
            )
        return items
    except Exception:
        return []


def build_default_weather_state() -> dict:
    # 启动时优先尝试真实定位和实时天气；
    # 如果没有 key 或接口失败，也要回退到稳定的演示天气，保证页面可用。
    location = detect_location_by_ip()
    if location:
        latest = fetch_realtime_weather_by_adcode(
            location.get("adcode", ""),
            location.get("province", ""),
            location.get("city", ""),
            location.get("district", ""),
        )
        if latest:
            return latest
    return build_mock_weather_by_city("", "汉中", "")

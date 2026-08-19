from datetime import date
from typing import Callable

import streamlit as st

from services.weather_service import (
    build_mock_forecast,
    build_mock_weather_by_city,
    detect_location_by_ip,
    fetch_forecast_by_adcode,
    fetch_realtime_weather_by_adcode,
    get_city_options,
    get_district_info,
    get_district_options,
    get_province_options,
)


# 整个天气页面的唯一主函数负责：UI 渲染 + 定位逻辑 + 天气查询 + 数据展示 + 保存
def render_weather_tab(*, on_save_profile: Callable[[], bool]) -> None:
    st.subheader("🌤️ 实时天气")
    weather = st.session_state.weather_state
    today = date.today().isoformat()
    if weather.get("weather_date") != today and weather.get("adcode"):
        latest = fetch_realtime_weather_by_adcode(
            weather.get("adcode", ""),
            weather.get("province", ""),
            weather.get("city", "汉中"),
            weather.get("district", ""),
        )
        if latest:
            st.session_state.weather_state = latest
            weather = latest

    provinces = get_province_options()
    if not provinces:
        st.warning("未获取到行政区数据，请检查 `AMAP_API_KEY`。")
        return

    province_names = [str(item.get("name", "")) for item in provinces]
    default_province = weather.get("province", "")
    province_index = province_names.index(default_province) if default_province in province_names else 0

    p1, p2, p3, p4, p5 = st.columns([2.2, 2.2, 2.2, 1, 1.4])
    with p1:
        province = st.selectbox("省", options=province_names, index=province_index)
    province_item = next((item for item in provinces if item.get("name") == province), provinces[0])
    province_adcode = str(province_item.get("adcode", ""))

    city_options = get_city_options(province_adcode)
    city_names = [str(item.get("name", "")) for item in city_options] or [weather.get("city", "")]
    default_city = weather.get("city", "")
    city_index = city_names.index(default_city) if default_city in city_names else 0
    with p2:
        city = st.selectbox("市", options=city_names, index=city_index)
    city_item = next((item for item in city_options if item.get("name") == city), city_options[0] if city_options else {"adcode": ""})
    city_adcode = str(city_item.get("adcode", ""))

    district_options = get_district_options(city_adcode)
    district_names = [str(item.get("name", "")) for item in district_options]
    default_district = weather.get("district", "")
    if not district_names:
        district_names = [default_district or "无"]
    district_index = district_names.index(default_district) if default_district in district_names else 0
    with p3:
        district = st.selectbox("区县", options=district_names, index=district_index)
    district_item = next((item for item in district_options if item.get("name") == district), {"adcode": city_adcode})
    district_adcode = str(district_item.get("adcode", city_adcode))

    with p4:
        st.markdown("<div style='height: 1.8rem;'></div>", unsafe_allow_html=True)
        query = st.button("查询", use_container_width=True)
    with p5:
        st.markdown("<div style='height: 1.8rem;'></div>", unsafe_allow_html=True)
        locate = st.button("自动定位", use_container_width=True)

    if locate:
        location = detect_location_by_ip()
        if location:
            info = get_district_info(location.get("adcode", "")) or {}
            level = str(info.get("level", ""))
            district_name = location.get("district", "")
            if level == "district":
                district_name = str(info.get("name", district_name))

            latest = fetch_realtime_weather_by_adcode(
                location.get("adcode", ""),
                location.get("province", ""),
                location.get("city", ""),
                district_name,
            )
            state = latest if latest else build_mock_weather_by_city(
                location.get("province", ""),
                location.get("city", "汉中"),
                district_name,
            )
            state["province"] = location.get("province", state.get("province", ""))
            state["city"] = location.get("city", state.get("city", ""))
            state["district"] = district_name
            state["adcode"] = location.get("adcode", state.get("adcode", ""))
            st.session_state.weather_state = state
            weather = st.session_state.weather_state
            source = "实时数据" if latest else "演示数据"
            st.toast(f"已自动定位到 {weather.get('province', '')} {weather['city']} {weather.get('district', '')}（{source}）")
            on_save_profile()
            st.rerun()
        else:
            st.warning("自动定位失败，请手动输入省/市/区。")

    if query:
        latest = fetch_realtime_weather_by_adcode(district_adcode, province, city, "" if district == "无" else district)
        st.session_state.weather_state = latest if latest else build_mock_weather_by_city(
            province,
            city,
            "" if district == "无" else district,
        )
        st.session_state.weather_state["adcode"] = district_adcode
        weather = st.session_state.weather_state
        source = "实时数据" if latest else "演示数据"
        st.toast(f"已更新 {province} {weather['city']} {weather.get('district', '')} 的天气（{source}）")
        on_save_profile()

    st.markdown(
        f"""
<div class="hma-card" style="text-align: center; padding: 1rem;">
  <div style="font-size: 1.9rem; font-weight: 600;">{weather.get('icon', '☀️')} {weather['temp']}°C {weather['weather']}</div>
  <div class="hma-muted" style="margin-top: 0.25rem;">日期：{weather.get('date', date.today().strftime('%Y-%m-%d'))}</div>
</div>
""",
        unsafe_allow_html=True,
    )

    m1, m2, m3 = st.columns(3)
    with m1:
        st.metric("体感温度", f"{weather.get('feels_like', weather['temp'])}°C")
    with m2:
        st.metric("湿度", f"{weather.get('humidity', 0)}%")
    with m3:
        st.metric("风力", weather.get("wind", weather.get("wind_power", "-")))

    m4, m5, m6 = st.columns(3)
    with m4:
        st.metric("紫外线", weather.get("uv", "中等"))
    with m5:
        st.metric("气压", f"{weather.get('pressure', 1013)} hPa")
    with m6:
        st.metric("空气质量", weather.get("air", "良"))

    wind_power = str(weather.get("wind_power", ""))
    st.markdown("**💡 健康建议**")
    tips = [
        "☀️ 紫外线较强，户外活动建议帽子和防晒" if weather.get("uv") == "较强" else "☀️ 紫外线中等，外出可做基础防晒",
        "🌬️ 当前风力适中，适合晨练与步行" if wind_power in {"1级", "2级"} else "🌬️ 风力偏大，户外训练注意保暖和补水",
        "🚶 天气舒适，推荐户外散步 30 分钟" if int(weather.get("temp", 25) or 25) < 32 else "🚶 气温偏高，建议改为室内有氧 20-30 分钟",
    ]
    for tip in tips:
        st.markdown(f"- {tip}")

    forecast = fetch_forecast_by_adcode(str(weather.get("adcode", "") or ""))
    forecast_source = "高德天气预报"
    if not forecast:
        forecast = build_mock_forecast(weather)
        forecast_source = "演示趋势（天气接口未返回预报）"

    st.markdown("**📅 未来3天预报**")
    st.caption(f"数据来源：{forecast_source}")
    forecast_columns = st.columns(3)
    for column, item in zip(forecast_columns, forecast[:3]):
        with column:
            st.markdown(
                (
                    "<div class='hma-card'>"
                    f"<b>{item.get('week_label', '')} {item.get('icon', '⛅')}</b><br/>"
                    f"{item.get('daytemp', '--')}° / {item.get('nighttemp', '--')}°<br/>"
                    f"<span class='hma-muted'>{item.get('dayweather', '')}</span>"
                    "</div>"
                ),
                unsafe_allow_html=True,
            )

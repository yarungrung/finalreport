import streamlit as st
import ee
import json
from streamlit.components.v1 import html
from google.oauth2 import service_account

# Streamlit Page Configuration
st.set_page_config(layout="wide", page_title="台灣土地覆蓋變化 (精簡版)", page_icon="🌎")

st.title("台灣土地覆蓋變化分析 (精簡版) 🌍")
st.markdown("此版本只顯示土地覆蓋圖資，並簡化了年份處理。")
st.markdown("---")

# --- GEE Authentication and Initialization ---
try:
    service_account_info = st.secrets["GEE_SERVICE_ACCOUNT"]
    credentials = service_account.Credentials.from_service_account_info(
        service_account_info,
        scopes=["https://www.googleapis.com/auth/earthengine"]
    )
    ee.Initialize(credentials)
    st.sidebar.success("Google Earth Engine 已成功初始化。")
except Exception as e:
    st.sidebar.error(f"Google Earth Engine 初始化失敗：{e}")
    st.sidebar.warning("請確認您已在 Streamlit Secrets 中正確配置 `GEE_SERVICE_ACCOUNT` 金鑰。")
    st.stop() # Stop execution if GEE fails

# --- Global Variables ---
taiwan_aoi = ee.Geometry.Rectangle([119.8, 22.5, 120.8, 23.5]) # Taiwan Southwest coast AOI
coords = taiwan_aoi.centroid().coordinates().getInfo()
center_lon, center_lat = coords[0], coords[1]

# Load GLC_FCS30D dataset
glc_annual = ee.ImageCollection('projects/sat-io/open-datasets/GLC-FCS30D/annual')
glc_five_yearly = ee.ImageCollection('projects/sat-io/open-datasets/GLC-FCS30D/five_yearly')

# --- Land Cover Visualization Parameters and Legend ---
PALETTE = [
    '#00008B',  # 0: Water (Dark Blue)
    '#DCDCDC',  # 10: Permanent snow and ice (Light Gray)
    '#FF0000',  # 20: Built-up land (Red)
    '#A0522D',  # 30: Bareland (Sienna)
    '#FFFF00',  # 40: Cropland (Yellow)
    '#ADFF2F',  # 50: Grassland (Green Yellow)
    '#8B4513',  # 60: Shrubland (Saddle Brown)
    '#006400',  # 70: Forest (Dark Green)
    '#87CEEB',  # 80: Wetland (Sky Blue)
    '#FFFFFF',  # 90: Tundra (White)
]

VIS_PARAMS = {
    'min': 0,
    'max': 90,
    'palette': PALETTE
}

# --- Function: Get Land Cover Image for a given year ---
@st.cache_data(ttl=3600)
def get_land_cover_image(year):
    image = None
    # Prioritize annual data (2000-2022)
    if 2000 <= year <= 2022:
        # Use .or(ee.Image(0)) here to ensure 'image' is always an ee.Image object,
        # even if glc_annual.filter().first() returns None.
        image = glc_annual.filter(ee.Filter.eq('year', year)).first().or(ee.Image(0)) # <--- 請仔細檢查這一行是否完整！
    # Fallback to five-yearly data for earlier years (1985, 1990, 1995)
    elif year < 2000:
        if year >= 1995:
            image = glc_five_yearly.filter(ee.Filter.eq('year', 1995)).first().or(ee.Image(0))
            st.warning(f"注意：GLC_FCS30D 在 {year} 年前沒有年度數據，顯示 1995 年的數據。")
        elif year >= 1990:
            image = glc_five_yearly.filter(ee.Filter.eq('year', 1990)).first().or(ee.Image(0))
            st.warning(f"注意：GLC_FCS30D 在 {year} 年前沒有年度數據，顯示 1990 年的數據。")
        else: # For years < 1990, default to 1985
            image = glc_five_yearly.filter(ee.Filter.eq('year', 1985)).first().or(ee.Image(0))
            st.warning(f"注意：GLC_FCS30D 在 {year} 年前沒有年度數據，顯示 1985 年的數據。")
    # For years beyond 2022, default to the latest available (2022)
    elif year > 2022:
        image = glc_annual.filter(ee.Filter.eq('year', 2022)).first().or(ee.Image(0))
        st.warning(f"注意：GLC_FCS30D 目前僅提供至 2022 年數據，顯示 2022 年的土地覆蓋圖。")

    # At this point, 'image' should always be an ee.Image object (even if ee.Image(0))

    try:
        # Check if the image has any bands (ee.Image(0) has no bands by default)
        # Using getInfo() is a GEE call, so it needs to be inside try-except
        if image.bandNames().length().getInfo() > 0:
            clipped_image = image.clip(taiwan_aoi)
            return clipped_image
        else:
            st.warning(f"未能獲取 {year} 年的土地覆蓋影像或影像為空 (無可用波段)。")
            return ee.Image(0) # Return a blank image if no bands
    except ee.EEException as e:
        st.error(f"獲取 {year} 年土地覆蓋數據時發生 Earth Engine 錯誤：{e}")
        return ee.Image(0) # Return a blank image on GEE error

# --- Year Selector ---
years = list(range(1990, 2025))
selected_year = st.sidebar.selectbox("選擇年份", years, index=years.index(2000))

st.subheader(f"土地覆蓋圖資 (GLC_FCS30D) - {selected_year} 年")

# Get Land Cover Image
land_cover_image = get_land_cover_image(selected_year)

# Get Map ID from GEE (Corrected function for Leaflet tile layer)
try:
    # Use getMapId() instead of getTileUrl() for Leaflet integration
    map_id_dict_lc = land_cover_image.getMapId(VIS_PARAMS)
    tile_url_lc = map_id_dict_lc['tile_fetcher'].url_format # Access the URL from the map_id_dict
except Exception as e:
    st.error(f"無法為土地覆蓋影像獲取瓦片 URL。錯誤：{e}")
    st.warning("將顯示預設的 OpenStreetMap 地圖。")
    tile_url_lc = 'https://tile.openstreetmap.org/{z}/{x}/{y}.png' # Fallback URL

# HTML/JavaScript for Leaflet Map
html_code_lc = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Land Cover Map</title>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"
     integrity="sha256-p4NxAoCcTZeWLgQz7PHrPvLeKkBGfG/6h7cdFG8FVY="
     crossorigin=""/>
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"
     integrity="sha256-20n6fxy+PGEQzYf/HjV36Ymg7XwU2Yf7g2Q/9g2X2Fw="
     crossorigin=""></script>
    <style>
        #map-lc {{ height: 500px; width: 100%; }}
        .legend {{
            padding: 6px 8px;
            font: 14px Arial, Helvetica, sans-serif;
            background: white;
            background: rgba(255,255,255,0.8);
            box-shadow: 0 0 15px rgba(0,0,0,0.2);
            border-radius: 5px;
            line-height: 18px;
            color: #555;
        }}
        .legend i {{
            width: 18px;
            height: 18px;
            float: left;
            margin-right: 8px;
            opacity: 0.7;
        }}
    </style>
</head>
<body>
    <div id="map-lc"></div>
    <script>
        var map_lc = L.map('map-lc').setView([{center_lat}, {center_lon}], 10);

        L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        }}).addTo(map_lc);

        L.tileLayer('{tile_url_lc}', {{
            attribution: 'Google Earth Engine - GLC_FCS30D',
            opacity: 0.8
        }}).addTo(map_lc);

        var legend = L.control({{position: 'bottomleft'}});
        legend.onAdd = function (map_lc) {{
            var div = L.DomUtil.create('div', 'info legend'),
                labels = ['水體', '永久冰雪', '建築用地', '裸地', '農田', '草地', '灌木叢', '森林', '濕地', '苔原'];
            var colors = {json.dumps(PALETTE)};

            div.innerHTML += '<b>土地覆蓋圖例</b><br>';
            for (var i = 0; i < labels.length; i++) {{
                div.innerHTML +=
                    '<i style="background:' + colors[i] + '"></i> ' + labels[i] + '<br>';
            }}
            return div;
        }};
        legend.addTo(map_lc);
    </script>
</body>
</html>
"""
html(html_code_lc, height=550)


st.markdown("---")
st.write("此應用使用 Google Earth Engine (GEE) 的 GLC_FCS30D 資料集顯示台灣的土地覆蓋變化，並透過 Leaflet.js 呈現。")
st.write("數據來源：[GLC_FCS30D (1985-2022)](https://gee-community-catalog.org/projects/glc_fcs/)")
st.markdown("""
    **注意事項：**
    * GLC_FCS30D 在 2000 年前為每五年一個數據 (1985, 1990, 1995)，非年度數據。
    * 對於 2023 和 2024 年，數據會顯示 2022 年的數據。
""")
git add .
git commit -m "Attempting extreme copy-paste fix for line 65 truncation"
git push origin main

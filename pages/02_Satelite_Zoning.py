import streamlit as st
import ee
from datetime import date
import json
from streamlit.components.v1 import html
from google.oauth2 import service_account

st.set_page_config(layout="wide", page_title="台灣土地覆蓋變化", page_icon="🌎")

st.title("台灣土地覆蓋變化分析 (1990 - 2024) 🌍")
st.markdown("左右兩邊的地圖將同步顯示相同年份的衛星真色影像與土地覆蓋圖資。")
st.markdown("---")

# --- GEE 認證與初始化 ---
try:
    ee.Initialize()
    st.success("Google Earth Engine 已成功初始化！")
except Exception as e:
    st.error(f"Google Earth Engine 初始化失敗：{e}")
    st.warning("請確認您已執行 `earthengine authenticate` 並授權 GEE 帳戶。")
    st.stop() # 停止執行，因為沒有 GEE 就無法工作
    
# 定義台灣的範圍 (以南科為中心稍微放大)
taiwan_aoi = ee.Geometry.Rectangle([120.174618, 23.008626, 120.297048, 23.069197])

# 獲取 AOI 的經緯度，用於初始化地圖中心
coords = taiwan_aoi.centroid().coordinates().getInfo()
center_lon, center_lat = coords[0], coords[1]


# --- 載入 GLC_FCS30D 資料集 ---
glc_annual = ee.ImageCollection('projects/sat-io/open-datasets/GLC-FCS30D/annual')
glc_five_yearly = ee.ImageCollection('projects/sat-io/open-datasets/GLC-FCS30D/five_yearly')

# --- 定義土地覆蓋分類的視覺化參數和圖例 ---
PALETTE = [
    '#00008B',  # 0: Water (Dark Blue)
    '#DCDCDC',  # 10: Permanent snow and ice (Light Gray) - unlikely to be shown
    '#FF0000',  # 20: Built-up land (Red)
    '#A0522D',  # 30: Bareland (Sienna)
    '#FFFF00',  # 40: Cropland (Yellow)
    '#ADFF2F',  # 50: Grassland (Green Yellow)
    '#8B4513',  # 60: Shrubland (Saddle Brown)
    '#006400',  # 70: Forest (Dark Green)
    '#87CEEB',  # 80: Wetland (Sky Blue)
    '#FFFFFF',  # 90: Tundra (White) - unlikely to be shown
]
labels = {
    0: "Water (Dark Blue)",
    10: " Permanent snow and ice (Light Gray)",
    20: "Built-up land (Red)",
    30: "Bareland (Sienna)",
    40: "Cropland (Yellow)",
    50: "Grassland (Green Yellow)",
    60: "Shrubland (Saddle Brown)",
    70: "Forest (Dark Green)",
    80: "Wetland (Sky Blue)",
    90: "Tundra (White)",
}
VIS_PARAMS = {
    'min': 0,
    'max': 90,
    'palette': PALETTE
}

# --- 函數：獲取指定年份的土地覆蓋圖層 ---
@st.cache_data(ttl=3600) # 緩存數據，避免每次運行都重新獲取
def get_land_cover_image(year):
    image = None
    if year >= 2000 and year <= 2022:
        image = glc_annual.filter(ee.Filter.eq('year', year)).first()
    elif year >= 1985 and year < 2000:
        if year == 1985:
            image = glc_five_yearly.filter(ee.Filter.eq('year', 1985)).first()
        elif year == 1990:
            image = glc_five_yearly.filter(ee.Filter.eq('year', 1990)).first()
        elif year == 1995:
            image = glc_five_yearly.filter(ee.Filter.eq('year', 1995)).first()
        elif year > 1995 and year < 2000:
            st.warning(f"注意：GLC_FCS30D 在 {year} 年前沒有年度數據，將顯示 1995 年的數據。")
            image = glc_five_yearly.filter(ee.Filter.eq('year', 1995)).first()
        else:
            st.warning(f"注意：GLC_FCS30D 在 {year} 年前沒有年度數據，將顯示 1985 年的數據。")
            image = glc_five_yearly.filter(ee.Filter.eq('year', 1985)).first()
    elif year > 2022:
        st.warning(f"注意：GLC_FCS30D 目前僅提供至 2022 年數據，將顯示 2022 年的土地覆蓋圖。")
        image = glc_annual.filter(ee.Filter.eq('year', 2022)).first()
    else:
        st.error("選擇的年份超出數據集範圍 (1985-2024)")
        return ee.Image(0) # 返回一個空白影像，避免 TypeError


# --- 函數：獲取指定年份的 Sentinel-2 真色影像 ---
@st.cache_data(ttl=3600) # 緩存數據，避免每次運行都重新獲取
def get_sentinel2_true_color_image(year):
    # 選擇該年份的影像，並過濾雲量，選擇雲量最低的單一影像
    start_date_str = f"{year}-01-01"
    end_date_str = f"{year}-12-31"

    s2_collection = ee.ImageCollection('COPERNICUS/S2_SR') \
        .filterDate(start_date_str, end_date_str) \
        .filterBounds(taiwan_aoi) \
        .sort('CLOUDY_PIXEL_PERCENTAGE') # 按雲量百分比排序，最低的在前

    image = s2_collection.first()
    # 視覺化參數 (真色：B4(紅), B3(綠), B2(藍))
    s2_vis_params = {
        'bands': ['B4', 'B3', 'B2'],
        'min': 0,
        'max': 3000 # 調整最大值以獲得更好的對比度
    }
    
    try:
        if image:
            try:
                # Use bandNames().length() instead of size() for robustness.
                if image.bandNames().length().getInfo() > 0:
                    clipped_image = image.clip(taiwan_aoi)
                    return clipped_image, s2_vis_params
                else:
                    st.warning(f"在 {year} 年份沒有足夠清晰的 Sentinel-2 影像數據，或影像無效 (無波段)。")
                    return ee.Image(0), s2_vis_params # 返回空白影像
            except ee.EEException as ee_inner_e:
                st.error(f"獲取 {year} 年份 Sentinel-2 影像時內部 Earth Engine 錯誤：{ee_inner_e}")
                return ee.Image(0), s2_vis_params # 返回空白影像
        else: # This path should be less likely with .or(ee.Image(0)) but kept for safety.
            st.warning(f"在 {year} 年份沒有足夠清晰的 Sentinel-2 影像數據 (影像物件為空)。")
            return ee.Image(0), s2_vis_params # 返回空白影像
    except ee.EEException as e:
        st.error(f"獲取 {year} 年份 Sentinel-2 影像時發生 Earth Engine 錯誤：{e}")
        return ee.Image(0), s2_vis_params # 返回空白影像

# --- 佈局：使用 st.columns 分成左右兩欄 ---
col1, col2 = st.columns(2)

# --- 年份選擇器 (控制左右兩邊的地圖) ---
years = list(range(1990, 2025))
selected_year = st.sidebar.selectbox("選擇年份", years, index=years.index(2000))

# --- 左欄：Sentinel-2 真色影像 ---
with col1:
    st.subheader(f"Sentinel-2 真色影像 - {selected_year} 年")
    
    # 獲取 Sentinel-2 影像
    sentinel_image, s2_vis_params = get_sentinel2_true_color_image(selected_year)

    # --- Debugging check ---
    if not isinstance(sentinel_image, ee.Image):
        st.error(f"偵測到 Sentinel-2 影像變數類型錯誤！預期 ee.Image，但實際為 {type(sentinel_image)}。")
        # If it's not an ee.Image, default to a blank image to prevent TypeError
        sentinel_image = ee.Image(0) 
        s2_vis_params = {'bands': ['B4', 'B3', 'B2'], 'min': 0, 'max': 1} # Minimal params for blank image
    # --- End Debugging check ---

    try:
        map_id_dict_s2 = ee.data.getTileUrl({
            'image': sentinel_image,
            'visParams': s2_vis_params
        })
        tile_url_s2 = map_id_dict_s2['url']

html_code_s2 = f"""
<!DOCTYPE html>
<html>
<head>
        <title>Sentinel-2 Map</title>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"
         integrity="sha256-p4NxAoCcTZeWLgQz7PHrPvLeKkBGfG/6h7cdFG8FVY="
         crossorigin=""/>
        <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"
         integrity="sha256-20n6fxy+PGEQzYf/HjV36Ymg7XwU2Yf7g2Q/9g2X2Fw="
         crossorigin=""></script>
        <style>
            #map-s2 {{ height: 500px; width: 100%; }}
        </style>
    </head>
    <body>
        <div id="map-s2"></div>
        <script>
            var map_s2 = L.map('map-s2').setView([{center_lat}, {center_lon}], 10);

            L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
                attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            }}).addTo(map_s2);

            L.tileLayer('{tile_url_s2}', {{
                attribution: 'Google Earth Engine - Sentinel-2 True Color',
                opacity: 0.8
            }}).addTo(map_s2);
        </script>
    </body>
    </html>
    """
    html(html_code_s2, height=550)


# --- 右欄：土地覆蓋圖資 ---
with col2:
    st.subheader(f"土地覆蓋圖資 (GLC_FCS30D) - {selected_year} 年")
    
    # 獲取土地覆蓋圖資
    land_cover_image = get_land_cover_image(selected_year)
    
    # --- Debugging check ---
    if not isinstance(land_cover_image, ee.Image):
        st.error(f"偵測到土地覆蓋影像變數類型錯誤！預期 ee.Image，但實際為 {type(land_cover_image)}。")
        # If it's not an ee.Image, default to a blank image to prevent TypeError
        land_cover_image = ee.Image(0)
    # --- End Debugging check ---

    try:
        map_id_dict_lc = ee.data.getTileUrl({
            'image': land_cover_image,
            'visParams': VIS_PARAMS
        })
        tile_url_lc = map_id_dict_lc['url']
    except Exception as e:
        st.error(f"無法為土地覆蓋影像獲取瓦片 URL。錯誤：{e}")
        st.warning("將顯示預設的 OpenStreetMap 地圖。")
        # Fallback to a placeholder tile URL if GEE fails
        tile_url_lc = 'https://tile.openstreetmap.org/{z}/{x}/{y}.png'


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
    * GLC_FCS30D 在 2000 年前是每五年一個數據 (1985, 1990, 1995)，非年度數據。
    * 對於 2023 和 2024 年，目前 GLC_FCS30D 尚未更新，程式碼會顯示 2022 年的數據。
    * 土地覆蓋分類顏色僅為示意，詳細定義請參考原始資料集說明。
    * Sentinel-2 真色影像可能因雲層覆蓋而無影像，或者在某些年份沒有足夠清晰的數據。
""")

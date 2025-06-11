import streamlit as st
import ee
from datetime import date
import json
from streamlit.components.v1 import html
from google.oauth2 import service_account

# 1. st.set_page_config() 必須是 Streamlit 腳本中執行的第一個 Streamlit 命令
st.set_page_config(layout="wide", page_title="台灣土地覆蓋變化", page_icon="🌎")

# 2. 接下來才是其他的 Streamlit 命令和你的應用邏輯
st.title("台灣土地覆蓋變化分析 (1990 - 2024) 🌍")
st.markdown("左右兩邊的地圖將同步顯示相同年份的衛星真色影像與土地覆蓋圖資。")
st.markdown("---")

# --- GEE 認證與初始化 ---
try:
    # 從 Streamlit Secrets 讀取 GEE 服務帳戶金鑰 JSON
    # 確保你的 .streamlit/secrets.toml 中有 [GEE_SERVICE_ACCOUNT] 段落
    service_account_info = st.secrets["GEE_SERVICE_ACCOUNT"]

    # 使用 google-auth 進行 GEE 授權
    credentials = service_account.Credentials.from_service_account_info(
        service_account_info,
        scopes=["https://www.googleapis.com/auth/earthengine"]
    )

    # 初始化 GEE
    ee.Initialize(credentials)
except Exception as e:
    st.error(f"Google Earth Engine 初始化失敗：{e}")
    st.warning(f"請確認您已在 Streamlit Secrets 中正確配置 `GEE_SERVICE_ACCOUNT` 金鑰。錯誤詳情：`{e}`")
    st.stop() # 停止執行，因為沒有 GEE 就無法工作


# --- 全局變數定義 ---
# 定義台灣的範圍 (以南科為中心稍微放大)
# 南科中心點大概在 23.08, 120.28
taiwan_aoi = ee.Geometry.Rectangle([119.8, 22.5, 120.8, 23.5]) # 台灣西南海岸大致範圍

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

VIS_PARAMS = {
    'min': 0,
    'max': 90,
    'palette': PALETTE
}

# --- 函數：獲取指定年份的土地覆蓋圖層 ---
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

    try:
        if image and image.bandNames().size().getInfo() > 0:
            clipped_image = image.clip(taiwan_aoi)
            return clipped_image
        else:
            st.warning(f"在 {year} 年份未能成功獲取土地覆蓋數據，影像可能為空。")
            return ee.Image(0) # 返回一個空白影像
    except ee.EEException as e:
        st.error(f"獲取 {year} 年份土地覆蓋數據時發生 Earth Engine 錯誤：{e}")
        return ee.Image(0) # 返回一個空白影像

# --- 函數：獲取指定年份的 Sentinel-2 真色影像 ---
def get_sentinel2_true_color_image(year):
    # 選擇該年份的影像，並過濾雲量，選擇雲量最低的單一影像
    start_date_str = f"{year}-01-01"
    end_date_str = f"{year}-12-31"

    s2_collection = ee.ImageCollection('COPERNICUS/S2_SR') \
        .filterDate(start_date_str, end_date_str) \
        .filterBounds(taiwan_aoi) \
        .sort('CLOUDY_PIXEL_PERCENTAGE') # 按雲量百分比排序，最低的在前

    # 選擇雲量最低的影像
    image = s2_collection.first()

    # 視覺化參數 (真色：B4(紅), B3(綠), B2(藍))
    s2_vis_params = {
        'bands': ['B4', 'B3', 'B2'],
        'min': 0,
        'max': 3000 # 調整最大值以獲得更好的對比度
    }
    
    try:
        # 檢查影像是否為空或無效
        if image and image.bandNames().size().getInfo() > 0:
            clipped_image = image.clip(taiwan_aoi)
            return clipped_image, s2_vis_params
        else:
            st.warning(f"在 {year} 年份沒有足夠清晰的 Sentinel-2 影像數據。請嘗試其他年份或調整地圖範圍。")
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
    
    map_id_dict_lc = ee.data.getTileUrl({
        'image': land_cover_image,
        'visParams': VIS_PARAMS
    })
    tile_url_lc = map_id_dict_lc['url']

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


---

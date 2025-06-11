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
st.markdown("左邊的地圖將展示選擇年份的土地覆蓋類型，而右邊則可以選擇日期區間來觀察 Sentinel-2 的假色影像。") # 修正文案以符合左右兩側功能
st.markdown("---")

# --- GEE 認證與初始化 ---
try:
    # 從 Streamlit Secrets 讀取 GEE 服務帳戶金鑰 JSON
    service_account_info = st.secrets["GEE_SERVICE_ACCOUNT"]

    # 使用 google-auth 進行 GEE 授權
    credentials = service_account.Credentials.from_service_account_info(
        service_account_info,
        scopes=["https://www.googleapis.com/auth/earthengine"]
    )

    # 初始化 GEE
    ee.Initialize(credentials)
    # st.success("Google Earth Engine 已成功初始化！") # 避免重複顯示成功訊息
except Exception as e:
    st.error(f"Google Earth Engine 初始化失敗：{e}")
    st.warning("請確認您已在 Streamlit Secrets 中正確配置 `GEE_SERVICE_ACCOUNT` 金鑰。")
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

# --- 函數：獲取指定年份的土地覆蓋圖層 ---
def get_land_cover_image(year):
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
            st.warning(f"注意：GLC_FCS30D 在 {year} 年前沒有年度數據，顯示 1995 年的數據。")
            image = glc_five_yearly.filter(ee.Filter.eq('year', 1995)).first()
        else:
             st.warning(f"注意：GLC_FCS30D 在 {year} 年前沒有年度數據，顯示 1985 年的數據。")
             image = glc_five_yearly.filter(ee.Filter.eq('year', 1985)).first()
    elif year > 2022:
        st.warning(f"注意：GLC_FCS30D 目前僅提供至 2022 年數據，將顯示 2022 年的土地覆蓋圖。")
        image = glc_annual.filter(ee.Filter.eq('year', 2022)).first()
    else:
        st.error("選擇的年份超出數據集範圍 (1985-2024)")
        return None

    if image:
        clipped_image = image.clip(taiwan_aoi)
        return clipped_image
    return None

# --- 函數：獲取 Sentinel-2 假色影像 (假定是近紅外、紅、綠波段組合) ---
def get_sentinel2_false_color_image(start_date, end_date):
    # 選擇 Sentinel-2 影像集，並過濾日期和雲量
    s2_collection = ee.ImageCollection('COPERNICUS/S2_SR') \
        .filterDate(start_date, end_date) \
        .filterBounds(taiwan_aoi) \
        .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20)) # 雲量小於20%

    # 選擇集合中位數影像 (通常用於減少雲的影響)
    image = s2_collection.median()

    # 視覺化參數 (假色：B8(NIR), B4(Red), B3(Green))
    s2_vis_params = {
        'bands': ['B8', 'B4', 'B3'],
        'min': 0,
        'max': 3000 # 調整最大值以獲得更好的對比度
    }
    
    if image.bandNames().size().getInfo() == 0: # 檢查影像是否為空
        return None, None
    
    # 裁剪影像到台灣 AOI
    clipped_image = image.clip(taiwan_aoi)
    return clipped_image, s2_vis_params

# --- 佈局：使用 st.columns 分成左右兩欄 ---
col1, col2 = st.columns(2)

with col1:
    st.subheader("選擇年份顯示土地覆蓋圖")
    years = list(range(1990, 2025))
    selected_year = st.selectbox("選擇年份", years, index=years.index(2000), key="land_cover_year_selector")

    if selected_year:
        land_cover_image = get_land_cover_image(selected_year)
        if land_cover_image:
            map_id_dict = ee.data.getTileUrl({
                'image': land_cover_image,
                'visParams': VIS_PARAMS
            })
            tile_url = map_id_dict['url']

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

                    L.tileLayer('{tile_url}', {{
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
            html(html_code_lc, height=550) # 高度要足夠顯示地圖和圖例
        else:
            st.warning("無法獲取該年份的土地覆蓋數據。請嘗試其他年份。")

with col2:
    st.subheader("選擇日期區間顯示 Sentinel-2 假色影像")
    # 初始化 session_state
    if 'start_date' not in st.session_state:
        st.session_state['start_date'] = date(2024, 1, 1)
    if 'end_date' not in st.session_state:
        st.session_state['end_date'] = date.today()

    start_date = st.date_input(label="選擇起始日期", value=st.session_state['start_date'], min_value=date(2018, 1, 1), max_value=date.today(), key="s2_start_date")
    end_date = st.date_input(label="選擇結束日期", value=st.session_state['end_date'], min_value=start_date, max_value=date.today(), key="s2_end_date")

    st.session_state['start_date'] = start_date
    st.session_state['end_date'] = end_date

    st.success(f"目前選擇的日期區間為：{start_date} 到 {end_date}")

    if start_date and end_date:
        sentinel_image, s2_vis_params = get_sentinel2_false_color_image(str(start_date), str(end_date))

        if sentinel_image:
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
                        attribution: 'Google Earth Engine - Sentinel-2 False Color',
                        opacity: 0.8
                    }}).addTo(map_s2);
                </script>
            </body>
            </html>
            """
            html(html_code_s2, height=550)
        else:
            st.warning("所選日期區間內沒有可用的 Sentinel-2 影像，或者影像雲量過高。請嘗試其他日期。")


st.markdown("---")
st.write("此應用使用 Google Earth Engine (GEE) 的 GLC_FCS30D 資料集顯示台灣的土地覆蓋變化，並透過 Leaflet.js 呈現。")
st.write("數據來源：[GLC_FCS30D (1985-2022)](https://gee-community-catalog.org/projects/glc_fcs/)")
st.markdown("""
    **注意事項：**
    * GLC_FCS30D 在 2000 年前是每五年一個數據 (1985, 1990, 1995)，非年度數據。
    * 對於 2023 和 2024 年，目前 GLC_FCS30D 尚未更新，程式碼會顯示 2022 年的數據。
    * 土地覆蓋分類顏色僅為示意，詳細定義請參考原始資料集說明。
    * Sentinel-2 假色影像可能因雲層覆蓋而無影像，請調整日期區間以獲得清晰影像。
""")

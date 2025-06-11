import streamlit as st
import ee
from datetime import date
import json # 用於處理 JSON 數據，特別是地圖邊界
from streamlit.components.v1 import html # 引入 html 組件
from google.oauth2 import service_account

# --- 將 st.set_page_config 放在所有 st.XXX() 命令的最前面 ---
st.set_page_config(layout="wide", page_title="台灣土地覆蓋變化", page_icon="🌎")

st.title("台灣土地覆蓋變化分析 (1990 - 2024)") # <-- 這是第一個允許在 set_page_config 之後的 st. 命令
st.markdown("---")

# ... 接下來才是 GEE 初始化、數據加載、函數定義等 ...
# 從 Streamlit Secrets 讀取 GEE 服務帳戶金鑰 JSON
service_account_info = st.secrets["GEE_SERVICE_ACCOUNT"]

# 使用 google-auth 進行 GEE 授權
credentials = service_account.Credentials.from_service_account_info(
    service_account_info,
    scopes=["https://www.googleapis.com/auth/earthengine"]
)


# 初始化 GEE
ee.Initialize(credentials)

###############################################

st.set_page_config(layout="wide")
st.title("台灣土地覆蓋變化分析 (1990 - 2024)🌍")
st.markdown("左邊的地圖為1984/01/01到2025/01/01的Sentinel-2的假色影像；右邊則為1984/01/01到2025/01/01的Sentinel-2的假色影像")
st.markdown("---")

# 地理區域
my_point = ee.Geometry.Point([120.271552, 23.106393])

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
modis_labels = {
    0: "Water (Dark Blue)",
    10: "Permanent snow and ice (Light Gray)",
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
    'max': 90, # 根據你的分類值範圍設定
    'palette': PALETTE
}
# --- 函數：獲取指定年份的土地覆蓋圖層 ---
def get_land_cover_image(year):
    """
    獲取指定年份的 GLC_FCS30D 土地覆蓋圖像。
    如果年份在 1985, 1990, 1995, 2000 之間，則從 five_yearly 獲取。
    如果年份在 2000-2022 之間，則從 annual 獲取。
    如果年份超過 2022，則返回 2022 年的數據。
    """
    if year >= 2000 and year <= 2022:
        # Annual data (2000-2022)
        image = glc_annual.filter(ee.Filter.eq('year', year)).first()
    elif year >= 1985 and year < 2000:
        # Five-yearly data (1985, 1990, 1995)
        # 需要處理一下，因為 five_yearly 只有 1985, 1990, 1995, 2000 四個精確年份的數據
        if year == 1985:
            image = glc_five_yearly.filter(ee.Filter.eq('year', 1985)).first()
        elif year == 1990:
            image = glc_five_yearly.filter(ee.Filter.eq('year', 1990)).first()
        elif year == 1995:
            image = glc_five_yearly.filter(ee.Filter.eq('year', 1995)).first()
        elif year > 1995 and year < 2000: # 如果是 1996-1999，則顯示 1995 年的數據
            st.warning(f"注意：GLC_FCS30D 在 {year} 年前沒有年度數據，顯示 1995 年的數據。")
            image = glc_five_yearly.filter(ee.Filter.eq('year', 1995)).first()
        else: # 如果是 1986-1989，則顯示 1985 年的數據
             st.warning(f"注意：GLC_FCS30D 在 {year} 年前沒有年度數據，顯示 1985 年的數據。")
             image = glc_five_yearly.filter(ee.Filter.eq('year', 1985)).first()
    elif year > 2022: # 如果選擇 2023 或 2024，則顯示 2022 年的數據 (目前 GLC_FCS30D 最新的)
        st.warning(f"注意：GLC_FCS30D 目前僅提供至 2022 年數據，將顯示 2022 年的土地覆蓋圖。")
        image = glc_annual.filter(ee.Filter.eq('year', 2022)).first()
    else: # 其他無效年份
        st.error("選擇的年份超出數據集範圍 (1985-2024)")
        return None

    if image:
        # 裁剪影像到台灣 AOI
        clipped_image = image.clip(taiwan_aoi)
        return clipped_image
    return None




st.title("選擇日期區間")
# 初始化 session_state
#if 'start_date' not in st.session_state:
#    st.session_state['start_date'] = date(2024, 1, 1)
#if 'end_date' not in st.session_state:
#    st.session_state['end_date'] = date.today()
st.session_state['start_date'] = date(2024, 1, 1)
st.session_state['end_date'] = date.today()
# 日期選擇器
start_date = st.date_input(label = "選擇起始日期", value = st.session_state['start_date'], min_value = date(2018, 1, 1), max_value = date.today())
end_date = st.date_input(label = "選擇結束日期", value = st.session_state['end_date'], min_value = start_date, max_value = date.today())

# 儲存使用者選擇
st.session_state['start_date'] = start_date
st.session_state['end_date'] = end_date

st.success(f"目前選擇的日期區間為：{start_date} 到 {end_date}")

import streamlit as st
import ee

st.set_page_config(layout="wide", page_title="台灣土地覆蓋變化", page_icon="🌎")

st.title("台灣土地覆蓋變化分析 (1990 - 2024)")
st.markdown("---")



years = list(range(1990, 2025))
selected_year = st.sidebar.selectbox("選擇年份", years, index=years.index(2000))

if selected_year:
    st.subheader(f"台灣土地覆蓋類型 - {selected_year} 年")

    land_cover_image = get_land_cover_image(selected_year)

    if land_cover_image:
        # 獲取 GEE 圖層的瓦片 URL
        map_id_dict = ee.data.getTileUrl({
            'image': land_cover_image,
            'visParams': VIS_PARAMS
        })
        tile_url = map_id_dict['url']

        # 創建 HTML 和 JavaScript 來初始化 Leaflet 地圖並添加 GEE 圖層
        # Leaflet 庫的 CDN 引入
        html_code = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>GEE Map</title>
            <meta charset="utf-8" />
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"
             integrity="sha256-p4NxAoCcTZeWLgQz7PHrPvLeKkBGfG/6h7cdFG8FVY="
             crossorigin=""/>
            <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"
             integrity="sha256-20n6fxy+PGEQzYf/HjV36Ymg7XwU2Yf7g2Q/9g2X2Fw="
             crossorigin=""></script>
            <style>
                #map {{ height: 600px; width: 100%; }}
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
            <div id="map"></div>
            <script>
                var map = L.map('map').setView([{center_lat}, {center_lon}], 10); // 設置中心點和初始縮放

                // 添加 OpenStreetMap 底圖
                L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
                    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                }}).addTo(map);

                // 添加 GEE 土地覆蓋圖層
                L.tileLayer('{tile_url}', {{
                    attribution: 'Google Earth Engine - GLC_FCS30D',
                    opacity: 0.8
                }}).addTo(map);

                // 添加圖例 (使用 HTML/CSS 實現)
                var legend = L.control({{position: 'bottomleft'}});
                legend.onAdd = function (map) {{
                    var div = L.DomUtil.create('div', 'info legend'),
                        labels = ['水體', '永久冰雪', '建築用地', '裸地', '農田', '草地', '灌木叢', '森林', '濕地', '苔原'];
                    var colors = {json.dumps(PALETTE)}; // 將 Python 列表轉換為 JSON 字符串

                    div.innerHTML += '<b>土地覆蓋圖例</b><br>';
                    for (var i = 0; i < labels.length; i++) {{
                        div.innerHTML +=
                            '<i style="background:' + colors[i] + '"></i> ' + labels[i] + '<br>';
                    }}
                    return div;
                }};
                legend.addTo(map);

                // 調整地圖以適應 AOI (可選，但建議)
                // var bounds = L.latLngBounds([[22.5, 119.8], [23.5, 120.8]]); // 根據 taiwan_aoi 設置邊界
                // map.fitBounds(bounds);

            </script>
        </body>
        </html>
        """

        # 在 Streamlit 中渲染 HTML
        html(html_code, height=650) # 高度要足夠顯示地圖和圖例
    else:
        st.warning("無法獲取該年份的土地覆蓋數據。請嘗試其他年份。")

st.markdown("---")
st.write("此應用使用 Google Earth Engine (GEE) 的 GLC_FCS30D 資料集顯示台灣的土地覆蓋變化，並透過 Leaflet.js 呈現。")
st.write("數據來源：[GLC_FCS30D (1985-2022)](https://gee-community-catalog.org/projects/glc_fcs/)")
st.markdown("""
    **注意事項：**
    * GLC_FCS30D 在 2000 年前是每五年一個數據 (1985, 1990, 1995)，非年度數據。
    * 對於 2023 和 2024 年，目前 GLC_FCS30D 尚未更新，程式碼會顯示 2022 年的數據。
    * 土地覆蓋分類顏色僅為示意，詳細定義請參考原始資料集說明。
""")

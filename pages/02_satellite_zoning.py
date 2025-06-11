import streamlit as st
import ee
from datetime import date
import json # 用於處理 JSON 數據，特別是地圖邊界
from streamlit.components.v1 import html # 引入 html 組件
from google.oauth2 import service_account
import geemap.foliumap as geemap

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
my_point = ee.Geometry.Point([120.282006,23.101410])

# 擷取 Harmonized Sentinel-2 MSI: MultiSpectral Instrument, Level-1C 衛星影像
my_image = (
    ee.ImageCollection('COPERNICUS/S2_HARMONIZED')
    .filterBounds(my_point)
    .filterDate('1984-01-01', '2025-01-01')
    .sort('CLOUDY_PIXEL_PERCENTAGE')
    .first()
    .select('B.*')
)

vis_params = {'min':100, 'max': 3500, 'bands': ['B11',  'B8',  'B3']}

from datetime import date
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
import folium
from streamlit_folium import folium_static # 用於在 Streamlit 中顯示 Folium 地圖

st.set_page_config(layout="wide", page_title="台灣土地覆蓋變化", page_icon="🌎")

st.title("台灣土地覆蓋變化分析 (1990 - 2024)")
st.markdown("---")

# --- GEE 初始化 ---
try:
    ee.Initialize()
    st.success("Google Earth Engine 已成功初始化！")
except Exception as e:
    st.error(f"Google Earth Engine 初始化失敗：{e}")
    st.warning("請確認您已執行 `earthengine authenticate` 並授權 GEE 帳戶。")
    st.stop() # 停止執行，因為沒有 GEE 就無法工作

# --- 定義台灣的範圍 (以南科為中心稍微放大) ---
# 南科中心點大概在 23.08, 120.28
# 我們定義一個包含南科及周邊較大範圍的邊界 (矩形)
# 這是一個粗略的範圍，你可以根據實際需求調整經緯度
taiwan_aoi = ee.Geometry.Rectangle([119.8, 22.5, 120.8, 23.5]) # 台灣西南海岸大致範圍

# --- 載入 GLC_FCS30D 資料集 ---
# GLC_FCS30D: Global 30-meter Land Cover Change Dataset (1985-2022)
# 這個資料集是每年更新到 2022 年，2000 年前是每五年一個數據。
# 我們將使用 'annual' collection (2000-2022) 和 'five_yearly' collection (1985-2000)
# Data source: https://gee-community-catalog.org/projects/glc_fcs/
# GLC_FCS30D classification system:


# 載入年鑑數據 (2000-2022)
glc_annual = ee.ImageCollection('projects/sat-io/open-datasets/GLC-FCS30D/annual')
# 載入五年數據 (1985, 1990, 1995)
glc_five_yearly = ee.ImageCollection('projects/sat-io/open-datasets/GLC-FCS30D/five_yearly')

# --- 定義土地覆蓋分類的視覺化參數和圖例 ---
# 顏色定義參考 GLC_FCS30D 的官方文檔或常見 LULC 圖例
# 我會選擇一些具有代表性的顏色
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

# --- Streamlit 介面 ---
years = list(range(1990, 2025)) # 從 1990 到 2024
selected_year = st.sidebar.selectbox("選擇年份", years, index=years.index(2000)) # 預設選擇 2000 年

if selected_year:
    st.subheader(f"台灣土地覆蓋類型 - {selected_year} 年")

    # 獲取土地覆蓋圖像
    land_cover_image = get_land_cover_image(selected_year)

    if land_cover_image:
        # 創建 Folium 地圖，中心點為南科大致位置
        m = folium.Map(location=[23.08, 120.28], zoom_start=10)

        # 添加 GEE 圖層到 Folium 地圖
        # 獲取 GEE 圖層的 URL
        map_id_dict = ee.data.getTileUrl({
            'image': land_cover_image,
            'visParams': VIS_PARAMS
        })
        folium.TileLayer(
            tiles=map_id_dict['url'],
            attr='Google Earth Engine - GLC_FCS30D',
            overlay=True,
            name=f'土地覆蓋 ({selected_year})'
        ).add_to(m)

        # 添加圖例
        legend_html = """
             <div style="position: fixed;
                         bottom: 50px; left: 50px; width: 150px; height: 220px;
                         border:2px solid grey; z-index:9999; font-size:14px;
                         background-color:white; opacity:0.9;">
               &nbsp; <b>土地覆蓋圖例</b> <br>
               &nbsp; <i style="background:#00008B; opacity:0.9;"></i>&nbsp; 水體 <br>
               &nbsp; <i style="background:#DCDCDC; opacity:0.9;"></i>&nbsp; 永久冰雪 <br>
               &nbsp; <i style="background:#FF0000; opacity:0.9;"></i>&nbsp; 建築用地 <br>
               &nbsp; <i style="background:#A0522D; opacity:0.9;"></i>&nbsp; 裸地 <br>
               &nbsp; <i style="background:#FFFF00; opacity:0.9;"></i>&nbsp; 農田 <br>
               &nbsp; <i style="background:#ADFF2F; opacity:0.9;"></i>&nbsp; 草地 <br>
               &nbsp; <i style="background:#8B4513; opacity:0.9;"></i>&nbsp; 灌木叢 <br>
               &nbsp; <i style="background:#006400; opacity:0.9;"></i>&nbsp; 森林 <br>
               &nbsp; <i style="background:#87CEEB; opacity:0.9;"></i>&nbsp; 濕地 <br>
               &nbsp; <i style="background:#FFFFFF; opacity:0.9;"></i>&nbsp; 苔原 <br>
             </div>
             <style>
               i {
                 width: 18px;
                 height: 18px;
                 float: left;
                 margin-right: 8px;
                 opacity: 0.7;
               }
             </style>
             """
        m.get_root().html.add_child(folium.Element(legend_html))
        # 添加圖層控制
        folium.LayerControl().add_to(m)
        # 顯示地圖
        folium_static(m, width=900, height=600)
    else:
        st.warning("無法獲取該年份的土地覆蓋數據。請嘗試其他年份。")

st.markdown("---")
st.write("此應用使用 Google Earth Engine (GEE) 的 GLC_FCS30D 資料集顯示台灣的土地覆蓋變化。")
st.write("數據來源：[GLC_FCS30D (1985-2022)](https://gee-community-catalog.org/projects/glc_fcs/)")
st.markdown("""
    **注意事項：**
    * GLC_FCS30D 在 2000 年前是每五年一個數據 (1985, 1990, 1995)，非年度數據。
    * 對於 2023 和 2024 年，目前 GLC_FCS30D 尚未更新，程式碼會顯示 2022 年的數據。
    * 土地覆蓋分類顏色僅為示意，詳細定義請參考原始資料集說明。
""")


# 顯示地圖
my_Map = geemap.Map()

left_layer = geemap.ee_tile_layer(my_image, vis_params, 'Sentinel-2 flase color')
right_layer = geemap.ee_tile_layer(result001, vis_params_001, 'wekaKMeans clustered land cover')

my_Map.centerObject(my_image.geometry(), 10)
my_Map.split_map(left_layer, right_layer)
my_Map.add_legend(title='Land Cover Type (Kmeans)', legend_dict = legend_dict1, draggable=False, position = 'bottomright')
my_Map.to_streamlit(height=600)

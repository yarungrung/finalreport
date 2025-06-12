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

  
# --- 右欄：土地覆蓋圖資 ---
with col2:
roi = ee.Geometry.Rectangle([120.174618, 23.008626, 120.297048, 23.069197)
my_point = ee.Geometry.Point([ 120.271555,23.106061]);
# 擷取 Sentinel-2 影像
image = (
    ee.ImageCollection("COPERNICUS/S2_HARMONIZED")
    .filterBounds(my_point)
    .filterDate("2021-01-01", "2022-01-01")
    .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20))
    .sort("CLOUDY_PIXEL_PERCENTAGE")
    .first()
    .clip(roi)
    .select('B.*')
)

# 可視化參數
vis_params = {'min': 100, 'max': 3500, 'bands': ['B11', 'B8', 'B3']}

# 讀取 ESA WorldCover 2021 土地覆蓋圖層
my_lc = ee.Image('ESA/WorldCover/v200/2021').clip(roi)

# Remap 土地覆蓋類別
classValues = [10, 20, 30, 40, 50, 60, 70, 80, 90, 95, 100]
remapValues = ee.List.sequence(0, 10)
my_lc = my_lc.remap(classValues, remapValues, bandName='Map').rename('lc').toByte()

# 土地覆蓋視覺化參數
classVis = {
    'min': 0,
    'max': 10,
    'palette': [
        '006400', 'ffbb22', 'ffff4c', 'f096ff', 'fa0000',
        'b4b4b4', 'f0f0f0', '0064c8', '0096a0', '00cf75', 'fae6a0'
    ]
}

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

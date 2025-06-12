import streamlit as st
import ee
import json
import geemap
from streamlit.components.v1 import html
from google.oauth2 import service_account
import geemap.foliumap as geemap


st.set_page_config(layout="wide", page_title="台灣土地覆蓋變化", page_icon="🌎")

st.title("1994年台灣土地覆蓋變化分析🌍")
st.markdown("左側為衛星真色影像；右側為土地覆蓋圖資。")

# ✅ 授權 Earth Engine
service_account_info = st.secrets["GEE_SERVICE_ACCOUNT"]
credentials = service_account.Credentials.from_service_account_info(
    service_account_info,
    scopes=["https://www.googleapis.com/auth/earthengine"]
)
ee.Initialize(credentials)
    
# 初始化 Google Earth Engine
try:
    ee.Initialize()
except Exception as e:
    st.error(f"Google Earth Engine 初始化失敗: {e}")
    st.info("請確認您已執行 `earthengine authenticate` 並正確設定 GEE 憑證。")
    st.stop() # 停止 Streamlit 應用程式執行

st.set_page_config(layout="wide")
st.title("土地覆蓋圖層左右分割顯示 (Landsat 影像與監督式分類)")

# 定義感興趣的區域 (台灣南部區域，符合你提供的 ROI)
roi = ee.Geometry.Rectangle([120.174618, 23.008626, 120.297048, 23.069197])
my_point = ee.Geometry.Point([120.271555, 23.106061]) # 原始點，作為篩選中心

# --- 左邊圖層：1994年 Landsat 影像 ---
# 獲取 1994 年的 Landsat 影像
# Landsat 5 TM (Thematic Mapper) 是 1994 年主要的 Landsat 衛星
landsat_1994 = (
    ee.ImageCollection("LANDSAT/LT05/C01/T1_SR") # Landsat 5 Surface Reflectance
    .filterBounds(my_point)
    .filterDate("1994-01-01", "1995-01-01") # 篩選 1994 年的影像
    .filter(ee.Filter.lt('CLOUD_COVER', 10)) # 雲量小於 10%
    .sort("CLOUD_COVER")
    .first() # 選擇雲量最低的第一張影像
    .clip(roi)
)

# Landsat 5 的波段可視化參數 (自然色：B3, B2, B1；假彩色：B5, B4, B3)
# 這裡使用接近真彩色的假彩色紅外 (NIR, Red, Green)
landsat_vis_params = {'min': 0, 'max': 3000, 'bands': ['B3', 'B2', 'B1']} # 自然色 B3(紅), B2(綠), B1(藍)

if landsat_1994:
    # --- 右邊圖層：Landsat 監督式分類 ---
    st.subheader("右側：Landsat 影像的監督式分類")
    st.write("""
    監督式分類需要訓練數據。以下是一個 **簡化且基於少量手動定義訓練點** 的分類範例。
    在實際應用中，需要收集代表不同土地覆蓋類型的精確訓練點，以獲得準確的分類結果。
    """)
     # 使用 Landsat 的光譜波段作為分類特徵 (B1, B2, B3, B4, B5, B7)
    bands = ['B1', 'B2', 'B3', 'B4', 'B5', 'B7']

    # 選擇影像中用於分類的波段
    training_image = landsat_1994.select(bands)
     # 手動定義一些訓練點
    training_data = ee.FeatureCollection([
        ee.Feature(ee.Geometry.Point([120.239463,23.128476]), {'class': 0}),   # Water
        ee.Feature(ee.Geometry.Point([120.220865,23.031108]), {'class': 0}),   # Water
        ee.Feature(ee.Geometry.Point([120.25, 23.08]), {'class': 10}),  # Permanent snow and ice
        ee.Feature(ee.Geometry.Point([120.25, 23.08]), {'class': 10}),  # Permanent snow and ice
        ee.Feature(ee.Geometry.Point([120.231850,23.027254]), {'class': 20}),  # Built-up land
        ee.Feature(ee.Geometry.Point([120.219439,23.042502]), {'class': 20}),  # Built-up land
        ee.Feature(ee.Geometry.Point([120.32, 23.15]), {'class': 30}),  # Bareland
        ee.Feature(ee.Geometry.Point([120.32, 23.15]), {'class': 30}),  # Bareland
        ee.Feature(ee.Geometry.Point([120.18, 23.01]), {'class': 40}),  # Cropland
        ee.Feature(ee.Geometry.Point([120.18, 23.01]), {'class': 40}),  # Cropland
        ee.Feature(ee.Geometry.Point([120.27, 23.06]), {'class': 50}),  # Grassland
        ee.Feature(ee.Geometry.Point([120.27, 23.06]), {'class': 50}),  # Grassland
        ee.Feature(ee.Geometry.Point([120.25, 23.08]), {'class': 60}),  # Shrubland
         ee.Feature(ee.Geometry.Point([120.25, 23.08]), {'class': 60}),  # Shrubland
        ee.Feature(ee.Geometry.Point([120.27, 23.05]), {'class': 70}),  # Forest
        ee.Feature(ee.Geometry.Point([120.27, 23.05]), {'class': 70}),  # Forest
        ee.Feature(ee.Geometry.Point([120.32, 23.15]), {'class': 80}),  # Wetland
        ee.Feature(ee.Geometry.Point([120.32, 23.15]), {'class': 80}),  # Wetland
        ee.Feature(ee.Geometry.Point([120.18, 23.01]), {'class': 90}),  # Tundra
        ee.Feature(ee.Geometry.Point([120.18, 23.01]), {'class': 90})   # Tundra
    ])

    # 從影像中採樣訓練數據
    sampled_points = training_image.sampleRegions(
        collection=training_data,
        properties=['class'],
        scale=30 # Landsat 影像解析度
    )

    # 訓練分類器 (使用分類器如 Random Forest)
    classifier = ee.Classifier.smileRandomForest(numberOfTrees=10).train(
        features=sampled_points,
        classProperty='class',
        inputProperties=bands
    )
    # 對影像進行分類
    classified_image = training_image.classify(classifier)

    # 實際分類需要大量且分佈合理的訓練數據     
labels = {
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
    'max': 90,
    'palette':  [
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
}
    # 4. 建立地圖並添加圖層
    my_Map = geemap.Map()

    # 左側圖層：1994年 Landsat 影像
    left_layer = geemap.ee_tile_layer(landsat_1994, landsat_vis_params, '1994年 Landsat 影像')
    # 右側圖層：Landsat 監督式分類結果
    right_layer = geemap.ee_tile_layer(classified_image, classification_vis, 'Landsat 監督式分類')

    my_Map.split_map(left_layer, right_layer)

    # 為監督式分類添加一個簡單的圖例 (手動建立，因為不是內建圖例)
    st.write("### 分類圖例 (右側地圖)")
    st.markdown("""
    <div style="display: flex; flex-wrap: wrap; gap: 10px;">
        <div style="display: flex; align-items: center;">
            <div style="width: 20px; height: 20px; background-color: #0000FF; border: 1px solid #ccc; margin-right: 5px;"></div>
            <span>水體</span>
        </div>
        <div style="display: flex; align-items: center;">
            <div style="width: 20px; height: 20px; background-color: #00FF00; border: 1px solid #ccc; margin-right: 5px;"></div>
            <span>植被</span>
        </div>
        <div style="display: flex; align-items: center;">
            <div style="width: 20px; height: 20px; background-color: #8B4513; border: 1px solid #ccc; margin-right: 5px;"></div>
            <span>裸地/建築</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # 設置地圖中心和縮放
    my_Map.centerObject(roi, 12)
    # 顯示地圖
    my_Map.to_streamlit(height=600)


st.title("2021年台灣土地覆蓋變化分析🌍")
st.markdown("左側為衛星真色影像；右側為土地覆蓋圖資。")

# ✅ 授權 Earth Engine
service_account_info = st.secrets["GEE_SERVICE_ACCOUNT"]
credentials = service_account.Credentials.from_service_account_info(
    service_account_info,
    scopes=["https://www.googleapis.com/auth/earthengine"]
)
ee.Initialize(credentials)
    
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
    
# --- 年份選擇器 (控制左右兩邊的地圖) ---
years = list(range(1990, 2025))
selected_year = st.sidebar.selectbox("選擇年份", years, index=years.index(2000))

roi = ee.Geometry.Rectangle([120.174618, 23.008626, 120.297048, 23.069197])
my_point = ee.Geometry.Point([120.271555,23.106061]);
# 擷取 Sentinel-2 影像
sentinel_image = (
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
s2_vis_params = {'min': 100, 'max': 3500, 'bands': ['B11', 'B8', 'B3']}

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

# 建立地圖並添加圖層
# --- 左欄：Sentinel-2 真色影像 ---
# --- 右欄：土地覆蓋圖資 --
my_Map = geemap.Map()
left_layer = geemap.ee_tile_layer(sentinel_image, s2_vis_params, 'Sentinel-2 真色影像')
right_layer = geemap.ee_tile_layer(my_lc, classVis, '土地覆蓋圖資')
my_Map.split_map(left_layer, right_layer)
my_Map.add_legend(title='Land Cover Type', builtin_legend='ESA_WorldCover')
my_Map.centerObject(roi, 12)

# 顯示地圖
my_Map.to_streamlit(height=600)

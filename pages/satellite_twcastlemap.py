import streamlit as st
import ee
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

# Streamlit 設定
st.set_page_config(layout="wide")
st.title("南科出現前後之衛星對比🌍")

# 地理區域與 AOI
my_point = ee.Geometry.Point([120.282006, 23.101410])
aoi = my_point.buffer(1000)

# 建立地圖
my_Map = geemap.Map()

# === 1984 Landsat 5 ===
collection_1984 = ee.ImageCollection('LANDSAT/LT05/C02/T1_L2') \
    .filterDate('1984-01-01', '1984-12-31') \
    .filterBounds(aoi) \
    .filter(ee.Filter.lt('CLOUD_COVER', 50)) \
    .sort('CLOUD_COVER')

my_image1984 = collection_1984.first()

# 預處理 Landsat：縮放與命名 RGB
image1984_rgb = my_image1984.select(['SR_B3', 'SR_B2', 'SR_B1']) \
    .multiply(0.0000275).add(-0.2) \
    .rename(['R', 'G', 'B'])  # 重新命名為通用 RGB 名稱

# === 2024 Sentinel-2 ===
collection_2024 = ee.ImageCollection('COPERNICUS/S2_SR') \
    .filterDate('2024-01-01', '2024-12-31') \
    .filterBounds(aoi) \
    .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20)) \
    .sort('CLOUDY_PIXEL_PERCENTAGE')

my_image2024 = collection_2024.first()
image2024_rgb = my_image2024.select(['B4', 'B3', 'B2'])  # Sentinel 原始 RGB 波段

# 驗證影像是否存在
if not isinstance(my_image1984, ee.Image):
    st.error("❌ 找不到符合條件的 1984 年影像。")
    st.stop()
if not isinstance(my_image2024, ee.Image):
    st.error("❌ 找不到符合條件的 2024 年影像。")
    st.stop()

# 視覺化參數
vis_1984 = {'min': 0.0, 'max': 0.3, 'bands': ['R', 'G', 'B']}
vis_2024 = {'min': 0, 'max': 3000, 'bands': ['B4', 'B3', 'B2']}

# 圖層
left_layer = geemap.ee_tile_layer(image1984_rgb, vis_1984, '1984 真色')
right_layer = geemap.ee_tile_layer(image2024_rgb, vis_2024, '2024 真色')

# 顯示地圖
my_Map.centerObject(aoi, 12)
my_Map.split_map(left_layer, right_layer)
my_Map.to_streamlit(height=600)

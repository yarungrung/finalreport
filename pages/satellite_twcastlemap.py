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

# 設定 AOI（興趣區域）：以指定經緯度為中心，建立 1000 公尺半徑緩衝區
center_point = ee.Geometry.Point([120.3138, 23.0865])
aoi = center_point.buffer(1000)

# 建立地圖
my_Map = geemap.Map()

# === 1984：Landsat 5 Collection 2 Level 2 ===
collection_1984 = ee.ImageCollection('LANDSAT/LT05/C02/T1_L2') \
    .filterDate('1984-01-01', '1984-12-31') \
    .filterBounds(aoi) \
    .filter(ee.Filter.lt('CLOUD_COVER', 50)) \
    .sort('CLOUD_COVER')

image_1984 = collection_1984.first()

if image_1984 is None:
    st.error("❌ 找不到符合條件的 1984 年 Landsat 影像。")
    st.stop()

# Landsat 5 SR 影像需要進行比例調整
image1984_rgb = image_1984.select(['SR_B3', 'SR_B2', 'SR_B1']) \
    .multiply(0.0000275).add(-0.2) \
    .rename(['SR_B3', 'SR_B2', 'SR_B1'])

# === 2024：Sentinel-2 SR ===
collection_2024 = ee.ImageCollection('COPERNICUS/S2_SR') \
    .filterDate('2024-01-01', '2024-12-31') \
    .filterBounds(aoi) \
    .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20)) \
    .sort('CLOUDY_PIXEL_PERCENTAGE')

image_2024 = collection_2024.first()

if image_2024 is None:
    st.error("❌ 找不到符合條件的 2024 年 Sentinel-2 影像。")
    st.stop()

image2024_rgb = image_2024.select(['B4', 'B3', 'B2'])

# 視覺化參數
vis_1984 = {'min': 0.0, 'max': 0.3, 'bands': ['SR_B3', 'SR_B2', 'SR_B1']}
vis_2024 = {'min': 0, 'max': 3000, 'bands': ['B4', 'B3', 'B2']}

# 建立圖層
left_layer = geemap.ee_tile_layer(image1984_rgb, vis_1984, '1984 真色')
right_layer = geemap.ee_tile_layer(image2024_rgb, vis_2024, '2024 真色')

# 顯示地圖
my_Map.centerObject(aoi, 13)
my_Map.split_map(left_layer, right_layer)
my_Map.to_streamlit(height=600)

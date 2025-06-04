import streamlit as st
import ee
from google.oauth2 import service_account
import geemap.foliumap as geemap

# ✅ 授權 Earth Engine（需要 secrets.toml 中有 GEE_SERVICE_ACCOUNT）
service_account_info = st.secrets["GEE_SERVICE_ACCOUNT"]
credentials = service_account.Credentials.from_service_account_info(
    service_account_info,
    scopes=["https://www.googleapis.com/auth/earthengine"]
)
ee.Initialize(credentials)

# ✅ Streamlit 設定
st.set_page_config(layout="wide")
st.title("南科 1994 vs 2024 衛星影像變遷比較 🌍")

# ✅ 定義 AOI（以點為中心，緩衝 3 公里）
center_point = ee.Geometry.Point([120.3138, 23.0865])
aoi = center_point.buffer(3000)

# ✅ 建立地圖
my_Map = geemap.Map()
my_Map.centerObject(aoi, 13)

# === 1994 年 Landsat 5 ===
collection_1994 = ee.ImageCollection('LANDSAT/LT05/C02/T1_L2') \
    .filterDate('1994-01-01', '1994-12-31') \
    .filterBounds(aoi) \
    .filter(ee.Filter.lt('CLOUD_COVER', 60)) \
    .sort('CLOUD_COVER')

image_1994 = collection_1994.first()

if not image_1994:
    st.error("❌ 找不到符合條件的 1994 年 Landsat 影像。")
    st.stop()
else:
    st.write("✅ 成功取得 1994 年 Landsat 影像。")

# Landsat 5 影像處理（真色）
collection_1994 = ee.ImageCollection('LANDSAT/LT05/C02/T1_L2') \
    .filterDate('1994-01-01', '1994-12-31') \
    .filterBounds(aoi) \
    .filter(ee.Filter.lt('CLOUD_COVER', 60))

# 取得平均影像 + 裁切 AOI，避免偏移問題
image_1994 = collection_1994.select(['SR_B3', 'SR_B2', 'SR_B1']) \
    .mean() \
    .clip(aoi)

# 處理並視覺化
image1994_rgb = image_1994.multiply(0.0000275).add(-0.2)

vis_1994 = {
    'min': 0.0,
    'max': 0.3,
    'bands': ['SR_B3', 'SR_B2', 'SR_B1']
}

# === 2024 年 Sentinel-2 ===
collection_2024 = ee.ImageCollection('COPERNICUS/S2_SR') \
    .filterDate('2024-01-01', '2024-12-31') \
    .filterBounds(aoi) \
    .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20)) \
    .sort('CLOUDY_PIXEL_PERCENTAGE')

image_2024 = collection_2024.first()

if not image_2024:
    st.error("❌ 找不到符合條件的 2024 年 Sentinel-2 影像。")
    st.stop()
else:
    st.write("✅ 成功取得 2024 年 Sentinel-2 影像。")

image2024_rgb = image_2024.select(['B4', 'B3', 'B2'])

vis_2024 = {
    'min': 0,
    'max': 3000,
    'bands': ['B4', 'B3', 'B2']
}

# ✅ 建立左右比較圖層
left_layer = geemap.ee_tile_layer(image1994_rgb, vis_1994, '1994 真色')
right_layer = geemap.ee_tile_layer(image2024_rgb, vis_2024, '2024 真色')

# ✅ 加入 split 地圖
my_Map.split_map(left_layer, right_layer)

# ✅ 顯示於 Streamlit
my_Map.to_streamlit(height=600)

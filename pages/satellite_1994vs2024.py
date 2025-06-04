import streamlit as st
import ee
from google.oauth2 import service_account
import geemap.foliumap as geemap

# ====== Earth Engine 授權 ======
service_account_info = st.secrets["GEE_SERVICE_ACCOUNT"]
credentials = service_account.Credentials.from_service_account_info(
    service_account_info,
    scopes=["https://www.googleapis.com/auth/earthengine"]
)
ee.Initialize(credentials)

# ====== UI 設定 ======
st.set_page_config(layout="wide")
st.title("🌍 南科區域 1994 vs 2024 衛星影像對比")

# ====== AOI 設定 ======
center_point = ee.Geometry.Point([120.3138, 23.0865])
aoi = center_point.buffer(1000)  # 半徑 1000 公尺

# ====== 建立地圖物件 ======
my_Map = geemap.Map()

# ====== 1994 年 Landsat 5 影像 ======
collection_1994 = ee.ImageCollection('LANDSAT/LT05/C02/T1_L2') \
    .filterDate('1994-01-01', '1994-12-31') \
    .filterBounds(aoi) \
    .filter(ee.Filter.lt('CLOUD_COVER', 50))

# 使用平均影像，避免偏移與雲層干擾
image_1994 = collection_1994.select(['SR_B3', 'SR_B2', 'SR_B1']).mean().clip(aoi)
image1994_rgb = image_1994.multiply(0.0000275).add(-0.2)

# 視覺化參數
vis_1994 = {
    'min': 0.0,
    'max': 0.3,
    'bands': ['SR_B3', 'SR_B2', 'SR_B1']
}

# ====== 2024 年 Sentinel-2 影像 ======
collection_2024 = ee.ImageCollection('COPERNICUS/S2_SR') \
    .filterDate('2024-01-01', '2024-12-31') \
    .filterBounds(aoi) \
    .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20))

image_2024 = collection_2024.first()
if image_2024 is None:
    st.error("❌ 找不到 2024 年合適的影像")
    st.stop()

image2024_rgb = image_2024.select(['B4', 'B3', 'B2'])

vis_2024 = {
    'min': 0,
    'max': 3000,
    'bands': ['B4', 'B3', 'B2']
}

# ====== 加入圖層與設定 ======
left_layer = geemap.ee_tile_layer(image1994_rgb, vis_1994, '1994 真色')
right_layer = geemap.ee_tile_layer(image2024_rgb, vis_2024, '2024 真色')

my_Map.centerObject(center_point, 13)
my_Map.split_map(left_layer, right_layer)
my_Map.to_streamlit(height=600)

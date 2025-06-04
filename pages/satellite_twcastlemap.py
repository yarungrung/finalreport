import streamlit as st
import ee
from google.oauth2 import service_account
import geemap.foliumap as geemap

# 授權
service_account_info = st.secrets["GEE_SERVICE_ACCOUNT"]
credentials = service_account.Credentials.from_service_account_info(
    service_account_info,
    scopes=["https://www.googleapis.com/auth/earthengine"]
)
ee.Initialize(credentials)

# UI 設定
st.set_page_config(layout="wide")
st.title("南科出現前後之衛星對比🌍")

# AOI 定義
center_point = ee.Geometry.Point([120.3138, 23.0865])
aoi = center_point.buffer(1000)

# 建立地圖
my_Map = geemap.Map()

# === 1984 年 Landsat 5 ===
collection_1984 = ee.ImageCollection('LANDSAT/LT05/C02/T1_L2') \
    .filterDate('1984-01-01', '1984-12-31') \
    .filterBounds(aoi) \
    .filter(ee.Filter.lt('CLOUD_COVER', 50)) \
    .sort('CLOUD_COVER')

image_1984 = collection_1984.first()

if image_1984 is None:
    st.error("❌ 找不到符合條件的 1984 年 Landsat 影像。")
    st.stop()
else:
    band_names_1984 = image_1984.bandNames().getInfo()
    st.write("✅ 1984 影像波段名稱:", band_names_1984)

# 若波段名稱確認沒問題，才進行轉換與選取
try:
    image1984_rgb = image_1984.select(['SR_B3', 'SR_B2', 'SR_B1']) \
        .multiply(0.0000275).add(-0.2) \
        .rename(['SR_B3', 'SR_B2', 'SR_B1'])
except Exception as e:
    st.error(f"⚠️ 波段選取錯誤：{e}")
    st.stop()

# === 2024 年 Sentinel-2 ===
collection_2024 = ee.ImageCollection('COPERNICUS/S2_SR') \
    .filterDate('2024-01-01', '2024-12-31') \
    .filterBounds(aoi) \
    .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20)) \
    .sort('CLOUDY_PIXEL_PERCENTAGE')

image_2024 = collection_2024.first()

if image_2024 is None:
    st.error("❌ 找不到符合條件的 2024 年 Sentinel-2 影像。")
    st.stop()
else:
    band_names_2024 = image_2024.bandNames().getInfo()
    st.write("✅ 2024 影像波段名稱:", band_names_2024)

image2024_rgb = image_2024.select(['B4', 'B3', 'B2'])

# 視覺化參數
vis_1984 = {'min': 0.0, 'max': 0.3, 'bands': ['SR_B3', 'SR_B2', 'SR_B1']}
vis_2024 = {'min': 0, 'max': 3000, 'bands': ['B4', 'B3', 'B2']}

# 圖層
left_layer = geemap.ee_tile_layer(image1984_rgb, vis_1984, '1984 真色')
right_layer = geemap.ee_tile_layer(image2024_rgb, vis_2024, '2024 真色')

# 顯示地圖
my_Map.centerObject(aoi, 13)
my_Map.split_map(left_layer, right_layer)
my_Map.to_streamlit(height=600)

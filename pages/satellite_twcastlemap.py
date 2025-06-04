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

###############################################

st.set_page_config(layout="wide")
st.title("南科出現前後之衛星對比🌍")

# 地理區域
my_point = ee.Geometry.Point([120.282006,23.101410])
aoi = my_point.buffer(1000)  # 1000 公尺緩衝區作為感興趣區域

# 建立地圖
my_Map = geemap.Map()

# 1984 年：Landsat 5
my_image1984 = ee.ImageCollection('LANDSAT/LT05/C01/T1_SR') \
    .filterDate('1984-01-01', '1984-12-31') \
    .filterBounds(aoi) \
    .sort('CLOUD_COVER') \
    .first()

# 2024 年：Sentinel-2
my_image2024 = ee.ImageCollection('COPERNICUS/S2_SR') \
    .filterDate('2024-01-01', '2024-12-31') \
    .filterBounds(aoi) \
    .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20)) \
    .sort('CLOUDY_PIXEL_PERCENTAGE') \
    .first()

# 檢查是否有成功取得影像
if not my_image1984:
    st.error("❌ 找不到符合條件的 1984 年影像。")
    st.stop()

if not my_image2024:
    st.error("❌ 找不到符合條件的 2024 年影像。")
    st.stop()

# 視覺化參數
vis_params_1984 = {'min': 0, 'max': 3000, 'bands': ['B3', 'B2', 'B1']}  # Landsat
vis_params_2024 = {'min': 0, 'max': 3000, 'bands': ['B4', 'B3', 'B2']}  # Sentinel-2

# 圖層
left_layer = geemap.ee_tile_layer(my_image1984, vis_params_1984, '1984 真色')
right_layer = geemap.ee_tile_layer(my_image2024, vis_params_2024, '2024 真色')

# 地圖顯示
my_Map.centerObject(aoi, 12)
my_Map.split_map(left_layer, right_layer)
my_Map.to_streamlit(height=600)

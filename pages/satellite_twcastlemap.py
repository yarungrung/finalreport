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

# 擷取 Harmonized Sentinel-2 MSI: MultiSpectral Instrument, Level-1C 1984衛星影像
my_image1984 = (
    ee.ImageCollection('COPERNICUS/S2_HARMONIZED')
    .filterBounds(my_point)
    .filterDate('1984-01-01', '1984-06-30')
    .sort('CLOUDY_PIXEL_PERCENTAGE')
    .first()
    .select('B.*')
)
vis_params = {'min':100, 'max': 3500, 'bands': ['B11',  'B8',  'B3']}

# 擷取 Harmonized Sentinel-2 MSI: MultiSpectral Instrument, Level-1C 2025衛星影像
my_image2025 = (ee.ImageCollection('COPERNICUS/S2_HARMONIZED')
    .filterBounds(my_point)
    .filterDate('2024-06-30', '2025-01-01')
    .sort('CLOUDY_PIXEL_PERCENTAGE')
    .first()
    .select('B.*')
)
vis_params = {'min':100, 'max': 3500, 'bands': ['B11',  'B8',  'B3']}


left_layer = geemap.ee_tile_layer(my_image1984,vis_params, '1984真色')
right_layer = geemap.ee_tile_layer(my_image2025,vis_params, '2025真色')

my_Map.centerObject(my_img.geometry(), 12)
my_Map.split_map(left_layer, right_layer)

my_Map = geemap.Map()

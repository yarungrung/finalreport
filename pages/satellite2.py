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
st.title("衛星與台灣堡圖🌍")

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

# 匯入台灣堡圖


vis_params = {'min':100, 'max': 3500, 'bands': ['B11',  'B8',  'B3']}

#匯入台灣堡圖


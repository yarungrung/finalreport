import streamlit as st
import ee
from google.oauth2 import service_account

# 替換為你剛下載的金鑰路徑
SERVICE_ACCOUNT = 'gee-service-account@ee-s1243032.iam.gserviceaccount.com'
KEY_FILE = 'C:\digital_earth\gold key.json'

# 建立認證物件
credentials = service_account.Credentials.from_service_account_file(
    KEY_FILE,
    scopes=['https://www.googleapis.com/auth/earthengine']
)

# 初始化 Earth Engine
ee.Initialize(credentials)


# 初始化 Google Earth Engine
try:
    ee.Initialize(credentials)
except Exception as e:
    st.error("未授權，請運行 `earthengine authenticate` 來授權。")
    st.stop()

st.set_page_config(layout="wide", page_title="台灣土地覆蓋變化", page_icon="🌎")

# 定義函數以獲取 Landsat 影像
def get_landsat_image(region):
    # 指定要獲取的年份
    years = [1994, 2024]
    images = []

    for year in years:
        if year < 1994:
            collection = ee.ImageCollection('LANDSAT/LT04/C01/T1_SR')  # Landsat 4
            bands = ['B1', 'B2', 'B3', 'B4', 'B5', 'B7']
        elif year < 2013:
            collection = ee.ImageCollection('LANDSAT/LT05/C01/T1_SR')  # Landsat 5
            bands = ['B1', 'B2', 'B3', 'B4', 'B5', 'B7']
        elif year < 2021:
            collection = ee.ImageCollection('LANDSAT/LC08/C01/T1_SR')  # Landsat 8
            bands = ['B2', 'B1', 'B3', 'B4', 'B5', 'B6', 'B7', 'B10', 'B11']
        else:
            collection = ee.ImageCollection('LANDSAT/LC09/C02/T1_L2')  # Landsat 9
            bands = ['B2', 'B1', 'B3', 'B4', 'B5', 'B6', 'B7']

        # 檢查影像集合中是否有影像
        image_count = collection.filterDate(f'{year}-01-01', f'{year}-12-31') \
                                 .filterBounds(region) \
                                 .size().getInfo()

        if image_count == 0:
            print(f"{year} 年的影像在指定區域內不存在。")
            continue

        image = collection.filterDate(f'{year}-01-01', f'{year}-12-31') \
                          .filterBounds(region) \
                          .median() \
                          .clip(region) \
                          .select(bands)

        images.append(image)

    return images

# 定義區域
region = ee.Geometry.Polygon([
    [[120.205, 23.020], [120.205, 22.990], [120.230, 22.990], [120.230, 23.020]]
])

# 獲取影像
landsat_images = get_landsat_image(region)
landsat_1994 = landsat_images[0] if len(landsat_images) > 0 else None
landsat_2024 = landsat_images[1] if len(landsat_images) > 1 else None

# 定義調色盤
palette = ['#466b9f', '#d1def8', '#dec5c5', '#d99282', '#eb0000', '#ab0000', '#b3ac9f', '#68ab5f', '#1c5f2c', '#b5c58f', '#ccb879', '#b8d9eb', '#6c9fb8']

# Streamlit 應用程式
st.title("南部科技園區土地使用分類衛星影像比較")

# 創建左右分割圖
col1, col2 = st.columns(2)

with col1:
    st.subheader("1994 年土地使用分類")
    if landsat_1994 is not None:
        st.image(landsat_1994.getThumbUrl({'min': 0, 'max': 0.3, 'palette': palette}), use_column_width=True)

with col2:
    st.subheader("2024 年土地使用分類")
    if landsat_2024 is not None:
        st.image(landsat_2024.getThumbUrl({'min': 0, 'max': 0.3, 'palette': palette}), use_column_width=True)

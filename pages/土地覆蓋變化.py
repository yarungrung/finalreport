import streamlit as st
import ee
import geemap

st.set_page_config(layout="wide", page_title="台灣土地覆蓋變化", page_icon="🌎")
#此分頁有兩個左右分割圖，一個是1994年的土地監督式分類圖資佐衛星影像圖；一個是2021年的(因為有現成圖資)

st.title("1994年台灣土地覆蓋變化分析🌍")
st.markdown("左側為衛星真色影像；右側為土地覆蓋圖資。"
# 初始化 Google Earth Engine
ee.Initialize()
# 定義函數以獲取 Landsat 影像
def get_landsat_image(year, region):
    if year < 2013:
        collection = ee.ImageCollection('LANDSAT/LT05/C01/T1_SR')
        bands = ['B1', 'B2', 'B3', 'B4', 'B5', 'B7']
    else:
        collection = ee.ImageCollection('LANDSAT/LC09/C02/T1_L2')
        bands = ['B1', 'B2', 'B3', 'B4', 'B5', 'B6', 'B7', 'B10', 'B11']
    image = collection.filterDate(f'{year}-01-01', f'{year}-12-31') \
                      .filterBounds(region) \
                      .median() \
                      .clip(region) \
                      .select(bands)
    return image
# 定義區域
region = ee.Geometry.Polygon([
    [[120.205, 23.020], [120.205, 22.990], [120.230, 22.990], [120.230, 23.020]]
])
# 獲取影像
landsat_1994 = get_landsat_image(1994, region)
landsat_2024 = get_landsat_image(2024, region)
# 定義調色盤
palette = ['#466b9f', '#d1def8', '#dec5c5', '#d99282', '#eb0000', '#ab0000', '#b3ac9f', '#68ab5f', '#1c5f2c', '#b5c58f', '#ccb879', '#b8d9eb', '#6c9fb8']
# Streamlit 應用程式
st.title("南部科技園區土地使用分類衛星影像比較")
# 創建左右分割圖
col1, col2 = st.columns(2)
with col1:
    st.subheader("1994 年土地使用分類")
    st.image(landsat_1994.getThumbUrl({'min': 0, 'max': 0.3, 'palette': palette}), use_column_width=True)
with col2:
    st.subheader("2024 年土地使用分類")
    st.image(landsat_2024.getThumbUrl({'min': 0, 'max': 0.3, 'palette': palette}), use_column_width=True)

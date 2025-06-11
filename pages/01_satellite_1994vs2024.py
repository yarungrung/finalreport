import streamlit as st
import ee
from google.oauth2 import service_account
import geemap.foliumap as geemap

# ✅ 授權 Earth Engine
service_account_info = st.secrets["GEE_SERVICE_ACCOUNT"]
credentials = service_account.Credentials.from_service_account_info(
    service_account_info,
    scopes=["https://www.googleapis.com/auth/earthengine"]
)
ee.Initialize(credentials)

# ✅ Streamlit 頁面設定
st.set_page_config(layout="wide")
st.title("南科 1994 vs 2024 衛星影像變遷比較🗺️")

# ✅ AOI：以南科中心點建立緩衝區
center_coords = [120.3138, 23.0865]
center_point = ee.Geometry.Point(center_coords)
aoi = center_point.buffer(3000)

# ✅ 建立地圖（指定中心與縮放）
my_Map = geemap.Map(center=center_coords[::-1], zoom=16)

# === 1994 年 Landsat 5 處理 ===
collection_1994 = ee.ImageCollection('LANDSAT/LT05/C02/T1_L2') \
    .filterDate('1994-01-01', '1994-12-31') \
    .filterBounds(aoi) \
    .filter(ee.Filter.lt('CLOUD_COVER', 60))

image_1994 = collection_1994.select(['SR_B3', 'SR_B2', 'SR_B1']) \
    .median() \
    .multiply(0.0000275).add(-0.2)

vis_1994 = {
    'min': 0.0,
    'max': 0.3,
    'bands': ['SR_B3', 'SR_B2', 'SR_B1']
}

# === 2024 年 Sentinel-2 處理 ===
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

# ✅ 建立比較圖層
left_layer = geemap.ee_tile_layer(image_1994, vis_1994, '1994 真色')
right_layer = geemap.ee_tile_layer(image2024_rgb, vis_2024, '2024 真色')

# ✅ 加入左右滑動地圖
my_Map.split_map(left_layer, right_layer)

# ✅ 顯示地圖於 Streamlit
my_Map.to_streamlit(height=600)


st.markdown(""" 
<p>
對比南科還沒出現的1994和南科三期擴建結束的2024年之衛星影像圖，觀察結果： <br>
1. 路網，由稀疏轉為明顯且複雜 <br>
2. 住宅及建築物，1994多為田地，而2024年大多過去的田地轉變成了各式建築物 <br>
    </p>
    """,
    unsafe_allow_html=True 
           )


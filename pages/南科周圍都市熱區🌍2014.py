import streamlit as st
import ee
from google.oauth2 import service_account
import geemap.foliumap as geemap
import json

st.markdown("南科周圍都市熱區🌍2014")
# --- Streamlit 應用程式設定 ---
st.set_page_config(layout="wide")
st.title("南科周圍都市熱區🌍2014")

# --- GEE 服務帳戶驗證 ---
try:
    service_account_info_raw = st.secrets["GEE_SERVICE_ACCOUNT"]

    # 嘗試將其解析為 JSON，如果失敗，則假設它已經是字典 (AttrDict)
    if isinstance(service_account_info_raw, str):
        service_account_info = json.loads(service_account_info_raw)
    else: # 它可能已經是 AttrDict 或 dict
        service_account_info = service_account_info_raw

    credentials = service_account.Credentials.from_service_account_info(
        service_account_info,
        scopes=["https://www.googleapis.com/auth/earthengine"]
    )
    ee.Initialize(credentials)
    st.success("Google Earth Engine 已成功初始化！")
except Exception as e:
    st.error(f"初始化 Google Earth Engine 失敗: {e}")
    st.info("請確認你的 Streamlit Secrets 中已正確設定 'GEE_SERVICE_ACCOUNT'，並確認其為有效的 JSON 格式或已正確載入。")
    st.stop() # <<< 這個 st.stop() 是關鍵，如果 GEE 失敗，它會阻止後續程式碼執行。

# --- 只有當 GEE 初始化成功後，才會執行以下代碼 ---

# --- 定義 AOI 座標和日期參數 ---
aoi_coords = [120.265429, 23.057127, 120.362146, 23.115991]
startDate = '2015-01-01'
endDate = '2015-04-30'

# 將 AOI 定義為 ee.Geometry.Rectangle
aoi = ee.Geometry.Rectangle(aoi_coords)

# --- 地圖物件 ---
Map = geemap.Map()
Map.addLayer(aoi, {}, 'AOI - TAINAN')
Map.centerObject(aoi, 12) # 設定了初始地圖的中心和縮放

# --- 顯示地圖 ---
st.write("### ")
Map.to_streamlit(height=500)


# --- 函數定義 ---
def applyScaleFactors(image):
    opticalBands = image.select('SR_B.').multiply(0.0000275).add(-0.2)
    thermalBands = image.select('ST_B.*').multiply(0.00341802).add(149.0)
    image = image.addBands(opticalBands, overwrite=True)
    image = image.addBands(thermalBands, overwrite=True)
    return image

def cloudMask(image):
    cloud_shadow_bitmask = (1 << 3)
    cloud_bitmask = (1 << 5)
    qa = image.select('QA_PIXEL')
    mask = qa.bitwiseAnd(cloud_shadow_bitmask).eq(0).And(qa.bitwiseAnd(cloud_bitmask).eq(0))
    return image.updateMask(mask)

# --- 影像資料獲取與處理 ---
st.write("載入 Landsat 8 影像")

@st.cache_data
def get_processed_image(start_date, end_date, coordinates):
    current_aoi = ee.Geometry.Rectangle(coordinates)
    current_collection = (ee.ImageCollection("LANDSAT/LC08/C02/T1_L2")
                         .filterBounds(current_aoi)
                         .filterDate(start_date, end_date))

    image = (current_collection
               .map(applyScaleFactors)
               .map(cloudMask)
               .median()
               .clip(current_aoi))
    return image

image = get_processed_image(startDate, endDate, tuple(aoi_coords))

# --- 顯示真彩色影像 ---
st.markdown("### 1.真彩色影像 (B4-B3-B2)")
visualization = {
    'bands': ['SR_B4', 'SR_B3', 'SR_B2'],
    'min': 0.0,
    'max': 0.3
}
# 修改這裡：直接使用已知的中心點和縮放級別
# 你可以從 Map.centerObject(aoi, 12) 中提取，或者使用 aoi_coords 的中心
# 或者簡化為一個固定的中心點和縮放，例如：
Map_true_color = geemap.Map(center=[23.0865, 120.3138], zoom=12) # 以aoi的中心點作為範例
Map_true_color.addLayer(image, visualization, 'True Color 432')
Map_true_color.to_streamlit(height=500)


# --- 計算與顯示 NDVI ---
st.write("### 2.NDVI (正規化差異植被指數)")
ndvi = image.normalizedDifference(['SR_B5', 'SR_B4']).rename('NDVI')
ndvi_vis = {
    'min': -1,
    'max': 1,
    'palette': ['blue', 'white', 'green']
}

# 修改這裡：
Map_ndvi = geemap.Map(center=[23.0865, 120.3138], zoom=12)
Map_ndvi.addLayer(ndvi, ndvi_vis, 'NDVI - TAINAN')
Map_ndvi.to_streamlit(height=500)

# --- 計算 NDVI 統計值 ---
@st.cache_data
def get_ndvi_stats(start_date, end_date, aoi_coordinates):
    current_aoi = ee.Geometry.Rectangle(aoi_coordinates)
    current_collection = (ee.ImageCollection("LANDSAT/LC08/C02/T1_L2")
                         .filterBounds(current_aoi)
                         .filterDate(start_date, end_date))

    processed_img_for_stats = (current_collection
                               .map(applyScaleFactors)
                               .map(cloudMask)
                               .median()
                               .clip(current_aoi))

    current_ndvi = processed_img_for_stats.normalizedDifference(['SR_B5', 'SR_B4']).rename('NDVI')

    ndvi_min = ee.Number(current_ndvi.reduceRegion(
        reducer=ee.Reducer.min(),
        geometry=current_aoi,
        scale=30,
        maxPixels=1e9
    ).values().get(0))

    ndvi_max = ee.Number(current_ndvi.reduceRegion(
        reducer=ee.Reducer.max(),
        geometry=current_aoi,
        scale=30,
        maxPixels=1e9
    ).values().get(0))
    return ndvi_min.getInfo(), ndvi_max.getInfo()

ndvi_min_val, ndvi_max_val = get_ndvi_stats(startDate, endDate, tuple(aoi_coords))


st.write(f"NDVI 最小值: {ndvi_min_val:.2f}")
st.write(f"NDVI 最大值: {ndvi_max_val:.2f}")


# --- 計算植被覆蓋率 (FV) 與地表發射率 (EM) ---
st.write("### 3.植被覆蓋率 (FV) 與地表發射率 (EM)")
fv = ndvi.subtract(ndvi_min_val).divide(ndvi_max_val - ndvi_min_val).pow(2).rename("FV")
em = fv.multiply(0.004).add(0.986).rename("EM")


# --- 計算與顯示地表溫度 (LST) ---
st.write("### 4.地表溫度 (LST)")
@st.cache_data
def calculate_lst(start_date, end_date, coordinates, ndvi_min_val, ndvi_max_val):
    current_aoi = ee.Geometry.Rectangle(coordinates)
    current_collection = (ee.ImageCollection("LANDSAT/LC08/C02/T1_L2")
                         .filterBounds(current_aoi)
                         .filterDate(start_date, end_date))

    processed_img = (current_collection
                               .map(applyScaleFactors)
                               .map(cloudMask)
                               .median()
                               .clip(current_aoi))

    current_thermal = processed_img.select('ST_B10').rename('thermal')

    current_ndvi = processed_img.normalizedDifference(['SR_B5', 'SR_B4']).rename('NDVI')
    current_fv = current_ndvi.subtract(ndvi_min_val).divide(ndvi_max_val - ndvi_min_val).pow(2).rename("FV")
    current_em = current_fv.multiply(0.004).add(0.986).rename("EM")

    lst = current_thermal.expression(
        '(TB / (1 + (0.00115 * (TB / 1.438)) * log(em))) - 273.15',
        {
            'TB': current_thermal.select('thermal'),
            'em': current_em
        }
    ).rename('LST TAINAN')
    return lst

lst = calculate_lst(startDate, endDate, tuple(aoi_coords), ndvi_min_val, ndvi_max_val)


lst_vis = {
    'min': 18.47,
    'max': 42.86,
    'palette': [
        '040274', '040281', '0502a3', '0502b8', '0502ce', '0502e6',
        '0602ff', '235cb1', '307ef3', '269db1', '30c8e2', '32d3ef',
        '3be285', '3ff38f', '86e26f', '3ae237', 'b5e22e', 'd6e21f',
        'fff705', 'ffd611', 'ffb613', 'ff8b13', 'ff6e08', 'ff500d',
        'ff0000', 'de0101', 'c21301', 'a71001', '911003'
    ]
}

# 修改這裡：
Map_lst = geemap.Map(center=[23.0865, 120.3138], zoom=12)
Map_lst.addLayer(lst, lst_vis, 'Land Surface Temperature')
Map_lst.to_streamlit(height=500)

st.write("---")
st.write("數據來源：Landsat 8 Collection 2 Tier 1 Level 2")

import streamlit as st
import ee
from google.oauth2 import service_account
import geemap.foliumap as geemap
import json # 為了處理 Streamlit secrets 中的 JSON

# --- Streamlit 應用程式設定 ---
st.set_page_config(layout="wide")
st.title("南科周圍都市熱區🌍")

# --- GEE 服務帳戶驗證 ---
# 從 Streamlit Secrets 讀取 GEE 服務帳戶金鑰 JSON
# 確保你在 Streamlit Cloud 的 "Secrets" 或本地 .streamlit/secrets.toml 中設定了 "GEE_SERVICE_ACCOUNT"
# 例如：
# # .streamlit/secrets.toml
# GEE_SERVICE_ACCOUNT = '''
# {
#   "type": "service_account",
#   "project_id": "your-project-id",
#   "private_key_id": "...",
#   "private_key": "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n",
#   "client_email": "...",
#   "client_id": "...",
#   "auth_uri": "...",
#   "token_uri": "...",
#   "auth_provider_x509_cert_url": "...",
#   "client_x509_cert_url": "...",
#   "universe_domain": "..."
# }
# '''

try:
    # 這裡假設你的 GEE_SERVICE_ACCOUNT 是一個 JSON 字串
    # 如果它已經是一個 Python 字典，則無需 json.loads
    service_account_info = json.loads(st.secrets["GEE_SERVICE_ACCOUNT"])
    credentials = service_account.Credentials.from_service_account_info(
        service_account_info,
        scopes=["https://www.googleapis.com/auth/earthengine"]
    )
    ee.Initialize(credentials)
    st.success("Google Earth Engine 已成功初始化！")
except Exception as e:
    st.error(f"初始化 Google Earth Engine 失敗: {e}")
    st.info("請確認你的 Streamlit Secrets 中已正確設定 'GEE_SERVICE_ACCOUNT'。")
    st.stop() # 停止程式運行，直到 GEE 驗證成功

# 你原始碼中的 ee.Authenticate() 和 ee.Initialize(project="ee-s1143056")
# 在使用服務帳戶時通常不需要，因為服務帳戶會直接處理身份驗證。
# 如果你的服務帳戶金鑰中已經包含了 project_id，這裡可以不用再指定。

# --- 定義 AOI ---
aoi = ee.Geometry.Rectangle([120.265429, 23.057127, 120.362146, 23.115991])

# --- 地圖物件 ---
# 在 Streamlit 中，通常會創建一個 Map 物件並在需要顯示時調用它的 _repr_html_ 方法
Map = geemap.Map()
Map.addLayer(aoi, {}, 'AOI - TAINAN')
Map.centerObject(aoi, 12)

# --- 顯示地圖 ---
# geemap.foliumap 地圖物件有一個 _repr_html_ 方法，Streamlit 可以直接渲染它
st.write("### 區域概覽")
Map.to_streamlit(height=500) # geemap 提供了一個方便的 Streamlit 整合方法

# --- 影像處理參數 ---
startDate = '2015-01-01'
endDate = '2015-04-30'

# --- 函數定義 ---
# 應用縮放因子
def applyScaleFactors(image):
    opticalBands = image.select('SR_B.').multiply(0.0000275).add(-0.2)
    thermalBands = image.select('ST_B.*').multiply(0.00341802).add(149.0)
    image = image.addBands(opticalBands, overwrite=True)
    image = image.addBands(thermalBands, overwrite=True)
    return image

# 應用 CloudMask
def cloudMask(image):
    cloud_shadow_bitmask = (1 << 3)
    cloud_bitmask = (1 << 5)
    qa = image.select('QA_PIXEL')
    mask = qa.bitwiseAnd(cloud_shadow_bitmask).eq(0).And(qa.bitwiseAnd(cloud_bitmask).eq(0))
    return image.updateMask(mask)

# --- 影像資料獲取與處理 ---
st.write("### 載入 Landsat 8 影像")
collection = (ee.ImageCollection("LANDSAT/LC08/C02/T1_L2")
              .filterBounds(aoi)
              .filterDate(startDate, endDate))

# st.write(f"影像數量: {collection.size().getInfo()}") # 這行會觸發 GEE 調用，可能導致 Streamlit 重新運行

# 使用 Streamlit 的緩存來避免重複的 Earth Engine 計算，特別是對於那些不常變動的資料
@st.cache_data
def get_processed_image(collection, aoi):
    # 導入 Landsat 8 影像
    image = (collection
               .map(applyScaleFactors)
               .map(cloudMask)
               .median()
               .clip(aoi))
    return image

image = get_processed_image(collection, aoi)


# --- 顯示真彩色影像 ---
st.write("### 真彩色影像 (432)")
visualization = {
    'bands': ['SR_B4', 'SR_B3', 'SR_B2'],
    'min': 0.0,
    'max': 0.3
}
Map_true_color = geemap.Map(center=Map.center, zoom=Map.zoom) # 創建新地圖實例
Map_true_color.addLayer(image, visualization, 'True Color 432')
Map_true_color.to_streamlit(height=500)


# --- 計算與顯示 NDVI ---
st.write("### NDVI (正規化差異植被指數)")
ndvi = image.normalizedDifference(['SR_B5', 'SR_B4']).rename('NDVI')
ndvi_vis = {
    'min': -1,
    'max': 1,
    'palette': ['blue', 'white', 'green']
}

Map_ndvi = geemap.Map(center=Map.center, zoom=Map.zoom) # 創建新地圖實例
Map_ndvi.addLayer(ndvi, ndvi_vis, 'NDVI - TAINAN')
Map_ndvi.to_streamlit(height=500)

# --- 計算 NDVI 統計值 ---
@st.cache_data
def get_ndvi_stats(ndvi_image, aoi_geometry):
    ndvi_min = ee.Number(ndvi_image.reduceRegion(
        reducer=ee.Reducer.min(),
        geometry=aoi_geometry,
        scale=30,
        maxPixels=1e9
    ).values().get(0))

    ndvi_max = ee.Number(ndvi_image.reduceRegion(
        reducer=ee.Reducer.max(),
        geometry=aoi_geometry,
        scale=30,
        maxPixels=1e9
    ).values().get(0))
    return ndvi_min.getInfo(), ndvi_max.getInfo()

ndvi_min_val, ndvi_max_val = get_ndvi_stats(ndvi, aoi)

st.write(f"NDVI 最小值: {ndvi_min_val:.2f}")
st.write(f"NDVI 最大值: {ndvi_max_val:.2f}")


# --- 計算植被覆蓋率 (FV) 與地表發射率 (EM) ---
st.write("### 植被覆蓋率 (FV) 與地表發射率 (EM)")
fv = ndvi.subtract(ndvi_min_val).divide(ndvi_max_val - ndvi_min_val).pow(2).rename("FV")
em = fv.multiply(0.004).add(0.986).rename("EM")

# 注意：fv.getInfo() 和 em.getInfo() 會返回字典，用於印出詳細資訊。
# 在 Streamlit 中，通常會直接使用這些 Image 物件進行後續處理。
# st.write(f"FV 資訊: {fv.getInfo()}")
# st.write(f"EM 資訊: {em.getInfo()}")


# --- 計算與顯示地表溫度 (LST) ---
st.write("### 地表溫度 (LST)")
thermal = image.select('ST_B10').rename('thermal')

# 在 Streamlit 中使用 .getInfo() 獲取數值時，要小心它會觸發 Earth Engine 請求。
# 確保你的 min/max 值是預先設定好，或者也在 @st.cache_data 函數中計算。
# 這裡我使用了你提供的固定值。
lst = thermal.expression(
    '(TB / (1 + (0.00115 * (TB / 1.438)) * log(em))) - 273.15',
    {
        'TB': thermal.select('thermal'),
        'em': em
    }
).rename('LST TAINAN')

lst_vis = {
    'min': 18.47, # 這些值通常來自你 AOI 的實際範圍，而不是硬編碼
    'max': 42.86, # 為了演示，我們使用你提供的範例值
    'palette': [
        '040274', '040281', '0502a3', '0502b8', '0502ce', '0502e6',
        '0602ff', '235cb1', '307ef3', '269db1', '30c8e2', '32d3ef',
        '3be285', '3ff38f', '86e26f', '3ae237', 'b5e22e', 'd6e21f',
        'fff705', 'ffd611', 'ffb613', 'ff8b13', 'ff6e08', 'ff500d',
        'ff0000', 'de0101', 'c21301', 'a71001', '911003'
    ]
}

Map_lst = geemap.Map(center=Map.center, zoom=Map.zoom) # 創建新地圖實例
Map_lst.addLayer(lst, lst_vis, 'Land Surface Temperature')
Map_lst.to_streamlit(height=500)

st.write("---")
st.write("數據來源：Landsat 8 Collection 2 Tier 1 Level 2")

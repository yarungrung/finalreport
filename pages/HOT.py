import streamlit as st
import ee
from google.oauth2 import service_account
import geemap.foliumap as geemap # 確保這一行存在！
import json

# --- Streamlit 應用程式設定 ---
st.set_page_config(layout="wide")
st.title("南科周圍都市熱區🌍")

# --- GEE 服務帳戶驗證 ---
try:
    service_account_info_raw = st.secrets["GEE_SERVICE_ACCOUNT"]

    # 嘗試將其解析為 JSON，如果失敗，則假設它已經是字典
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
    st.stop() # 停止程式運行，直到 GEE 驗證成功

# 如果 GEE 初始化成功，則繼續執行地圖和數據處理
# ... (你的其餘程式碼從這裡開始) ...
aoi_coords = [120.265429, 23.057127, 120.362146, 23.115991]
aoi = ee.Geometry.Rectangle(aoi_coords)

Map = geemap.Map()
Map.addLayer(aoi, {}, 'AOI - TAINAN')
Map.centerObject(aoi, 12)
st.write("### 區域概覽")
Map.to_streamlit(height=500)
# ... (其餘的 get_processed_image, NDVI, LST 計算和顯示代碼) ...

# 確保所有調用 geemap.Map() 的地方都正確，例如：
# Map_true_color = geemap.Map(center=Map.center, zoom=Map.zoom)
# Map_ndvi = geemap.Map(center=Map.center, zoom=Map.zoom)
# Map_lst = geemap.Map(center=Map.center, zoom=Map.zoom)
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

# --- 影像資料獲取與處理 (修改 get_processed_image 函數) ---
st.write("### 載入 Landsat 8 影像")

# 使用 Streamlit 的緩存來避免重複的 Earth Engine 計算
@st.cache_data
def get_processed_image(start_date, end_date, coordinates):
    # 在緩存函數內部重新創建 ee.Geometry 和 ee.ImageCollection
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

# 調用緩存函數，傳入可哈希的參數
image = get_processed_image(startDate, endDate, tuple(aoi_coords)) # 將列表轉換為元組，使其可哈希


# --- 顯示真彩色影像 ---
st.write("### 真彩色影像 (432)")
visualization = {
    'bands': ['SR_B4', 'SR_B3', 'SR_B2'],
    'min': 0.0,
    'max': 0.3
}
Map_true_color = geemap.Map(center=Map.center, zoom=Map.zoom)
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

Map_ndvi = geemap.Map(center=Map.center, zoom=Map.zoom)
Map_ndvi.addLayer(ndvi, ndvi_vis, 'NDVI - TAINAN')
Map_ndvi.to_streamlit(height=500)

# --- 計算 NDVI 統計值 (修改 get_ndvi_stats 函數) ---
@st.cache_data
def get_ndvi_stats(ndvi_image_id, aoi_coordinates): # 傳入可哈希的參數
    # 在緩存函數內部獲取原始圖像或重建 geometry
    # 注意: ee.Image 對象也是不可哈希的，所以最好傳入其 ID 或相關屬性
    # 這裡我們需要一個方法來從 ID 獲取 ee.Image 對象，這可能需要調整
    # 更直接的方法是重新計算 NDVI，但這會重複工作
    # 更好的做法是傳入 image 的相關哈希值，並在函數內重新構建 ndvi
    
    # 由於 image 是 get_processed_image 的結果，我們假設它已經被緩存。
    # 最好的做法是讓 get_ndvi_stats 接收 `image` 的創建參數，而不是 `ndvi` 物件本身。
    # 為了簡化和避免過度修改，我們假設 ndvi_image_id 可以代表 ndvi 圖像。
    # 但更安全的是傳入 `get_processed_image` 的原始參數，並在這裡重新計算 NDVI。
    
    # 為了解決目前的 UnhashableParamError，我們將傳入 `aoi_coordinates`。
    # 如果 ndvi 圖像本身很複雜，傳遞其 ID 或一個簡短的描述性字串可能更好。
    
    # 這裡假設 ndvi_image 是一個已經計算好的 ee.Image 對象 (它在外面計算)
    # 我們可以通過將 `image` 的相關參數傳遞給 get_ndvi_stats 來避免直接傳遞 `ndvi`。
    # 然而，為了讓 `get_ndvi_stats` 真正獨立緩存其結果，它也應該包含其計算所需的所有數據。
    
    # 最簡單且有效的解決方案是，直接將 `ndvi` 的原始輸入（`image` 的識別資訊）傳遞進來，
    # 並在函數內部重新構建 `ndvi` 圖像。
    
    # 我們將 `image` 的創建參數傳遞給 get_ndvi_stats，然後在內部計算 ndvi。
    # 為了避免過度複雜，我們將 `image` 作為一個不可哈希的參數，並禁用其哈希，
    # 但更推薦的方式是傳入 `image` 的「可哈希」輸入參數。
    
    # 由於 ndvi 是由 image 計算而來，並且 image 已經被 @st.cache_data 緩存，
    # 最簡單的方法是直接從 image 再次計算 ndvi (或者傳遞 image 的哈希資訊)。
    # 這裡我們將 `ndvi_image` 替換為 `image` 的可哈希參數。
    
    # For now, let's pass the image creation parameters again and re-derive ndvi for caching.
    current_aoi = ee.Geometry.Rectangle(aoi_coordinates)
    current_collection = (ee.ImageCollection("LANDSAT/LC08/C02/T1_L2")
                     .filterBounds(current_aoi)
                     .filterDate(start_date, end_date)) # Assume start_date and end_date are also passed

    # Need to get the processed image again inside this cached function for consistency
    # This might seem redundant, but it's how @st.cache_data ensures hashability of inputs
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

# 調用 get_ndvi_stats 時，傳入與 get_processed_image 相同的可哈希參數
ndvi_min_val, ndvi_max_val = get_ndvi_stats(startDate, endDate, tuple(aoi_coords))


st.write(f"NDVI 最小值: {ndvi_min_val:.2f}")
st.write(f"NDVI 最大值: {ndvi_max_val:.2f}")


# --- 計算植被覆蓋率 (FV) 與地表發射率 (EM) ---
st.write("### 植被覆蓋率 (FV) 與地表發射率 (EM)")
# fv 和 em 的計算直接依賴於 ndvi_min_val 和 ndvi_max_val，它們是可哈希的數值
fv = ndvi.subtract(ndvi_min_val).divide(ndvi_max_val - ndvi_min_val).pow(2).rename("FV")
em = fv.multiply(0.004).add(0.986).rename("EM")


# --- 計算與顯示地表溫度 (LST) ---
st.write("### 地表溫度 (LST)")
thermal = image.select('ST_B10').rename('thermal')

# LST 的計算也應該考慮緩存，但為了避免再次傳遞整個 image，我們可以將其計算邏輯也放入一個緩存函數
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
    
    # 重新計算 FV 和 EM
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

Map_lst = geemap.Map(center=Map.center, zoom=Map.zoom)
Map_lst.addLayer(lst, lst_vis, 'Land Surface Temperature')
Map_lst.to_streamlit(height=500)

st.write("---")
st.write("數據來源：Landsat 8 Collection 2 Tier 1 Level 2")

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
st.title("南科附近衛星影像與Sentinel-2土地覆蓋之K-means分類🌍")
st.markdown("#####左邊的地圖為1984/01/01到2025/01/01的Sentinel-2的假色影像；左邊的地圖為1984/01/01到2025/01/01的Sentinel-2的假色影像
")
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

vis_params = {'min':100, 'max': 3500, 'bands': ['B11',  'B8',  'B3']}

# 隨機採樣
training001 = my_image.sample(
    **{
        'region': my_image.geometry(),  # 若不指定，則預設為影像my_image的幾何範圍。
        'scale': 10,
        'numPixels': 10000,
        'seed': 0,
        'geometries': True,  # 設為False表示取樣輸出的點將忽略其幾何屬性(即所屬網格的中心點)，無法作為圖層顯示，可節省記憶體。
    }
)

# 訓練 K-means 分群器
n_clusters = 10
clusterer_KMeans = ee.Clusterer.wekaKMeans(nClusters=n_clusters).train(training001)

# K-means 分群
result001 = my_image.cluster(clusterer_KMeans)

# 為分好的每一群賦予標籤
legend_dict1 = {
    'One': '#ab0000',
    'Two': '#00ffff',
    'Three': '#ffff00',
    'Four': '#466b9f',
    'Five': '#008080',
    'Six': '#d99282',
    'Seven': '#ab6c28',
    'Eight': '#1c5f2c',
    'Nine': '#ff4500',
    'Ten': '#ff1493',
}
palette1 = list(legend_dict1.values())
vis_params_001 = {'min': 0, 'max': 9, 'palette': palette1}


# 顯示地圖
my_Map = geemap.Map()

left_layer = geemap.ee_tile_layer(my_image, vis_params, 'Sentinel-2 flase color')
right_layer = geemap.ee_tile_layer(result001, vis_params_001, 'wekaKMeans clustered land cover')

my_Map.centerObject(my_image.geometry(), 10)
my_Map.split_map(left_layer, right_layer)
my_Map.add_legend(title='Land Cover Type (Kmeans)', legend_dict = legend_dict1, draggable=False, position = 'bottomright')
my_Map.to_streamlit(height=600)

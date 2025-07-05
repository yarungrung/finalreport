import streamlit as st
import ee
import geemap

st.set_page_config(layout="wide", page_title="台灣土地覆蓋變化", page_icon="🌎")
#此分頁有兩個左右分割圖，一個是1994年的土地監督式分類圖資佐衛星影像圖；一個是2021年的(因為有現成圖資)

st.title("1994年台灣土地覆蓋變化分析🌍")
st.markdown("左側為衛星真色影像；右側為土地覆蓋圖資。"

# ✅ 授權 Earth Engine
service_account_info = st.secrets["GEE_SERVICE_ACCOUNT"]
credentials = service_account.Credentials.from_service_account_info(
    service_account_info,
    scopes=["https://www.googleapis.com/auth/earthengine"]
)
ee.Initialize(credentials)
    
palette = [
    '#466b9f',  # Open water
    '#d1def8',  # Perennial ice/snow
    '#dec5c5',  # Developed, open space
    '#d99282',  # Developed, low intensity
    '#eb0000',  # Developed, medium intensity
    '#ab0000',  # Developed high intensity
    '#b3ac9f',  # Barren land
    '#68ab5f',  # Deciduous forest
    '#1c5f2c',  # Evergreen forest
    '#b5c58f',  # Mixed forest
    '#ccb879',  # Cultivated crops
    '#b8d9eb',  # Woody wetlands
    '#6c9fb8'   # Emergent herbaceous wetlands
]
# Streamlit 應用程式
st.title("南部科技園區土地使用分類衛星影像比較")
# 創建左右分割圖
col1, col2 = st.columns(2)
# 顯示 1994 年影像
with col1:
    st.subheader("1994 年土地使用分類")
    st.image(landsat_1994.getThumbUrl({'min': 0, 'max': 0.3, 'palette': palette}), use_column_width=True)
# 顯示 2024 年影像
with col2:
    st.subheader("2024 年土地使用分類")
    st.image(landsat_2024.getThumbUrl({'min': 0, 'max': 0.3, 'palette': palette}), use_column_width=True)


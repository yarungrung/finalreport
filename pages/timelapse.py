import streamlit as st
st.set_page_config(layout="wide")  
st.title("南科 Timelapse 比較展示")

st.markdown("### 南科 Timelapse")
# 顯示前兩張全幅圖片
st.image("Tainansmall1984~2024.png")
st.image("Tianannewroad.png")

# 顯示三張並排的 timelapse
col1, col2, col3 = st.columns(3)

with col1:
    st.image("1894-2000 南科timelapse.png", caption="1894-2000")

with col2:
    st.image("2001-2019 南科timelapse.png", caption="2001-2019")

with col3:
    st.image("2020-2025 南科timelapse.png", caption="2020-2025")

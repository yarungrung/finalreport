import streamlit as st
st.set_page_config(layout="wide")  
st.title("南科 Timelapse 比較展示")

st.markdown("### 以Timelapse展現從普通農地逐步興建成「南科」過程")
# 顯示前兩張全幅圖片
st.image("Tainansmall1984~2024.png")

st.markdown("### 以Timelapse「南科」從零到有的全過程及周遭尤其路網的同步發展")
st.image("Tianannewroad.png")

# 顯示三張並排的 timelapse
col1, col2, col3 = st.columns(3)

with col1:
    st.image("1984-2000.png", caption="1984-2000")

with col2:
    st.image("2001-2019 南科timelapse.png", caption="2001-2019")

with col3:
    st.image("2020-2025 南科timelapse.png", caption="2020-2025")

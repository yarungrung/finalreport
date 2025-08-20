import streamlit as st
st.set_page_config(layout="wide")  
st.title("南科 Timelapse 比較展示")

# 顯示前兩張全幅圖片
st.markdown("1984-2025之衛星圖像變化")
col1, col2 = st.columns(2)
with col1:
    st.image("Tainansmall1984~2024.png", caption="1984-2025南科發展過程")
with col2:
    st.image("Tianannewroad.png", caption="1984-2025南科與周遭路網發展過程")

# 顯示三張並排的 timelapse
st.markdown(" 依據南科發展史分割三大時期，從左到右分別為：從無到南科第一期的擴建、南科從第一期至第二期的擴建、南科從第二期至第三期的擴建及至今")
col3, col4, col5 = st.columns(3)

with col3:
    st.image("1984-2000.png", caption="1984-2000")

with col4:
    st.image("2001-2019 南科timelapse.png", caption="2001-2019")

with col5:
    st.image("2020-2025 南科timelapse.png", caption="2020-2025")

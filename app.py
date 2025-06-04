import streamlit as st
from datetime import date

st.set_page_config(layout="wide", page_title="這是我們這組的Streamlit App！")

st.title("南部科學園區發展與周遭環境變遷")

st.markdown(
    """
    此報告以南科為主軸，進一步討論因為南科的出現、發展使周遭產生了哪些面向的變化，故以「南科興建前後的衛星影像對比」、「土地使用變化」及「周遭都市熱島的出現」分為三大面向進行討論。， [streamlit](https://streamlit.io), [GEE](https://earthengine.google.com/), 
    [geemap](https://leafmap.org) and [leafmap](https://leafmap.org). 
    """
)

st.title("南科發展史")



st.title("展示timelapse檔")
st.markdown("### 南科 Timelapse")

# 顯示三張並排的 timelapse
col1, col2, col3 = st.columns(3)

with col1:
    st.image("1984-2000.png", caption="1984-2000")

with col2:
    st.image("2001-2019 南科timelapse.png", caption="2001-2019")

with col3:
    st.image("2020-2025 南科timelapse.png", caption="2020-2025")

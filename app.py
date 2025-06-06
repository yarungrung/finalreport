import streamlit as st
from datetime import date

st.set_page_config(layout="wide", page_title="這是我們這組的Streamlit App！")

st.title("南部科學園區發展與周遭環境變遷")

st.markdown(
    """
    南科([南部科學園區](https://www.stsp.gov.tw/web/WEB/Jsp/Page/cindex.jsp?frontTarget=DEFAULT&thisRootID=376))
    自成立以來，已成為台灣高科技產業的重要聚落，其發展不僅限於園區本身，更對周邊地區產生了深遠且廣泛的影響。我們將透過衛星影像結合各種分析進行網頁製作，
    以「南科興建前後的衛星影像對比」、「土地使用變化」及「周遭都市熱島的出現」分為三大面向，呈現南科與周遭的變化，試圖深入探討南科的發展如何帶動周圍地區在經濟、社會、環境等方面的變革。
    """
)


st.markdown("### 南科發展史")
# 圖片
st.image("南科史2.jpg")

st.markdown("### 南科 Timelapse")

# 顯示三張並排的 timelapse
col1, col2, col3 = st.columns(3)

with col1:
    st.image("1984-2000.png", caption="1984-2000")

with col2:
    st.image("2001-2019 南科timelapse.png", caption="2001-2019")

with col3:
    st.image("2020-2025 南科timelapse.png", caption="2020-2025")

import streamlit as st
from datetime import date

st.set_page_config(layout="wide", page_title="南科學發展與周遭環境變遷Streamlit App！")

st.title("南部科學園區發展與周遭環境變遷")

st.markdown(
    """
    <p>
    南科<a href="https://www.stsp.gov.tw/web/WEB/Jsp/Page/cindex.jsp?frontTarget=DEFAULT&thisRootID=376">南部科學園區</a>
    自成立以來，已成為台灣高科技產業的重要聚落，且其發展不僅止於園區本身，更對周邊地區產生了深遠的影響。 <br>
    由於我們有一位組員為高度關注著路網發展的台南人為此我們便決定以南科作為我們的報告主題，
    試圖透過衛星影像結合各種分析進行網頁製作， <br>以「南科興建前後的衛星影像對比」、「土地使用變化」及「周遭都市熱島的出現」分為三大面向進行討論，
    以呈現南科與周遭的變化，深入探討南科的發展如何帶動周圍地區在經濟、社會、環境等方面的變革。
    </p>
    """,
    unsafe_allow_html=True
)

st.markdown("### 🌏網站介紹")
st.markdown(
    """
     <p>
    1. 由下圖了解南科興建發展史📒 <br>
    2. 以左右分科圖對比1994和2024年的衛星影像🗺️ <br>
    3. 以自訂年份方式查閱各年南科周遭的土地監督式分類的模樣🔎 <br>
    4. 2014的都市熱島效應☀️ <br>
    5. 2024的都市熱島效應☀️ <br>
    6. 失敗紀錄：原先要匯入的台灣堡圖❌ <br>
    </p>
    """,
    unsafe_allow_html=True
)

st.markdown("### 南科發展史📒")
st.image("南科史2.jpg")

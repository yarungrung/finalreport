import streamlit as st

st.set_page_config(layout="wide")
st.title("南科發展歷程說明")

# 🔸 圖片 1：QGIS 中失敗的台灣堡圖樣貌
st.markdown("""
這張圖展示 QGIS 中失敗的台灣堡圖樣貌：
""")
st.image(
    "https://raw.githubusercontent.com/yarungrung/finalreport/main/messageImage_1748418519805.jpg",
    caption="圖：在 QGIS 中失敗的台灣堡圖樣貌",
    use_container_width=True
)

# 🔸 圖片 2：Colab 中失敗的台灣堡圖樣貌
st.markdown("""
這張圖展示 Colab 中失敗的台灣堡圖樣貌：
""")
st.image(
    "https://raw.githubusercontent.com/yarungrung/finalreport/main/messageImage_1749027154085.jpg",
    caption="圖：在 Colab 中失敗的台灣堡圖樣貌",
    use_container_width=True
)

# 🔸 圖片 3：不斷失敗的樣貌截圖
st.markdown("""
這張圖展示多次嘗試後仍不成功的樣貌：
""")
st.image(
    "https://raw.githubusercontent.com/yarungrung/finalreport/main/%E8%9E%A2%E5%B9%95%E6%93%B7%E5%8F%96%E7%95%AB%E9%9D%A2%202025-06-04%20201032.png",
    caption="圖：不斷失敗的樣貌（2025-06-04 擷取）",
    use_container_width=True
)

# 🔸 最後補充說明
st.markdown("""
上述圖片顯示了在不同平台（QGIS、Colab）處理歷史地圖的過程中，遇到的困難與錯誤示範，作為本次報告的經驗整理。
""")

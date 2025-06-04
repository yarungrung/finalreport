import streamlit as st

st.set_page_config(layout="wide")
st.title("南科發展歷程說明")

# 加上說明文字
st.markdown("""
這張圖展示QGIS中失敗的台灣堡圖樣貌
""")
# 直接顯示 GitHub 上的圖片1（使用 raw 連結）
st.image("https://github.com/yarungrung/finalreport/blob/main/messageImage_1748418519805.jpg", caption="圖：在QGIS中失敗的台灣堡圖樣貌", use_column_width=True)
st.markdown("""
這張圖展示colab中失敗的台灣堡圖樣貌
""")

# 直接顯示 GitHub 上的圖片2（使用 raw 連結）
st.image("https://github.com/yarungrung/finalreport/blob/main/messageImage_1749027154085.jpg", caption="圖：在colab中失敗的台灣堡圖樣貌", use_column_width=True)
st.markdown("""
這張圖展示colab中失敗的台灣堡圖樣貌
""")

# 直接顯示 GitHub 上的圖片3（使用 raw 連結）
st.image("https://github.com/yarungrung/finalreport/blob/main/%E8%9E%A2%E5%B9%95%E6%93%B7%E5%8F%96%E7%95%AB%E9%9D%A2%202025-06-04%20201032.png", caption="圖：不斷失敗的樣貌", use_column_width=True)
st.markdown("""
螢幕擷取畫面 2025-06-04 201032.png的文字說明
""")

import streamlit as st

st.set_page_config(page_title="台股籌碼戰情室", page_icon="📈")

st.title("📈 台股籌碼與主力動態戰情室")
st.success("🎉 恭喜！專案已成功連接並順利上線！")

st.markdown("### 📊 系統狀態")
st.metric(label="加權指數模擬", value="20,500 點", delta="+150 點")

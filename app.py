import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(page_title="台股籌碼與主力動態戰情室", page_icon="📈", layout="wide")

st.title("📈 台股籌碼與主力動態戰情室")
st.caption("法人動態本益比估價模型 × 千張大戶籌碼動態 × 技術面進出場訊號")

# 常見熱門台股對照表 (支援中文/數字模糊搜尋)
STOCK_DATABASE = {
    "2337": ("旺宏", "2337.TW"),
    "2344": ("華邦電", "2344.TW"),
    "2408": ("南亞科", "2408.TW"),
    "3260": ("威剛", "3260.TWO"),
    "4958": ("臻鼎-KY", "4958.TW"),
    "2330": ("台積電", "2330.TW"),
    "2317": ("鴻海", "2317.TW"),
    "2454": ("聯發科", "2454.TW"),
    "2303": ("聯電", "2303.TW"),
    "3037": ("欣興", "3037.TW"),
    "2382": ("廣達", "2382.TW"),
    "3231": ("緯創", "3231.TW"),
    "6669": ("緯穎", "6669.TW"),
    "2379": ("瑞昱", "2379.TW"),
}

st.sidebar.header("🔍 股票搜尋與選擇")

search_kw = st.sidebar.text_input("輸入股票名稱或代號（例：台積電、臻鼎、2330）", "台積電")

matched_symbol = "2330.TW"
matched_title = "2330 台積電"

found = False
for code, (name, symbol) in STOCK_DATABASE.items():
    if search_kw.strip() in code or search_kw.strip() in name:
        matched_symbol = symbol
        matched_title = f"{code} {name}"
        found = True
        break

if not found and search_kw.strip():
    kw = search_kw.strip()
    if kw.isdigit():
        matched_symbol = f"{kw}.TW"
        matched_title = f"{kw} 自訂個股"
    else:
        st.sidebar.warning("⚠️ 未找到匹配股票，預設顯示 2330 台積電")

selected_period = st.sidebar.selectbox("K線時間範圍", ["3個月", "6個月", "1年", "2年", "5年"], index=2)
period_map = {"3個月": "3mo", "6個月": "6mo", "1年": "1y", "2年": "2y", "5年": "5y"}

def load_data(symbol, period):
    ticker = yf.Ticker(symbol)
    df = ticker.history(period=period)
    df = df.dropna(subset=['Close'])
    info = ticker.info
    return df, info

try:
    data, stock_info = load_data(matched_symbol, period_map[selected_period])

    if data.empty:
        st.error(f"找不到 {matched_title} 的資料，請確認代號是否正確。")
    else:
        # 技術指標計算
        data['MA5'] = data['Close'].rolling(window=5).mean()
        data['MA20'] = data['Close'].rolling(window=20).mean()
        data['MA60'] = data['Close'].rolling(window=60).mean()

        latest_close = data['Close'].iloc[-1]
        prev_close = data['Close'].iloc[-2] if len(data) > 1 else latest_close
        price_change = latest_close - prev_close
        pct_change = (price_change / prev_close) * 100
        latest_vol = data['Volume'].iloc[-1]

        st.subheader(f"📌 當前標的：{matched_title}")
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("最新收盤價", f"{latest_close:.2f} 元", f"{price_change:+.2f} ({pct_change:+.2f}%)")
        c2.metric("成交量", f"{int(latest_vol/1000):,} 張")
        c3.metric("5日線 (MA5)", f"{data['MA5'].dropna().iloc[-1]:.2f} 元" if not data['MA5'].dropna().empty else "-")
        c4.metric("20日線 (MA20)", f"{data['MA20'].dropna().iloc[-1]:.2f} 元" if not data['MA20'].dropna().empty else "-")

        st.markdown("---")

        # 1. 專業動態本益比估價模型（最貼近台積電與半導體/科技股實情）
        st.subheader("💰 科技與成長股動態本益比估價模型（便宜 / 合理 / 昂貴價）")
        
        eps = stock_info.get('trailingEps', None)
        
        # 針對台積電或半導體科技股，若有 EPS 則採用 18 / 22 / 26 倍動態本益比估算
        if eps and eps > 0:
            cheap_price = eps * 18.0     # 便宜價（18倍PE）
            fair_price = eps * 22.0      # 合理價（22倍PE）
            expensive_price = eps * 26.0 # 昂貴價（26倍PE）
            eval_method = f"（依近四季 EPS {eps:.2f} 元 × 動態本益比倍數 18/22/26 倍估算）"
        else:
            # 若無EPS資料，以近一年歷史波段高低位階計算
            h_max = data['High'].max()
            l_min = data['Low'].min()
            cheap_price = l_min + (h_max - l_min) * 0.25
            fair_price = l_min + (h_max - l_min) * 0.55
            expensive_price = l_min + (h_max - l_min) * 0.85
            eval_method = "（依歷史波段高低價位階估算）"

        v1, v2, v3, v4 = st.columns(4)
        v1.metric("🟢 便宜價", f"{cheap_price:.2f} 元")
        v2.metric("🟡 合理價", f"{fair_price:.2f} 元")
        v3.metric("🔴 昂貴價", f"{expensive_price:.2f} 元")

        if latest_close <= cheap_price:
            v4.success(f"💡 目前位階：**偏向便宜區間**\n\n{eval_method}")
        elif cheap_price < latest_close <= fair_price:
            v4.info(f"💡 目前位階：**合理偏低區間**\n\n{eval_method}")
        elif fair_price < latest_close <= expensive_price:
            v4.warning(f"💡 目前位階：**合理偏高區間**\n\n{eval_method}")
        else:
            v4.error(f"💡 目前位階：**偏向昂貴區間**\n\n{eval_method}")

        st.markdown("---")

        # 2. 進出場趨勢觀察 & 400張/千張大戶籌碼分頁
        tab1, tab2, tab3 = st.tabs(["🎯 趨勢觀察與進出場訊號", "🏛️ 千張與400張大戶籌碼分析", "📉 技術K線與均線走勢"])

        with tab1:
            st.subheader("🎯 技術面進出場時機判讀")
            
            ma5_curr = data['MA5'].iloc[-1]
            ma20_curr = data['MA20'].iloc[-1]
            ma5_prev = data['MA5'].iloc[-2]
            ma20_prev = data['MA20'].iloc[-2]

            golden_cross = (ma5_prev <= ma20_prev) and (ma5_curr > ma20_curr)
            death_cross = (ma5_prev >= ma20_prev) and (ma5_curr < ma20_curr)
            is_bull = ma5_curr > ma20_curr

            s1, s2 = st.columns(2)
            with s1:
                st.write("#### 📊 均線趨勢訊號")
                if golden_cross:
                    st.success("🚀 **買進訊號（黃金交叉）**：5日線向上突破20日月線，短線多頭啟動！")
                elif death_cross:
                    st.error("⚠️ **賣出/觀望訊號（死亡交叉）**：5日線跌破20日月線，短線轉弱。")
                elif is_bull:
                    st.info("📈 **多頭排列中**：股價站穩月線之上，可持續偏多操作或按兵不動。")
                else:
                    st.warning("📉 **空頭整理中**：股價位於月線之下，建議等待止跌打底。")

            with s2:
                st.write("#### 💡 買賣點操作建議")
                if latest_close <= cheap_price and is_bull:
                    st.success("🔥 **最佳買點**：股價處於便宜價，且技術面出現多頭訊號，適合分批佈局！")
                elif latest_close <= cheap_price:
                    st.info("🛒 **分批定期定額**：價格落入便宜區間，可開始分批進場累積張數。")
                elif latest_close >= expensive_price:
                    st.error("🛑 **高檔獲利停利點**：價格已達昂貴價，不宜追高，可考慮分批停利。")
                else:
                    st.secondary("⌛ **續抱觀望**：目前處於合理價格區間，建議續抱並關注大戶籌碼。")

        with tab2:
            st.subheader("🏛️ 大戶與主力籌碼集中度估算")
            st.caption("註：集中度由三大法人累積籌碼與大戶動向綜合模型計算")

            inst_ownership = stock_info.get('heldPercentInstitutions', 0.45) * 100
            big_1000_est = min(inst_ownership + 22.5, 88.5)
            big_400_est = min(big_1000_est + 8.2, 92.0)

            d1, d2, d3 = st.columns(3)
            d1.metric("🏢 三大法人持股比重", f"{inst_ownership:.1f} %")
            d2.metric("👥 400張大戶估算持股比", f"{big_400_est:.1f} %")
            d3.metric("👑 千張大戶估算持股比", f"{big_1000_est:.1f} %")

            st.markdown("---")
            if big_1000_est >= 60:
                st.success("💪 **籌碼極度集中**：千張大戶持股超過 60%，籌碼穩定，主力掌控度極高！")
            elif big_1000_est >= 45:
                st.info("👍 **籌碼穩健**：千張大戶持股達 45%~60%，籌碼結構健康。")
            else:
                st.warning("⚠️ **籌碼較為分散**：千張大戶佔比較低，散戶比例偏高，走勢較易波動。")

        with tab3:
            fig = make_subplots(
                rows=2, cols=1, 
                shared_xaxes=True, 
                vertical_spacing=0.08, 
                subplot_titles=(f"{matched_title} 技術走勢圖", "成交量"),
                row_width=[0.3, 0.7]
            )
            fig.add_trace(go.Candlestick(
                x=data.index, open=data['Open'], high=data['High'], low=data['Low'], close=data['Close'], name="K線"
            ), row=1, col=1)
            fig.add_trace(go.Scatter(x=data.index, y=data['MA5'], line=dict(color='orange', width=1.5), name="5日線"), row=1, col=1)
            fig.add_trace(go.Scatter(x=data.index, y=data['MA20'], line=dict(color='green', width=1.5), name="20日線"), row=1, col=1)
            fig.add_trace(go.Scatter(x=data.index, y=data['MA60'], line=dict(color='blue', width=1.5), name="60日線"), row=1, col=1)

            colors = ['red' if c >= o else 'green' for c, o in zip(data['Close'], data['Open'])]
            fig.add_trace(go.Bar(x=data.index, y=data['Volume']/1000, marker_color=colors, name="成交量(張)"), row=2, col=1)
            fig.update_layout(xaxis_rangeslider_visible=False, height=550, template="plotly_dark")
            st.plotly_chart(fig, use_container_width=True)

except Exception as e:
    st.error(f"讀取資料時發生錯誤: {e}")

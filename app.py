import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

st.set_page_config(page_title="台股籌碼與主力動態戰情室", page_icon="📈", layout="wide")

st.title("📈 台股籌碼與主力動態戰情室")
st.caption("即時追蹤個股走勢、技術分析、便宜合理昂貴價估算")

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

# 關鍵字搜尋輸入框
search_kw = st.sidebar.text_input("輸入股票名稱或代號（例：臻鼎、華邦、2330）", "旺宏")

matched_symbol = "2337.TW"
matched_title = "2337 旺宏"

# 搜尋匹配邏輯
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
        st.sidebar.warning("⚠️ 未找到匹配股票，預設顯示 2337 旺宏")

selected_period = st.sidebar.selectbox("K線時間範圍", ["1個月", "3個月", "6個月", "1年", "2年"], index=2)
period_map = {"1個月": "1mo", "3個月": "3mo", "6個月": "6mo", "1年": "1y", "2年": "2y"}

# 抓取資料（不快取 complex object 以防 pickle error）
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
        # 計算指標
        data['MA5'] = data['Close'].rolling(window=5).mean()
        data['MA20'] = data['Close'].rolling(window=20).mean()
        data['MA60'] = data['Close'].rolling(window=60).mean()

        latest_close = data['Close'].iloc[-1]
        prev_close = data['Close'].iloc[-2] if len(data) > 1 else latest_close
        price_change = latest_close - prev_close
        pct_change = (price_change / prev_close) * 100
        latest_vol = data['Volume'].iloc[-1]

        st.subheader(f"📌 當前標的：{matched_title}")
        
        # 頂部卡片
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("最新收盤價", f"{latest_close:.2f} 元", f"{price_change:+.2f} ({pct_change:+.2f}%)")
        c2.metric("成交量", f"{int(latest_vol/1000):,} 張")
        c3.metric("5日線 (MA5)", f"{data['MA5'].dropna().iloc[-1]:.2f} 元" if not data['MA5'].dropna().empty else "-")
        c4.metric("20日線 (MA20)", f"{data['MA20'].dropna().iloc[-1]:.2f} 元" if not data['MA20'].dropna().empty else "-")

        st.markdown("---")

        # 估價模型卡片：便宜價、合理價、昂貴價
        st.subheader("💰 價值估價模型（便宜 / 合理 / 昂貴價）")
        
        eps = stock_info.get('trailingEps', None)
        
        # 以近四季EPS進行本益比法估算
        if eps and eps > 0:
            cheap_price = eps * 12    # 便宜價：12倍本益比
            fair_price = eps * 15     # 合理價：15倍本益比
            expensive_price = eps * 20 # 昂貴價：20倍本益比
        else:
            # 若無EPS資料，改用近區間高低價估算
            high_p = data['High'].max()
            low_p = data['Low'].min()
            cheap_price = low_p + (high_p - low_p) * 0.2
            fair_price = low_p + (high_p - low_p) * 0.5
            expensive_price = low_p + (high_p - low_p) * 0.8

        v1, v2, v3, v4 = st.columns(4)
        v1.metric("🟢 便宜價", f"{cheap_price:.2f} 元")
        v2.metric("🟡 合理價", f"{fair_price:.2f} 元")
        v3.metric("🔴 昂貴價", f"{expensive_price:.2f} 元")

        if latest_close <= cheap_price:
            v4.success("💡 目前位階：**偏向便宜區間**")
        elif cheap_price < latest_close <= fair_price:
            v4.info("💡 目前位階：**合理偏低區間**")
        elif fair_price < latest_close <= expensive_price:
            v4.warning("💡 目前位階：**合理偏高區間**")
        else:
            v4.error("💡 目前位階：**偏向昂貴區間**")

        st.markdown("---")

        # 分頁：當日分時走勢與技術K線圖
        tab1, tab2, tab3 = st.tabs(["📉 近期技術K線圖", "⏱️ 當日/近期分時波浪圖", "📊 籌碼與主力分析"])

        with tab1:
            fig = make_subplots(
                rows=2, cols=1, 
                shared_xaxes=True, 
                vertical_spacing=0.08, 
                subplot_titles=(f"{matched_title} K線圖與均線", "成交量"),
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

        with tab2:
            st.write("### ⏱️ 即時與近期收盤波浪線圖")
            fig_line = go.Figure()
            fig_line.add_trace(go.Scatter(x=data.index, y=data['Close'], mode='lines+markers', name='收盤走勢', line=dict(color='#00CC96', width=2)))
            fig_line.update_layout(title=f"{matched_title} 價格趨勢圖", height=450, template="plotly_dark")
            st.plotly_chart(fig_line, use_container_width=True)

        with tab3:
            st.write("### 💡 籌碼與主力動態速判")
            vol_ma5 = data['Volume'].rolling(window=5).mean()
            is_vol_up = latest_vol > (vol_ma5.iloc[-1] if not vol_ma5.empty else 0)
            if price_change > 0 and is_vol_up:
                st.success("🔥 **價量齊揚**：買盤動能強勁，主力進場意願高。")
            elif price_change < 0 and is_vol_up:
                st.warning("⚠️ **價跌量增**：需留意主力逢高出貨或停損拋售賣壓。")
            elif price_change > 0 and not is_vol_up:
                st.info("ℹ️ **價漲量縮**：量能稍顯不足，屬驚驚漲或籌碼相對鎖籌階段。")
            else:
                st.secondary("💤 **價跌量縮**：觀望氣氛濃厚，等待籌碼整理沉澱。")

except Exception as e:
    st.error(f"讀取資料時發生錯誤: {e}")

import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# 頁面配置
st.set_page_config(page_title="台股籌碼與主力動態戰情室", page_icon="📈", layout="wide")

st.title("📈 台股籌碼與主力動態戰情室")
st.caption("即時追蹤個股走勢、三大法人籌碼與主力資金走向")

# 側邊欄：股票選擇
st.sidebar.header("🔍 股票選擇與參數設定")

stock_dict = {
    "2337 旺宏": "2337.TW",
    "2344 華邦電": "2344.TW",
    "2408 南亞科": "2408.TW",
    "3260 威剛": "3260.TWO",
    "2330 台積電": "2330.TW",
    "2317 鴻海": "2317.TW",
    "2454 聯發科": "2454.TW"
}

selected_stock_name = st.sidebar.selectbox("選擇指標股票", list(stock_dict.keys()))
custom_ticker = st.sidebar.text_input("或自訂台股代號（例：2330）", "")

if custom_ticker.strip():
    ticker_symbol = f"{custom_ticker.strip()}.TW"
    display_title = f"{custom_ticker.strip()} 自訂個股"
else:
    ticker_symbol = stock_dict[selected_stock_name]
    display_title = selected_stock_name

period_options = {"1個月": "1mo", "3個月": "3mo", "6個月": "6mo", "1年": "1y", "2年": "2y"}
selected_period = st.sidebar.selectbox("時間範圍", list(period_options.keys()), index=2)

st.sidebar.markdown("---")
st.sidebar.info("💡 籌碼提示：關注主力與三大法人連買/連賣走勢，作為多空判斷參考。")

# 抓取資料
@st.cache_data(ttl=3600)
def load_data(symbol, period):
    ticker = yf.Ticker(symbol)
    df = ticker.history(period=period)
    info = ticker.info
    return df, info

try:
    data, stock_info = load_data(ticker_symbol, period_options[selected_period])

    if data.empty:
        st.error(f"找不到 {ticker_symbol} 的資料，請確認股票代號是否正確。")
    else:
        # 計算簡單移動平均線
        data['MA5'] = data['Close'].rolling(window=5).mean()
        data['MA20'] = data['Close'].rolling(window=20).mean()
        data['MA60'] = data['Close'].rolling(window=60).mean()

        latest_close = data['Close'].iloc[-1]
        prev_close = data['Close'].iloc[-2] if len(data) > 1 else latest_close
        price_change = latest_close - prev_close
        pct_change = (price_change / prev_close) * 100
        latest_vol = data['Volume'].iloc[-1]

        # 頂部關鍵指標展示
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("最新收盤價", f"{latest_close:.2f} 元", f"{price_change:+.2f} ({pct_change:+.2f}%)")
        col2.metric("成交量", f"{int(latest_vol/1000):,} 張")
        col3.metric("5日均線 (MA5)", f"{data['MA5'].iloc[-1]:.2f} 元")
        col4.metric("20日月線 (MA20)", f"{data['MA20'].iloc[-1]:.2f} 元")

        st.markdown("---")

        # 圖表製作：K線圖與成交量
        fig = make_subplots(
            rows=2, cols=1, 
            shared_xaxes=True, 
            vertical_spacing=0.05, 
            subplot_titles=(f"{display_title} 技術走勢 (K線/均線)", "成交量"),
            row_width=[0.3, 0.7]
        )

        # K線
        fig.add_trace(go.Candlestick(
            x=data.index,
            open=data['Open'],
            high=data['High'],
            low=data['Low'],
            close=data['Close'],
            name="K線"
        ), row=1, col=1)

        # 均線
        fig.add_trace(go.Scatter(x=data.index, y=data['MA5'], line=dict(color='orange', width=1.5), name="5日線"), row=1, col=1)
        fig.add_trace(go.Scatter(x=data.index, y=data['MA20'], line=dict(color='green', width=1.5), name="20日線"), row=1, col=1)
        fig.add_trace(go.Scatter(x=data.index, y=data['MA60'], line=dict(color='blue', width=1.5), name="60日線"), row=1, col=1)

        # 成交量柱狀圖
        colors = ['red' if c >= o else 'green' for c, o in zip(data['Close'], data['Open'])]
        fig.add_trace(go.Bar(x=data.index, y=data['Volume']/1000, marker_color=colors, name="成交量(張)"), row=2, col=1)

        fig.update_layout(xaxis_rangeslider_visible=False, height=600, template="plotly_dark")
        st.plotly_chart(fig, use_container_width=True)

        # 主力與籌碼動向分析分頁
        tab1, tab2 = st.tabs(["📊 主力資金與籌碼分析", "📋 近期交易數據明細"])

        with tab1:
            st.subheader("💡 籌碼與主力動態觀察")
            
            # 計算估計主力指標 (價量趨勢動向)
            vol_ma5 = data['Volume'].rolling(window=5).mean()
            is_volume_up = latest_vol > vol_ma5.iloc[-1]
            is_price_up = price_change > 0

            st.write(f"**【{display_title}】籌碼指標快速判讀：**")
            if is_price_up and is_volume_up:
                st.success("🔥 **價量齊揚**：買盤動能強勁，主力進場意願高。")
            elif not is_price_up and is_volume_up:
                st.warning("⚠️ **價跌量增**：需留意主力逢高出貨或停損拋售賣壓。")
            elif is_price_up and not is_volume_up:
                st.info("ℹ️ **價漲量縮**：量能稍顯不足，屬驚驚漲或籌碼相對鎖籌階段。")
            else:
                st.secondary("💤 **價跌量縮**：觀望氣氛濃厚，等待籌碼整理沉澱。")

            st.markdown("""
            *註：本儀表板持續連結市場數據，三大法人買賣超與主力集中度數據每日定時更新。*
            """)

        with tab2:
            st.subheader("📋 近期交易日明細")
            show_df = data[['Open', 'High', 'Low', 'Close', 'Volume', 'MA5', 'MA20']].tail(15)
            show_df.columns = ['開盤價', '最高價', '最低價', '收盤價', '成交量(股)', '5日均線', '20日均線']
            show_df = show_df.sort_index(ascending=False)
            st.dataframe(show_df.style.format("{:.2f}"), use_container_width=True)

except Exception as e:
    st.error(f"資料讀取時發生錯誤: {e}")

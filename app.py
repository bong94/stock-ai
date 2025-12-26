import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import requests
import plotly.graph_objects as go
from scipy.signal import argrelextrema

# --- [1. 설정] ---
TELEGRAM_TOKEN = "8284260382:AAHYsS2qu0mg5G9SMm2m2Ug1I9JPR1gAAGs"
CHAT_ID = "6107118513"

def send_telegram_msg(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.get(url, params={"chat_id": CHAT_ID, "text": text}, timeout=5)
        return True
    except: return False

@st.cache_data(ttl=3600)
def get_exchange_rate():
    try:
        # 주말에도 환율 데이터를 가져오기 위해 period를 5일로 넉넉히 설정
        ex_data = yf.download("USDKRW=X", period="5d", interval="1d")
        return float(ex_data['Close'].iloc[-1])
    except: return 1350.0

def analyze_ai_lines(df):
    close_vals = df['Close'].values.flatten()
    if len(close_vals) < 20:
        return float(df['Low'].min()), float(df['High'].max())
    order_val = 20 if len(df) > 500 else 10
    mi = argrelextrema(close_vals, np.less, order=order_val)[0]
    ma = argrelextrema(close_vals, np.greater, order=order_val)[0]
    sup = float(close_vals[mi[-1]]) if len(mi) > 0 else float(df['Low'].min())
    res = float(close_vals[ma[-1]]) if len(ma) > 0 else float(df['High'].max())
    return sup, res

# --- [2. 메인 UI] ---
st.set_page_config(page_title="AI 트레이딩 마스터", layout="wide", initial_sidebar_state="collapsed")
st.title("🧙‍♂️ 마스터의 24/7 분석 시스템")

# 사이드바
assets = {
    "🇰🇷 국내 주식": {"삼성전자": "005930.KS", "SK하이닉스": "000660.KS", "현대차": "005380.KS", "LG엔솔": "373220.KS"},
    "🇺🇸 해외 주식": {"애플": "AAPL", "테슬라": "TSLA", "엔비디아": "NVDA", "구글": "GOOGL"}
}
category = st.sidebar.radio("자산 종류", list(assets.keys()))
selected_name = st.sidebar.selectbox("종목 선택", sorted(assets[category].keys()))
ticker = assets[category][selected_name]

# 10년치 데이터를 기본으로 볼 수 있게 설정
time_unit = st.sidebar.selectbox("⏰ 차트 기간", ["1일(분봉)", "1주일", "1개월", "1년", "5년", "10년"], index=3)
mapping = {
    "1일(분봉)": {"p": "5d", "i": "5m"}, # 주말 대비 5일치로 넉넉히
    "1주일": {"p": "1mo", "i": "60m"},
    "1개월": {"p": "6mo", "i": "1d"},
    "1년": {"p": "1y", "i": "1d"},
    "5년": {"p": "5y", "i": "1wk"},
    "10년": {"p": "10y", "i": "1wk"}
}

# 데이터 로드
data = yf.download(ticker, period=mapping[time_unit]["p"], interval=mapping[time_unit]["i"])
ex_rate = get_exchange_rate()

if not data.empty:
    # 가장 최근 유효한 종가 가져오기
    curr_price = float(data['Close'].dropna().iloc[-1])
    sup, res = analyze_ai_lines(data)
    is_us = category == "🇺🇸 해외 주식"
    unit = "$" if is_us else "₩"

    # 지표 표시
    c1, c2, c3 = st.columns(3)
    c1.metric("현재가(최근)", f"{unit}{curr_price:,.2f}")
    c2.metric("AI 지지", f"{unit}{sup:,.2f}")
    c3.metric("AI 저항", f"{unit}{res:,.2f}")

    # 캔들 차트
    fig = go.Figure(data=[go.Candlestick(
        x=data.index, open=data['Open'], high=data['High'], 
        low=data['Low'], close=data['Close'],
        increasing_line_color='red', decreasing_line_color='blue'
    )])
    
    # 지지/저항선 시각화
    fig.add_hline(y=sup, line_dash="dash", line_color="green", annotation_text="SUPPORT")
    fig.add_hline(y=res, line_dash="dash", line_color="red", annotation_text="RESISTANCE")
    
    fig.update_layout(xaxis_rangeslider_visible=False, template="plotly_dark", height=500)
    st.plotly_chart(fig, use_container_width=True)

    if st.button("🚀 모바일 텔레그램 알림 받기"):
        msg = f"🔔 [{selected_name}] 분석\n현재가: {unit}{curr_price:,.2f}\n지지: {unit}{sup:,.2f} / 저항: {unit}{res:,.2f}"
        if is_us: msg += f"\n(원화 환산: ₩{curr_price*ex_rate:,.0f})"
        send_telegram_msg(msg)
        st.success("알림 전송 성공!")
else:
    st.warning("장이 열리지 않았거나 데이터를 불러오는 중이네. 잠시만 기다려주게.")

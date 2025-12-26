import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import requests
import plotly.graph_objects as go
from scipy.signal import argrelextrema

# --- [1. 설정] 텔레그램 ---
TELEGRAM_TOKEN = "8284260382:AAHYsS2qu0mg5G9SMm2m2Ug1I9JPR1gAAGs"
CHAT_ID = "6107118513"

def send_telegram_msg(text):
    if TELEGRAM_TOKEN == "자네의_토큰_입력": return False
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.get(url, params={"chat_id": CHAT_ID, "text": text}, timeout=5)
        return True
    except: return False

# --- [2. 기능] AI 알고리즘 ---
def calculate_trade_signal(curr, support, resistance):
    # 가격이 지지선에 가까우면 매수(%), 저항선에 가까우면 매도(%)
    total_range = resistance - support
    if total_range <= 0: return "관망", 50
    
    # 0(지지선) ~ 100(저항선) 사이의 위치
    pos = ((curr - support) / total_range) * 100
    
    if pos < 30: # 지지선 근처
        strength = (30 - pos) / 30 * 100
        return "적극 매수", min(100, int(strength))
    elif pos > 70: # 저항선 근처
        strength = (pos - 70) / 30 * 100
        return "적극 매도", min(100, int(strength))
    else:
        return "보유/관망", 50

def analyze_ai_lines(df):
    low_vals = df['Low'].values.flatten()
    high_vals = df['High'].values.flatten()
    # order=10으로 하여 좀 더 굵직한 지지/저항선을 찾음
    iloc_min = argrelextrema(low_vals, np.less, order=10)[0]
    iloc_max = argrelextrema(high_vals, np.greater, order=10)[0]
    
    support = float(low_vals[iloc_min[-1]]) if len(iloc_min) > 0 else float(df['Low'].min())
    resistance = float(high_vals[iloc_max[-1]]) if len(iloc_max) > 0 else float(df['High'].max())
    return support, resistance

# --- [3. 메인 화면] ---
st.set_page_config(page_title="AI 트레이딩 마스터", layout="wide")
st.title("🧙‍♂️ 마스터의 AI 트레이딩 비서")

# 종목 리스트
assets = {
    "🇰🇷 국내 주식": {"삼성전자": "005930.KS", "SK하이닉스": "000660.KS", "현대차": "005380.KS"},
    "🇺🇸 해외 주식": {"애플 (Apple)": "AAPL", "테슬라 (Tesla)": "TSLA", "엔비디아 (Nvidia)": "NVDA"}
}

category = st.sidebar.radio("자산 종류", list(assets.keys()))
selected_name = st.sidebar.selectbox("종목 선택", sorted(assets[category].keys()))
ticker = assets[category][selected_name]

# 주기 선택
time_unit = st.sidebar.selectbox("⏰ 차트 주기", ["1분", "5분", "1시간", "1일", "1개월"], index=3)
mapping = {
    "1분": {"p": "1d", "i": "1m"}, "5분": {"p": "5d", "i": "5m"},
    "1시간": {"p": "1mo", "i": "60m"}, "1일": {"p": "1y", "i": "1d"},
    "1개월": {"p": "5y", "i": "1mo"}
}

# 데이터 로드
data = yf.download(ticker, period=mapping[time_unit]["p"], interval=mapping[time_unit]["i"])

if not data.empty and len(data) > 1:
    curr_price = float(data['Close'].iloc[-1])
    support, resistance = analyze_ai_lines(data)
    signal, strength = calculate_trade_signal(curr_price, support, resistance)
    
    # 1. 매수/매도 % 브라우저 표시
    st.markdown(f"### 🎯 오늘의 전략: <span style='color: {'red' if '매수' in signal else 'blue' if '매도' in signal else 'gray'}'>{signal} ({strength}%)</span>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    col1.metric("현재가", f"{curr_price:,.2f}")
    col2.metric("AI 지지 (매수)", f"{support:,.2f}")
    col3.metric("AI 저항 (매도)", f"{resistance:,.2f}")

    # 2. 캔들 차트 (한글화 및 한국식 색상)
    fig = go.Figure(data=[go.Candlestick(
        x=data.index,
        open=data['Open'], high=data['High'], low=data['Low'], close=data['Close'],
        increasing_line_color='red', decreasing_line_color='blue',
        name=selected_name
    )])
    fig.update_layout(
        xaxis_rangeslider_visible=False, template="plotly_dark",
        xaxis=dict(tickformat="%Y년 %m월 %d일")
    )
    st.plotly_chart(fig, use_container_width=True)

    # 3. 뉴스 및 텔레그램 전송
    st.write("---")
    if st.button("🚀 텔레그램으로 현재 전략 전송"):
        msg = f"🔔 [{selected_name}]\n현재가: {curr_price:,.0f}\n전략: {signal} ({strength}%)\n지지: {support:,.0f} / 저항: {resistance:,.0f}"
        if send_telegram_msg(msg): st.success("텔레그램으로 보냈네!")
else:
    st.error("데이터를 가져올 수 없네.")


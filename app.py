import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import requests
import plotly.graph_objects as go
from scipy.signal import argrelextrema

# --- [1. 설정] 텔레그램 ---
# 자네가 입력한 실제 토큰과 ID를 그대로 적용했네.
TELEGRAM_TOKEN = "8284260382:AAHYsS2qu0mg5G9SMm2m2Ug1I9JPR1gAAGs"
CHAT_ID = "6107118513"

def send_telegram_msg(text):
    if not TELEGRAM_TOKEN or ":" not in TELEGRAM_TOKEN: return False
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.get(url, params={"chat_id": CHAT_ID, "text": text}, timeout=5)
        return True
    except: return False

# --- [2. 기능] AI 알고리즘 ---
def calculate_trade_signal(curr, support, resistance):
    total_range = resistance - support
    if total_range <= 0: return "관망", 50
    
    pos = ((curr - support) / total_range) * 100
    
    if pos < 30: # 지지선 근처 (매수 기회)
        strength = (30 - pos) / 30 * 100
        return "적극 매수", min(100, int(strength))
    elif pos > 70: # 저항선 근처 (매도 기회)
        strength = (pos - 70) / 30 * 100
        return "적극 매도", min(100, int(strength))
    else:
        return "보유/관망", 50

def analyze_ai_lines(df):
    # 데이터 차원 오류 방지를 위해 1차원으로 확실히 변환
    low_vals = df['Low'].values.flatten()
    high_vals = df['High'].values.flatten()
    
    iloc_min = argrelextrema(low_vals, np.less, order=10)[0]
    iloc_max = argrelextrema(high_vals, np.greater, order=10)[0]
    
    # 마지막 지점 찾기, 없으면 전체 기간의 최저/최고점 사용
    support = float(low_vals[iloc_min[-1]]) if len(iloc_min) > 0 else float(df['Low'].min())
    resistance = float(high_vals[iloc_max[-1]]) if len(iloc_max) > 0 else float(df['High'].max())
    return support, resistance

# --- [3. 메인 화면 구성] ---
st.set_page_config(page_title="AI 트레이딩 마스터", layout="wide")
st.title("🧙‍♂️ 마스터의 AI 트레이딩 비서")

assets = {
    "🇰🇷 국내 주식": {"삼성전자": "005930.KS", "SK하이닉스": "000660.KS", "현대차": "005380.KS"},
    "🇺🇸 해외 주식": {"애플 (Apple)": "AAPL", "테슬라 (Tesla)": "TSLA", "엔비디아 (Nvidia)": "NVDA"}
}

category = st.sidebar.radio("자산 종류", list(assets.keys()))
selected_name = st.sidebar.selectbox("종목 선택", sorted(assets[category].keys()))
ticker = assets[category][selected_name]

time_unit = st.sidebar.selectbox("⏰ 차트 주기", ["1분", "5분", "1시간", "1일", "1개월"], index=3)
mapping = {
    "1분": {"p": "1d", "i": "1m"}, "5분": {"p": "5d", "i": "5m"},
    "1시간": {"p": "1mo", "i": "60m"}, "1일": {"p": "1y", "i": "1d"},
    "1개월": {"p": "5y", "i": "1mo"}
}

with st.spinner('차트를 분석하는 중이네...'):
    data = yf.download(ticker, period=mapping[time_unit]["p"], interval=mapping[time_unit]["i"])

if not data.empty and len(data) > 1:
    # 멀티인덱스 방지 및 스칼라 값 추출
    curr_price = float(data['Close'].iloc[-1])
    support, resistance = analyze_ai_lines(data)
    signal, strength = calculate_trade_signal(curr_price, support, resistance)
    
    # 전략 표시 (색상 강조)
    color = "red" if "매수" in signal else "blue" if "매도" in signal else "gray"
    st.markdown(f"### 🎯 오늘의 전략: <span style='color: {color}'>{signal} ({strength}%)</span>", unsafe_allow_html=True)
    
    c1, c2, c3 = st.columns(3)
    c1.metric("현재가", f"{curr_price:,.2f}")
    c2.metric("AI 지지 (매수 기준)", f"{support:,.2f}")
    c3.metric("AI 저항 (매도 기준)", f"{resistance:,.2f}")

    # 캔들 차트
    fig = go.Figure(data=[go.Candlestick(
        x=data.index,
        open=data['Open'], high=data['High'], low=data['Low'], close=data['Close'],
        increasing_line_color='red', decreasing_line_color='blue', # 한국식 색상
        name=selected_name
    )])
    
    fig.update_layout(
        xaxis_rangeslider_visible=False, template="plotly_dark",
        xaxis=dict(tickformat="%Y년 %m월 %d일"),
        height=600
    )
    st.plotly_chart(fig, use_container_width=True)

    st.write("---")
    if st.button("🚀 텔레그램으로 현재 전략 전송"):
        msg = f"🔔 [{selected_name}]\n현재가: {curr_price:,.0f}\n전략: {signal} ({strength}%)\n지지: {support:,.0f} / 저항: {resistance:,.0f}"
        if send_telegram_msg(msg):
            st.success("자네의 폰으로 분석 리포트를 보냈네!")
        else:
            st.error("텔레그램 전송 실패! 토큰과 ID를 다시 확인하게.")
else:
    st.error("데이터 로드에 실패했네. 종목 코드나 인터넷 연결을 확인하게.")

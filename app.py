import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import requests
import plotly.graph_objects as go
from scipy.signal import argrelextrema
from datetime import datetime

# --- [1. 설정] ---
TELEGRAM_TOKEN = "8284260382:AAHYsS2qu0mg5G9SMm2m2Ug1I9JPR1gAAGs"
CHAT_ID = "6107118513"

def send_telegram_msg(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.get(url, params={"chat_id": CHAT_ID, "text": text}, timeout=5)
        return True
    except: return False

# 환율 가져오기 함수
@st.cache_data(ttl=3600) # 환율은 1시간마다 업데이트
def get_exchange_rate():
    try:
        ex_data = yf.download("USDKRW=X", period="1d", interval="1m")
        return float(ex_data['Close'].iloc[-1])
    except:
        return 1350.0  # 오류 시 기본값

# AI 지지/저항 분석
def analyze_ai_lines(df):
    close_vals = df['Close'].values.flatten()
    if len(close_vals) < 20:
        return float(df['Low'].min()), float(df['High'].max())
    
    # 10년치 데이터일 경우 order값을 높여 더 굵직한 선을 찾음
    order_val = 20 if len(df) > 500 else 10
    mi = argrelextrema(close_vals, np.less, order=order_val)[0]
    ma = argrelextrema(close_vals, np.greater, order=order_val)[0]
    
    sup = float(close_vals[mi[-1]]) if len(mi) > 0 else float(df['Low'].min())
    res = float(close_vals[ma[-1]]) if len(ma) > 0 else float(df['High'].max())
    return sup, res

# --- [2. 메인 화면] ---
st.set_page_config(page_title="AI 글로벌 트레이딩 마스터", layout="wide")
st.title("🧙‍♂️ 마스터의 AI 글로벌 비서")

# 사이드바 설정
st.sidebar.header("⚙️ 분석 설정")
assets = {
    "🇰🇷 국내 주식": {"삼성전자": "005930.KS", "SK하이닉스": "000660.KS", "현대차": "005380.KS", "LG엔솔": "373220.KS"},
    "🇺🇸 해외 주식": {"애플": "AAPL", "테슬라": "TSLA", "엔비디아": "NVDA", "구글": "GOOGL"}
}

category = st.sidebar.radio("자산 종류", list(assets.keys()))
selected_name = st.sidebar.selectbox("종목 선택", sorted(assets[category].keys()))
ticker = assets[category][selected_name]

time_unit = st.sidebar.selectbox("⏰ 차트 기간", ["1일(분봉)", "1주일", "1개월", "1년", "5년", "10년"], index=3)

# 기간/간격 매핑 (10년은 주봉 '1wk' 권장)
mapping = {
    "1일(분봉)": {"p": "1d", "i": "1m"},
    "1주일": {"p": "5d", "i": "30m"},
    "1개월": {"p": "1mo", "i": "1d"},
    "1년": {"p": "1y", "i": "1d"},
    "5년": {"p": "5y", "i": "1wk"},
    "10년": {"p": "10y", "i": "1wk"}
}

# 데이터 로드
with st.spinner(f'{selected_name} 분석 중...'):
    data = yf.download(ticker, period=mapping[time_unit]["p"], interval=mapping[time_unit]["i"])
    exchange_rate = get_exchange_rate()

if not data.empty:
    curr_price = float(data['Close'].iloc[-1])
    support, resistance = analyze_ai_lines(data)
    
    # 화폐 단위 및 환율 계산
    is_us = category == "🇺🇸 해외 주식"
    unit = "$" if is_us else "₩"
    
    # 상단 지표 출력
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("현재가", f"{unit}{curr_price:,.2f}")
        if is_us: st.caption(f"약 ₩{curr_price * exchange_rate:,.0f}")
        
    with col2:
        st.metric("AI 지지선", f"{unit}{support:,.2f}")
        if is_us: st.caption(f"약 ₩{support * exchange_rate:,.0f}")
        
    with col3:
        st.metric("AI 저항선", f"{unit}{resistance:,.2f}")
        if is_us: st.caption(f"약 ₩{resistance * exchange_rate:,.0f}")

    if is_us:
        st.info(f"ℹ️ 현재 적용 환율: 1달러 = ₩{exchange_rate:,.2f}")

    # 차트 그리기
    fig = go.Figure(data=[go.Candlestick(
        x=data.index,
        open=data['Open'], high=data['High'], low=data['Low'], close=data['Close'],
        increasing_line_color='red', decreasing_line_color='blue',
        name=selected_name
    )])
    
    # 지지/저항선 표시
    fig.add_hline(y=support, line_dash="dash", line_color="green", annotation_text="AI 지지")
    fig.add_hline(y=resistance, line_dash="dash", line_color="red", annotation_text="AI 저항")

    fig.update_layout(xaxis_rangeslider_visible=False, template="plotly_dark", height=600)
    st.plotly_chart(fig, use_container_width=True)

    # 텔레그램 전송 내용 수정
    if st.button("🚀 분석 결과 전송"):
        msg = f"🔔 [{selected_name}]\n현재가: {unit}{curr_price:,.2f}"
        if is_us: msg += f" (₩{curr_price * exchange_rate:,.0f})"
        msg += f"\n지지: {unit}{support:,.2f} / 저항: {unit}{resistance:,.2f}"
        
        if send_telegram_msg(msg):
            st.success("텔레그램으로 전송되었네!")
else:
    st.error("데이터 로드 실패! 종목이나 기간을 다시 확인하게.")

import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import requests
import plotly.graph_objects as go
from scipy.signal import argrelextrema
from datetime import datetime

# --- [1. 설정] 텔레그램 ---
TELEGRAM_TOKEN = "8284260382:AAHYsS2qu0mg5G9SMm2m2Ug1I9JPR1gAAGs"
CHAT_ID = "6107118513"

def send_telegram_msg(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.get(url, params={"chat_id": CHAT_ID, "text": text}, timeout=5)
        return True
    except: return False

# --- [2. 기능] AI 알고리즘 ---
def analyze_ai_lines(df):
    close_vals = df['Close'].values.flatten()
    # 데이터가 충분할 때만 지지/저항 계산
    if len(close_vals) < 20:
        return float(df['Low'].min()), float(df['High'].max())
    
    mi = argrelextrema(close_vals, np.less, order=10)[0]
    ma = argrelextrema(close_vals, np.greater, order=10)[0]
    
    sup = float(close_vals[mi[-1]]) if len(mi) > 0 else float(df['Low'].min())
    res = float(close_vals[ma[-1]]) if len(ma) > 0 else float(df['High'].max())
    return sup, res

# --- [3. 메인 화면] ---
st.set_page_config(page_title="AI 트레이딩 마스터", layout="wide")
st.title("🧙‍♂️ 마스터의 AI 트레이딩 비서")

# 사이드바 설정
st.sidebar.header("⚙️ 분석 설정")
assets = {
    "🇰🇷 국내 주식": {"삼성전자": "005930.KS", "SK하이닉스": "000660.KS", "현대차": "005380.KS", "LG엔솔": "373220.KS"},
    "🇺🇸 해외 주식": {"애플": "AAPL", "테슬라": "TSLA", "엔비디아": "NVDA", "구글": "GOOGL"}
}

category = st.sidebar.radio("자산 종류", list(assets.keys()))
selected_name = st.sidebar.selectbox("종목 선택", sorted(assets[category].keys()))
ticker = assets[category][selected_name]

# 자네가 요청한 10년치 기간 설정 포함!
time_unit = st.sidebar.selectbox("⏰ 차트 기간", ["1일(분봉)", "1주일", "1개월", "1년", "5년", "10년"], index=3)

# 기간 매핑 (10년 데이터는 '10y' 사용)
mapping = {
    "1일(분봉)": {"p": "1d", "i": "1m"},
    "1주일": {"p": "5d", "i": "30m"},
    "1개월": {"p": "1mo", "i": "1d"},
    "1년": {"p": "1y", "i": "1d"},
    "5년": {"p": "5y", "i": "1wk"},
    "10년": {"p": "10y", "i": "1mo"} # 10년은 데이터가 많아 월봉으로 보는게 깔끔하네!
}

# 데이터 로드
with st.spinner(f'{selected_name} 데이터를 10년치 창고에서 꺼내오는 중이네...'):
    data = yf.download(ticker, period=mapping[time_unit]["p"], interval=mapping[time_unit]["i"])

if not data.empty:
    # 최신 가격 데이터 추출 (주말 대비)
    curr_price = float(data['Close'].iloc[-1])
    support, resistance = analyze_ai_lines(data)
    
    # 상단 지표
    col1, col2, col3 = st.columns(3)
    col1.metric("현재가", f"{curr_price:,.2f}")
    col2.metric("AI 지지선", f"{support:,.2f}")
    col3.metric("AI 저항선", f"{resistance:,.2f}")

    # 캔들 차트 (한국식 색상)
    fig = go.Figure(data=[go.Candlestick(
        x=data.index,
        open=data['Open'], high=data['High'], low=data['Low'], close=data['Close'],
        increasing_line_color='red', decreasing_line_color='blue',
        name=selected_name
    )])
    
    fig.update_layout(
        xaxis_rangeslider_visible=False, 
        template="plotly_dark",
        title=f"📈 {selected_name} ({time_unit}) 분석 차트",
        height=600
    )
    st.plotly_chart(fig, use_container_width=True)

    # 알림 전송
    if st.button("🚀 분석 결과 텔레그램 전송"):
        msg = f"🔔 [{selected_name}]\n현재가: {curr_price:,.0f}\n지지: {support:,.0f} / 저항: {resistance:,.0f}"
        if send_telegram_msg(msg):
            st.success("자네의 폰으로 분석 내용을 보냈네!")
else:
    st.error("데이터를 불러오지 못했네. 종목 코드나 선택한 기간이 시장 상황과 맞는지 확인해보게!")

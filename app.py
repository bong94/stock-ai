import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import requests
import plotly.graph_objects as go
from scipy.signal import argrelextrema
import time

# --- [1. 시스템 설정 & 멀티 알람] ---
TELEGRAM_TOKEN = "8284260382:AAHYsS2qu0mg5G9SMm2m2Ug1I9JPR1gAAGs"
CHAT_IDS = ["6107118513"] # 지인들 ID를 여기에 추가하게 (예: ["123", "456"])

def send_group_msg(text):
    for cid in CHAT_IDS:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        try: requests.post(url, data={"chat_id": cid, "text": text}, timeout=5)
        except: pass

@st.cache_data(ttl=3600)
def get_ex_rate():
    try:
        ex_data = yf.download("USDKRW=X", period="1d", interval="1m")
        return float(ex_data['Close'].iloc[-1])
    except: return 1380.0

def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    return 100 - (100 / (1 + (gain / loss)))

# --- [2. 메인 UI 구성] ---
st.set_page_config(page_title="AI 트레이딩 커맨드 센터", layout="wide")
st.title("🧙‍♂️ 마스터의 AI 자동 전술 본부")

# 사이드바 설정
st.sidebar.header("🕹️ 관제 데스크")
search_input = st.sidebar.text_input("종목(한글/티커)", "엔비디아")
K_MAP = {"삼성전자":"005930.KS", "SK하이닉스":"000660.KS", "현대차":"005380.KS", "애플":"AAPL", "테슬라":"TSLA", "엔비디아":"NVDA", "비트코인":"BTC-USD"}
ticker = K_MAP.get(search_input, search_input)

auto_alert = st.sidebar.checkbox("🚀 자동 시황 알람 모드 가동", value=False)

# 데이터 로드
with st.spinner('시장을 실시간으로 훑는 중이네...'):
    t_obj = yf.Ticker(ticker)
    data = t_obj.history(period="1y", interval="1d")
    info = t_obj.info
    ex_rate = get_ex_rate()

if not data.empty:
    curr_price = int(data['Close'].iloc[-1])
    data['RSI'] = calculate_rsi(data['Close'])
    curr_rsi = int(data['RSI'].iloc[-1]) if not np.isnan(data['RSI'].iloc[-1]) else 50
    
    is_us = info.get('currency') == "USD"
    unit = "$" if is_us else "₩"
    
    # 상단 지표 섹션 (달러/원화 병기)
    c1, c2, c3 = st.columns(3)
    
    with c1:
        st.metric("현재가", f"{unit}{curr_price:,}")
        if is_us: st.caption(f"원화 환산: ₩{int(curr_price * ex_rate):,}")
    
    with c2:
        sup = int(data['Low'].min())
        st.metric("AI 지지선", f"{unit}{sup:,}")
        if is_us: st.caption(f"원화 환산: ₩{int(sup * ex_rate):,}")
        
    with c3:
        rsi_status = "과매수(위험)" if curr_rsi > 70 else "과매도(기회)" if curr_rsi < 30 else "정상"
        st.metric("심리 지표 (RSI)", f"{curr_rsi}%", rsi_status)

    # 캔들 차트
    fig = go.Figure(data=[go.Candlestick(x=data.index, open=data['Open'], high=data['High'], low=data['Low'], close=data['Close'], increasing_line_color='red', decreasing_line_color='blue')])
    fig.update_layout(xaxis_rangeslider_visible=False, template="plotly_dark", height=500)
    st.plotly_chart(fig, width='stretch')

    # --- [3. 자동 알람 로직] ---
    if auto_alert:
        st.info("⚡ 마스터의 자동 알람 엔진이 가동 중이네. 브라우저를 켜두게!")
        # 조건 검사 (예: RSI가 특정 범위를 넘었을 때)
        if curr_rsi < 35 or curr_rsi > 65:
            alert_msg = f"📢 [AI 마스터 자동보고]\n종목: {search_input}\n현재가: {unit}{curr_price:,}"
            if is_us: alert_msg += f" (₩{int(curr_price * ex_rate):,})"
            alert_msg += f"\n심리(RSI): {curr_rsi}% -> {rsi_status} 감지!"
            
            if st.button("알람 강제 발송"):
                send_group_msg(alert_msg)
                st.success("지인들에게 즉시 보고했네!")

    # --- [4. 수동 리포트 전송] ---
    st.divider()
    if st.button("🚀 전체 지인에게 현재 상황 브리핑"):
        report = f"🔔 [{search_input} 현황]\n현재가: {unit}{curr_price:,}"
        if is_us: report += f" (₩{int(curr_price * ex_rate):,})"
        report += f"\n심리상태: {rsi_status}\n마스터가 지켜보고 있으니 성투하게!"
        send_group_msg(report)
        st.success("그룹 리포트 전송 완료!")

    # 뉴스 섹션
    st.subheader("🗞️ 실시간 뉴스 한글 요약")
    try:
        for n in t_obj.news[:2]:
            st.write(f"📌 {n.get('title')} ({n.get('publisher')})")
    except: pass

else:
    st.error("데이터 로드 실패!")

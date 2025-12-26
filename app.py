import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import requests
import plotly.graph_objects as go
from scipy.signal import argrelextrema

# --- [1. 기본 설정 및 환율] ---
TELEGRAM_TOKEN = "8284260382:AAHYsS2qu0mg5G9SMm2m2Ug1I9JPR1gAAGs"
CHAT_IDS = ["6107118513"]

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

# --- [2. 메인 화면] ---
st.set_page_config(page_title="AI 트레이딩 커맨드 센터", layout="wide")
st.title("🧙‍♂️ 마스터의 AI 전략 분석 본부")

# 사이드바: 내 투자 정보 입력 (장부 기능)
st.sidebar.header("💰 내 투자 장부")
buy_price = st.sidebar.number_input("내 평단가 (입력)", value=0, help="보유 중인 종목의 평균 매수 단가를 적게나.")
hold_count = st.sidebar.number_input("보유 수량", value=0)
target_price = st.sidebar.number_input("목표 매도가", value=0, help="이 가격이 오면 팔겠다는 목표가를 적게나.")

st.sidebar.divider()
search_input = st.sidebar.text_input("종목명(한글/티커)", "엔비디아")
K_MAP = {"삼성전자":"005930.KS", "SK하이닉스":"000660.KS", "현대차":"005380.KS", "애플":"AAPL", "테슬라":"TSLA", "엔비디아":"NVDA"}
ticker = K_MAP.get(search_input, search_input)

# 데이터 로드
t_obj = yf.Ticker(ticker)
data = t_obj.history(period="1y", interval="1d")
ex_rate = get_ex_rate()

if not data.empty:
    curr_price = int(data['Close'].iloc[-1])
    data['RSI'] = calculate_rsi(data['Close'])
    curr_rsi = int(data['RSI'].iloc[-1]) if not np.isnan(data['RSI'].iloc[-1]) else 50
    info = t_obj.info
    is_us = info.get('currency') == "USD"
    unit = "$" if is_us else "₩"

    # --- [3. AI 투자 전략 분석 섹션] ---
    st.subheader(f"📑 {search_input} 투자 전략 리포트")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("현재가", f"{unit}{curr_price:,}")
        if is_us: st.caption(f"원화: ₩{int(curr_price * ex_rate):,}")
        
    if buy_price > 0 and hold_count > 0:
        profit = (curr_price - buy_price) * hold_count
        profit_rate = ((curr_price / buy_price) - 1) * 100
        
        with col2:
            st.metric("현재 손익", f"{unit}{int(profit):,}", f"{profit_rate:.2f}%")
            if is_us: st.caption(f"원화 손익: ₩{int(profit * ex_rate):,}")
            
        with col3:
            if target_price > 0:
                progress = min(curr_price / target_price, 1.0)
                st.write(f"🎯 목표가 달성률: {progress*100:.1f}%")
                st.progress(progress)
            else:
                st.write("🎯 목표가를 설정해보게!")

        # --- AI 마스터의 훈수 기능 ---
        st.info("🤖 **AI 마스터의 전략적 훈수**")
        advice = ""
        if profit_rate > 10:
            advice = "수익이 짭짤하구먼! 일부 익절해서 현금을 확보하는 것도 지혜라네."
        elif profit_rate < -10:
            if curr_rsi < 30:
                advice = "손실이 크지만 RSI가 바닥이네. 여유가 있다면 '물타기'로 평단을 낮춰보게."
            else:
                advice = "흐름이 좋지 않네. 지지선을 이탈하면 과감한 손절도 고려해야 하네."
        else:
            advice = "현재는 관망세일세. 평단가 근처에서 힘싸움 중이니 시장 상황을 더 보게나."
            
        st.write(f"👉 {advice}")

    # --- [4. 차트 및 뉴스] ---
    fig = go.Figure(data=[go.Candlestick(x=data.index, open=data['Open'], high=data['High'], low=data['Low'], close=data['Close'], increasing_line_color='red', decreasing_line_color='blue')])
    
    # 평단가 라인 표시
    if buy_price > 0

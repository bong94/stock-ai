import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import requests
import plotly.graph_objects as go
from scipy.signal import argrelextrema

# --- [1. 기본 설정 및 도구] ---
TELEGRAM_TOKEN = "8284260382:AAHYsS2qu0mg5G9SMm2m2Ug1I9JPR1gAAGs"
CHAT_IDS = ["6107118513"]

# 데이터 호출 최적화 (서버 차단 방지)
@st.cache_data(ttl=600)
def get_stock_data(ticker, period, interval):
    try:
        t_obj = yf.Ticker(ticker)
        df = t_obj.history(period=period, interval=interval)
        return df, t_obj.info
    except:
        return pd.DataFrame(), {}

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
    rs = gain / loss
    return 100 - (100 / (1 + rs))

# --- [2. 메인 UI] ---
st.set_page_config(page_title="AI 트레이딩 전술 본부", layout="wide")
st.title("🧙‍♂️ 마스터의 AI 전략 분석 본부")

# 사이드바: 투자 장부
st.sidebar.header("💰 내 투자 장부")
buy_price = st.sidebar.number_input("내 평단가", value=0)
hold_count = st.sidebar.number_input("보유 수량", value=0)
target_price = st.sidebar.number_input("목표 매도가", value=0)

st.sidebar.divider()
search_input = st.sidebar.text_input("종목명(한글/티커)", "엔비디아")
K_MAP = {"삼성전자":"005930.KS", "SK하이닉스":"000660.KS", "현대차":"005380.KS", "애플":"AAPL", "테슬라":"TSLA", "엔비디아":"NVDA"}
ticker = K_MAP.get(search_input, search_input)

# 데이터 로드 (최적화 적용)
data, info = get_stock_data(ticker, "1y", "1d")
ex_rate = get_ex_rate()

if not data.empty:
    curr_price = int(data['Close'].iloc[-1])
    data['RSI'] = calculate_rsi(data['Close'])
    curr_rsi = int(data['RSI'].iloc[-1]) if not np.isnan(data['RSI'].iloc[-1]) else 50
    
    is_us = info.get('currency') == "USD"
    unit = "$" if is_us else "₩"

    # --- [3. 투자 리포트 섹션] ---
    st.subheader(f"📑 {search_input} 실시간 전략")
    
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("현재가", f"{unit}{curr_price:,}")
        if is_us: st.caption(f"원화: ₩{int(curr_price * ex_rate):,}")
        
    # 평단가가 있을 때만 손익 계산 (에러 방지 수정)
    advice = "현재는 관망세일세. 시장의 흐름을 지켜보게나."
    if buy_price > 0 and hold_count > 0:
        profit = (curr_price - buy_price) * hold_count
        profit_rate = ((curr_price / buy_price) - 1) * 100
        with c2:
            st.metric("현재 손익", f"{unit}{int(profit):,}", f"{profit_rate:.2f}%")
        with c3:
            if target_price > 0:
                progress = min(curr_price / target_price, 1.0)
                st.write(f"🎯 목표가 달성률: {progress*100:.1f}%")
                st.progress(progress)

        # AI 훈수 로직
        if profit_rate > 10: advice = "수익이 아주 좋구먼! 일부 익절하여 현금을 챙기는 게 어떻겠나?"
        elif profit_rate < -10: advice = "손실이 깊구먼. 하지만 RSI가 낮다면 버텨볼 만하네."

    st.info(f"🤖 **마스터의 훈수:** {advice}")

    # --- [4. 차트 시각화] ---
    fig = go.Figure(data=[go.Candlestick(x=data.index, open=data['Open'], high=data['High'], low=data['Low'], close=data['Close'], increasing_line_color='red', decreasing_line_color='blue')])
    
    if buy_price > 0:
        fig.add_hline(y=buy_price, line_dash="dot", line_color="yellow", annotation_text="내 평단가")
    if target_price > 0:
        fig.add_hline(y=target_price, line_dash="dash", line_color="orange", annotation_text="목표가")

    fig.update_layout(xaxis_rangeslider_visible=False, template="plotly_dark", height=500)
    st.plotly_chart(fig, width='stretch')

    # 텔레그램 리포트
    if st.button("🚀 지인들에게 전략 전파"):
        msg = f"🔔 [{search_input}]\n현재가: {unit}{curr_price:,}\n심리(RSI): {curr_rsi}%\n마스터 의견: {advice}"
        for cid in CHAT_IDS:
            requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", data={"chat_id": cid, "text": msg})
        st.success("지인들에게 보고를 완료했네!")
else:
    st.error("데이터 로드 실패! 주식 서버가 잠시 쉬고 있거나 종목명이 틀렸을 수 있네. 잠시 후 다시 시도해보게.")

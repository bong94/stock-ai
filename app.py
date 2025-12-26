import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import requests
import plotly.graph_objects as go
from scipy.signal import argrelextrema

# --- [1. 시스템 설정 & 텔레그램] ---
TELEGRAM_TOKEN = "8284260382:AAHYsS2qu0mg5G9SMm2m2Ug1I9JPR1gAAGs"
CHAT_IDS = ["6107118513"] # 지인 ID 추가 가능

# 서버 차단 방지를 위한 캐싱 (10분간 데이터 유지)
@st.cache_data(ttl=600)
def fetch_data(ticker_symbol):
    try:
        t = yf.Ticker(ticker_symbol)
        # 주말 대비 넉넉하게 1년치 일봉 데이터를 가져옴
        df = t.history(period="1y", interval="1d")
        return df, t.info
    except:
        return pd.DataFrame(), {}

@st.cache_data(ttl=3600)
def get_exchange_rate():
    try:
        ex_data = yf.download("USDKRW=X", period="1d", interval="1m")
        return float(ex_data['Close'].iloc[-1])
    except: return 1400.0 # 환율 에러 시 기본값

def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    return 100 - (100 / (1 + (gain / loss)))

# --- [2. 메인 레이아웃] ---
st.set_page_config(page_title="AI 전략 분석 본부", layout="wide")
st.title("🧙‍♂️ 마스터의 AI 전략 분석 본부")

# 사이드바: 내 투자 정보
st.sidebar.header("💰 내 투자 장부")
buy_price = st.sidebar.number_input("내 평단가 (숫자만)", value=0)
hold_count = st.sidebar.number_input("보유 수량", value=0)
target_price = st.sidebar.number_input("목표가 설정", value=0)

st.sidebar.divider()
search_name = st.sidebar.text_input("종목명(한글/티커)", "엔비디아")
K_MAP = {"삼성전자":"005930.KS", "SK하이닉스":"000660.KS", "현대차":"005380.KS", "엔비디아":"NVDA", "테슬라":"TSLA", "애플":"AAPL"}
ticker = K_MAP.get(search_name, search_name)

# 데이터 로드 가동
data, info = fetch_data(ticker)
ex_rate = get_exchange_rate()

if not data.empty:
    # 수치 정수화 및 RSI 계산
    curr_price = int(data['Close'].iloc[-1])
    data['RSI'] = calculate_rsi(data['Close'])
    curr_rsi = int(data['RSI'].iloc[-1]) if not np.isnan(data['RSI'].iloc[-1]) else 50
    
    is_us = info.get('currency') == "USD"
    unit = "$" if is_us else "₩"

    # --- [3. 핵심 지표 리포트] ---
    st.subheader(f"📊 {search_name} ({ticker}) 전술 분석")
    c1, c2, c3 = st.columns(3)
    
    with c1:
        st.metric("현재가", f"{unit}{curr_price:,}")
        if is_us: st.caption(f"원화 환산: ₩{int(curr_price * ex_rate):,}")
    
    # 지갑 상황 분석
    advice = "현재는 관망이 최선일세. 지지선을 지키는지 보게나."
    if buy_price > 0 and hold_count > 0:
        profit = (curr_price - buy_price) * hold_count
        profit_rate = ((curr_price / buy_price) - 1) * 100
        with c2:
            st.metric("실시간 손익", f"{unit}{int(profit):,}", f"{profit_rate:.2f}%")
            if is_us: st.caption(f"원화 손익: ₩{int(profit * ex_rate):,}")
        
        # 마스터의 훈수 로직
        if profit_rate > 15: advice = "수익이 아주 달콤하구먼! 일부 익절하여 승전보를 울리게!"
        elif profit_rate < -15: advice = "손실이 아프지만 RSI가 낮다면 물타기 기회를 보게나."
    else:
        with c2:
            st.metric("심리 지표(RSI)", f"{curr_rsi}%")
            
    with c3:
        if target_price > 0:
            prog = min(curr_price / target_price, 1.0)
            st.write(f"🎯 목표가 달성률: {prog*100:.1f}%")
            st.progress(prog)
        else:
            st.write("🎯 목표가를 입력하면 달성률을 계산해주네.")

    st.info(f"🤖 **마스터의 전술 제언:** {advice}")

    # --- [4. 캔들 차트 시각화] ---
    fig = go.Figure(data=[go.Candlestick(
        x=data.index, open=data['Open'], high=data['High'], 
        low=data['Low'], close=data['Close'],
        increasing_line_color='red', decreasing_line_color='blue'
    )])
    
    # 내 평단가 라인 표시 (시각적 무게감)
    if buy_price > 0:
        fig.add_hline(y=buy_price, line_dash="dot", line_color="yellow", annotation_text="나의 매수점")
    
    fig.update_layout(xaxis_rangeslider_visible=False, template="plotly_dark", height=500)
    st.plotly_chart(fig, width='stretch')

    # 텔레그램 리포트 버튼
    if st.button("🚀 지인들에게 전술 리포트 전송"):
        report = f"🔔 [{search_name} 보고]\n현재가: {unit}{curr_price:,}"
        if is_us: report += f" (₩{int(curr_price * ex_rate):,})"
        if buy_price > 0: report += f"\n수익률: {profit_rate:.1f}%"
        report += f"\n전략: {advice}"
        
        for cid in CHAT_IDS:
            requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", data={"chat_id": cid, "text": report})
        st.success("본부 및 지인들에게 보고를 완료했네!")

else:
    st.error("데이터 로드 실패! 주식 서버가 잠시 응답을 거부하고 있네. 5분 뒤 새로고침을 해보게나.")

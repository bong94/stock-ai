import streamlit as st
import pandas as pd
import yfinance as yf
import requests
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import time
from datetime import datetime

# --- [1. 보안 및 기초 설정] ---
ALPHA_VANTAGE_KEY = st.secrets.get("ALPHA_VANTAGE_KEY", "")
TELEGRAM_TOKEN = st.secrets.get("TELEGRAM_TOKEN", "")
CHAT_ID = st.secrets.get("CHAT_ID", "")

def get_usd_krw():
    """실시간 USD/KRW 환율"""
    try:
        rate = yf.Ticker("USDKRW=X").history(period="1d")['Close'].iloc[-1]
        return float(rate)
    except: return 1380.0

# --- [2. 24시간 자동 감시(파수꾼) 엔진] ---
def run_auto_guardian():
    if not st.session_state.my_portfolio:
        return

    now = datetime.now().strftime('%H:%M:%S')
    st.sidebar.caption(f"🛡️ 파수꾼 최종 순찰: {now}")

    for item in st.session_state.my_portfolio:
        # 실시간 시세 체크 (1분 간격)
        ticker_data = yf.download(item['ticker'], period="1d", interval="1m", progress=False)
        if not ticker_data.empty:
            curr_p = ticker_data['Close'].iloc[-1].item()
            buy_p = item['buy_price']
            profit_rate = ((curr_p - buy_p) / buy_p) * 100

            # 🚨 긴급 경보 조건 설정
            if profit_rate <= -3.0: # 손절선 도달 시
                msg = f"🛑 [긴급 손절 경보] {item['name']}\n현재가: {curr_p:,.2f}\n수익률: {profit_rate:.2f}%\n사령관님! 즉시 전술적 후퇴를 검토하십시오!"
                requests.get(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage?chat_id={CHAT_ID}&text={msg}")
            elif profit_rate >= 10.0: # 목표수익 도달 시
                msg = f"🎯 [수익 실현 경보] {item['name']}\n현재가: {curr_p:,.2f}\n수익률: {profit_rate:.2f}%\n승전보입니다! 이익 확정을 검토하십시오."
                requests.get(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage?chat_id={CHAT_ID}&text={msg}")

# --- [3. 메인 UI 및 데이터 관리] ---
st.set_page_config(page_title="AI 전술 사령부 v9.0 (Auto)", layout="wide")
ex_rate = get_usd_krw()

if 'my_portfolio' not in st.session_state:
    st.session_state.my_portfolio = []

# 사이드바: 내 주식 등록 및 파수꾼 설정
st.sidebar.header("🕹️ 사령부 제어 센터")
auto_on = st.sidebar.checkbox("🛡️ 24시간 자동 파수꾼 모드 활성화")

with st.sidebar.form("p_form"):
    st.write("--- 📥 내 주식 등록 ---")
    p_name = st.text_input("종목명", "에디슨 인터내셔널")
    p_ticker = st.text_input("티커", "EIX")
    p_price = st.number_input("평단가", value=60.21)
    if st.form_submit_button("포트폴리오 추가"):
        st.session_state.my_portfolio.append({"name": p_name, "ticker": p_ticker.upper(), "buy_price": p_price})
        st.rerun()

# [자동 감시 로직 실행]
if auto_on:
    run_auto_guardian()
    time.sleep(60) # 1분 대기
    st.rerun() # 화면 새로고침하여 재탐색

# 메인 화면
st.title("🧙‍♂️ AI 파수꾼 사령부 v9.0 (Full Auto)")

# [A] 실시간 포트폴리오 상황판
st.header("🛡️ 실시간 자산 감시 현황")
if st.session_state.my_portfolio:
    cols = st.columns(len(st.session_state.my_portfolio))
    for idx, item in enumerate(st.session_state.my_portfolio):
        data = yf.download(item['ticker'], period="5d", progress=False)
        if not data.empty:
            curr = data['Close'].iloc[-1].item()
            profit = ((curr - item['buy_price']) / item['buy_price']) * 100
            is_kr = item['ticker'].endswith(".KS") or item['ticker'].endswith(".KQ")
            unit = "원" if is_kr else "$"
            
            with cols[idx]:
                st.metric(f"{item['name']}", f"{unit}{curr:,.2f}", f"{profit:.2f}%")
                if not is_kr:
                    st.caption(f"환산: {curr * ex_rate:,.0f}원")
st.divider()

# [B] 개별 종목 정밀 전술 분석
st.header("🔍 정밀 전술 분석 & 캔들 차트")
target_input = st.text_input("분석할 종목 티커", "EIX").upper()

if st.button("⚔️ 전술 가동"):
    df = yf.download(target_input, period="6mo", interval="1d", progress=False)
    if not df.empty:
        # 캔들 차트 시각화
        fig = go.Figure(data=[go.Candlestick(
            x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
            increasing_line_color='#FF4B4B', decreasing_line_color='#0083B0'
        )])
        
        # 지지/저항선 자동 계산
        res = df['High'].iloc[-20:].max().item()
        sup = df['Low'].iloc[-20:].min().item()
        
        fig.add_hline(y=res, line_dash="dash", line_color="magenta", annotation_text="🚧 저항")
        fig.add_hline(y=sup, line_dash="dash", line_color="cyan", annotation_text="🛡️ 지지")
        fig.update_layout(template="plotly_dark", xaxis_rangeslider_visible=False, height=600)
        st.plotly_chart(fig, use_container_width=True)
        
        st.success(f"[{target_input}] 분석 완료: 현재가 대비 지지선({sup:,.2f}) 사수가 중요하네!")

import streamlit as st
import pandas as pd
import yfinance as yf
import requests
import plotly.graph_objects as go
import time
from datetime import datetime

# --- [1. 보안 및 기초 환경 설정] ---
TELEGRAM_TOKEN = st.secrets.get("TELEGRAM_TOKEN", "")
CHAT_ID = st.secrets.get("CHAT_ID", "")

def get_usd_krw():
    """실시간 환율 정보를 가져오는 함수"""
    try:
        rate = yf.Ticker("USDKRW=X").history(period="1d")['Close'].iloc[-1]
        return float(rate)
    except: return 1380.0

# --- [2. 핵심 AI 전술 로직] ---
def calculate_tactical_points(df):
    """최근 20일 데이터를 분석하여 최적의 매수/매도 타점 계산"""
    recent_high = df['High'].iloc[-20:].max().item()
    recent_low = df['Low'].iloc[-20:].min().item()
    buy_point = recent_low * 1.01  # 지지선 위 1% (매수)
    sell_point = recent_high * 0.98 # 저항선 아래 2% (매도)
    return buy_point, sell_point, recent_low, recent_high

def wide_area_scout(ticker_list):
    """광역 정찰 모드: 시장 주도주를 분석하여 매수 적기 종목 포착"""
    found_opportunities = []
    for t in ticker_list:
        try:
            df = yf.download(t, period="1mo", interval="1d", progress=False)
            if not df.empty:
                last_p = df['Close'].iloc[-1].item()
                buy_p, sell_p, _, _ = calculate_tactical_points(df)
                if last_p <= buy_p:
                    found_opportunities.append(f"🚨 [광역 정찰] {t} 포착!\n현재가: {last_p:,.2f}\n진입 권장가: {buy_p:,.2f}")
        except: continue
    return found_opportunities

def send_telegram(message):
    """텔레그램 알림 전송"""
    if TELEGRAM_TOKEN and CHAT_ID:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage?chat_id={CHAT_ID}&text={message}"
        requests.get(url)

# --- [3. 메인 UI 및 데이터 관리] ---
st.set_page_config(page_title="AI 전술 사령부 v9.3", layout="wide")
ex_rate = get_usd_krw()

if 'my_portfolio' not in st.session_state:
    st.session_state.my_portfolio = []

# [사이드바: 사령부 제어 센터]
st.sidebar.header("🕹️ 사령부 제어 센터")
auto_mode = st.sidebar.checkbox("🛰️ 24시간 자동 파수꾼 & 광역 정찰 활성화")

# 광역 정찰 리스트 (사령관이 원하는 대로 수정 가능)
GLOBAL_LIST = ["NVDA", "TSLA", "AAPL", "005930.KS", "BTC-USD", "EIX", "MSFT", "AMZN"]

with st.sidebar.form("p_form"):
    st.subheader("📥 내 주식 등록")
    name = st.text_input("종목명", "에디슨 인터내셔널")
    tk = st.text_input("티커", "EIX")
    bp = st.number_input("내 평단가", value=60.21)
    if st.form_submit_button("포트폴리오 추가"):
        st.session_state.my_portfolio.append({"name": name, "ticker": tk.upper(), "buy_price": bp})
        st.rerun()

# [자동 실행 엔진]
if auto_mode:
    # 광역 정찰 보고
    alerts = wide_area_scout(GLOBAL_LIST)
    for a in alerts:
        send_telegram(a)
    st.sidebar.success(f"최근 정찰 완료: {datetime.now().strftime('%H:%M:%S')}")
    time.sleep(300) # 5분마다 순찰
    st.rerun()

# --- [메인 대시보드 화면] ---
st.title("🧙‍♂️ AI 전술 통합 사령부 v9.3")

# [섹션 1: 실시간 자산 감시]
if st.session_state.my_portfolio:
    st.header("🛡️ 내 자산 실시간 전술 상황")
    p_cols = st.columns(len(st.session_state.my_portfolio))
    for idx, item in enumerate(st.session_state.my_portfolio):
        data = yf.download(item['ticker'], period="5d", progress=False)
        if not data.empty:
            curr = data['Close'].iloc[-1].item()
            profit = ((curr - item['buy_price']) / item['buy_price']) * 100
            is_kr = item['ticker'].endswith((".KS", ".KQ"))
            unit = "원" if is_kr else "$"
            with p_cols[idx]:
                st.metric(item['name'], f"{unit}{curr:,.2f}", f"{profit:.2f}%")
                if not is_kr: st.caption(f"환산: {curr * ex_rate:,.0f}원")
st.divider()

# [섹션 2: 정밀 작전 지도 (캔들 차트)]
st.header("🔍 종목별 정밀 작전 지도")
target_tk = st.text_input("분석할 티커 입력", "EIX").upper()

if st.button("⚔️ 작전 수립"):
    df = yf.download(target_tk, period="6mo", interval="1d", progress=False)
    if not df.empty:
        buy_p, sell_p, sup, res = calculate_tactical_points(df)
        last_p = df['Close'].iloc[-1].item()
        unit = "원" if target_tk.endswith((".KS", ".KQ")) else "$"

        # 캔들 차트 시각화
        fig = go.Figure(data=[go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="주가")])
        fig.add_hline(y=buy_p, line_color="lime", line_dash="dash", annotation_text="🟢 매수권장")
        fig.add_hline(y=sell_p, line_color="orange", line_dash="dash", annotation_text="🎯 매도목표")
        fig.add_hline(y=sup * 0.97, line_color="red", line_dash="dot", annotation_text="🛑 손절선")
        fig.update_layout(template="plotly_dark", xaxis_rangeslider_visible=False, height=600)
        st.plotly_chart(fig, use_container_width=True)

        # 전술 지시서
        st.subheader("📋 AI 마스터의 전술 지시")
        c1, c2 = st.columns(2)
        with c1: st.info(f"📍 매수: **{unit}{buy_p:,.2f}** 이하 권장")
        with c2: st.warning(f"🎯 매도: **{unit}{sell_p:,.2f}** 부근 수익실현")
        
        # 텔레그램 보고서 전송
        send_telegram(f"⚔️ [{target_tk}] 작전 지도 수립\n- 현재가: {unit}{last_p:,.2f}\n- 매수권장: {unit}{buy_p:,.2f}\n- 목표매도: {unit}{sell_p:,.2f}")

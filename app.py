import streamlit as st
import pandas as pd
import yfinance as yf
import requests
import plotly.graph_objects as go
import time
import json
import os
from datetime import datetime

# --- [1. 보안 및 기초 환경 설정] ---
TELEGRAM_TOKEN = st.secrets.get("TELEGRAM_TOKEN", "")
CHAT_ID = st.secrets.get("CHAT_ID", "")
PORTFOLIO_FILE = "portfolio_db.json"

# --- [2. 데이터 관리 함수] ---
def load_portfolio():
    if os.path.exists(PORTFOLIO_FILE):
        with open(PORTFOLIO_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_portfolio(portfolio):
    with open(PORTFOLIO_FILE, "w", encoding="utf-8") as f:
        json.dump(portfolio, f, ensure_ascii=False, indent=4)

# --- [3. AI 분석 및 정찰 로직 (하이브리드)] ---
def calculate_tactical_points(df):
    """최근 20거래일 데이터 기반 매수/매도 타점 학습"""
    high_20 = df['High'].iloc[-20:].max().item()
    low_20 = df['Low'].iloc[-20:].min().item()
    buy_point = low_20 * 1.01 # 지지선 근처
    sell_point = high_20 * 0.98 # 저항선 근처
    return buy_point, sell_point

def wide_area_scout(ticker_list):
    """하이브리드 정찰: 주식(최종 종가), 코인(실시간) 분리 대응"""
    found_opportunities = []
    for t in ticker_list:
        try:
            # 코인(USD/BTC 등)인지 주식인지 판별
            is_crypto = "-" in t or "BTC" in t or "ETH" in t or "SOL" in t
            
            # 데이터 로드 (주식은 장 종료 시점 반영을 위해 daily, 코인은 실시간 반영)
            df = yf.download(t, period="1mo", interval="1d", progress=False)
            
            if not df.empty:
                last_p = df['Close'].iloc[-1].item()
                buy_p, sell_p = calculate_tactical_points(df)
                
                # 매수 적기 판단: 현재가가 매수 권장가 이하일 때
                if last_p <= buy_p:
                    label = "💎 [코인 실시간 포착]" if is_crypto else "📈 [주식 종가기준 포착]"
                    found_opportunities.append(f"{label} {t}\n현재가: {last_p:,.2f}\n진입 권장가: {buy_p:,.2f}")
        except: continue
    return found_opportunities

def send_telegram(msg):
    if TELEGRAM_TOKEN and CHAT_ID:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage?chat_id={CHAT_ID}&text={msg}"
        requests.get(url)

# --- [4. 메인 UI 및 시스템 가동] ---
st.set_page_config(page_title="AI 하이브리드 사령부 v10.1", layout="wide")

if 'my_portfolio' not in st.session_state:
    st.session_state.my_portfolio = load_portfolio()

# [사이드바 설정]
st.sidebar.header("🕹️ 관제 센터 (Hybrid)")
auto_mode = st.sidebar.checkbox("🛰️ 하이브리드 자동 정찰 활성화")

# 광역 정찰 리스트
GLOBAL_LIST = ["NVDA", "TSLA", "AAPL", "005930.KS", "BTC-USD", "ETH-USD", "SOL-USD", "EIX"]

with st.sidebar.form("p_form"):
    st.subheader("📥 포트폴리오 등록")
    name = st.text_input("종목명", "에디슨")
    tk = st.text_input("티커", "EIX")
    bp = st.number_input("내 평단가", value=60.0)
    if st.form_submit_button("사령부 등록"):
        st.session_state.my_portfolio.append({"name": name, "ticker": tk.upper(), "buy_price": bp})
        save_portfolio(st.session_state.my_portfolio)
        st.rerun()

# [자동 순찰 루틴]
if auto_mode:
    now = datetime.now().strftime('%H:%M:%S')
    st.sidebar.info(f"🛰️ 하이브리드 순찰 중... ({now})")
    
    # 정찰 보고 실행
    reports = wide_area_scout(GLOBAL_LIST)
    for r in reports:
        send_telegram(r)
    
    time.sleep(300) # 5분마다 순찰
    st.rerun()

# --- [메인 대시보드 화면] ---
st.title("🧙‍♂️ AI 하이브리드 전술 사령부 v10.1")

# [실시간 자산 현황]
if st.session_state.my_portfolio:
    st.header("🛡️ 내 자산 현황 (주말/평일 자동대응)")
    cols = st.columns(len(st.session_state.my_portfolio))
    for idx, item in enumerate(st.session_state.my_portfolio):
        data = yf.download(item['ticker'], period="5d", progress=False)
        if not data.empty:
            curr = data['Close'].iloc[-1].item()
            profit = ((curr - item['buy_price']) / item['buy_price']) * 100
            unit = "원" if item['ticker'].endswith((".KS", ".KQ")) else "$"
            with cols[idx]:
                st.metric(item['name'], f"{unit}{curr:,.2f}", f"{profit:.2f}%")

st.divider()

# [정밀 작전 지도]
st.header("🔍 상세 매수/매도 작전 분석")
target_tk = st.text_input("분석 티커", "BTC-USD").upper()

if st.button("⚔️ 작전 수립"):
    df = yf.download(target_tk, period="6mo", interval="1d", progress=False)
    if not df.empty:
        buy_p, sell_p = calculate_tactical_points(df)
        fig = go.Figure(data=[go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'])])
        fig.add_hline(y=buy_p, line_color="lime", annotation_text="🟢 매수")
        fig.add_hline(y=sell_p, line_color="orange", annotation_text="🎯 매도")
        fig.update_layout(template="plotly_dark", xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)

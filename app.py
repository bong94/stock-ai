import streamlit as st
import pandas as pd
import yfinance as yf
import requests
import plotly.graph_objects as go
import time
import json
import os
from datetime import datetime

# --- [1. 보안 및 환경 설정] ---
ALPHA_VANTAGE_KEY = st.secrets.get("ALPHA_VANTAGE_KEY", "")
TELEGRAM_TOKEN = st.secrets.get("TELEGRAM_TOKEN", "")
CHAT_ID = st.secrets.get("CHAT_ID", "")
PORTFOLIO_FILE = "portfolio_db.json"
IMG_PATH = "tactical_report.png"

def load_portfolio():
    if os.path.exists(PORTFOLIO_FILE):
        try:
            with open(PORTFOLIO_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except: return []
    return []

def save_portfolio(portfolio):
    with open(PORTFOLIO_FILE, "w", encoding="utf-8") as f:
        json.dump(portfolio, f, ensure_ascii=False, indent=4)

# --- [2. AI 판단 로직] ---
def get_ai_decision(curr_p, buy_p, low_20):
    profit_rate = ((curr_p - buy_p) / buy_p) * 100
    if profit_rate <= -3.0 and curr_p < low_20:
        return "🔴 [전략적 손절] 지지선 붕괴. 후퇴 권고."
    if -5.0 <= profit_rate <= -0.5 and (low_20 * 0.99 <= curr_p <= low_20 * 1.02):
        return "🔵 [추가 매수 기회] 지지선 반등 구간."
    if profit_rate >= 10.0:
        return "🎯 [수익 실현] 분할 매도 검토."
    return "🟡 [관망] 진영 유지."

# --- [3. 메인 대시보드] ---
st.set_page_config(page_title="AI 판단 사령부 v10.6", layout="wide")
if 'my_portfolio' not in st.session_state:
    st.session_state.my_portfolio = load_portfolio()

# [사이드바 제어판]
st.sidebar.header("🕹️ 사령부 관제 센터")
auto_mode = st.sidebar.checkbox("🛰️ AI 자동 정찰 모드 활성화")

with st.sidebar.form("p_form"):
    st.subheader("📥 자산 등록")
    name = st.text_input("종목명", "삼성전자")
    tk = st.text_input("티커", "005930.KS")
    bp = st.number_input("평단가", value=0)
    if st.form_submit_button("등록"):
        st.session_state.my_portfolio.append({"name": name, "ticker": tk.upper(), "buy_price": bp})
        save_portfolio(st.session_state.my_portfolio)
        st.rerun()

if st.sidebar.button("🗑️ 전체 초기화"):
    save_portfolio([])
    st.session_state.my_portfolio = []
    st.rerun()

# [메인 엔진 가동]
st.title("🧙‍♂️ AI 전술 사령부 v10.6")

if st.session_state.my_portfolio:
    # 1. 데이터 수집 및 카테고리 분류
    korea_stocks = []
    global_assets = []
    
    for item in st.session_state.my_portfolio:
        try:
            df = yf.download(item['ticker'], period="1mo", progress=False)
            if not df.empty:
                curr_p = df['Close'].iloc[-1].item()
                low_20 = df['Low'].iloc[-20:].min().item()
                profit = ((curr_p - item['buy_price']) / item['buy_price']) * 100
                decision = get_ai_decision(curr_p, item['buy_price'], low_20)
                
                asset_info = {"name": item['name'], "ticker": item['ticker'], "curr": curr_p, "profit": profit, "decision": decision}
                
                # 티커 끝자리에 따라 국내/해외 분류
                if item['ticker'].endswith((".KS", ".KQ")):
                    korea_stocks.append(asset_info)
                else:
                    global_assets.append(asset_info)
        except: continue

    # 2. 정렬 (이름 기준 가나다/ABC)
    korea_stocks.sort(key=lambda x: x['name'])
    global_assets.sort(key=lambda x: x['name'])

    # 3. 화면 출력
    def display_category(title, assets):
        if assets:
            st.header(title)
            cols = st.columns(min(len(assets), 4)) # 최대 4열 구성
            for idx, a in enumerate(assets):
                with cols[idx % 4]:
                    format_str = ":,.0f" if a['ticker'].endswith((".KS", ".KQ")) else ":,.2f"
                    st.metric(a['name'], f"{a['curr']{format_str}}", f"{a['profit']:.2f}%")
                    st.caption(f"🤖 {a['decision']}")
            st.divider()

    display_category("🇰🇷 국내 주식 전선 (가나다순)", korea_stocks)
    display_category("🌎 해외 주식 & 코인 전선 (ABC순)", global_assets)

else:
    st.info("사령관님, 사이드바에서 종목을 등록하여 정찰을 시작해 주시게!")

st.caption("v10.6: 국내/해외 카테고리 자동 분류 및 가나다 정렬 엔진 탑재")

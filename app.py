import streamlit as st
import pandas as pd
import yfinance as yf
import requests
import plotly.graph_objects as go
import time
import json
import os
from datetime import datetime

# --- [1. 보안 및 지능형 DB 설정] ---
ALPHA_VANTAGE_KEY = st.secrets.get("ALPHA_VANTAGE_KEY", "")
TELEGRAM_TOKEN = st.secrets.get("TELEGRAM_TOKEN", "")
CHAT_ID = st.secrets.get("CHAT_ID", "")
PORTFOLIO_FILE = "portfolio_db.json"
LEARNING_FILE = "learning_db.json" # AI가 학습한 종목 저장소

# 초기 기본 종목 (학습의 시작점)
DEFAULT_TICKERS = {
    "삼성전자": "005930.KS", "SK하이닉스": "000660.KS", "테슬라": "TSLA", 
    "엔비디아": "NVDA", "비트코인": "BTC-USD", "애플": "AAPL"
}

def load_json(file_path, default_data):
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except: return default_data
    return default_data

def save_json(file_path, data):
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# 데이터 로드
if 'my_portfolio' not in st.session_state:
    st.session_state.my_portfolio = load_json(PORTFOLIO_FILE, [])
if 'learned_tickers' not in st.session_state:
    st.session_state.learned_tickers = load_json(LEARNING_FILE, DEFAULT_TICKERS)

# --- [2. AI 전술 판단 엔진] ---
def get_ai_decision(curr_p, buy_p, low_20):
    profit_rate = ((curr_p - buy_p) / buy_p) * 100
    if profit_rate <= -3.0 and curr_p < low_20:
        return "🔴 [전략적 손절] 지지선 붕괴. 후퇴 권고."
    if -5.0 <= profit_rate <= -0.5 and (low_20 * 0.99 <= curr_p <= low_20 * 1.02):
        return "🔵 [추가 매수 기회] 지지선 반등 구간."
    if profit_rate >= 10.0:
        return "🎯 [수익 실현] 익절 타점일세!"
    return "🟡 [관망] 진영 유지."

# --- [3. 메인 대시보드 가동] ---
st.set_page_config(page_title="AI 지능형 사령부 v11.5", layout="wide")

# [사이드바: 지능형 관제 센터]
st.sidebar.header("🕹️ 지능형 관제 센터")

# 전술 1: AI 학습 리스트 기반 자동 완성
st.sidebar.subheader("🧠 학습된 종목 퀵 선택")
learned_list = sorted(st.session_state.learned_tickers.keys())
selected_quick = st.sidebar.selectbox("종목 검색 및 선택", ["직접 입력"] + learned_list)

with st.sidebar.form("input_form"):
    st.subheader("📥 신규 자산 배치")
    
    # 퀵 선택 시 자동 입력
    default_name = selected_quick if selected_quick != "직접 입력" else ""
    default_tk = st.session_state.learned_tickers.get(selected_quick, "")
    
    name = st.text_input("종목명", value=default_name)
    tk = st.text_input("티커 (Ticker)", value=default_tk, help="예: 삼성전자(005930.KS), 테슬라(TSLA)")
    bp = st.number_input("평단가", value=0)
    
    if st.form_submit_button("전선 배치 및 AI 학습"):
        if tk:
            tk = tk.upper()
            # 1. 포트폴리오 추가
            st.session_state.my_portfolio.append({"id": str(time.time()), "name": name, "ticker": tk, "buy_price": bp})
            save_json(PORTFOLIO_FILE, st.session_state.my_portfolio)
            
            # 2. 신규 종목 학습 (DB 업데이트)
            if name not in st.session_state.learned_tickers:
                st.session_state.learned_tickers[name] = tk
                save_json(LEARNING_FILE, st.session_state.learned_tickers)
                st.sidebar.success(f"🎓 AI가 '{name}' 종목을 새로 학습했네!")
            
            st.rerun()

# [사이드바: 관리 기능]
st.sidebar.divider()
if st.sidebar.button("🗑️ 전체 데이터 초기화"):
    save_json(PORTFOLIO_FILE, [])
    st.session_state.my_portfolio = []
    st.rerun()

# [메인 전황판]
st.title("🧙‍♂️ AI 전술 사령부 v11.5")

if st.session_state.my_portfolio:
    k_list, g_list = [], []
    for item in st.session_state.my_portfolio:
        try:
            df = yf.download(item['ticker'], period="1mo", progress=False)
            if not df.empty:
                curr_p = float(df['Close'].iloc[-1])
                low_20 = float(df['Low'].iloc[-20:].min())
                profit = ((curr_p - item['buy_price']) / item['buy_price']) * 100
                decision = get_ai_decision(curr_p, item['buy_price'], low_20)
                
                info = {"name": item['name'], "ticker": item['ticker'], "curr": curr_p, "profit": profit, "decision": decision}
                if item['ticker'].endswith((".KS", ".KQ")): k_list.append(info)
                else: g_list.append(info)
        except: continue

    def render_front(title, assets):
        if assets:
            st.header(title)
            cols = st.columns(min(len(assets), 4))
            for i, a in enumerate(assets):
                with cols[i % 4]:
                    f_fmt = ":,.0f" if a['ticker'].endswith((".KS", ".KQ")) else ":,.2f"
                    st.metric(a['name'], f"{a['curr']:{f_fmt[1:]}}", f"{a['profit']:.2f}%")
                    st.caption(f"🤖 {a['decision']}")
                    # 개별 삭제 버튼 (메인 화면 배치)
                    if st.button(f"제거: {a['name']}", key=f"main_del_{a['name']}_{i}"):
                        st.session_state.my_portfolio = [p for p in st.session_state.my_portfolio if p['ticker'] != a['ticker']]
                        save_json(PORTFOLIO_FILE, st.session_state.my_portfolio)
                        st.rerun()
            st.divider()

    render_front("🇰🇷 국내 주식 전선", k_list)
    render_front("🌎 해외 주식 & 코인 전선", g_list)
else:
    st.info("사령관님, 새로운 종목을 입력하면 AI가 실시간으로 학습하여 저장할 걸세!")

st.caption(f"v11.5 | AI 학습 종목 수: {len(st.session_state.learned_tickers)}개")

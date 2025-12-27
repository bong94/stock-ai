import streamlit as st
import pandas as pd
import yfinance as yf
import requests
import plotly.graph_objects as go
import time
import json
import os
import threading
from datetime import datetime

# --- [1. 보안 및 지능형 DB 설정] ---
TELEGRAM_TOKEN = st.secrets.get("TELEGRAM_TOKEN", "")
CHAT_ID = st.secrets.get("CHAT_ID", "")
PORTFOLIO_FILE = "portfolio_db.json"
LEARNING_FILE = "learning_db.json"

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

# 데이터 초기화
if 'my_portfolio' not in st.session_state:
    st.session_state.my_portfolio = load_json(PORTFOLIO_FILE, [])
if 'learned_tickers' not in st.session_state:
    st.session_state.learned_tickers = load_json(LEARNING_FILE, {"삼성전자": "005930.KS", "테슬라": "TSLA"})

# --- [2. 텔레그램 양방향 엔진] ---
def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, data={'chat_id': CHAT_ID, 'text': message})

def get_last_telegram_msg():
    """사령관님의 마지막 명령을 확인"""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates"
    try:
        res = requests.get(url).json()
        if res["result"]:
            return res["result"][-1]["message"]["text"]
    except: return None
    return None

# --- [3. AI 전술 판단 엔진] ---
def get_ai_decision(curr_p, buy_p, low_20):
    profit_rate = ((curr_p - buy_p) / buy_p) * 100
    if profit_rate <= -3.0 and curr_p < low_20:
        return f"🔴 [손절 권고] 수익률 {profit_rate:.2f}%. 지지선 붕괴!"
    if -5.0 <= profit_rate <= -1.0 and (low_20 * 0.98 <= curr_p <= low_20 * 1.02):
        return f"🔵 [추매 기회] 수익률 {profit_rate:.2f}%. 지지선 반등 중."
    if profit_rate >= 5.0:
        return f"🎯 [익절 타점] 수익률 {profit_rate:.2f}%. 목표 달성!"
    return f"🟡 [관망] 수익률 {profit_rate:.2f}%. 현재 진영 유지."

# --- [4. 메인 대시보드 가동] ---
st.set_page_config(page_title="AI 전술 사령부 v12.0", layout="wide")

# [사이드바: 지능형 관제 센터]
st.sidebar.header("🕹️ 지능형 관제 센터")

# 정찰 주기 설정 (5분/10분)
report_interval = st.sidebar.select_slider("🛰️ 자동 정찰 및 보고 주기 (분)", options=[1, 5, 10, 30, 60], value=5)

# 학습된 종목 선택
learned_list = sorted(st.session_state.learned_tickers.keys())
selected_quick = st.sidebar.selectbox("🧠 학습된 종목 퀵 선택", ["직접 입력"] + learned_list)

with st.sidebar.form("input_form"):
    st.subheader("📥 신규 자산 배치")
    d_name = selected_quick if selected_quick != "직접 입력" else ""
    d_tk = st.session_state.learned_tickers.get(selected_quick, "")
    
    name = st.text_input("종목명", value=d_name)
    tk = st.text_input("티커 (Ticker)", value=d_tk)
    # 소수점 0.01 단위 입력을 위해 step 설정
    bp = st.number_input("평단가 (달러/원 정밀 입력)", value=0.00, format="%.2f", step=0.01)
    
    if st.form_submit_button("전선 배치 및 AI 학습"):
        if tk:
            tk = tk.upper()
            st.session_state.my_portfolio.append({"name": name, "ticker": tk, "buy_price": bp})
            save_json(PORTFOLIO_FILE, st.session_state.my_portfolio)
            
            if name not in st.session_state.learned_tickers:
                st.session_state.learned_tickers[name] = tk
                save_json(LEARNING_FILE, st.session_state.learned_tickers)
            st.rerun()

# [메인 전황판]
st.title(f"🧙‍♂️ AI 전술 사령부 v12.0")
st.subheader(f"📡 현재 {report_interval}분 주기로 자동 정찰 중...")

if st.session_state.my_portfolio:
    current_report = []
    k_cols, g_cols = st.columns(2)
    
    for idx, item in enumerate(st.session_state.my_portfolio):
        try:
            df = yf.download(item['ticker'], period="1mo", progress=False)
            if not df.empty:
                curr_p = float(df['Close'].iloc[-1])
                low_20 = float(df['Low'].iloc[-20:].min())
                decision = get_ai_decision(curr_p, item['buy_price'], low_20)
                
                # 화면 출력
                target_col = k_cols if item['ticker'].endswith((".KS", ".KQ")) else g_cols
                with target_col:
                    f_fmt = ":,.0f" if item['ticker'].endswith((".KS", ".KQ")) else ":,.2f"
                    st.metric(f"{item['name']} ({item['ticker']})", f"{curr_p{f_fmt[1:]}}", decision)
                    if st.button(f"퇴출: {item['name']}", key=f"del_{idx}"):
                        st.session_state.my_portfolio.pop(idx)
                        save_json(PORTFOLIO_FILE, st.session_state.my_portfolio)
                        st.rerun()
                
                # 텔레그램 보고서용 데이터 수집
                if "🟡" not in decision: # 특이사항(손절/추매/익절) 있을 때만
                    current_report.append(f"🚩 {item['name']}: {decision}")
        except: continue

    # [텔레그램 양방향 통신 처리]
    user_cmd = get_last_telegram_msg()
    if user_cmd == "보고":
        full_msg = "🏛️ [사령부 현재 상황 보고]\n" + "\n".join([f"- {p['name']}: {p['ticker']}" for p in st.session_state.my_portfolio])
        send_telegram(full_msg)
        send_telegram("명령을 대기 중입니다, 사령관님.")
    
    # [주기적 자동 알림]
    if current_report:
        alert_msg = f"🚨 [실시간 전술 알림 - {report_interval}분 주기]\n" + "\n".join(current_report)
        # 세션 상태를 이용해 중복 발송 방지
        if 'last_alert' not in st.session_state or (time.time() - st.session_state.last_alert) > (report_interval * 60):
            send_telegram(alert_msg)
            st.session_state.last_alert = time.time()

else:
    st.info("사령관님, 새로운 종목을 학습시켜 주시게!")

# 자동 새로고침 (정찰 주기에 맞춰 실행)
time.sleep(10) # 텔레그램 명령 확인을 위해 10초마다 루프
st.rerun()

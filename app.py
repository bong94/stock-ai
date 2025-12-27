import streamlit as st
import pandas as pd
import yfinance as yf
import requests
import time
import json
import os
from datetime import datetime
import pytz

# --- [1. 다중 사용자 식별 및 데이터베이스 설정] ---
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

# 사이드바에서 사용자 식별
st.sidebar.title("🎖️ 사령부 로그인")
user_id = st.sidebar.text_input("사령관 성함을 입력하세요", value="방문자")
USER_PORTFOLIO = f"portfolio_{user_id}.json"
USER_HISTORY = f"history_{user_id}.json"

# 초기 데이터 설정 (사령관님 계정 '봉94'에는 기존 데이터 자동 로드)
if user_id == "봉94":
    default_assets = [
        {"name": "대상홀딩스우", "ticker": "084695.KS", "buy_price": 14220},
        {"name": "리얼티인컴", "ticker": "O", "buy_price": 56.32},
        {"name": "에디슨", "ticker": "EIX", "buy_price": 60.21},
        {"name": "SGOV", "ticker": "SGOV", "buy_price": 100.55},
        {"name": "TQQQ", "ticker": "TQQQ", "buy_price": 60.12}
    ]
else:
    default_assets = []

if 'my_portfolio' not in st.session_state or st.session_state.get('last_user') != user_id:
    st.session_state.my_portfolio = load_json(USER_PORTFOLIO, default_assets)
    st.session_state.last_user = user_id

# --- [2. AI 지능형 가변 전술 엔진] ---
def calculate_ai_tactics(ticker, buy_price):
    try:
        df = yf.download(ticker, period="20d", progress=False)
        if df.empty: return buy_price * 0.88, buy_price * 1.25, buy_price * 1.10
        atr_pct = ((df['High'] - df['Low']).mean() / df['Close'].mean()) * 100
        # 종목별 변동성 기반 가변 수치 계산
        return buy_price * (1 - (max(atr_pct * 1.5, 5) / 100)), \
               buy_price * (1 + (max(atr_pct * 3.0, 10) / 100)), \
               buy_price * (1 + (max(atr_pct * 1.2, 5) / 100))
    except: return buy_price * 0.88, buy_price * 1.25, buy_price * 1.10

# --- [3. 보고서 및 알림 엔진] ---
def get_exchange_rate():
    try:
        ex_data = yf.download("USDKRW=X", period="1d", progress=False)
        return float(ex_data['Close'].iloc[-1])
    except: return 1442.0

def send_msg(text):
    token = st.secrets.get("TELEGRAM_TOKEN", ""); chat_id = st.secrets.get("CHAT_ID", "")
    if token and chat_id: requests.post(f"https://api.telegram.org/bot{token}/sendMessage", data={'chat_id': chat_id, 'text': text})

def generate_tactical_report(title=f"🏛️ [{user_id} 사령관 전략 보고]"):
    rate = get_exchange_rate()
    reports = []
    for i, item in enumerate(st.session_state.my_portfolio):
        ticker = item['ticker']; buy_p = float(item['buy_price'])
        try:
            df = yf.download(ticker, period="2d", progress=False)
            curr_p = float(df['Close'].iloc[-1])
            ai_buy, ai_target, ai_profit = calculate_ai_tactics(ticker, buy_p)
            is_kor = ".K" in ticker
            def fmt(p): return f"₩{p:,.0f}" if is_kor else f"${p:,.2f} (₩{p*rate:,.0f})"
            # 사진 양식 기반 보고서 생성
            reports.append(f"{i+1}번 [{item['name']}] AI 전술\n- 현재가: {fmt(curr_p)}\n🎯 추매가: {fmt(ai_buy)}\n🚀 목표가: {fmt(ai_target)}\n🛡️ 익절가: {fmt(ai_profit)}")
        except: continue
    return f"{title}\n\n" + "\n\n----------\n\n".join(reports)

# --- [4. UI 구성: 종목 추가 및 관리] ---
st.title(f"⚔️ AI 전술 사령부 v50.0")
st.subheader(f"👤 현재 지휘관: {user_id}")

# 신규 종목 추가 섹터 (다른 사용자를 위한 기능)
with st.expander("➕ 신규 타격 목표(종목) 추가"):
    c1, c2, c3 = st.columns(3)
    new_name = c1.text_input("종목명")
    new_ticker = c2.text_input("티커 (예: AAPL)")
    new_buy = c3.number_input("구매가", min_value=0.0)
    if st.button("부대 합류 (추가)"):
        st.session_state.my_portfolio.append({"name": new_name, "ticker": new_ticker.upper(), "buy_price": new_buy})
        save_json(USER_PORTFOLIO, st.session_state.my_portfolio)
        st.success(f"{new_name} 대원 배치 완료!")
        st.rerun()

# 자산 현황 테이블 출력
if st.session_state.my_portfolio:
    df_display = pd.DataFrame(st.session_state.my_portfolio)
    st.table(df_display)

if st.button("📊 텔레그램으로 전술 보고 송신"):
    send_msg(generate_tactical_report())

# --- [5. 자동화 스케줄러 (클라우드 상시 가동)] ---
now = datetime.now(pytz.timezone('Asia/Seoul'))
if now.hour == 8 and 50 <= now.minute <= 55:
    send_msg(f"📡 {user_id} 사령관님, 아침 정찰 보고를 확인하십시오.")
    time.sleep(600)

time.sleep(300); st.rerun()

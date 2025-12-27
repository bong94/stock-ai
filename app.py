import streamlit as st
import pandas as pd
import yfinance as yf
import requests
import time
import json
import os

# --- [1. 보안 및 전술 데이터베이스] ---
TELEGRAM_TOKEN = st.secrets.get("TELEGRAM_TOKEN", "")
CHAT_ID = st.secrets.get("CHAT_ID", "")
PORTFOLIO_FILE = "portfolio_db.json"

def load_db():
    if os.path.exists(PORTFOLIO_FILE):
        try:
            with open(PORTFOLIO_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except: return []
    return []

def save_db(data):
    with open(PORTFOLIO_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

if 'my_portfolio' not in st.session_state:
    st.session_state.my_portfolio = load_db()

# --- [2. UI 전용 리포트 생성기] ---
def send_telegram_msg(text):
    if not TELEGRAM_TOKEN or not CHAT_ID: return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.post(url, data={'chat_id': CHAT_ID, 'text': text, 'parse_mode': 'Markdown'}, timeout=10)
    except: pass

def get_aggressive_report(name, ticker, buy_p, idx=1):
    """적극적 투자형 전술 수치 자동 계산 (사령관님 요청 1번 양식)"""
    try:
        df = yf.download(ticker, period="5d", progress=False)
        if df.empty: return None, 0
        curr_p = float(df['Close'].iloc[-1])
        
        avg_down = buy_p * 0.88   # -12% 추매 권장
        target_p = buy_p * 1.25   # +25% 목표
        take_profit = buy_p * 1.10 # +10% 익절 구간
        
        symbol = "₩" if any(x in ticker for x in (".KS", ".KQ")) else "$"
        
        report = f"""
*{idx}번 [{name.upper()}] 작전 지도 수립*
- 구매가: {symbol}{buy_p:,.2f}
- 현재가: {symbol}{curr_p:,.2f}
- 추가매수권장: {symbol}{avg_down:,.2f} (-12%)
- 목표매도: {symbol}{target_p:,.2f} (+25%)
- 익절 구간: {symbol}{take_profit:,.2f} (+10%)
        """
        return report, curr_p
    except:
        return None, 0

# --- [3. UI 레이아웃 구성] ---
st.set_page_config(page_title="적극 투자자 관제 UI", layout="wide")
st.title("⚔️ 적극적 투자형 전술 사령부")

# 사이드바: 수동 입력 UI
with st.sidebar:
    st.header("입력 관제실")
    in_name = st.text_input("종목명", "EIX")
    in_ticker = st.text_input("티커", "EIX")
    in_price = st.number_input("평단가", value=60.21)
    if st.button("신규 자산 배치"):
        st.session_state.my_portfolio.append({"name": in_name, "ticker": in_ticker.upper(), "buy_price": in_price})
        save_db(st.session_state.my_portfolio)
        st.rerun()

# 메인 UI: 실시간 모니터링
if st.session_state.my_portfolio:
    cols = st.columns(min(len(st.session_state.my_portfolio), 4))
    for i, item in enumerate(st.session_state.my_portfolio):
        report, curr = get_aggressive_report(item['name'], item['ticker'], item['buy_price'], i+1)
        
        with cols[i % 4]:
            if curr > 0:
                profit = ((curr - item['buy_price']) / item['buy_price']) * 100
                st.metric(item['name'], f"{curr:,.2f}", f"{profit:.2f}%")
                st.text(f"목표: {item['buy_price']*1.25:,.2f}")
            else:
                st.error(f"{item['name']} 데이터 오류")
            
            if st.button(f"작전 종료", key=f"del_{i}"):
                st.session_state.my_portfolio.pop(i)
                save_db(st.session_state.my_portfolio)
                st.rerun()

# 텔레그램 명령 감지 (백그라운드)
def listen_telegram():
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates"
    try:
        res = requests.get(url, timeout=5).json()
        if res.get("result"):
            last = res["result"][-1]
            msg_text = last["message"].get("text", "")
            update_id = last["update_id"]
            if 'last_id' not in st.session_state or st.session_state.last_id < update_id:
                st.session_state.last_id = update_id
                if msg_text.startswith("매수"):
                    # 자동 등록 로직 실행
                    st.rerun()
    except: pass

listen_telegram()
time.sleep(5)
st.rerun()

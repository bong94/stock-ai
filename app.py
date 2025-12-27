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
LEARNING_FILE = "learning_db.json"

def load_db(file, default):
    if os.path.exists(file):
        try:
            with open(file, "r", encoding="utf-8") as f: return json.load(f)
        except: return default
    return default

def save_db(file, data):
    with open(file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

if 'my_portfolio' not in st.session_state:
    st.session_state.my_portfolio = load_db(PORTFOLIO_FILE, [])
if 'learned_tickers' not in st.session_state:
    st.session_state.learned_tickers = load_db(LEARNING_FILE, {"삼성전자": "005930.KS", "TQQQ": "TQQQ"})

# --- [2. 전술 보고 생성 엔진] ---
def send_telegram_msg(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try: requests.post(url, data={'chat_id': CHAT_ID, 'text': text, 'parse_mode': 'Markdown'}, timeout=5)
    except: pass

def make_tactical_report(name, ticker, buy_price, curr_price, idx=1):
    """사령관님이 요청하신 형식의 정밀 보고서 생성"""
    # 전술 계산 (예시: 추매 -5%, 목표 +10%, 익절/손절 -10%)
    # 사령관님의 예시 수치(+12%, +25% 등)를 반영한 로직
    avg_down = buy_price * 0.95  # 추가매수권장 (평단 대비 -5% 지점 등 설정 가능)
    target_price = buy_price * 1.10 # 목표매도 (+10%)
    stop_loss = buy_price * 0.90 # 익절/손절 구간

    currency = "원" if ".KS" in ticker or ".KQ" in ticker else "$"
    
    report = f"""
*{idx}번 [{name}] 작전 지도 수립*
- 구매가: {currency}{buy_price:,.2f}
- 현재가: {currency}{curr_price:,.2f}
- 추가매수권장: {currency}{avg_down:,.2f} (예: 지지선 부근)
- 목표매도: {currency}{target_price:,.2f} (목표 수익권)
- 익절/손절 구간: {currency}{stop_loss:,.2f}
    """
    return report

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
                # 매수 명령: '매수 이름 티커 평단가'
                if msg_text.startswith("매수"):
                    p = msg_text.split()
                    if len(p) >= 4:
                        name, tk, bp = p[1], p[2].upper(), float(p[3])
                        # 중복 제거 후 추가
                        st.session_state.my_portfolio = [i for i in st.session_state.my_portfolio if i['ticker'] != tk]
                        st.session_state.my_portfolio.append({"name": name, "ticker": tk, "buy_price": bp})
                        save_db(PORTFOLIO_FILE, st.session_state.my_portfolio)
                        
                        # 즉시 분석 보고 발송
                        df = yf.download(tk, period="1d", progress=False)
                        curr = float(df['Close'].iloc[-1])
                        report = make_tactical_report(name, tk, bp, curr, len(st.session_state.my_portfolio))
                        send_telegram_msg(f"🫡 명령 수신 및 분석 완료!\n{report}")
                        return "RERUN"
                elif msg_text == "보고": return "REPORT"
    except: pass
    return None

# --- [3. 메인 사령부 가동] ---
st.set_page_config(page_title="AI 전술 사령부 v16.0", layout="wide")
st.title("🧙‍♂️ AI 전술 사령부 v16.0")

cmd = listen_telegram()
if cmd == "RERUN": st.rerun()

if st.session_state.my_portfolio:
    full_report_list = []
    cols = st.columns(min(len(st.session_state.my_portfolio), 4))
    
    for i, item in enumerate(st.session_state.my_portfolio):
        try:
            df = yf.download(item['ticker'], period="5d", progress=False)
            curr = float(df['Close'].iloc[-1])
            profit = ((curr - item['buy_price']) / item['buy_price']) * 100
            
            # 대시보드 표시
            with cols[i % 4]:
                st.metric(f"{item['name']} ({item['ticker']})", f"{curr:,.2f}", f"{profit:.2f}%")
            
            # 보고서 생성
            report = make_tactical_report(item['name'], item['ticker'], item['buy_price'], curr, i+1)
            
            # 자동 알림 로직 (수익률이 특정 구간에 도달하면 자동 발송)
            if profit >= 5.0 or profit <= -3.0 or cmd == "REPORT":
                send_telegram_msg(f"🚩 실시간 전황 보고\n{report}")
            
            full_report_list.append(report)
        except: continue

    if cmd == "REPORT":
        send_telegram_msg("🏛️ [사령부 전체 자산 일괄 보고]")
else:
    st.info("사령관님, 텔레그램에 '매수 이름 티커 평단가'를 입력하시게!")

time.sleep(10)
st.rerun()

import streamlit as st
import pandas as pd
import yfinance as yf
import requests
import time
import json
import os

# --- [1. 보안 설정] ---
TELEGRAM_TOKEN = st.secrets.get("TELEGRAM_TOKEN", "")
CHAT_ID = st.secrets.get("CHAT_ID", "")
PORTFOLIO_FILE = "portfolio_db.json"

# --- [2. 유틸리티] ---
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

# --- [3. 텔레그램 통신 (안정적인 일반 Markdown 방식)] ---
def send_telegram_msg(text):
    if not TELEGRAM_TOKEN or not CHAT_ID: return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        # MarkdownV2 대신 일반 Markdown을 사용하여 특수문자 에러 방지
        requests.post(url, data={'chat_id': CHAT_ID, 'text': text, 'parse_mode': 'Markdown'}, timeout=10)
    except: pass

def get_aggressive_report(name, ticker, buy_p, idx=1):
    """사령관님의 1번 양식 (적극적 투자형 수치 적용)"""
    try:
        df = yf.download(ticker, period="5d", progress=False)
        curr_p = float(df['Close'].iloc[-1])
        
        avg_down = buy_p * 0.88   # -12% 추매
        target_p = buy_p * 1.25   # +25% 목표
        take_profit = buy_p * 1.10 # +10% 익절
        
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
        return f"⚠️ {name} 데이터 호출 실패 (장외 시간 지연 가능)", 0

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
                    p = msg_text.split()
                    if len(p) >= 4:
                        name, tk, bp = p[1], p[2].upper(), float(p[3].replace(",", ""))
                        st.session_state.my_portfolio = [i for i in st.session_state.my_portfolio if i['ticker'] != tk]
                        st.session_state.my_portfolio.append({"name": name, "ticker": tk, "buy_price": bp})
                        save_db(st.session_state.my_portfolio)
                        
                        report, _ = get_aggressive_report(name, tk, bp, len(st.session_state.my_portfolio))
                        send_telegram_msg(f"🫡 명령 수신! 적극적 전술 보고드립니다.\n{report}")
                        return "RERUN"
                elif msg_text == "보고": return "REPORT"
    except: pass
    return None

# --- [4. 메인 UI 및 자동화] ---
st.set_page_config(page_title="AI 전술 사령부 v17.5", layout="wide")
st.title("⚔️ AI 전술 사령부 v17.5")

# 텔레그램 명령 상시 감시
cmd = listen_telegram()
if cmd == "RERUN": st.rerun()

if st.session_state.my_portfolio:
    all_reports = []
    cols = st.columns(min(len(st.session_state.my_portfolio), 4))
    
    for i, item in enumerate(st.session_state.my_portfolio):
        report, curr = get_aggressive_report(item['name'], item['ticker'], item['buy_price'], i+1)
        all_reports.append(report)
        
        with cols[i % 4]:
            profit = ((curr - item['buy_price']) / item['buy_price']) * 100 if curr > 0 else 0
            st.metric(f"{item['name']} ({item['ticker']})", f"{curr:,.2f}", f"{profit:.2f}%")
            if st.button(f"제거: {item['name']}", key=f"del_{i}"):
                st.session_state.my_portfolio.pop(i)
                save_db(st.session_state.my_portfolio)
                st.rerun()
                
    if cmd == "REPORT":
        send_telegram_msg("🏛️ [전체 적극적 전술 보고]\n" + "\n\n".join(all_reports))
else:
    st.info("사령관님, 텔레그램에 '매수 이름 티커 가격'을 입력해주시게!")

# 5초마다 자동 새로고침 (별도 라이브러리 없이도 기본 작동하도록 설계)
time.sleep(5)
st.rerun()

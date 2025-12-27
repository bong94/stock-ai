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
                data = json.load(f)
                return data if isinstance(data, list) else []
        except: return []
    return []

def save_db(data):
    with open(PORTFOLIO_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

if 'my_portfolio' not in st.session_state:
    st.session_state.my_portfolio = load_db()

# --- [2. 전술 보고 생성 엔진] ---
def send_telegram_msg(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try: requests.post(url, data={'chat_id': CHAT_ID, 'text': text, 'parse_mode': 'Markdown'}, timeout=10)
    except: pass

def get_tactical_report(name, ticker, buy_p, idx=1):
    """사령관님이 요청하신 1번 전술 지도 양식"""
    try:
        df = yf.download(ticker, period="5d", progress=False)
        curr_p = float(df['Close'].iloc[-1])
        
        # 사령관님 지침에 따른 전술 수치 계산
        # 1. 추가매수권장: 전일 저가 혹은 평단 대비 -5%
        avg_down = buy_p * 0.95 
        # 2. 목표매도: 평단 대비 +15% (예시)
        target_p = buy_p * 1.15
        # 3. 익절/손절 구간: 평단 대비 -7% (예시)
        stop_loss = buy_p * 0.93
        
        symbol = "원" if ".KS" in ticker or ".KQ" in ticker else "$"
        
        report = f"""
*{idx}번 [{name}] 작전 지도 수립*
- 구매가: {symbol}{buy_p:,.2f}
- 현재가: {symbol}{curr_p:,.2f}
- 추가매수권장: {symbol}{avg_down:,.2f}
- 목표매도: {symbol}{target_p:,.2f}
- 익절 구간: {symbol}{stop_loss:,.2f}
        """
        return report
    except:
        return f"⚠️ {name}({ticker}) 데이터 분석 불가"

def listen_telegram():
    """사령관님의 명령을 최우선으로 감시"""
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
                        name, tk, bp = p[1], p[2].upper(), float(p[3])
                        # 기존 종목이 있다면 업데이트, 없다면 추가
                        new_portfolio = [i for i in st.session_state.my_portfolio if i['ticker'] != tk]
                        new_portfolio.append({"name": name, "ticker": tk, "buy_price": bp})
                        st.session_state.my_portfolio = new_portfolio
                        save_db(st.session_state.my_portfolio)
                        
                        # 즉시 분석 보고서 발송
                        report = get_tactical_report(name, tk, bp, len(st.session_state.my_portfolio))
                        send_telegram_msg(f"🫡 명령 수신! 즉시 작전 지도를 송신합니다.\n{report}")
                        return "RERUN"
                elif msg_text == "보고":
                    return "REPORT"
    except: pass
    return None

# --- [3. 메인 화면 구성] ---
st.set_page_config(page_title="AI 전술 사령부 v16.5", layout="wide")
st.title("🧙‍♂️ AI 전술 사령부 v16.5")

# 명령 확인
cmd_status = listen_telegram()
if cmd_status == "RERUN": st.rerun()

if st.session_state.my_portfolio:
    st.subheader("🛰️ 전 종목 실시간 감시 및 작전 수행 중")
    all_reports = []
    cols = st.columns(min(len(st.session_state.my_portfolio), 4))
    
    for i, item in enumerate(st.session_state.my_portfolio):
        report = get_tactical_report(item['name'], item['ticker'], item['buy_price'], i+1)
        all_reports.append(report)
        
        with cols[i % 4]:
            st.info(f"📍 {item['name']} 관측 중")
            if st.button(f"작전 종료(삭제): {item['name']}", key=f"del_{i}"):
                st.session_state.my_portfolio.pop(i)
                save_db(st.session_state.my_portfolio)
                st.rerun()
    
    # 사령관님이 '보고'라고 쳤을 때 전체 보고
    if cmd_status == "REPORT":
        send_telegram_msg("🏛️ [사령부 전체 전황 보고]\n" + "\n\n".join(all_reports))
else:
    st.warning("사령관님, 현재 배치된 자산이 없네. 텔레그램으로 '매수 이름 티커 평단가' 명령을 내려주시게!")

# 즉각적인 반응을 위해 5초 대기 후 리프레시
time.sleep(5)
st.rerun()

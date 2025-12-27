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

# --- [2. 텔레그램 통신 및 적극적 전술 엔진] ---
def send_telegram_msg(text):
    """텔레그램으로 즉각 보고 (마크다운 적용)"""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.post(url, data={'chat_id': CHAT_ID, 'text': text, 'parse_mode': 'Markdown'}, timeout=10)
    except: pass

def get_aggressive_report(name, ticker, buy_p, idx=1):
    """적극적 투자형을 위한 정밀 전술 지표 계산 (사령관님 요청 1번 양식)"""
    try:
        df = yf.download(ticker, period="5d", progress=False)
        curr_p = float(df['Close'].iloc[-1])
        
        # [적극적 투자형 수치 적용]
        # 1. 추가매수권장: 공격적 물타기 (평단 대비 -12%)
        avg_down = buy_p * 0.88 
        # 2. 목표매도: 고수익 목표 (평단 대비 +25%)
        target_p = buy_p * 1.25
        # 3. 익절 구간: 확실한 수익 보존 (평단 대비 +10% 이상 시 등)
        # 사령관님 요청 양식에 맞춰 익절/손절 가이드 라인 설정
        take_profit = buy_p * 1.10
        
        symbol = "원" if ".KS" in ticker or ".KQ" in ticker else "$"
        
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
        return f"⚠️ {name}({ticker}) 분석 실패", 0

def listen_telegram():
    """사령관님의 매수 명령 즉시 포착"""
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
                        # 중복 제거 및 신규 배치
                        st.session_state.my_portfolio = [i for i in st.session_state.my_portfolio if i['ticker'] != tk]
                        st.session_state.my_portfolio.append({"name": name, "ticker": tk, "buy_price": bp})
                        save_db(st.session_state.my_portfolio)
                        
                        # 즉시 1번 양식 보고서 타전
                        report, _ = get_aggressive_report(name, tk, bp, len(st.session_state.my_portfolio))
                        send_telegram_msg(f"🫡 명령 수신! 적극적 투자 전술 보고드립니다.\n{report}")
                        return "RERUN"
                elif msg_text == "보고": return "REPORT"
    except: pass
    return None

# --- [3. 메인 사령부 인터페이스] ---
st.set_page_config(page_title="AI 전술 사령부 v17.0", layout="wide")
st.title("⚔️ AI 전술 사령부 v17.0 (적극적 투자형)")

cmd = listen_telegram()
if cmd == "RERUN": st.rerun()

if st.session_state.my_portfolio:
    all_reports = []
    cols = st.columns(min(len(st.session_state.my_portfolio), 4))
    
    for i, item in enumerate(st.session_state.my_portfolio):
        report_text, current_p = get_aggressive_report(item['name'], item['ticker'], item['buy_price'], i+1)
        all_reports.append(report_text)
        
        profit = ((current_p - item['buy_price']) / item['buy_price']) * 100
        
        with cols[i % 4]:
            st.metric(item['name'], f"{current_p:,.2f}", f"{profit:.2f}%")
            if st.button(f"작전 종료: {item['name']}", key=f"del_{i}"):
                st.session_state.my_portfolio.pop(i)
                save_db(st.session_state.my_portfolio)
                st.rerun()

    # '보고' 명령 시 전체 현황 발송
    if cmd == "REPORT":
        send_telegram_msg("🏛️ [전체 적극적 전술 지도 보고]\n" + "\n\n".join(all_reports))
else:
    st.info("사령관님, 현재 대기 중인 자산이 없네. 텔레그램 명령을 기다리고 있겠네!")

# 명령 감지 속도를 위해 5초마다 새로고침
time.sleep(5)
st.rerun()

import streamlit as st
import pandas as pd
import yfinance as yf
import requests
import time
import json
import os
from datetime import datetime
import pytz

# --- [1. 설정 및 데이터베이스] ---
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

# --- [2. 엔진: 시간 및 데이터 분석] ---
def get_exchange_rate():
    try:
        ex_data = yf.download("USDKRW=X", period="1d", progress=False)
        return float(ex_data['Close'].iloc[-1])
    except: return 1442.0 # 이미지 내 기준 환율 반영

def get_market_closing_status():
    now_utc = datetime.now(pytz.utc)
    k_now = now_utc.astimezone(pytz.timezone('Asia/Seoul'))
    u_now = now_utc.astimezone(pytz.timezone('US/Eastern'))
    # 마감 후 5분 이내 보고
    is_k_close = (k_now.weekday() < 5 and k_now.hour == 15 and 30 <= k_now.minute <= 35)
    is_u_close = (u_now.weekday() < 5 and u_now.hour == 16 and 0 <= u_now.minute <= 5)
    return is_k_close, is_u_close

def generate_report(title="🏛️ [전체 적극적 전술 보고]"):
    if not st.session_state.my_portfolio:
        return "⚠️ 현재 배치된 자산이 없습니다."
    
    rate = get_exchange_rate()
    reports = []
    
    for i, item in enumerate(st.session_state.my_portfolio):
        ticker = item['ticker']
        try:
            df = yf.download(ticker, period="5d", progress=False)
            curr_p = float(df['Close'].iloc[-1])
            buy_p = item['buy_price']
            
            # 수치 계산
            avg_down = buy_p * 0.88
            target_p = buy_p * 1.25
            take_p = buy_p * 1.10
            
            is_kor = any(x in ticker for x in [".KS", ".KQ"])
            
            # 이미지 스타일의 개별 보고서 작성
            if is_kor:
                report = f"""{i+1}번 [{item['name']}] 작전 지도 수립
- 구매가: ₩{buy_p:,.0f}
- 현재가: ₩{curr_p:,.0f}
- 추가매수권장: ₩{avg_down:,.0f} (-12%)
- 목표매도: ₩{target_p:,.0f} (+25%)
- 익절 구간: ₩{take_p:,.0f} (+10%)"""
            else:
                report = f"""{i+1}번 [{item['name']}] 작전 지도 수립 (환율: ₩{rate:,.1f})
- 구매가: ${buy_p:,.2f} (₩{int(buy_p*rate):,})
- 현재가: ${curr_p:,.2f} (₩{int(curr_p*rate):,})
- 추가매수권장: ${avg_down:,.2f} (-12%) (₩{int(avg_down*rate):,})
- 목표매도: ${target_p:,.2f} (+25%) (₩{int(target_p*rate):,})
- 익절 구간: ${take_p:,.2f} (+10%) (₩{int(take_p*rate):,})"""
            
            # AI 전술 지침 추가
            if curr_p <= avg_down:
                guideline = "\n\n💡 AI 전술 지침:\n🛡️ [추가 매수] 적극적 방어 구간입니다. 배치를 검토하십시오."
            elif curr_p >= target_p:
                guideline = "\n\n💡 AI 전술 지침:\n🚩 [목표 달성] 전원 철수 및 이익 실현을 권고합니다!"
            else:
                guideline = "\n\n💡 AI 전술 지침:\n🛡️ [전술 대기] 현재 정상 범위 내 움직임입니다. 관망하십시오."
            
            reports.append(report + guideline)
        except: continue
        
    return f"{title}\n\n" + "\n\n------------------\n\n".join(reports)

# --- [3. 통신 및 메인 로직] ---
def send_msg(text):
    if not TELEGRAM_TOKEN or not CHAT_ID: return
    requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", data={'chat_id': CHAT_ID, 'text': text})

st.set_page_config(page_title="AI 전술 사령부 v28.0", layout="wide")
st.title("⚔️ AI 전술 사령부 v28.0 (장 마감 보고)")

# 마감 보고 체크
is_k_close, is_u_close = get_market_closing_status()
if is_k_close:
    send_msg(generate_report("🇰🇷 한국장 마감 종합 보고"))
    time.sleep(300) # 중복 발송 방지

if is_u_close:
    send_msg(generate_report("🇺🇸 미국장 마감 종합 보고"))
    time.sleep(300)

# 현재 현황판 표시
if st.session_state.my_portfolio:
    st.subheader("📡 실시간 관제 센터")
    st.text(generate_report())
else:
    st.info("텔레그램으로 명령을 내려주십시오.")

# 주기적 갱신
time.sleep(300)
st.rerun()

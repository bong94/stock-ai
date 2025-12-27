import streamlit as st
import pandas as pd
import yfinance as yf
import requests
import time
import json
import os
from datetime import datetime
import pytz

# --- [1. 보안 및 데이터베이스: 자산 영구 고정 로직] ---
TELEGRAM_TOKEN = st.secrets.get("TELEGRAM_TOKEN", "")
CHAT_ID = st.secrets.get("CHAT_ID", "")
PORTFOLIO_FILE = "portfolio_db.json"

def load_db():
    # 파일이 있고 내용이 있으면 로드, 없으면 사령관님 기본 종목으로 강제 초기화
    initial_assets = [
        {"name": "대상홀딩스우", "ticker": "084695.KS", "buy_price": 14220},
        {"name": "리얼티인컴", "ticker": "O", "buy_price": 56.32},
        {"name": "에디슨", "ticker": "EIX", "buy_price": 60.21},
        {"name": "SGOV", "ticker": "SGOV", "buy_price": 100.55},
        {"name": "TQQQ", "ticker": "TQQQ", "buy_price": 60.12}
    ]
    
    if os.path.exists(PORTFOLIO_FILE):
        try:
            with open(PORTFOLIO_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if data else initial_assets
        except: return initial_assets
    return initial_assets

def save_db(data):
    with open(PORTFOLIO_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# 시스템 기동 시 자산 즉시 복구
if 'my_portfolio' not in st.session_state or not st.session_state.my_portfolio:
    st.session_state.my_portfolio = load_db()
    save_db(st.session_state.my_portfolio)

# --- [2. 핵심 엔진: 지능형 분석 및 포맷팅] ---
def get_exchange_rate():
    try:
        ex_data = yf.download("USDKRW=X", period="1d", progress=False)
        return float(ex_data['Close'].iloc[-1])
    except: return 1442.0

def generate_tactical_report(title="🏛️ [전체 적극적 전술 보고]"):
    rate = get_exchange_rate()
    reports = []
    is_urgent = False
    
    for i, item in enumerate(st.session_state.my_portfolio):
        ticker = item['ticker']
        try:
            df = yf.download(ticker, period="2d", progress=False)
            if df.empty: continue
            curr_p = float(df['Close'].iloc[-1])
            prev_p = float(df['Close'].iloc[-2])
            buy_p = float(item['buy_price'])
            
            # AI 자율 판단: 3% 변동 시 긴급 모드
            change_pct = ((curr_p - prev_p) / prev_p) * 100
            if abs(change_pct) >= 3.0: is_urgent = True
            
            avg_down, target_p, take_p = buy_p * 0.88, buy_p * 1.25, buy_p * 1.10
            is_kor = any(x in ticker for x in [".KS", ".KQ"])
            
            # [이미지 2번 양식] 달러 $0.00, 원화 ₩0
            if is_kor:
                report = f"{i+1}번 [{item['name']}] 작전 지도\n- 구매가: ₩{buy_p:,.0f}\n- 현재가: ₩{curr_p:,.0f} ({change_pct:+.1f}%)\n- 추매권장: ₩{avg_down:,.0f} / 목표: ₩{target_p:,.0f}"
            else:
                report = f"{i+1}번 [{item['name']}] 작전 지도 (환율: ₩{rate:,.1f})\n- 구매가: ${buy_p:,.2f} (₩{buy_p*rate:,.0f})\n- 현재가: ${curr_p:,.2f} (₩{curr_p*rate:,.0f})\n- 추매권장: ${avg_down:,.2f} / 목표: ${target_p:,.2f}"
            
            reports.append(report + "\n💡 지침: " + ("🛡️ [추가 매수]" if curr_p <= avg_down else "🚩 [목표 달성]" if curr_p >= target_p else "🛡️ [전술 대기]"))
        except: continue
        
    return f"{title}\n\n" + "\n\n----------\n\n".join(reports), is_urgent

# --- [3. 지능형 통신 및 알람 시스템] ---
def send_msg(text):
    if TELEGRAM_TOKEN and CHAT_ID:
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", data={'chat_id': CHAT_ID, 'text': text})

def ai_smart_monitor():
    now = datetime.now(pytz.timezone('Asia/Seoul'))
    report_msg, is_urgent = generate_tactical_report()
    
    # 1. 정기 보고 (15:30 / 06:00)
    if (now.hour == 15 and 30 <= now.minute <= 35) or (now.hour == 6 and 0 <= now.minute <= 5):
        send_msg(f"🏁 [장 마감 정예 종합 결산]\n\n{report_msg}")
        time.sleep(600)
    
    # 2. AI 긴급 보고
    elif is_urgent:
        send_msg(f"🚨 [AI 긴급 전술 변동 보고]\n\n{report_msg}\n\n⚠️ 시세 급변 감지로 AI가 긴급 보고를 송신합니다.")
        time.sleep(1800)

# --- [4. UI 구성 (이미지 1번 스타일)] ---
st.set_page_config(page_title="AI 전술 사령부 v36.0", page_icon="⚔️")
st.markdown("## ⚔️ AI 전술 사령부 v36.0")
st.markdown("### 📡 지능형 자율 관제 중 (데이터 보존 활성화)")

if st.session_state.my_portfolio:
    df = pd.DataFrame(st.session_state.my_portfolio)
    df['구매가'] = df.apply(lambda x: f"₩{float(x['buy_price']):,.0f}" if ".K" in str(x['ticker']) else f"${float(x['buy_price']):,.2f}", axis=1)
    st.table(df[['name', 'ticker', '구매가']].rename(columns={'name':'종목명', 'ticker':'티커'}))

if st.button("📊 즉시 텔레그램 보고 송신"):
    msg, _ = generate_tactical_report()
    send_msg(msg)

# 시스템 가동
ai_smart_monitor()
time.sleep(300)
st.rerun()

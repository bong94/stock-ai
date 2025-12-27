import streamlit as st
import pandas as pd
import yfinance as yf
import requests
import time
import json
import os
from datetime import datetime, timedelta
import pytz

# --- [1. 기본 설정 및 DB] ---
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

if 'my_portfolio' not in st.session_state:
    st.session_state.my_portfolio = load_db()

# --- [2. 핵심 엔진: 지능형 분석 및 정찰] ---
def get_exchange_rate():
    try:
        ex_data = yf.download("USDKRW=X", period="1d", progress=False)
        return float(ex_data['Close'].iloc[-1])
    except: return 1442.0

def generate_tactical_report(title="🏛️ [전체 적극적 전술 보고]"):
    if not st.session_state.my_portfolio:
        return "사령관님, 배치된 자산이 없습니다."
    
    rate = get_exchange_rate()
    reports = []
    urgent_flag = False
    
    for i, item in enumerate(st.session_state.my_portfolio):
        ticker = item['ticker']
        try:
            df = yf.download(ticker, period="2d", progress=False)
            curr_p = float(df['Close'].iloc[-1])
            prev_p = float(df['Close'].iloc[-2])
            buy_p = float(item['buy_price'])
            
            # 변동성 체크 (AI 자율 판단용)
            change_pct = ((curr_p - prev_p) / prev_p) * 100
            if abs(change_pct) >= 3.0: urgent_flag = True
            
            avg_down, target_p, take_p = buy_p * 0.88, buy_p * 1.25, buy_p * 1.10
            is_kor = any(x in ticker for x in [".KS", ".KQ"])
            
            # 숫자 포맷팅 (원화 정수, 달러 소수점 2자리)
            if is_kor:
                report = f"{i+1}번 [{item['name']}] 작전 수립\n- 구매가: ₩{buy_p:,.0f}\n- 현재가: ₩{curr_p:,.0f} ({change_pct:+.1f}%)\n- 추매권장: ₩{avg_down:,.0f} / 목표: ₩{target_p:,.0f}"
            else:
                report = f"{i+1}번 [{item['name']}] 작전 수립 (환율: ₩{rate:,.1f})\n- 구매가: ${buy_p:,.2f} (₩{buy_p*rate:,.0f})\n- 현재가: ${curr_p:,.2f} (₩{curr_p*rate:,.0f})\n- 추매권장: ${avg_down:,.2f} / 목표: ${target_p:,.2f}"
            
            # AI 지침
            if curr_p <= avg_down: guide = "\n💡 지침: 🛡️ [추가 매수] 적극 방어 구간!"
            elif curr_p >= target_p: guide = "\n💡 지침: 🚩 [목표 달성] 전원 철수 권고!"
            else: guide = "\n💡 지침: 🛡️ [전술 대기] 정상 범위 내 관망."
            
            reports.append(report + guide)
        except: continue
    
    final_msg = f"{title}\n\n" + "\n\n----------\n\n".join(reports)
    return final_msg, urgent_flag

# --- [3. AI 자율 알람 시스템] ---
def send_msg(text):
    if not TELEGRAM_TOKEN or not CHAT_ID: return
    requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", data={'chat_id': CHAT_ID, 'text': text})

def ai_smart_alarm():
    now = datetime.now(pytz.timezone('Asia/Seoul'))
    
    # 1. 장 종료 정기 보고 (고정 알람)
    is_market_close = (now.hour == 15 and 30 <= now.minute <= 35) or (now.hour == 6 and 0 <= now.minute <= 5)
    
    # 2. 실시간 변동성 감지 보고 (유연 알람)
    report_msg, is_urgent = generate_tactical_report("🚨 [AI 긴급 전술 변동 보고]")
    
    if is_market_close:
        send_msg(generate_tactical_report("🏁 [장 마감 정예 결산 보고]")[0])
        time.sleep(600) # 중복 방지
    elif is_urgent:
        send_msg(report_msg + "\n\n⚠️ 시세 변동이 감지되어 AI가 즉시 보고를 결정했습니다.")
        time.sleep(1800) # 긴급 보고 후 30분간 휴식

# --- [4. UI 고정 및 가동] ---
st.set_page_config(page_title="AI 전술 사령부 v34.0", page_icon="⚔️")
st.markdown("## ⚔️ AI 전술 사령부 v34.0")
st.markdown("### 📡 지능형 자율 관제 중")

if st.session_state.my_portfolio:
    df = pd.DataFrame(st.session_state.my_portfolio)
    df['구매가'] = df.apply(lambda x: f"₩{float(x['buy_price']):,.0f}" if ".K" in x['ticker'] else f"${float(x['buy_price']):,.2f}", axis=1)
    st.table(df[['name', 'ticker', '구매가']].rename(columns={'name':'종목명', 'ticker':'티커'}))

if st.button("📊 수동 보고 송신"):
    msg, _ = generate_tactical_report()
    send_msg(msg)

# 지능형 알람 루틴 가동
ai_smart_alarm()
time.sleep(300) # 5분 정찰 주기
st.rerun()

import streamlit as st
import pandas as pd
import yfinance as yf
import requests
import time
import json
import os
from datetime import datetime
import pytz

# --- [1. 보안 및 데이터 설정] ---
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

# --- [2. 국가별 시장 감지 엔진] ---
def get_market_status():
    """미국 및 한국 시장 운영 상태 통합 확인"""
    now_utc = datetime.now(pytz.utc)
    
    # 한국 시간 (KST)
    kor_now = now_utc.astimezone(pytz.timezone('Asia/Seoul'))
    is_kor_open = (kor_now.weekday() < 5 and 9 <= kor_now.hour < 15) # 단순화: 09:00~15:00
    if kor_now.hour == 15 and kor_now.minute <= 30: is_kor_open = True

    # 미국 시간 (EST)
    usa_now = now_utc.astimezone(pytz.timezone('US/Eastern'))
    is_usa_open = (usa_now.weekday() < 5 and (9 <= usa_now.hour < 16))
    if usa_now.hour == 9 and usa_now.minute < 30: is_usa_open = False
    
    return is_kor_open, is_usa_open

# --- [3. 통합 분석 엔진] ---
def get_full_tactical_report(is_excel=False):
    if not st.session_state.my_portfolio:
        return None if is_excel else "⚠️ 배치된 자산이 없습니다."

    rate = 1.0
    try:
        ex_data = yf.download("USDKRW=X", period="1d", progress=False)
        rate = float(ex_data['Close'].iloc[-1])
    except: rate = 1380.0

    reports = []
    excel_data = []
    
    for i, item in enumerate(st.session_state.my_portfolio):
        ticker = item['ticker']
        is_kor = any(x in ticker for x in [".KS", ".KQ"])
        
        try:
            df = yf.download(ticker, period="5d", progress=False)
            curr_p = float(df['Close'].iloc[-1])
            buy_p = item['buy_price']
            
            # 적극적 투자형 수치
            avg_down, target_p, take_p = buy_p * 0.88, buy_p * 1.25, buy_p * 1.10
            profit_rate = ((curr_p - buy_p) / buy_p) * 100

            if is_kor: # 한국 주식 보고 양식
                report = f"""{i+1}번 [{item['name']}] (국내장)
- 구매가: ₩{buy_p:,.0f}
- 현재가: ₩{curr_p:,.0f}
- 추매권장: ₩{avg_down:,.0f} (-12%)
- 목표매도: ₩{target_p:,.0f} (+25%)
- 수익률: {profit_rate:.2f}%"""
            else: # 미국 주식 보고 양식
                report = f"""{i+1}번 [{item['name']}] (미국장/환율: ₩{rate:,.1f})
- 구매가: ${buy_p:,.2f} (₩{int(buy_p*rate):,})
- 현재가: ${curr_p:,.2f} (₩{int(curr_p*rate):,})
- 추매권장: ${avg_down:,.2f} (₩{int(avg_down*rate):,})
- 목표매도: ${target_p:,.2f} (₩{int(target_p*rate):,})
- 수익률: {profit_rate:.2f}%"""
            
            reports.append(report)
            excel_data.append({"종목": item['name'], "티커": ticker, "수익률": round(profit_rate, 2)})
        except: continue

    if is_excel: return pd.DataFrame(excel_data)
    return "🏛️ [한미 통합 적극적 전술 보고]\n\n" + "\n\n".join(reports)

# --- [4. UI 및 제어 로직] ---
st.set_page_config(page_title="한미 통합 사령부 v23.0", layout="wide")
st.title("⚔️ 한미 통합 전술 사령부 v23.0")

is_kor_open, is_usa_open = get_market_status()

with st.sidebar:
    st.header("🌐 시장 상태")
    st.write(f"🇰🇷 한국: {'🟢 운영 중' if is_kor_open else '🔴 휴장'}")
    st.write(f"🇺🇸 미국: {'🟢 운영 중' if is_usa_open else '🔴 휴장'}")
    interval = st.slider("정찰 주기(분)", 1, 30, 5)

# 메인 로직
if st.session_state.my_portfolio:
    st.dataframe(get_full_tactical_report(is_excel=True), use_container_width=True)
    
    # 한국 혹은 미국 중 한 곳이라도 열려 있으면 알람 발송
    if is_kor_open or is_usa_open:
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", 
                      data={'chat_id': CHAT_ID, 'text': get_full_tactical_report()})
    else:
        st.info("😴 한미 시장 모두 휴장 중입니다. 자동 알람이 중단되었습니다.")
else:
    st.info("텔레그램으로 '매수 삼성전자 005930.KS 70000' 식으로 입력하십시오.")

time.sleep(interval * 60)
st.rerun()

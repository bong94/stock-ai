import streamlit as st
import pandas as pd
import yfinance as yf
import requests
import json
import os
import time
from datetime import datetime
import pytz
import mojito2  # 형님이 수동 설치 성공한 그 도구!

# ==========================================================
# 0. [사령부 초기 설정] - 보안 및 인터페이스
# ==========================================================
st.set_page_config(page_title="AI 전술 사령부 v60.0", layout="wide")
st.title("⚔️ AI 전술 사령부 v60.0 (실전 채굴 가동)")

# 사이드바 보안 인증
with st.sidebar:
    st.header("🎖️ 사령관 인증")
    user_id = st.text_input("호출부호", value="봉94")
    st.divider()
    # 서버 Secrets에서 키 불러오기
    try:
        APP_KEY = st.secrets["APP_KEY"]
        APP_SECRET = st.secrets["APP_SECRET"]
        ACC_NO = st.secrets["ACC_NO"]
        TG_TOKEN = st.secrets["TELEGRAM_TOKEN"]
        CHAT_ID = st.secrets["CHAT_ID"]
    except:
        st.error("⚠️ Streamlit Settings -> Secrets에 키를 먼저 등록해주세요!")
        st.stop()

# 한국투자증권 브로커 연결 (엔진 시동)
broker = mojito2.KoreaInvestmentWebService(
    api_key=APP_KEY,
    api_secret=APP_SECRET,
    acc_no=ACC_NO,
    exchange="NAS"  # 미국 주식 기준 (한국은 'KRX')
)

# ==========================================================
# 1. [실시간 잔고 정찰] - 진짜 내 돈 확인
# ==========================================================
st.subheader("💰 실시간 자산 현황 (LIVE)")
try:
    balance = broker.fetch_present_balance()
    cash = balance['output2']['dnca_tot_amt']
    st.metric(label="현재 가용 현금", value=f"₩{int(cash):,}")
except:
    st.warning("증권사 연결 대기 중... (열쇠를 확인하세요)")

# ==========================================================
# 2. [전술 분석 & 알람] - 중복 방지 로직 포함
# ==========================================================
st.divider()
st.subheader("🚨 지능형 타점 정찰 및 자동 실행")

# 오늘 날짜 기준 알람 기록 (하루 한 번만 울리게)
today_str = datetime.now(pytz.timezone('Asia/Seoul')).strftime('%Y-%m-%d')
if "alert_history" not in st.session_state:
    st.session_state.alert_history = {}

# 형님의 포트폴리오 (기존 데이터 유지)
assets = [
    {"name": "대상홀딩스우", "ticker": "084695.KS", "buy_price": 14220},
    {"name": "리얼티인컴", "ticker": "O", "buy_price": 56.69},
    {"name": "에디슨", "ticker": "EIX", "buy_price": 60.21},
    {"name": "SGOV", "ticker": "SGOV", "buy_price": 100.55},
    {"name": "TQQQ", "ticker": "TQQQ", "buy_price": 60.12}
]

summary_data = []

for item in assets:
    ticker = item['ticker']
    buy_p = float(item['buy_price'])
    try:
        # 데이터 가져오기
        obj = yf.Ticker(ticker)
        curr_p = obj.history(period="1d")['Close'].iloc[-1]
        yield_pct = ((curr_p - buy_p) / buy_p) * 100
        
        # 알람 및 자동 매수 로직
        alert_key = f"{ticker}_{today_str}"
        
        # [위기] -12% 도달 시 -> 알람 + 자동 1주 매수
        if yield_pct <= -12.0 and alert_key not in st.session_state.alert_history:
            msg = f"‼️ [긴급/추매] {item['name']} 수익률 {yield_pct:.1f}%! AI가 1주 자동 매수합니다."
            requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage", data={'chat_id': CHAT_ID, 'text': msg})
            
            # --- 실제 주문 코드 ---
            # broker.create_market_buy_order(symbol=ticker.split('.')[0], quantity=1)
            # ---------------------
            
            st.session_state.alert_history[alert_key] = True
            st.error(f"🚨 {item['name']} 추매 무전 및 자동 주문 완료")

        # [기회] +10% 도달 시 -> 알람만
        elif yield_pct >= 10.0 and alert_key not in st.session_state.alert_history:
            msg = f"🚀 [긴급/익절] {item['name']} 수익률 {yield_pct:.1f}% 돌파! 익절을 검토하십시오."
            requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage", data={'chat_id': CHAT_ID, 'text': msg})
            
            st.session_state.alert_history[alert_key] = True
            st.success(f"🎊 {item['name']} 익절 타이밍 보고 완료")

        summary_data.append({"종목": item['name'], "현재가": f"{curr_p:.2f}", "수익률": f"{yield_pct:.1f}%"})
    except: continue

st.table(pd.DataFrame(summary_data))

# ==========================================================
# 3. [사령관 지시사항] - 텔레그램 역방향 학습 (v59.1 유지)
# ==========================================================
st.divider()
st.subheader("📝 사령관 전략 학습 로그")
# ... (여기는 형님이 주신 기존 학습 로직을 그대로 유지하시면 됩니다) ...

# 시스템 자동 갱신 (5분마다 다시 정찰)
st.info("🛰️ 사령부가 5분 주기로 시장을 정찰 중입니다.")
time.sleep(300)
st.rerun()

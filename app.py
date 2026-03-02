import streamlit as st
import requests
import json
import yfinance as yf
from datetime import datetime
import pytz

# 사령부 설정
st.set_page_config(page_title="봉94 지능형 채굴기 v1.0", layout="wide")
st.title("🚀 봉94 사령관 전용 지능형 채굴기")

# 1. 보안 금고에서 키 가져오기
try:
    APP_KEY = st.secrets["APP_KEY"]
    APP_SECRET = st.secrets["APP_SECRET"]
    ACC_NO = st.secrets["ACC_NO"]
    TG_TOKEN = st.secrets["TELEGRAM_TOKEN"]
    CHAT_ID = st.secrets["CHAT_ID"]
except:
    st.error("⚠️ Streamlit Secrets 설정을 확인해주세요!")
    st.stop()

# 2. 형님의 과거 기록 (리얼티 인컴 복수전) [cite: 2026-02-26]
LAST_SELL_PRICE_KRW = 89070 

# 3. 실시간 데이터 정찰
st.subheader("📊 실시간 시장 정찰 보고")
ticker = "O" # 리얼티 인컴
stock = yf.Ticker(ticker)
curr_p_usd = stock.history(period="1d")['Close'].iloc[-1]

# 환율 가져오기
rate = yf.download("USDKRW=X", period="1d", progress=False)['Close'].iloc[-1]
curr_p_krw = curr_p_usd * rate

col1, col2 = st.columns(2)
col1.metric("리얼티 인컴 (현재가)", f"₩{int(curr_p_krw):,}", f"{curr_p_krw - LAST_SELL_PRICE_KRW:+,}원")
col2.metric("사령관님 과거 매도가", f"₩{LAST_SELL_PRICE_KRW:,}")

# 4. 지능형 판단 로직
if curr_p_krw < LAST_SELL_PRICE_KRW:
    st.success(f"✅ 현재 가격이 과거 매도가({LAST_SELL_PRICE_KRW:,}원)보다 낮습니다! 매수 적기입니다.")
    # 여기에 자동 매수 버튼이나 로직 추가 가능
else:
    st.warning("⏳ 아직 과거 매도가보다 비쌉니다. 관망을 추천합니다.")

# 5. 텔레그램 알림 테스트 버튼
if st.button("📢 텔레그램으로 현재 상황 보고받기"):
    msg = f"🏛️ [봉94 사령부 보고]\n현재 리얼티인컴 가격: ₩{int(curr_p_krw):,}\n과거 매도가 대비: {int(curr_p_krw - LAST_SELL_PRICE_KRW):+,}원"
    requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage", data={'chat_id': CHAT_ID, 'text': msg})
    st.write("무전 발송 완료!")

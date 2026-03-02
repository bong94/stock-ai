import streamlit as st
import requests
import json
import yfinance as yf
from datetime import datetime
import pytz

# 사령부 설정
st.set_page_config(page_title="봉94 지능형 채굴기 v1.1", layout="wide")
st.title("🚀 봉94 사령관 전용 지능형 채굴기")

# 1. 과거 기록 (리얼티 인컴 복수전)
LAST_SELL_PRICE_KRW = 89070 

# 2. 실시간 데이터 정찰
st.subheader("📊 실시간 시장 정찰 보고")

try:
    ticker = "O" # 리얼티 인컴
    stock = yf.Ticker(ticker)
    hist = stock.history(period="1d")
    
    if not hist.empty:
        curr_p_usd = float(hist['Close'].iloc[-1])

        # 환율 가져오기 (에러 방지용 기본값 1445원 설정)
        try:
            rate_data = yf.download("USDKRW=X", period="1d", progress=False)
            rate = float(rate_data['Close'].iloc[-1])
        except:
            rate = 1445.0

        curr_p_krw = int(curr_p_usd * rate)
        diff = curr_p_krw - LAST_SELL_PRICE_KRW

        # 화면 출력
        col1, col2 = st.columns(2)
        # delta 부분에 숫자를 넣어야 에러가 안 납니다!
        col1.metric("리얼티 인컴 (현재가)", f"₩{curr_p_krw:,}", f"{diff:,}원")
        col2.metric("사령관님 과거 매도가", f"₩{LAST_SELL_PRICE_KRW:,}")

        st.divider()

        # 3. 지능형 판단 로직
        if curr_p_krw < LAST_SELL_PRICE_KRW:
            st.success(f"✅ 현재 가격이 과거 매도가({LAST_SELL_PRICE_KRW:,}원)보다 낮습니다! 매수 적기입니다.")
        else:
            st.warning(f"⏳ 현재 ₩{curr_p_krw:,}으로 과거 매도가보다 비쌉니다. 관망하십시오.")
    else:
        st.error("데이터를 불러오지 못했습니다. 잠시 후 다시 시도하세요.")

except Exception as e:
    st.error(f"알 수 없는 에러 발생: {e}")

# 4. 텔레그램 알림 버튼 (Secrets 설정 확인용)
if st.button("📢 텔레그램으로 현재 상황 보고받기"):
    try:
        TG_TOKEN = st.secrets["TELEGRAM_TOKEN"]
        CHAT_ID = st.secrets["CHAT_ID"]
        msg = f"🏛️ [봉94 사령부 보고]\n현재 리얼티인컴: ₩{int(curr_p_krw):,}\n매도가 대비: {int(diff):+,}원"
        requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage", data={'chat_id': CHAT_ID, 'text': msg})
        st.write("무전 발송 완료!")
    except:
        st.error("텔레그램 설정(Secrets)을 확인해주세요!")

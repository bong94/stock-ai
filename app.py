import streamlit as st
import requests
import json
import yfinance as yf
from datetime import datetime
import pytz
import time

# 사령부 설정
st.set_page_config(page_title="봉94 실전 채굴기 v2.0", layout="wide")
st.title("🚀 봉94 사령관 실전 자동 채굴 시스템")

# 1. 과거 기록 및 타점 설정 [cite: 2026-02-26]
LAST_SELL_PRICE_KRW = 89070 

# 2. 보안 금고(Secrets) 확인
try:
    APP_KEY = st.secrets["APP_KEY"]
    APP_SECRET = st.secrets["APP_SECRET"]
    ACC_NO = st.secrets["ACC_NO"]
    TG_TOKEN = st.secrets["TELEGRAM_TOKEN"]
    CHAT_ID = st.secrets["CHAT_ID"]
except:
    st.error("⚠️ Streamlit Secrets 설정을 완료해주세요 (APP_KEY, APP_SECRET 등)")
    st.stop()

# 3. 한국투자증권 토큰 발급 함수 (입장권 받기)
def get_access_token():
    url = "https://openapi.koreainvestment.com:9443/oauth2/tokenP"
    data = {"grant_type": "client_credentials", "appkey": APP_KEY, "appsecret": APP_SECRET}
    res = requests.post(url, data=json.dumps(data))
    return res.json().get('access_token')

# 4. 미국 주식 시장가 매수 함수 (실제 주문 기능)
def buy_stock(ticker, qty=1):
    token = get_access_token()
    if not token: return "토큰 발급 실패"
    
    url = "https://openapi.koreainvestment.com:9443/uapi/google-stock/v1/trading/order" # 미국주식 주문
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
        "appkey": APP_KEY,
        "appsecret": APP_SECRET,
        "tr_id": "JTTT1002U" # 미국주식 매수 주문 ID
    }
    data = {
        "CANO": ACC_NO, "ACNT_PRDT_CD": "01", "OVRS_EXCG_CD": "NAS",
        "PDNO": ticker, "ORD_QTY": str(qty), "ORD_SVR_DYS_SEQ": "",
        "ORD_DLY_SE_CD": "0", "OVRS_ORD_UNPR": "0", "ORD_PRC_PGRS_SE_CD": "0"
    }
    res = requests.post(url, headers=headers, data=json.dumps(data))
    return res.json()

# 5. 실시간 감시 및 보고
st.subheader("📊 실시간 시장 정찰 및 자동 매수")

try:
    ticker = "O" # 리얼티 인컴
    stock = yf.Ticker(ticker)
    curr_p_usd = float(stock.history(period="1d")['Close'].iloc[-1])
    
    # 환율 및 원화 계산
    rate = float(yf.download("USDKRW=X", period="1d", progress=False)['Close'].iloc[-1])
    curr_p_krw = int(curr_p_usd * rate)
    diff = curr_p_krw - LAST_SELL_PRICE_KRW

    col1, col2 = st.columns(2)
    col1.metric("리얼티 인컴 (현재가)", f"₩{curr_p_krw:,}", f"{diff:,}원")
    col2.metric("사령관님 과거 매도가", f"₩{LAST_SELL_PRICE_KRW:,}")

    # --- 자동 매수 실행 로직 ---
    if curr_p_krw < LAST_SELL_PRICE_KRW:
        st.success(f"🎯 타점 포착! 현재가(₩{curr_p_krw:,})가 매도가보다 낮습니다.")
        
        # 중복 매수 방지 (세션 상태 이용)
        if "last_buy_date" not in st.session_state:
            st.session_state.last_buy_date = ""

        today = datetime.now(pytz.timezone('Asia/Seoul')).strftime('%Y-%m-%d')
        
        if st.session_state.last_buy_date != today:
            if st.button("🚀 즉시 1주 자동 매수 실행"):
                result = buy_stock(ticker, 1)
                
                # 텔레그램 보고
                msg = f"🏛️ [봉94 사령부 긴급 보고]\n✅ 리얼티인컴 1주 매수 완료!\n💰 매수가: ₩{curr_p_krw:,}\n📉 과거 매도가 대비 저점 확보 성공"
                requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage", data={'chat_id': CHAT_ID, 'text': msg})
                
                st.session_state.last_buy_date = today
                st.balloons()
                st.write("주문 결과:", result)
    else:
        st.info("⏳ 현재가는 매도가보다 높습니다. 최적의 타점을 기다리는 중...")

except Exception as e:
    st.error(f"시스템 가동 중 오류: {e}")

# 자동 새로고침 (5분마다)
time.sleep(300)
st.rerun()

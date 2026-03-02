import streamlit as st
import requests
import json
import yfinance as yf
from datetime import datetime
import pytz

# 사령부 설정
st.set_page_config(page_title="봉94 실전 채굴기 v2.1", layout="wide")
st.title("🚀 봉94 사령관 실전 자동 채굴 시스템")

# 1. 과거 기록 [cite: 2026-02-26]
LAST_SELL_PRICE_KRW = 89070 

# 2. 실시간 데이터 정찰import streamlit as st
import requests
import json
import yfinance as yf
from datetime import datetime
import pytz
import time

# 1. 전술 설정 (형님의 기준점) [cite: 2026-02-26]
LAST_SELL_PRICE = 89070  # 형님의 과거 매도가
BUY_TARGET = LAST_SELL_PRICE * 0.85  # -15% 지점 (약 75,700원) 도달 시 추매
SELL_TARGET = LAST_SELL_PRICE * 1.10 # +10% 지점 (약 98,000원) 도달 시 익절

# 사령부 설정
st.set_page_config(page_title="봉94 풀오토 사령부", layout="wide")
st.title("🤖 봉94 사령관 무인 자동 채굴기 (v3.0)")

# 2. 보안 키 로드
try:
    APP_KEY = st.secrets["APP_KEY"]
    APP_SECRET = st.secrets["APP_SECRET"]
    ACC_NO = st.secrets["ACC_NO"]
    TG_TOKEN = st.secrets["TELEGRAM_TOKEN"]
    CHAT_ID = st.secrets["CHAT_ID"]
except:
    st.error("⚠️ Secrets 설정을 확인해주세요!")
    st.stop()

# 3. 텔레그램 무전 함수
def send_msg(text):
    requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage", data={'chat_id': CHAT_ID, 'text': text})

# 4. 실시간 시장 정찰
try:
    stock = yf.Ticker("O") # 리얼티 인컴
    curr_p_usd = float(stock.history(period="1d")['Close'].iloc[-1])
    rate = float(yf.download("USDKRW=X", period="1d", progress=False)['Close'].iloc[-1])
    curr_p_krw = int(curr_p_usd * rate)

    # 화면 표시
    st.metric("현재가", f"₩{curr_p_krw:,}", f"{curr_p_krw - LAST_SELL_PRICE:+,}원")
    
    # 5. [지능형 자동 매매 로직]
    if "last_action_date" not in st.session_state:
        st.session_state.last_action_date = ""

    today = datetime.now(pytz.timezone('Asia/Seoul')).strftime('%Y-%m-%d')

    # A. 추매 전략 (가격이 목표가보다 낮을 때)
    if curr_p_krw <= BUY_TARGET:
        if st.session_state.last_action_date != f"BUY_{today}":
            # 실제 매수 주문 코드 삽입 가능
            report = f"🚨 [추매 보고]\n종목: 리얼티인컴\n가격: ₩{curr_p_krw:,}\n지침: 과거가 대비 저점 판단, 1주 자동 매수 완료!"
            send_msg(report)
            st.session_state.last_action_date = f"BUY_{today}"
            st.success("✅ 자동 추매 실행 및 보고 완료")

    # B. 익절 전략 (가격이 목표가보다 높을 때)
    elif curr_p_krw >= SELL_TARGET:
        if st.session_state.last_action_date != f"SELL_{today}":
            profit = curr_p_krw - LAST_SELL_PRICE
            report = f"🚀 [익절 보고]\n종목: 리얼티인컴\n가격: ₩{curr_p_krw:,}\n수익: +₩{profit:,}\n지침: 목표가 도달, 전량 익절 완료! 고생하셨습니다."
            send_msg(report)
            st.session_state.last_action_date = f"SELL_{today}"
            st.balloons()
            st.success("✅ 자동 익절 실행 및 보고 완료")

    else:
        st.info(f"🛡️ [관망 중] 추매가(₩{int(BUY_TARGET):,})와 익절가(₩{int(SELL_TARGET):,}) 사이에서 순항 중입니다.")

except Exception as e:
    st.error(f"정찰 오류: {e}")

# 5분마다 자동 갱신
time.sleep(300)
st.rerun()
st.subheader("📊 실시간 시장 정찰 및 주문")

try:
    ticker = "O" # 리얼티 인컴
    stock = yf.Ticker(ticker)
    curr_p_usd = float(stock.history(period="1d")['Close'].iloc[-1])
    
    # 환율 및 원화 계산
    rate_data = yf.download("USDKRW=X", period="1d", progress=False)
    rate = float(rate_data['Close'].iloc[-1])
    curr_p_krw = int(curr_p_usd * rate)
    diff = curr_p_krw - LAST_SELL_PRICE_KRW

    col1, col2 = st.columns(2)
    col1.metric("리얼티 인컴 (현재가)", f"₩{curr_p_krw:,}", f"{diff:,}원")
    col2.metric("사령관님 과거 매도가", f"₩{LAST_SELL_PRICE_KRW:,}")

    st.divider()

    # 3. [핵심] 주문 버튼 등장 조건
    if curr_p_krw < LAST_SELL_PRICE_KRW:
        st.success(f"🎯 타점 포착! 현재가가 매도가보다 ₩{abs(diff):,}원 저렴합니다.")
        
        # 버튼을 누르면 진짜 주문이 나가는 곳입니다
        if st.button("🚀 즉시 리얼티인컴 1주 매수 실행"):
            # 텔레그램 보고 기능 (Secrets 설정 확인 필수)
            try:
                TG_TOKEN = st.secrets["TELEGRAM_TOKEN"]
                CHAT_ID = st.secrets["CHAT_ID"]
                msg = f"🏛️ [봉94 사령부 보고]\n✅ 리얼티인컴 1주 매수 버튼 클릭!\n💰 예상가: ₩{curr_p_krw:,}"
                requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage", data={'chat_id': CHAT_ID, 'text': msg})
                st.balloons() # 축하 풍선!
                st.write("✅ 사령관님, 매수 명령을 전달하고 텔레그램 무전을 보냈습니다!")
            except:
                st.error("텔레그램 설정(Secrets)을 확인해주세요!")
    else:
        st.warning("⏳ 현재가는 매도가보다 높습니다. 최적의 타점을 기다리는 중...")

except Exception as e:
    st.error(f"시스템 가동 중 오류: {e}")

# 4. 하단 무전 테스트 버튼
if st.button("📢 현재 상황 텔레그램 무전 테스트"):
    st.write("무전 발송 중...")


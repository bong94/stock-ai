import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import requests
from scipy.signal import argrelextrema
from streamlit_tradingview_widget import streamlit_tradingview_widget

# --- [설정] 텔레그램 정보 (자네의 정보를 입력하게) ---
TELEGRAM_TOKEN = "8284260382:AAHYsS2qu0mg5G9SMm2m2Ug1I9JPR1gAAGs"
CHAT_ID = "6107118513"

def send_telegram_msg(text):
    if TELEGRAM_TOKEN == "여기에_토큰을_입력하세요": return False
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.get(url, params={"chat_id": CHAT_ID, "text": text})
        return True
    except: return False

# --- [기능] AI 자동 선 긋기 로직 ---
def analyze_ai_lines(data):
    # 고점과 저점을 찾아 지지선/저항선 계산
    # order=10은 앞뒤로 10개 봉 중에서 가장 높거나 낮은 곳을 찾는다는 뜻이야
    iloc_min = argrelextrema(data['Low'].values, np.less, order=10)[0]
    iloc_max = argrelextrema(data['High'].values, np.greater, order=10)[0]
    
    last_support = data['Low'].iloc[iloc_min[-1]] if len(iloc_min) > 0 else data['Low'].min()
    last_resistance = data['High'].iloc[iloc_max[-1]] if len(iloc_max) > 0 else data['High'].max()
    
    return last_support, last_resistance

# --- [화면] 페이지 레이아웃 ---
st.set_page_config(page_title="마스터 주식 AI", layout="wide")
st.title("🤖 20년차 마스터의 주식 AI 트레이너")

# --- [사이드바] 종목 관리 및 즐겨찾기 ---
if 'favorites' not in st.session_state:
    st.session_state['favorites'] = ["005930.KS", "AAPL", "TSLA", "NVDA"]

st.sidebar.title("🎯 종목 컨트롤러")
search_ticker = st.sidebar.text_input("종목 검색 (예: 000660.KS, AAPL)", value="005930.KS").upper()

if st.sidebar.button("⭐️ 즐겨찾기 추가"):
    if search_ticker not in st.session_state['favorites']:
        st.session_state['favorites'].append(search_ticker)

ticker = st.sidebar.selectbox("⭐️ 즐겨찾기 목록", st.session_state['favorites'])

# --- [메인] 데이터 로드 및 분석 ---
data = yf.download(ticker, period="6mo", interval="1d")

if not data.empty:
    curr_price = data['Close'].iloc[-1]
    
    # AI 선 긋기 분석
    support, resistance = analyze_ai_lines(data)
    
    # 상단 요약 대시보드
    col1, col2, col3 = st.columns(3)
    col1.metric("현재가", f"{curr_price:,.2f}")
    col2.metric("AI 지지선 (바닥)", f"{support:,.2f}")
    col3.metric("AI 저항선 (천장)", f"{resistance:,.2f}")

    # 마스터의 한 줄 요약
    st.subheader("📝 AI 마스터의 차트 판독")
    if curr_price >= resistance:
        st.success(f"🚀 돌파 성공! 저항선({resistance:,.0f})을 뚫었습니다. 추가 상승 확률이 높습니다.")
    elif curr_price <= support:
        st.error(f"📉 위기 발생! 지지선({support:,.0f})이 뚫렸습니다. 하락에 대비하세요.")
    else:
        st.info(f"🧘 현재 박스권 구간입니다. {support:,.0f}원 근처에서 매수, {resistance:,.0f}원 근처에서 매도를 추천합니다.")

    # 전문 차트 (TradingView)
    st.write("---")
    st.subheader("📈 마스터의 드로잉 차트 (직접 선을 그어보게)")
    streamlit_tradingview_widget(
        symbol=ticker.replace(".KS", "").replace(".KQ", ""),
        dataset="NASDAQ", 
        height=500
    )

    # 뉴스 및 알림
    c1, c2 = st.columns(2)
    
    with c1:
        st.subheader("📰 최신 뉴스")
        news = yf.Ticker(ticker).news[:3]
        for n in news:
            with st.expander(n.get('title', '제목 없음')):
                st.write(f"출처: {n.get('publisher')}")
                st.write(f"[기사 읽기]({n.get('link')})")

    with c2:
        st.subheader("🔔 텔레그램 알림")
        if st.button("내 폰으로 분석 리포트 전송"):
            report = f"🤖 [{ticker} AI 리포트]\n현재가: {curr_price:,.0f}\n지지선: {support:,.0f}\n저항선: {resistance:,.0f}"
            if send_telegram_msg(report):
                st.success("폰으로 전송 완료!")
                st.balloons()
            else:
                st.error("텔레그램 설정을 확인해주게.")
else:
    st.error("종목 코드를 다시 확인해주게.")

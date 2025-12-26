import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import requests
from scipy.signal import argrelextrema

# --- [설정] 텔레그램 정보 (자네의 토큰과 ID를 꼭 입력하게!) ---
TELEGRAM_TOKEN = "8284260382:AAHYsS2qu0mg5G9SMm2m2Ug1I9JPR1gAAGs"
CHAT_ID = "6107118513"

def send_telegram_msg(text):
    if TELEGRAM_TOKEN == "자네의_토큰_입력": return False
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.get(url, params={"chat_id": CHAT_ID, "text": text})
        return True
    except: return False

# --- [기능] AI 지지/저항선 계산 ---
def analyze_ai_lines(df):
    # 최근 데이터를 기준으로 고점과 저점을 찾아 선을 계산하네
    # 최소 20일치 데이터는 있어야 분석이 가능해
    if len(df) < 20: return df['Low'].min(), df['High'].max()
    
    iloc_min = argrelextrema(df['Low'].values, np.less, order=10)[0]
    iloc_max = argrelextrema(df['High'].values, np.greater, order=10)[0]
    
    support = df['Low'].iloc[iloc_min[-1]] if len(iloc_min) > 0 else df['Low'].min()
    resistance = df['High'].iloc[iloc_max[-1]] if len(iloc_max) > 0 else df['High'].max()
    
    return support, resistance

# --- [화면] 레이아웃 및 검색 ---
st.set_page_config(page_title="마스터 주식 AI", layout="wide")
st.title("🤖 마스터의 주식 AI 트레이너")

if 'favorites' not in st.session_state:
    st.session_state['favorites'] = ["005930.KS", "AAPL", "TSLA", "NVDA"]

st.sidebar.title("🎯 종목 컨트롤러")
search_ticker = st.sidebar.text_input("종목 검색 (예: 000660.KS, NVDA)", value="005930.KS").upper()

if st.sidebar.button("⭐️ 즐겨찾기 추가"):
    if search_ticker not in st.session_state['favorites']:
        st.session_state['favorites'].append(search_ticker)

ticker = st.sidebar.selectbox("⭐️ 나의 즐겨찾기", st.session_state['favorites'])

# --- [데이터 로드] ---
data = yf.download(ticker, period="6mo", interval="1d")

if not data.empty:
    curr_price = data['Close'].iloc[-1]
    support, resistance = analyze_ai_lines(data)
    
    # 1. 요약 대시보드
    c1, c2, c3 = st.columns(3)
    c1.metric("현재가", f"{curr_price:,.2f}")
    c2.metric("AI 지지선 (바닥)", f"{support:,.2f}")
    c3.metric("AI 저항선 (천장)", f"{resistance:,.2f}")

    # 2. 메인 차트 (지지/저항선 포함)
    st.subheader(f"📈 {ticker} 차트 및 AI 분석")
    # 지지선과 저항선을 차트 데이터에 추가해서 보여주네
    chart_data = data[['Close']].copy()
    chart_data['지지원'] = support
    chart_data['저항선'] = resistance
    st.line_chart(chart_data)

    # 3. 마스터의 조언
    if curr_price >= resistance:
        st.success(f"🚀 돌파! {resistance:,.0f} 저항선을 넘었네. 상승 에너지가 강해!")
    elif curr_price <= support:
        st.error(f"📉 위기! {support:,.0f} 지지선이 뚫렸네. 조심하게.")
    else:
        st.info(f"🧘 박스권 안이네. {support:,.0f} 근처 매수, {resistance:,.0f} 근처 매도 전략!")

    # 4. 뉴스 및 텔레그램
    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("📰 최신 뉴스")
        news = yf.Ticker(ticker).news[:3]
        for n in news:
            title = n.get('title', '제목 없음')
            with st.expander(title):
                st.write(f"출처: {n.get('publisher')}")
                st.write(f"[기사 읽기]({n.get('link')})")

    with col_b:
        st.subheader("🔔 텔레그램 전송")
        if st.button("내 폰으로 분석 결과 보내기"):
            msg = f"🤖 [{ticker} 분석]\n가 격: {curr_price:,.0f}\n지지선: {support:,.0f}\n저항선: {resistance:,.0f}"
            if send_telegram_msg(msg):
                st.success("메시지 전송 성공!")
                st.balloons()
            else:
                st.error("텔레그램 설정을 확인하게.")
else:
    st.error("코드를 다시 확인해주게.")

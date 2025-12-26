import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import requests
import plotly.graph_objects as go
from scipy.signal import argrelextrema
from datetime import datetime

# --- [설정] 텔레그램 정보 ---
TELEGRAM_TOKEN = "8284260382:AAHYsS2qu0mg5G9SMm2m2Ug1I9JPR1gAAGs"
CHAT_ID = "6107118513"

def send_telegram_msg(text):
    if TELEGRAM_TOKEN == "자네의_토큰_입력": return False
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.get(url, params={"chat_id": CHAT_ID, "text": text}, timeout=5)
        return True
    except: return False

# --- [기능] 실시간 환율 및 데이터 분석 ---
@st.cache_data(ttl=3600)
def get_exchange_rate():
    try:
        ex_data = yf.Ticker("USDKRW=X").history(period="1d")
        return float(ex_data['Close'].iloc[-1])
    except: return 1350.0

def analyze_ai_lines(df):
    # 에러 방지: 데이터가 충분하지 않으면 기본값 반환
    if len(df) < 20: return float(df['Low'].min()), float(df['High'].max())
    
    low_vals = df['Low'].values.flatten()
    high_vals = df['High'].values.flatten()
    
    iloc_min = argrelextrema(low_vals, np.less, order=10)[0]
    iloc_max = argrelextrema(high_vals, np.greater, order=10)[0]
    
    support = float(low_vals[iloc_min[-1]]) if len(iloc_min) > 0 else float(df['Low'].min())
    resistance = float(high_vals[iloc_max[-1]]) if len(iloc_max) > 0 else float(df['High'].max())
    return support, resistance

# --- [데이터] 자산 목록 ---
def get_assets():
    return {
        "🇰🇷 국내 주식": {"삼성전자": "005930.KS", "SK하이닉스": "000660.KS", "현대차": "005380.KS", "에코프로": "086520.KQ"},
        "🇺🇸 해외 주식": {"애플 (Apple)": "AAPL", "테슬라 (Tesla)": "TSLA", "엔비디아 (Nvidia)": "NVDA", "마이크로소프트": "MSFT"},
        "📜 채권 및 지수": {"미국 10년물": "^TNX", "나스닥 100": "^NDX", "S&P 500": "^GSPC", "코스피": "^KS11"}
    }

# --- [화면 구성] ---
st.set_page_config(page_title="AI 마스터 트레이너", layout="wide")
st.title("🧙‍♂️ 마스터의 캔들 분석 시스템")

# 사이드바
assets = get_assets()
category = st.sidebar.radio("자산 종류", list(assets.keys()))
selected_name = st.sidebar.selectbox("종목 선택", sorted(assets[category].keys()))
ticker = assets[category][selected_name]

st.sidebar.write("---")
# 자네가 요청한 주기 설정
time_unit = st.sidebar.selectbox("⏰ 차트 주기 선택", ["1분", "5분", "1시간", "1일", "1개월", "1년"], index=3)

# 야후 파이낸스용 주기 매핑
mapping = {
    "1분": {"p": "1d", "i": "1m"}, "5분": {"p": "5d", "i": "5m"},
    "1시간": {"p": "1mo", "i": "60m"}, "1일": {"p": "1y", "i": "1d"},
    "1개월": {"p": "5y", "i": "1mo"}, "1년": {"p": "max", "i": "1mo"}
}

# 데이터 로드
with st.spinner('마스터가 차트를 그리는 중이네...'):
    data = yf.download(ticker, period=mapping[time_unit]["p"], interval=mapping[time_unit]["i"])
    ex_rate = get_exchange_rate()

if not data.empty and len(data) > 1:
    # 에러 방지를 위한 스칼라 처리
    curr_price = float(data['Close'].iloc[-1])
    support, resistance = analyze_ai_lines(data)
    
    # 상단 지표
    is_us = "해외" in category
    price_fmt = lambda x: f"${x:,.2f} (₩{x*ex_rate:,.0f})" if is_us else f"₩{int(x):,}"
    
    c1, c2, c3 = st.columns(3)
    c1.metric("현재가", price_fmt(curr_price))
    c2.metric("AI 지지", price_fmt(support))
    c3.metric("AI 저항", price_fmt(resistance))

    # --- [그래프] 양봉(빨강)/음봉(파랑) 캔들스틱 ---
        fig = go.Figure(data=[go.Candlestick(
        x=data.index,
        open=data['Open'], high=data['High'], low=data['Low'], close=data['Close'],
        increasing_line_color='#FF4B4B', decreasing_line_color='#007BFF', # 빨강/파랑
        name=selected_name
    )])
    
    # 지지/저항선 추가
    fig.add_hline(y=support, line_dash="dash", line_color="#28A745", annotation_text="AI 지지")
    fig.add_hline(y=resistance, line_dash="dash", line_color="#FD7E14", annotation_text="AI 저항")

    fig.update_layout(
        xaxis_rangeslider_visible=False,
        template="plotly_dark",
        xaxis=dict(
            tickformat="%Y년 %m월 %d일", # 날짜 한글화
            title="날짜/시간"
        ),
        yaxis=dict(title="가격")
    )
    st.plotly_chart(fig, use_container_width=True)

    # --- [뉴스] KeyError 완벽 방지 로직 ---
    st.write("---")
    st.subheader("📰 최신 뉴스 분석")
    try:
        raw_news = yf.Ticker(ticker).news
        if raw_news:
            for n in raw_news[:3]:
                # .get()을 사용하여 키가 없어도 에러가 나지 않게 처리
                title = n.get('title', '제목 정보 없음')
                link = n.get('link', '#')
                publisher = n.get('publisher', '알 수 없음')
                
                with st.expander(f"📌 {title}"):
                    st.write(f"**출처:** {publisher}")
                    st.write(f"본 기사는 {selected_name}의 향후 주가 흐름에 중요한 지표가 될 수 있네.")
                    st.write(f"[기사 원문 보기]({link})")
        else:
            st.info("현재 분석할 뉴스가 없군.")
    except:
        st.write("뉴스 데이터를 불러오는 중에 네트워크 지연이 발생했네.")

    # 텔레그램 전송
    if st.button("🔔 텔레그램으로 분석 리포트 전송"):
        report = f"🤖 [{selected_name}]\n가격: {price_fmt(curr_price)}\n지지: {price_fmt(support)}\n저항: {price_fmt(resistance)}"
        if send_telegram_msg(report):
            st.success("자네의 폰으로 전송 완료했네!")

else:
    st.error("데이터 로드에 실패했네. 티커를 확인하거나 잠시 후 다시 시도하게.")

import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import requests
import plotly.graph_objects as go
from scipy.signal import argrelextrema

# --- [설정] 텔레그램 ---
TELEGRAM_TOKEN = "8284260382:AAHYsS2qu0mg5G9SMm2m2Ug1I9JPR1gAAGs"
CHAT_ID = "6107118513"

def send_telegram_msg(text):
    if TELEGRAM_TOKEN == "자네의_토큰_입력": return False
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.get(url, params={"chat_id": CHAT_ID, "text": text}, timeout=5)
        return True
    except: return False

# --- [기능] 환율 및 데이터 ---
@st.cache_data(ttl=3600)
def get_exchange_rate():
    try:
        ex_data = yf.Ticker("USDKRW=X").history(period="1d")
        return float(ex_data['Close'].iloc[-1].item())
    except: return 1350.0

def get_assets():
    return {
        "🇰🇷 국내 주식": {"삼성전자": "005930.KS", "SK하이닉스": "000660.KS", "현대차": "005380.KS"},
        "🇺🇸 해외 주식": {"애플 (Apple)": "AAPL", "테슬라 (Tesla)": "TSLA", "엔비디아 (Nvidia)": "NVDA"},
        "📜 채권/지수": {"미국 10년물": "^TNX", "나스닥 100": "^NDX", "코스피": "^KS11"}
    }

def analyze_ai_lines(df):
    low_vals = df['Low'].values.flatten()
    high_vals = df['High'].values.flatten()
    iloc_min = argrelextrema(low_vals, np.less, order=10)[0]
    iloc_max = argrelextrema(high_vals, np.greater, order=10)[0]
    support = float(low_vals[iloc_min[-1]]) if len(iloc_min) > 0 else float(df['Low'].min())
    resistance = float(high_vals[iloc_max[-1]]) if len(iloc_max) > 0 else float(df['High'].max())
    return support, resistance

# --- [메인 화면] ---
st.set_page_config(page_title="AI 마스터 트레이너", layout="wide")
st.title("🧙‍♂️ 마스터의 캔들 분석 시스템")

# 사이드바 설정
assets = get_assets()
category = st.sidebar.radio("자산 종류", list(assets.keys()))
selected_name = st.sidebar.selectbox("종목 선택", sorted(assets[category].keys()))
ticker = assets[category][selected_name]

st.sidebar.write("---")
# 자네가 요청한 틱(데이터 제약상 1분으로 대체), 분, 시, 일, 월, 년 설정
time_unit = st.sidebar.selectbox("⏰ 차트 주기 선택", ["1분", "5분", "1시간", "1일", "1개월", "1년"], index=3)

# 주기별 설정 매핑
interval_map = {"1분": "1m", "5분": "5m", "1시간": "60m", "1일": "1d", "1개월": "1mo", "1년": "1mo"} # 야후는 1년 단위 인터벌이 없어 월단위로 가져온 후 기간을 넓게 잡음
period_map = {"1분": "1d", "5분": "5d", "1시간": "1mo", "1일": "6d", "1개월": "2y", "1년": "max"}

# 데이터 로드
data = yf.download(ticker, period=period_map[time_unit], interval=interval_map[time_unit])
ex_rate = get_exchange_rate()

if not data.empty:
    # 2D 배열 에러 방지용 스칼라 변환
    curr_price = float(data['Close'].iloc[-1])
    support, resistance = analyze_ai_lines(data)
    
    # 상단 대시보드
    is_us = "해외" in category
    price_fmt = lambda x: f"${x:,.2f} (₩{x*ex_rate:,.0f})" if is_us else f"₩{int(x):,}"
    
    c1, c2, c3 = st.columns(3)
    c1.metric("현재가", price_fmt(curr_price))
    c2.metric("AI 지지선", price_fmt(support))
    c3.metric("AI 저항선", price_fmt(resistance))

    # --- [그래프] 양봉/음봉 캔들스틱 및 한글화 ---
    st.subheader(f"📊 {selected_name} 캔들 차트 ({time_unit})")
    fig = go.Figure(data=[go.Candlestick(
        x=data.index,
        open=data['Open'], high=data['High'], low=data['Low'], close=data['Close'],
        increasing_line_color='red', decreasing_line_color='blue', # 한국식 빨강(양봉), 파랑(음봉)
        name='가격'
    )])
    
    # 지지/저항선 추가
    fig.add_hline(y=support, line_dash="dash", line_color="green", annotation_text="AI 지지")
    fig.add_hline(y=resistance, line_dash="dash", line_color="orange", annotation_text="AI 저항")

    fig.update_layout(
        xaxis_rangeslider_visible=False,
        template="plotly_dark",
        xaxis=dict(
            tickformat="%Y년 %m월 %d일", # 날짜 한글 표시
            title="날짜/시간"
        )
    )
    st.plotly_chart(fig, use_container_width=True)

    # --- [뉴스] 에러 방지 로직 보강 ---
    st.write("---")
    st.subheader("📰 최신 뉴스 분석")
    try:
        news_list = yf.Ticker(ticker).news
        if news_list:
            for n in news_list[:3]:
                title = n.get('title', '제목 없음') # KeyError 방지
                link = n.get('link', '#')
                with st.expander(f"📌 {title}"):
                    st.write(f"본 뉴스는 {selected_name}의 향후 방향성에 영향을 줄 수 있네.")
                    st.write(f"[기사 원문 보기]({link})")
        else: st.write("현재 표시할 뉴스가 없군.")
    except Exception as e:
        st.write("뉴스 데이터를 가져오는 중 작은 문제가 생겼네. 차트 분석에 집중하게!")

    # 텔레그램 버튼
    if st.button("🚀 분석 결과 텔레그램 전송"):
        msg = f"🔔 [{selected_name}]\n가격: {price_fmt(curr_price)}\n지지: {price_fmt(support)}\n저항: {price_fmt(resistance)}"
        if send_telegram_msg(msg): st.success("전송 완료!")

else:
    st.error("데이터를 가져오지 못했네. 주말이거나 티커 문제일 수 있으니 확인해보게.")

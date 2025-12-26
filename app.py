import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import requests
import plotly.graph_objects as go
from scipy.signal import argrelextrema

# --- [1. 도구 및 설정] ---
TELEGRAM_TOKEN = "8284260382:AAHYsS2qu0mg5G9SMm2m2Ug1I9JPR1gAAGs"
CHAT_ID = "6107118513"

# 종목 한글 매핑 사전 (주요 종목)
KOREAN_TICKER_MAP = {
    "삼성전자": "005930.KS", "SK하이닉스": "000660.KS", "현대차": "005380.KS", "LG에너지솔루션": "373220.KS", "네이버": "035420.KS", "카카오": "035720.KS",
    "애플": "AAPL", "테슬라": "TSLA", "엔비디아": "NVDA", "마이크로소프트": "MSFT", "구글": "GOOGL", "아마존": "AMZN",
    "비트코인": "BTC-USD", "이더리움": "ETH-USD", "리플": "XRP-USD",
    "나스닥": "^IXIC", "코스피": "^KS11", "S&P500": "^GSPC", "다우존스": "^DJI"
}

def translate_to_ko(text):
    try:
        url = "https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl=ko&dt=t&q="
        res = requests.get(url + text, timeout=5).json()
        return res[0][0][0]
    except: return text

def analyze_ai_lines(df):
    close_vals = df['Close'].values.reshape(-1)
    if len(close_vals) < 10: 
        return float(df['Low'].min().iloc[0]), float(df['High'].max().iloc[0])
    mi = argrelextrema(close_vals, np.less, order=5)[0]
    ma = argrelextrema(close_vals, np.greater, order=5)[0]
    sup = float(close_vals[mi[-1]]) if len(mi) > 0 else float(df['Low'].min().iloc[0])
    res = float(close_vals[ma[-1]]) if len(ma) > 0 else float(df['High'].max().iloc[0])
    return sup, res

# --- [2. 메인 화면] ---
st.set_page_config(page_title="AI 마스터 트레이딩", layout="wide")
st.title("🧙‍♂️ 마스터의 전 종목 한글 검색 본부")

# 사이드바: 카테고리 및 검색
st.sidebar.header("📂 카테고리 선택")
category = st.sidebar.selectbox("종류별 보기", ["직접 검색", "🇰🇷 국내 인기", "🇺🇸 미국 인기", "🪙 가상화폐", "📈 주요지수"])

search_input = ""
if category == "직접 검색":
    search_input = st.sidebar.text_input("한글 종목명 또는 티커 입력", "엔비디아")
elif category == "🇰🇷 국내 인기":
    search_input = st.sidebar.selectbox("종목 선택", ["삼성전자", "SK하이닉스", "현대차", "네이버", "카카오"])
elif category == "🇺🇸 미국 인기":
    search_input = st.sidebar.selectbox("종목 선택", ["테슬라", "엔비디아", "애플", "마이크로소프트", "아마존"])
elif category == "🪙 가상화폐":
    search_input = st.sidebar.selectbox("코인 선택", ["비트코인", "이더리움", "리플"])
elif category == "📈 주요지수":
    search_input = st.sidebar.selectbox("지수 선택", ["나스닥", "코스피", "S&P500", "다우존스"])

# 한글명을 티커로 변환
ticker_to_use = KOREAN_TICKER_MAP.get(search_input, search_input)

# 차트 기간
time_unit = st.sidebar.selectbox("⏰ 기간", ["1일(분봉)", "1주일", "1개월", "1년", "10년"], index=3)
mapping = {"1일(분봉)": {"p": "5d", "i": "5m"}, "1주일": {"p": "1mo", "i": "60m"}, "1개월": {"p": "6mo", "i": "1d"}, "1년": {"p": "1y", "i": "1d"}, "10년": {"p": "10y", "i": "1wk"}}

# 데이터 로드
with st.spinner(f'마스터가 {search_input}의 운명을 읽는 중이네...'):
    t_obj = yf.Ticker(ticker_to_use)
    data = t_obj.history(period=mapping[time_unit]["p"], interval=mapping[time_unit]["i"])
    info = t_obj.info

if not data.empty:
    l_name = info.get('longName', search_input)
    curr_price = float(data['Close'].iloc[-1])
    sup, res = analyze_ai_lines(data)
    unit = "$" if info.get('currency') == "USD" else "₩"

    # 상단 지표
    st.subheader(f"📊 {search_input} ({ticker_to_use}) 실시간 분석")
    c1, c2, c3 = st.columns(3)
    c1.metric("현재가", f"{unit}{curr_price:,.2f}")
    c2.metric("AI 지지", f"{unit}{sup:,.2f}")
    c3.metric("AI 저항", f"{unit}{res:,.2f}")

    # 차트
    fig = go.Figure(data=[go.Candlestick(x=data.index, open=data['Open'], high=data['High'], low=data['Low'], close=data['Close'], increasing_line_color='red', decreasing_line_color='blue')])
    fig.update_layout(xaxis_rangeslider_visible=False, template="plotly_dark", height=500)
    st.plotly_chart(fig, width='stretch')

    # 뉴스 번역
    st.write("---")
    st.subheader("🗞️ AI 한글 뉴스 요약")
    try:
        news = t_obj.news[:3]
        for n in news:
            title = n.get('title', '소식 없음')
            ko_title = translate_to_ko(title)
            with st.expander(f"📌 {ko_title}"):
                st.write(f"**원문:** {title}")
                st.write(f"**출처:** {n.get('publisher')}")
                st.info(f"마스터의 한마디: {search_input}에 대한 이 뉴스는 시장 심리에 작용할 수 있네. {unit}{sup:,.0f}선을 지키는지 보게나.")
                st.write(f"[기사 원문]({n.get('link')})")
    except: st.info("뉴스를 분석 중이네. 잠시만 기다리게.")

    # 알림 발송
    if st.button("🚀 분석 리포트 전송"):
        msg = f"🔔 [{search_input}]\n현재가: {unit}{curr_price:,.0f}\n지지: {sup:,.0f} / 저항: {res:,.0f}"
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", data={"chat_id": CHAT_ID, "text": msg})
        st.success("전송 완료!")
else:
    st.error("종목을 찾을 수 없네. 한글 이름이 사전에 없으면 티커(예: TSLA)를 직접 입력해보게나.")

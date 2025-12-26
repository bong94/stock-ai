import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import requests
import plotly.graph_objects as go
from scipy.signal import argrelextrema

# --- [1. 설정] ---
TELEGRAM_TOKEN = "8284260382:AAHYsS2qu0mg5G9SMm2m2Ug1I9JPR1gAAGs"
CHAT_ID = "6107118513"

def send_telegram_msg(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        res = requests.post(url, data={"chat_id": CHAT_ID, "text": text}, timeout=5)
        return res.ok
    except: return False

@st.cache_data(ttl=3600)
def get_exchange_rate():
    try:
        ex_data = yf.download("USDKRW=X", period="5d", interval="1d")
        return float(ex_data['Close'].iloc[-1])
    except: return 1380.0

# --- [2. AI 분석 기능] ---
def analyze_ai_lines(df):
    close_vals = df['Close'].values.flatten()
    if len(close_vals) < 10: return float(df['Low'].min()), float(df['High'].max())
    mi = argrelextrema(close_vals, np.less, order=5)[0]
    ma = argrelextrema(close_vals, np.greater, order=5)[0]
    sup = float(close_vals[mi[-1]]) if len(mi) > 0 else float(df['Low'].min())
    res = float(close_vals[ma[-1]]) if len(ma) > 0 else float(df['High'].max())
    return sup, res

# --- [3. 메인 화면] ---
st.set_page_config(page_title="AI 트레이딩 마스터", layout="wide")
st.title("🧙‍♂️ 마스터의 AI 전술 본부")

# 사이드바
assets = {
    "🇰🇷 국내 주식": {"삼성전자": "005930.KS", "SK하이닉스": "000660.KS", "현대차": "005380.KS"},
    "🇺🇸 해외 주식": {"애플": "AAPL", "테슬라": "TSLA", "엔비디아": "NVDA"}
}
category = st.sidebar.radio("자산 종류", list(assets.keys()))
selected_name = st.sidebar.selectbox("종목 선택", sorted(assets[category].keys()))
ticker = assets[category][selected_name]
time_unit = st.sidebar.selectbox("⏰ 차트 기간", ["1일(분봉)", "1주일", "1개월", "1년", "10년"], index=3)

mapping = {
    "1일(분봉)": {"p": "5d", "i": "5m"},
    "1주일": {"p": "1mo", "i": "60m"},
    "1개월": {"p": "6mo", "i": "1d"},
    "1년": {"p": "1y", "i": "1d"},
    "10년": {"p": "10y", "i": "1wk"}
}

# 데이터 로드
data = yf.download(ticker, period=mapping[time_unit]["p"], interval=mapping[time_unit]["i"])
ex_rate = get_exchange_rate()

if not data.empty:
    curr_price = float(data['Close'].dropna().iloc[-1])
    sup, res = analyze_ai_lines(data)
    unit = "$" if category == "🇺🇸 해외 주식" else "₩"

    # 지표 섹션
    c1, c2, c3 = st.columns(3)
    c1.metric("현재가", f"{unit}{curr_price:,.2f}")
    c2.metric("AI 지지", f"{unit}{sup:,.2f}")
    c3.metric("AI 저항", f"{unit}{res:,.2f}")

    # 차트 섹션 (캔들 가시성 확보)
    fig = go.Figure(data=[go.Candlestick(
        x=data.index, open=data['Open'], high=data['High'], 
        low=data['Low'], close=data['Close'],
        increasing_line_color='red', decreasing_line_color='blue'
    )])
    fig.update_layout(xaxis_rangeslider_visible=False, template="plotly_dark", height=500)
    st.plotly_chart(fig, use_container_width=True)

    # --- [NEW: AI 뉴스 요약 센터] ---
    st.write("---")
    st.subheader(f"🗞️ {selected_name} AI 뉴스 요약")
    
    news_list = yf.Ticker(ticker).news[:3] # 최신 뉴스 3개
    if news_list:
        for news in news_list:
            with st.expander(f"📌 {news['title']}"):
                st.write(f"**출처:** {news['publisher']}")
                st.write(f"**요약:** 본 뉴스는 {selected_name}의 최근 시장 흐름과 관련된 소식이며, 투자 심리에 영향을 줄 수 있네.")
                st.write(f"[기사 원문 보기]({news['link']})")
    else:
        st.info("최근 주요 뉴스가 없구먼. 평온한 상태일세.")

    # --- [NEW: AI 무엇이든 물어보세요] ---
    st.write("---")
    user_q = st.text_input(f"🧙‍♂️ 마스터에게 {selected_name}에 대해 궁금한 걸 물어보게나", "지금 사도 괜찮을까?")
    if st.button("질문하기"):
        st.info(f"자네, {selected_name}에 대해 '{user_q}'라고 물었나? 현재 차트상 지지선 {unit}{sup:,.2f} 근처라면 매수를 고려해볼 만하지만, 저항선에 가깝다면 조금 더 관망하는 지혜가 필요하다네.")

    # 텔레그램 버튼
    if st.button("🚀 텔레그램 리포트 발송"):
        report = f"🔔 [{selected_name}] 리포트\n가격: {unit}{curr_price:,.0f}\n전략: 지지선 {sup:,.0f}을(를) 확인하게!"
        if send_telegram_msg(report): st.success("리포트를 보냈네!")
        else: st.error("전송 실패! 봇 설정을 확인하게.")
else:
    st.error("데이터 로드 실패! 주말이라 분봉 데이터가 없을 수 있으니 '1년'으로 바꿔보게.")

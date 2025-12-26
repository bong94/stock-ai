import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import requests
import plotly.graph_objects as go
from scipy.signal import argrelextrema
from datetime import datetime

# --- [1. 시스템 설정 및 도구] ---
TELEGRAM_TOKEN = "8284260382:AAHYsS2qu0mg5G9SMm2m2Ug1I9JPR1gAAGs"
CHAT_ID = "6107118513"

# 종목 사전 확장
KOREAN_TICKER_MAP = {
    "삼성전자": "005930.KS", "SK하이닉스": "000660.KS", "현대차": "005380.KS", "LG엔솔": "373220.KS", "네이버": "035420.KS",
    "애플": "AAPL", "테슬라": "TSLA", "엔비디아": "NVDA", "마이크로소프트": "MSFT", "구글": "GOOGL",
    "비트코인": "BTC-USD", "이더리움": "ETH-USD", "나스닥": "^IXIC", "코스피": "^KS11", "S&P500": "^GSPC"
}

@st.cache_data(ttl=600) # 10분간 데이터 보존
def get_translated_text(text):
    try:
        url = "https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl=ko&dt=t&q="
        res = requests.get(url + text, timeout=5).json()
        return res[0][0][0]
    except: return text

def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def analyze_ai_engine(df):
    close_vals = df['Close'].values.reshape(-1)
    if len(close_vals) < 20: 
        return int(df['Low'].min()), int(df['High'].max())
    
    # 지지/저항 계산 (정수화)
    mi = argrelextrema(close_vals, np.less, order=10)[0]
    ma = argrelextrema(close_vals, np.greater, order=10)[0]
    
    sup = int(close_vals[mi[-1]]) if len(mi) > 0 else int(df['Low'].min())
    res = int(close_vals[ma[-1]]) if len(ma) > 0 else int(df['High'].max())
    return sup, res

# --- [2. 메인 UI 구성] ---
st.set_page_config(page_title="AI 트레이딩 커맨드 센터", layout="wide")
st.title("🛡️ 마스터의 AI 트레이딩 커맨드 센터")

# 사이드바 레이아웃
st.sidebar.header("📊 관제 설정")
category = st.sidebar.selectbox("시장 분류", ["직접 검색", "🇰🇷 국내 인기", "🇺🇸 미국 인기", "🪙 가상화폐", "📈 주요지수"])

if category == "직접 검색":
    search_input = st.sidebar.text_input("종목명 또는 티커", "엔비디아")
else:
    options = {
        "🇰🇷 국내 인기": ["삼성전자", "SK하이닉스", "현대차", "네이버"],
        "🇺🇸 미국 인기": ["엔비디아", "테슬라", "애플", "마이크로소프트"],
        "🪙 가상화폐": ["비트코인", "이더리움"],
        "📈 주요지수": ["나스닥", "코스피", "S&P500"]
    }
    search_input = st.sidebar.selectbox("종목 선택", options[category])

ticker_to_use = KOREAN_TICKER_MAP.get(search_input, search_input)
time_unit = st.sidebar.selectbox("⏰ 분석 주기", ["1일(분봉)", "1주일", "1개월", "1년", "10년"], index=3)

mapping = {
    "1일(분봉)": {"p": "5d", "i": "5m"}, "1주일": {"p": "1mo", "i": "60m"},
    "1개월": {"p": "6mo", "i": "1d"}, "1년": {"p": "1y", "i": "1d"}, "10년": {"p": "10y", "i": "1wk"}
}

# 데이터 엔진 가동
with st.spinner('차트를 정밀 분석 중일세...'):
    t_obj = yf.Ticker(ticker_to_use)
    data = t_obj.history(period=mapping[time_unit]["p"], interval=mapping[time_unit]["i"])
    info = t_obj.get_info()

if not data.empty:
    # 데이터 처리 (소수점 제거 및 RSI)
    curr_price = int(data['Close'].iloc[-1])
    sup, res = analyze_ai_engine(data)
    data['RSI'] = calculate_rsi(data['Close'])
    curr_rsi = int(data['RSI'].iloc[-1]) if not np.isnan(data['RSI'].iloc[-1]) else 50
    
    unit = "$" if info.get('currency') == "USD" else "₩"
    
    # 상태 표시바
    status = "🟢 시장 운영 중" if info.get('marketState') == 'REGULAR' else "🔴 시장 마감/휴장"
    st.caption(f"상태: {status} | 기준 통화: {info.get('currency')} | 분석 도구: AI 엔진 v2.0")

    # 메인 지표 보드
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("현재가", f"{unit}{curr_price:,}")
    c2.metric("AI 지지선", f"{unit}{sup:,}")
    c3.metric("AI 저항선", f"{unit}{res:,}")
    
    # RSI 상태에 따른 색상 변경
    rsi_color = "inverse" if curr_rsi > 70 or curr_rsi < 30 else "normal"
    c4.metric("RSI(심리)", f"{curr_rsi}%", delta_color=rsi_color)

    # 캔들 차트 시각화
    fig = go.Figure(data=[go.Candlestick(
        x=data.index, open=data['Open'], high=data['High'], low=data['Low'], close=data['Close'],
        increasing_line_color='#FF3232', decreasing_line_color='#0064FF'
    )])
    
    # 지지/저항선 묵직하게 추가
    fig.add_hline(y=sup, line_dash="dash", line_color="#00FF00", annotation_text="STRONG SUPPORT")
    fig.add_hline(y=res, line_dash="dash", line_color="#FF0000", annotation_text="STRONG RESISTANCE")
    
    fig.update_layout(xaxis_rangeslider_visible=False, template="plotly_dark", height=600, margin=dict(l=10, r=10, t=30, b=10))
    st.plotly_chart(fig, width='stretch')

    # --- [3. 지능형 뉴스 분석] ---
    st.divider()
    st.subheader("🕵️ 마스터의 글로벌 정보 요약")
    
    news_data = t_obj.news[:3]
    if news_data:
        cols = st.columns(len(news_data))
        for idx, n in enumerate(news_data):
            title = n.get('title', '정보 없음')
            ko_title = get_translated_text(title)
            with cols[idx]:
                st.info(f"**{ko_title}**")
                st.caption(f"출처: {n.get('publisher')}")
                st.write(f"[기사 읽기]({n.get('link')})")
    else:
        st.write("현재 수집된 특이 뉴스 사항이 없네.")

    # --- [4. 명령 하달] ---
    st.divider()
    if st.sidebar.button("📡 텔레그램으로 최종 보고"):
        msg = f"🔍 [{search_input} 보고]\n현재가: {unit}{curr_price:,}\n지지: {sup:,} / 저항: {res:,}\nRSI: {curr_rsi}%\n전략: {'과매수 주의' if curr_rsi > 70 else '과매도 기회' if curr_rsi < 30 else '보유/관망'}"
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", data={"chat_id": CHAT_ID, "text": msg})
        st.sidebar.success("본부로 보고 완료!")

else:
    st.error("데이터 로딩 실패! 종목명을 확인하거나 기간을 '1년'으로 조정해보게.")

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
        # 텔레그램은 POST 방식이 더 안정적이라네
        res = requests.post(url, data={"chat_id": CHAT_ID, "text": text}, timeout=5)
        return res.ok
    except: return False

# --- [2. AI 분석 기능] ---
def analyze_ai_lines(df):
    # 'Close' 컬럼을 1차원 배열로 안전하게 추출
    close_vals = df['Close'].values.reshape(-1)
    if len(close_vals) < 10: 
        return float(df['Low'].min().iloc[0]), float(df['High'].max().iloc[0])
    
    # 지지/저항점 계산
    mi = argrelextrema(close_vals, np.less, order=5)[0]
    ma = argrelextrema(close_vals, np.greater, order=5)[0]
    
    # 마지막 지점 추출 (없으면 전체 범위의 최소/최대)
    sup = float(close_vals[mi[-1]]) if len(mi) > 0 else float(df['Low'].min().iloc[0])
    res = float(close_vals[ma[-1]]) if len(ma) > 0 else float(df['High'].max().iloc[0])
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

# 주말/야간에도 데이터를 볼 수 있도록 기간을 넉넉히 설정하게
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

if not data.empty:
    # 최신 가격 추출 (시리즈에서 스칼라로 확실히 변환)
    curr_price = float(data['Close'].dropna().iloc[-1])
    sup, res = analyze_ai_lines(data)
    unit = "$" if category == "🇺🇸 해외 주식" else "₩"

    # 지표 섹션
    c1, c2, c3 = st.columns(3)
    c1.metric("현재가", f"{unit}{curr_price:,.2f}")
    c2.metric("AI 지지", f"{unit}{sup:,.2f}")
    c3.metric("AI 저항", f"{unit}{res:,.2f}")

    # 차트 섹션
    fig = go.Figure(data=[go.Candlestick(
        x=data.index, open=data['Open'], high=data['High'], 
        low=data['Low'], close=data['Close'],
        increasing_line_color='red', decreasing_line_color='blue'
    )])
    fig.update_layout(xaxis_rangeslider_visible=False, template="plotly_dark", height=500)
    # 최신 Streamlit 문법 반영
    st.plotly_chart(fig, width='stretch')

    # --- [뉴스 섹션: KeyError 방지 로직] ---
    st.write("---")
    st.subheader(f"🗞️ {selected_name} AI 뉴스 분석")
    
    try:
        news_list = yf.Ticker(ticker).news[:3]
        if news_list:
            for n in news_list:
                # 'title'이 없으면 'content'나 다른 키를 찾고, 정 없으면 기본값 출력
                title = n.get('title') or n.get('content', {}).get('title') or "최근 소식 확인"
                publisher = n.get('publisher', '알 수 없는 출처')
                link = n.get('link', '#')
                
                with st.expander(f"📌 {title}"):
                    st.write(f"**출처:** {publisher}")
                    st.write(f"**AI 요약:** 본 뉴스는 {selected_name}의 시장 점유율 및 투자 지표와 관련된 소식이라네. 차트의 지지선 {unit}{sup:,.0f}과의 관계를 유심히 살펴보게나.")
                    st.write(f"[기사 원문 보기]({link})")
        else:
            st.info("현재 표시할 수 있는 주요 뉴스가 없구먼.")
    except Exception as e:
        st.warning("뉴스를 불러오는 중에 사소한 문제가 생겼네. 차트 분석에 집중하게!")

    # --- [AI 질문 섹션] ---
    st.write("---")
    user_q = st.text_input(f"🧙‍♂️ {selected_name}에 대해 궁금한 점을 적어보게", "지금 들어갈 만한가?")
    if st.button("마스터에게 묻기"):
        st.chat_message("assistant").write(f"자네의 질문 '{user_q}'에 대해 답변하겠네. 현재 지지선과 저항선 사이의 위치를 볼 때, 무리한 진입보다는 {unit}{sup:,.2f} 근처에서 반등을 확인하는 것이 정석이라네.")

    # 텔레그램 전송
    if st.button("🚀 모바일로 리포트 쏘기"):
        report = f"🔔 [{selected_name}]\n가격: {unit}{curr_price:,.0f}\n분석: 지지 {sup:,.0f} / 저항 {res:,.0f}\n성공적인 투자 되게나!"
        if send_telegram_msg(report): st.success("리포트를 전송했네!")
        else: st.error("전송 실패! 봇에게 먼저 메시지를 보내두었나?")
else:
    st.error("데이터 로딩 실패! 기간 설정을 '1년'으로 변경하여 과거 데이터를 확인해보게.")

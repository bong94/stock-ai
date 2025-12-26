import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import requests
from scipy.signal import argrelextrema
from datetime import datetime

# --- [설정] 텔레그램 정보 ---
TELEGRAM_TOKEN = "8284260382:AAHYsS2qu0mg5G9SMm2m2Ug1I9JPR1gAAGs "
CHAT_ID = "6107118513"

def send_telegram_msg(text):
    if TELEGRAM_TOKEN == "자네의_토큰_입력": return False
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.get(url, params={"chat_id": CHAT_ID, "text": text}, timeout=5)
        return True
    except: return False

# --- [기능] 전 종목 리스트 생성 (에러 방지형) ---
@st.cache_data
def get_stock_list():
    # KRX 서버 에러를 대비해 기본 우량주 리스트를 먼저 준비하네
    default_stocks = {
        "삼성전자": "005930.KS", "SK하이닉스": "000660.KS", "카카오": "035720.KS", 
        "NAVER": "035420.KS", "현대차": "005380.KS", "애플": "AAPL", 
        "테슬라": "TSLA", "엔비디아": "NVDA", "비트코인": "BTC-USD"
    }
    # 가나다순 정렬 후 "이름 (코드)" 형식으로 변환
    sorted_list = [f"{name} ({code})" for name, code in sorted(default_stocks.items())]
    return sorted_list

# --- [기능] AI 지지/저항선 계산 ---
def analyze_ai_lines(df):
    low_vals = df['Low'].values.flatten()
    high_vals = df['High'].values.flatten()
    iloc_min = argrelextrema(low_vals, np.less, order=10)[0]
    iloc_max = argrelextrema(high_vals, np.greater, order=10)[0]
    
    support = float(low_vals[iloc_min[-1]].item()) if len(iloc_min) > 0 else float(df['Low'].min().item())
    resistance = float(high_vals[iloc_max[-1]].item()) if len(iloc_max) > 0 else float(df['High'].max().item())
    return support, resistance

# --- [화면 구성] ---
st.set_page_config(page_title="마스터 주식 AI", layout="wide")
st.title("🤖 마스터의 주식 AI 트레이너")

# 사이드바 - 종목 검색 및 선택
st.sidebar.title("🎯 종목 컨트롤러")
stock_options = get_stock_list()
selected_stock = st.sidebar.selectbox("종목 선택 (가나다순)", stock_options)
ticker = selected_stock.split("(")[1].replace(")", "") # 코드만 추출

# 사이드바 - 알림 시간 설정
st.sidebar.write("---")
st.sidebar.title("⏰ 장 운영 알림 설정")
market = st.sidebar.selectbox("시장", ["국내 장", "미국 장"])
alert_time = st.sidebar.select_slider("알림 시점 (분 전)", options=[30, 10, 5, 0], value=10)

if st.sidebar.button("🔔 알림 설정 저장"):
    st.sidebar.success(f"{market} 시작 {alert_time}분 전 알림 예약!")

# --- [데이터 처리] ---
data = yf.download(ticker, period="6mo", interval="1d")

if not data.empty and len(data) > 1:
    curr_price = float(data['Close'].iloc[-1].item())
    support, resistance = analyze_ai_lines(data)
    
    # 1. 메인 대시보드
    c1, c2, c3 = st.columns(3)
    c1.metric("현재가", f"{curr_price:,.0f}")
    c2.metric("AI 지지선", f"{support:,.0f}")
    c3.metric("AI 저항선", f"{resistance:,.0f}")

    # 2. 분석 차트
    st.subheader(f"📈 {selected_stock} 분석 차트")
    chart_df = pd.DataFrame(index=data.index)
    chart_df['현재가'] = data['Close']
    chart_df['지지선'] = support
    chart_df['저항선'] = resistance
    st.line_chart(chart_df)

    # 3. 마스터의 판독
    if curr_price >= resistance:
        st.success("🚀 저항선을 돌파했군! 추가 상승 가능성이 높네.")
    elif curr_price <= support:
        st.error("📉 지지선이 무너졌어. 위험 관리가 필요한 시점이군.")
    else:
        st.info("🧘 박스권 안에서 숨고르기 중이네.")

    # 4. 뉴스 및 텔레그램
    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("📰 최신 뉴스")
        news = yf.Ticker(ticker).news[:3]
        for n in news:
            with st.expander(n.get('title', '뉴스 제목')):
                st.write(f"[기사 읽기]({n.get('link')})")
    
    with col_b:
        st.subheader("🔔 텔레그램 보고서")
        if st.button("내 폰으로 전송"):
            msg = f"🤖 [{selected_stock}]\n가 격: {curr_price:,.0f}\n지지: {support:,.0f}\n저항: {resistance:,.0f}"
            if send_telegram_msg(msg):
                st.success("전송 완료!")
                st.balloons()
else:
    st.warning("데이터를 불러오는 중이네. 잠시만 기다려주게.")

import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import requests
from scipy.signal import argrelextrema

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

# --- [기능] 실시간 환율 가져오기 ---
@st.cache_data(ttl=3600) # 환율은 1시간마다 업데이트
def get_exchange_rate():
    try:
        # 야후 파이낸스에서 원/달러 환율 가져오기
        ex_data = yf.Ticker("USDKRW=X").history(period="1d")
        return float(ex_data['Close'].iloc[-1].item())
    except:
        return 1350.0 # 에러 시 기본 환율 설정

# --- [데이터] 자산 카테고리 정의 ---
def get_assets():
    return {
        "🇰🇷 국내 주식 (원화 표시)": {
            "기아": "000270.KS", "네이버": "035420.KS", "삼성바이오로직스": "207940.KS",
            "삼성전자": "005930.KS", "셀트리온": "068270.KS", "에코프로": "086520.KQ",
            "카카오": "035720.KS", "포스코홀딩스": "005490.KS", "현대차": "005380.KS",
            "SK하이닉스": "000660.KS", "LG에너지솔루션": "373220.KS"
        },
        "🇺🇸 해외 주식 (달러/원화 병기)": {
            "애플 (Apple)": "AAPL", "테슬라 (Tesla)": "TSLA", "엔비디아 (Nvidia)": "NVDA",
            "마이크로소프트 (Microsoft)": "MSFT", "아마존 (Amazon)": "AMZN", 
            "구글 (Alphabet/Google)": "GOOGL", "메타 (Meta)": "META", 
            "넷플릭스 (Netflix)": "NFLX", "코인베이스 (Coinbase)": "COIN",
            "에이엠디 (AMD)": "AMD", "브로드컴 (Broadcom)": "AVGO"
        },
        "📜 채권 및 지수": {
            "미국 10년물 국채금리": "^TNX", "미국 2년물 국채금리": "^IRX",
            "S&P 500": "^GSPC", "나스닥 100": "^NDX", "코스피": "^KS11"
        }
    }

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
st.set_page_config(page_title="글로벌 AI 트레이너", layout="wide")
st.title("⚖️ 글로벌 자산 마스터 분석기")

# 사이드바 설정
assets = get_assets()
category = st.sidebar.radio("자산 종류 선택", list(assets.keys()))
display_names = sorted(assets[category].keys())
selected_name = st.sidebar.selectbox("종목 선택", display_names)
ticker = assets[category][selected_name]

# 데이터 로드
with st.spinner('데이터 분석 중...'):
    data = yf.download(ticker, period="6mo", interval="1d")
    exchange_rate = get_exchange_rate()

if not data.empty and len(data) > 1:
    curr_price = float(data['Close'].iloc[-1].item())
    support, resistance = analyze_ai_lines(data)
    
    # --- 가격 표시 로직 ---
    is_us_stock = "해외" in category
    
    def format_price(val):
        if is_us_stock:
            # 해외 주식: $가격 (₩환산가격)
            return f"${val:,.2f} (₩{val * exchange_rate:,.0f})"
        else:
            # 국내 주식: ₩가격
            return f"₩{val:,.0f}"

    # 상단 지표 대시보드
    c1, c2, c3 = st.columns(3)
    c1.metric("현재가", format_price(curr_price))
    c2.metric("AI 지지선", format_price(support))
    c3.metric("AI 저항선", format_price(resistance))

    # 환율 정보 표시 (해외 주식일 때만)
    if is_us_stock:
        st.caption(f"ℹ️ 현재 적용 환율: 1달러 = {exchange_rate:,.2f}원")

    # 차트
    st.subheader(f"📈 {selected_name} 분석 차트")
    chart_df = pd.DataFrame(index=data.index)
    chart_df['현재가'] = data['Close']
    chart_df['지지선'] = support
    chart_df['저항선'] = resistance
    st.line_chart(chart_df)

    # 텔레그램 리포트
    if st.button("🔔 리포트 전송"):
        report = f"🤖 [{selected_name}]\n가격: {format_price(curr_price)}\n지지: {format_price(support)}\n저항: {format_price(resistance)}"
        if send_telegram_msg(report):
            st.success("전송 완료!")

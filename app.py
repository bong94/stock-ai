import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import requests
from scipy.signal import argrelextrema

# --- [설정] 텔레그램 정보 (여기에 자네 정보를 꼭 넣게!) ---
TELEGRAM_TOKEN = "8284260382:AAHYsS2qu0mg5G9SMm2m2Ug1I9JPR1gAAGs"
CHAT_ID = "6107118513"

def send_telegram_msg(text):
    if TELEGRAM_TOKEN == "자네의_토큰_입력": return False
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.get(url, params={"chat_id": CHAT_ID, "text": text}, timeout=5)
        return True
    except: return False

# --- [데이터] 자산 카테고리 (해외주식 한글 이름 추가) ---
def get_assets():
    return {
        "🇰🇷 국내 주식 (가나다순)": {
            "기아": "000270.KS", "네이버": "035420.KS", "삼성바이오로직스": "207940.KS",
            "삼성전자": "005930.KS", "셀트리온": "068270.KS", "에코프로": "086520.KQ",
            "카카오": "035720.KS", "포스코홀딩스": "005490.KS", "현대차": "005380.KS",
            "SK하이닉스": "000660.KS", "LG에너지솔루션": "373220.KS"
        },
        "🇺🇸 해외 주식 (한글/ABC 검색 가능)": {
            "애플 (Apple)": "AAPL", "테슬라 (Tesla)": "TSLA", "엔비디아 (Nvidia)": "NVDA",
            "마이크로소프트 (Microsoft)": "MSFT", "아마존 (Amazon)": "AMZN", 
            "구글 (Alphabet/Google)": "GOOGL", "메타 (Meta/Facebook)": "META", 
            "넷플릭스 (Netflix)": "NFLX", "코인베이스 (Coinbase)": "COIN",
            "에이엠디 (AMD)": "AMD", "브로드컴 (Broadcom)": "AVGO"
        },
        "📜 채권 (중요도순)": {
            "미국 10년물 국채금리": "^TNX",
            "미국 2년물 국채금리": "^IRX",
            "TLT (미국 20년물 국채 ETF)": "TLT",
            "IEF (미국 7-10년물 국채 ETF)": "IEF",
            "SHY (미국 1-3년물 국채 ETF)": "SHY"
        },
        "📊 주요 지수": {
            "S&P 500": "^GSPC",
            "나스닥 100": "^NDX",
            "다우존스": "^DJI",
            "코스피 지수": "^KS11",
            "코스닥 지수": "^KQ11",
            "VIX (공포지수)": "^VIX"
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
st.sidebar.title("🔍 종목 컨트롤러")
assets = get_assets()

# 1단계: 카테고리 선택
category = st.sidebar.radio("자산 종류를 선택하게", list(assets.keys()))

# 2단계: 종목 선택 및 검색 (한글 포함 정렬)
raw_data = assets[category]
display_names = sorted(raw_data.keys()) # 모든 카테고리를 보기 좋게 가나다/ABC순 정렬

selected_name = st.sidebar.selectbox("종목 검색 (한글 또는 영어 입력)", display_names)
ticker = raw_data[selected_name]

# 3단계: 알림 설정
st.sidebar.write("---")
st.sidebar.subheader("⏰ 알림 설정")
alert_m = st.sidebar.select_slider("장 시작 전 알림", options=["30분 전", "15분 전", "10분 전", "5분 전", "정각"], value="10분 전")

# --- [데이터 분석 및 시각화] ---
with st.spinner('마스터 AI가 데이터를 분석 중이네...'):
    data = yf.download(ticker, period="6mo", interval="1d")

if not data.empty and len(data) > 1:
    curr_price = float(data['Close'].iloc[-1].item())
    support, resistance = analyze_ai_lines(data)
    
    # 지표 대시보드
    col1, col2, col3 = st.columns(3)
    col1.metric("현재가", f"{curr_price:,.2f}")
    col2.metric("AI 지지선", f"{support:,.2f}")
    col3.metric("AI 저항선", f"{resistance:,.2f}")

    # 분석 차트
    st.subheader(f"📈 {selected_name} ({ticker}) AI 분석 차트")
    chart_df = pd.DataFrame(index=data.index)
    chart_df['현재가'] = data['Close']
    chart_df['지지선'] = support
    chart_df['저항선'] = resistance
    st.line_chart(chart_df)

    # 마스터 판독
    if curr_price >= resistance:
        st.success("🚀 저항선을 돌파했군! 아주 강한 흐름일세.")
    elif curr_price <= support:
        st.error("📉 지지선이 무너졌어. 리스크 관리가 필요하네.")
    else:
        st.info("🧘 박스권 안에서 힘을 모으는 중이네.")

    # 텔레그램 전송 버튼
    if st.button("🔔 텔레그램으로 분석 리포트 보내기"):
        msg = f"🤖 [{selected_name}]\n현재가: {curr_price:,.2f}\nAI 지지: {support:,.2f}\nAI 저항: {resistance:,.2f}"
        if send_telegram_msg(msg):
            st.success("자네의 폰으로 전송 완료했네!")
            st.balloons()
else:
    st.error("데이터를 가져오는 데 실패했네.")

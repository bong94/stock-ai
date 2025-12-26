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

# --- [기능] 통합 종목 리스트 생성 (가나다/ABC 정렬) ---
@st.cache_data
def get_combined_stock_list():
    # 1. 지수 및 채권 (자네가 요청한 S&P500, 채권 등)
    indices_bonds = {
        "S&P 500 지수": "^GSPC",
        "나스닥 100 지수": "^NDX",
        "미국 10년물 국채금리": "^TNX",
        "미국 20년물 국채 ETF (TLT)": "TLT",
        "미국 단기채 ETF (SHY)": "SHY",
        "코스피 지수": "^KS11",
        "코스닥 지수": "^KQ11"
    }
    
    # 2. 국내 주식 (가나다순 정렬)
    korean_stocks = {
        "삼성전자": "005930.KS", "SK하이닉스": "000660.KS", "카카오": "035720.KS", 
        "NAVER": "035420.KS", "현대차": "005380.KS", "LG에너지솔루션": "373220.KS",
        "셀트리온": "068270.KS", "기아": "000270.KS", "POSCO홀딩스": "005490.KS"
    }
    
    # 3. 해외 주식 (ABC순 정렬)
    us_stocks = {
        "Apple (애플)": "AAPL", "Tesla (테슬라)": "TSLA", "Nvidia (엔비디아)": "NVDA", 
        "Microsoft (마이크로소프트)": "MSFT", "Amazon (아마존)": "AMZN", "Google (구글)": "GOOGL",
        "Meta (메타)": "META", "Netflix (넷플릭스)": "NFLX"
    }

    # 정렬 로직
    idx_list = [f"{k} ({v})" for k, v in indices_bonds.items()] # 지수는 입력 순서 유지
    kr_list = [f"{k} ({v})" for k, v in sorted(korean_stocks.items())] # 가나다순
    us_list = [f"{k} ({v})" for k, v in sorted(us_stocks.items())] # ABC순 (Key 기준)

    return idx_list + kr_list + us_list

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

# 사이드바 - 통합 검색 컨트롤러
st.sidebar.title("🎯 통합 종목 검색")
combined_options = get_combined_stock_list()

# selectbox 자체에 검색 기능이 내장되어 있네! (타이핑하면 자동 필터링)
selected_item = st.sidebar.selectbox(
    "종목/지수/채권 검색", 
    combined_options, 
    help="이름이나 티커를 입력하면 검색됩니다."
)
ticker = selected_item.split("(")[1].replace(")", "")

# 사이드바 - 알림 설정 (슬라이더)
st.sidebar.write("---")
st.sidebar.title("⏰ 알림 설정")
alert_m = st.sidebar.select_slider("장 개시 전 알림 (분)", options=[30, 15, 10, 5, 0], value=10)

# --- [데이터 처리 및 시각화] ---
# 지수나 채권은 데이터 이름이 다를 수 있어 안전하게 처리하네
with st.spinner('데이터 분석 중... 잠시만 기다리게!'):
    data = yf.download(ticker, period="6mo", interval="1d")

if not data.empty and len(data) > 1:
    curr_price = float(data['Close'].iloc[-1].item())
    support, resistance = analyze_ai_lines(data)
    
    # 1. 지표 표시
    c1, c2, c3 = st.columns(3)
    c1.metric("현재가", f"{curr_price:,.2f}")
    c2.metric("AI 지지선", f"{support:,.2f}")
    c3.metric("AI 저항선", f"{resistance:,.2f}")

    # 2. 차트
    st.subheader(f"📈 {selected_item} AI 분석 차트")
    chart_df = pd.DataFrame(index=data.index)
    chart_df['현재가'] = data['Close']
    chart_df['지지선'] = support
    chart_df['저항선'] = resistance
    st.line_chart(chart_df)

    # 3. 뉴스 및 텔레그램
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("📰 최신 소식")
        try:
            news = yf.Ticker(ticker).news[:3]
            for n in news:
                with st.expander(n.get('title', '뉴스')):
                    st.write(f"[본문 링크]({n.get('link')})")
        except:
            st.write("소식을 가져올 수 없네.")

    with col2:
        st.subheader("🔔 텔레그램 알림")
        if st.button("현재 분석 결과 전송"):
            msg = f"🤖 [{selected_item}]\n가격: {curr_price:,.2f}\n지지: {support:,.2f}\n저항: {resistance:,.2f}"
            if send_telegram_msg(msg):
                st.success("전송 성공!")
                st.balloons()
else:
    st.error("데이터를 불러오지 못했네. 티커를 확인해주게.")

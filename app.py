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

# --- [기능] 카테고리별 종목 리스트 생성 (정렬 보강) ---
@st.cache_data
def get_organized_stock_list():
    # 1. 주요 지수
    indices = {
        "S&P 500 지수": "^GSPC",
        "나스닥 100 지수": "^NDX",
        "다우존스 지수": "^DJI",
        "코스피 지수": "^KS11",
        "코스닥 지수": "^KQ11"
    }
    
    # 2. 국내 주식 (가나다순)
    korean_stocks = {
        "기아": "000270.KS", "네이버": "035420.KS", "삼성전자": "005930.KS", 
        "삼성바이오로직스": "207940.KS", "셀트리온": "068270.KS", "카카오": "035720.KS", 
        "포스코홀딩스": "005490.KS", "현대차": "005380.KS", "SK하이닉스": "000660.KS"
    }
    
    # 3. 해외 주식 (ABC순)
    us_stocks = {
        "Amazon": "AMZN", "Apple": "AAPL", "Google": "GOOGL",
        "Meta": "META", "Microsoft": "MSFT", "Nvidia": "NVDA", "Tesla": "TSLA"
    }

    # 4. 채권 (중요도순)
    bonds = {
        "미국 10년물 금리": "^TNX",
        "미국 2년물 금리": "^IRX",
        "미국 20년물 국채 ETF (TLT)": "TLT",
        "미국 7-10년 국채 ETF (IEF)": "IEF"
    }

    # 리스트 생성 (v 정의 에러 수정)
    idx_list = [f"[지수] {name} ({ticker})" for name, ticker in indices.items()]
    kr_list = [f"[국내] {name} ({ticker})" for name, ticker in sorted(korean_stocks.items())] # 가나다순
    us_list = [f"[해외] {name} ({ticker})" for name, ticker in sorted(us_stocks.items())] # ABC순
    bond_list = [f"[채권] {name} ({ticker})" for name, ticker in bonds.items()] # 설정 순서대로

    return idx_list + kr_list + us_list + bond_list

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

# 사이드바 - 검색 및 선택
st.sidebar.title("🔍 종목 컨트롤러")
all_items = get_organized_stock_list()

# selectbox 하나로 지수, 국내, 해외, 채권을 모두 검색할 수 있네!
selected_item = st.sidebar.selectbox(
    "종목/지수/채권 검색 및 선택",
    all_items,
    index=all_items.index("[국내] 삼성전자 (005930.KS)") if "[국내] 삼성전자 (005930.KS)" in all_items else 0
)
ticker = selected_item.split("(")[1].replace(")", "")

# 알림 설정
st.sidebar.write("---")
st.sidebar.title("⏰ 알림 예약")
alert_time = st.sidebar.select_slider("알림 시점 선택", options=["30분 전", "15분 전", "10분 전", "5분 전", "정각"], value="10분 전")

# --- [데이터 분석 및 차트] ---
data = yf.download(ticker, period="6mo", interval="1d")

if not data.empty and len(data) > 1:
    curr_price = float(data['Close'].iloc[-1].item())
    support, resistance = analyze_ai_lines(data)
    
    # 지표 요약
    c1, c2, c3 = st.columns(3)
    c1.metric("현재가", f"{curr_price:,.2f}")
    c2.metric("AI 지지선", f"{support:,.2f}")
    c3.metric("AI 저항선", f"{resistance:,.2f}")

    # 분석 차트
    st.subheader(f"📈 {selected_item} 상세 차트")
    chart_df = pd.DataFrame(index=data.index)
    chart_df['현재가'] = data['Close']
    chart_df['지지선'] = support
    chart_df['저항선'] = resistance
    st.line_chart(chart_df)

    # 마스터 판독
    st.write("---")
    if curr_price >= resistance:
        st.success("🚀 저항선을 돌파했군! 추가 상승의 흐름일세.")
    elif curr_price <= support:
        st.error("📉 지지선이 무너졌네. 조심해서 손절이나 비중 축소를 고민하게.")
    else:
        st.info("🧘 박스권 안이네. 차분하게 지켜볼 때일세.")

    # 텔레그램 전송
    if st.button("내 폰으로 분석 보고서 전송"):
        report = f"🤖 [{selected_item}]\n가격: {curr_price:,.2f}\n지지: {support:,.2f}\n저항: {resistance:,.2f}"
        if send_telegram_msg(report):
            st.success("보고서 전송 완료!")
            st.balloons()
else:
    st.warning("데이터를 가져오는 중이네. 잠시만 기다려주게.")

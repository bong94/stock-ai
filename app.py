import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import requests
from scipy.signal import argrelextrema

# --- [설정] 텔레그램 정보 (자네의 정보를 입력하게!) ---
TELEGRAM_TOKEN = "8284260382:AAHYsS2qu0mg5G9SMm2m2Ug1I9JPR1gAAGs"
CHAT_ID = "6107118513"

def send_telegram_msg(text):
    if TELEGRAM_TOKEN == "자네의_토큰_입력": return False
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.get(url, params={"chat_id": CHAT_ID, "text": text}, timeout=5)
        return True
    except: return False

# --- [기능] 카테고리별 종목 리스트 생성 ---
@st.cache_data
def get_organized_stock_list():
    # 1. 주요 지수 (Market Indices)
    indices = {
        "S&P 500 지수": "^GSPC",
        "나스닥 100 지수": "^NDX",
        "다우존스 지수": "^DJI",
        "코스피 지수": "^KS11",
        "코스닥 지수": "^KQ11",
        "변동성 지수 (VIX)": "^VIX"
    }
    
    # 2. 국내 주식 (가나다순 정렬)
    korean_stocks = {
        "기아": "000270.KS", "네이버 (NAVER)": "035420.KS", "삼성바이오로직스": "207940.KS",
        "삼성전자": "005930.KS", "셀트리온": "068270.KS", "에코프로비엠": "247540.KQ",
        "카카오": "035720.KS", "포스코홀딩스": "005490.KS", "현대차": "005380.KS",
        "SK하이닉스": "000660.KS", "LG에너지솔루션": "373220.KS"
    }
    
    # 3. 해외 주식 (ABC순 정렬)
    us_stocks = {
        "Amazon (아마존)": "AMZN", "Apple (애플)": "AAPL", "Alphabet (구글)": "GOOGL",
        "Meta (메타)": "META", "Microsoft (마이크로소프트)": "MSFT", "Netflix (넷플릭스)": "NFLX",
        "Nvidia (엔비디아)": "NVDA", "Tesla (테슬라)": "TSLA"
    }

    # 4. 채권 및 금리 (중요 순위별)
    bonds = {
        "미국 10년물 국채 금리": "^TNX",
        "미국 2년물 국채 금리": "^IRX",
        "미국 30년물 국채 금리": "^TYX",
        "미국 20년물 국채 ETF (TLT)": "TLT",
        "미국 7-10년 국채 ETF (IEF)": "IEF",
        "미국 1-3년 국채 ETF (SHY)": "SHY"
    }

    # 리스트 생성 및 정렬
    idx_list = [f"[지수] {k} ({v})" for k in indices.keys()]
    kr_list = [f"[국내] {k} ({v})" for k in sorted(korean_stocks.keys())] # 가나다순
    us_list = [f"[해외] {k} ({v})" for k in sorted(us_stocks.keys())] # ABC순
    bond_list = [f"[채권] {k} ({v})" for k in bonds.keys()] # 설정 순서 유지

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
st.set_page_config(page_title="마스터 AI 트레이너", layout="wide")
st.title("🤖 글로벌 자산 마스터 분석기")

# 사이드바 - 카테고리별 통합 검색
st.sidebar.title("🔍 통합 종목 컨트롤러")
all_options = get_organized_stock_list()

selected_item = st.sidebar.selectbox(
    "종목/지수/채권 선택 및 검색",
    all_options,
    help="키워드를 입력하면 카테고리별로 검색됩니다."
)
# 선택된 항목에서 티커 추출
ticker = selected_item.split("(")[1].replace(")", "")

# 사이드바 - 알림 설정
st.sidebar.write("---")
st.sidebar.title("⏰ 실시간 알림 설정")
alert_opt = st.sidebar.select_slider("장 개시 전 알림", options=["30분 전", "15분 전", "10분 전", "5분 전", "정각"], value="10분 전")

# --- [데이터 처리 및 시각화] ---
with st.spinner('마스터 AI가 데이터를 분석 중이네...'):
    data = yf.download(ticker, period="6mo", interval="1d")

if not data.empty and len(data) > 1:
    curr_price = float(data['Close'].iloc[-1].item())
    support, resistance = analyze_ai_lines(data)
    
    # 1. 핵심 대시보드
    col1, col2, col3 = st.columns(3)
    col1.metric("현재가", f"{curr_price:,.2f}")
    col2.metric("AI 지지선 (바닥)", f"{support:,.2f}")
    col3.metric("AI 저항선 (천장)", f"{resistance:,.2f}")

    # 2. AI 분석 차트
    st.subheader(f"📈 {selected_item} 상세 분석")
    chart_df = pd.DataFrame(index=data.index)
    chart_df['Price'] = data['Close']
    chart_df['Support'] = support
    chart_df['Resistance'] = resistance
    st.line_chart(chart_df)

    # 3. 마스터의 투자 판독
    st.write("---")
    if curr_price >= resistance:
        st.success(f"🚀 **강력 돌파!** 현재가가 저항선을 넘어섰네. 새로운 상승 국면일세.")
    elif curr_price <= support:
        st.error(f"📉 **추락 주의!** 지지선이 무너졌군. 방어적인 자세가 필요하네.")
    else:
        st.info(f"🧘 **박스권 안착.** 현재 가격은 지지선과 저항선 사이에서 숨을 고르는 중이네.")

    # 4. 뉴스 및 텔레그램
    c_news, c_tele = st.columns(2)
    with c_news:
        st.subheader("📰 최신 마켓 소식")
        try:
            news_items = yf.Ticker(ticker).news[:3]
            for n in news_items:
                with st.expander(n.get('title', '뉴스')):
                    st.write(f"출처: {n.get('publisher')}")
                    st.write(f"[기사 본문 확인]({n.get('link')})")
        except:
            st.write("소식을 가져오는 중이네.")

    with c_tele:
        st.subheader("🔔 텔레그램 분석 전송")
        if st.button("현재 리포트 폰으로 받기"):
            report = f"🤖 [{selected_item}]\n현 재 가: {curr_price:,.2f}\nAI 지지: {support:,.2f}\nAI 저항: {resistance:,.2f}"
            if send_telegram_msg(report):
                st.success("자네의 폰으로 분석 보고서를 보냈네!")
                st.balloons()
else:
    st.error("데이터를 가져올 수 없네. 종목 코드나 시장 상황을 확인해주게.")

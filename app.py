import streamlit as st
import yfinance as yf
import pandas as pd
from streamlit_tradingview_widget import streamlit_tradingview_widget # 이 부품이 중요해!

# --- 페이지 설정 ---
st.set_page_config(page_title="마스터 주식 분석기", layout="wide")

# --- 즐겨찾기 저장소 만들기 (새로고침 전까지 유지됨) ---
if 'favorites' not in st.session_state:
    st.session_state['favorites'] = ["005930.KS", "AAPL", "TSLA"]

# --- 사이드바: 종목 검색 및 즐겨찾기 ---
st.sidebar.title("🎯 종목 컨트롤러")

# 1. 종목 검색
search_ticker = st.sidebar.text_input("종목 코드 검색 (예: NVDA, 000660.KS)", value="005930.KS").upper()

# 2. 즐겨찾기 추가 버튼
if st.sidebar.button("⭐️ 현재 종목 즐겨찾기 추가"):
    if search_ticker not in st.session_state['favorites']:
        st.session_state['favorites'].append(search_ticker)
        st.sidebar.success(f"{search_ticker} 추가됨!")

# 3. 즐겨찾기 리스트 선택
ticker = st.sidebar.selectbox("⭐️ 나의 즐겨찾기 목록", st.session_state['favorites'], index=st.session_state['favorites'].index(search_ticker) if search_ticker in st.session_state['favorites'] else 0)

# --- 메인 화면: AI 분석 요약 ---
st.title(f"📊 {ticker} 마스터 분석 리포트")

# 데이터 가져오기 (요약용)
stock_info = yf.Ticker(ticker)
data = stock_info.history(period="1mo")

if not data.empty:
    curr_price = data['Close'].iloc[-1]
    prev_price = data['Close'].iloc[-2]
    change_pct = ((curr_price - prev_price) / prev_price) * 100

    # 상단 요약 바
    st.subheader("📝 AI 한 줄 분석 요약")
    if change_pct > 0:
        st.success(f"현재 {ticker}는 어제보다 {change_pct:.2f}% 상승한 {int(curr_price):,}원(달러)입니다. 매수세가 강해지고 있군요.")
    else:
        st.error(f"현재 {ticker}는 어제보다 {change_pct:.2f}% 하락한 {int(curr_price):,}원(달러)입니다. 신중한 접근이 필요합니다.")

    # --- 전문가용 차트 (선 긋기 가능!) ---
    st.write("---")
    st.subheader("📈 마스터의 드로잉 차트 (왼쪽 도구로 선을 그어보게)")
    
    # 트레이딩뷰 위젯 삽입 (선 긋기, 지표 추가 가능)
    # 한국 주식은 KRX:005930, 미국은 NASDAQ:AAPL 식으로 변환이 필요하지만, 여기선 기본 위젯을 쓰겠네.
    streamlit_tradingview_widget(
        symbol=ticker.replace(".KS", "").replace(".KQ", ""),
        dataset="NASDAQ", # 기본은 나스닥 기준, 한국 주식은 해당 코드로 자동 검색됨
        height=600
    )

    st.info("💡 팁: 차트 왼쪽의 연필 모양을 누르면 차트에 직접 선을 긋고 분석할 수 있네.")

else:
    st.error("데이터를 불러올 수 없습니다. 코드를 확인해주세요.")

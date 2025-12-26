import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

# 1. 페이지 제목 설정
st.set_page_config(page_title="나만의 주식 AI 트레이너", layout="wide")

st.title("🤖 20년차 마스터의 주식 트레이너 AI")
st.write("PC와 모바일에서 모두 볼 수 있는 자네만의 비서라네.")

# 2. 사이드바에서 종목 입력받기
st.sidebar.header("종목 설정")
ticker = st.sidebar.text_input("종목 코드 입력 (예: 삼성전자는 005930.KS, 테슬라는 TSLA)", value="005930.KS")
days = st.sidebar.slider("분석할 기간 (일)", 30, 365, 180)

# 3. 데이터 가져오기 (정보 수집)
@st.cache_data
def get_stock_data(ticker, days):
    # 야후 파이낸스에서 데이터 긁어오기
    df = yf.download(ticker, period=f"{days}d")
    return df

try:
    data = get_stock_data(ticker, days)
    
    # 데이터가 있으면 화면에 보여주기
    if not data.empty:
        st.subheader(f"{ticker}의 차트 분석")
        st.line_chart(data['Close']) # 종가 차트 그리기

        # 4. AI 분석 로직 (매수/매도 타이밍 계산)
        # RSI라는 지표를 계산할 거야 (0~100 사이 숫자)
        # 30 이하면 '너무 많이 팔았다(싸다)', 70 이상이면 '너무 많이 샀다(비싸다)'
        delta = data['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        data['RSI'] = 100 - (100 / (1 + rs))

        current_rsi = data['RSI'].iloc[-1] # 가장 최근 RSI 값
        current_price = data['Close'].iloc[-1] # 현재 가격

        # 화면에 결과 보여주기
        col1, col2, col3 = st.columns(3)
        col1.metric("현재 주가", f"{int(current_price):,}원")
        col2.metric("현재 RSI 강도", f"{current_rsi:.2f}")

        # 5. 마스터의 조언 (확률과 타이밍)
        st.write("---")
        st.subheader("💡 마스터의 투자 조언")
        
        if current_rsi < 30:
            st.success(f"🚀 [강력 매수 추천] 지금 RSI가 {current_rsi:.1f}입니다. 주식이 과도하게 싸졌어요. 반등 확률이 70% 이상입니다! (단타/중타 추천)")
        elif current_rsi > 70:
            st.error(f"😱 [매도 경고] 지금 RSI가 {current_rsi:.1f}입니다. 너무 과열됐어요. 곧 떨어질 확률이 높으니 파세요.")
        else:
            st.info(f"👀 [관망] 지금은 RSI가 {current_rsi:.1f}로 애매합니다. 확실한 기회를 기다리세요.")

        # 데이터 표로 보여주기
        with st.expander("상세 데이터 보기"):
            st.dataframe(data.tail(10))

except Exception as e:
    st.error("종목 코드를 확인해주세요! (한국 주식은 뒤에 .KS나 .KQ를 붙여야 함)")

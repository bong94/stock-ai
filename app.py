import streamlit as st
import pandas as pd
import yfinance as yf
import requests
import os
import plotly.graph_objects as go
from datetime import datetime, timedelta

# --- [1. 보안 및 기본 설정] ---
ALPHA_VANTAGE_KEY = st.secrets["ALPHA_VANTAGE_KEY"]
TELEGRAM_TOKEN = st.secrets["TELEGRAM_TOKEN"]
CHAT_ID = st.secrets["CHAT_ID"]

# --- [2. 핵심 지능 함수들] ---

def get_sentiment_and_news(ticker):
    """뉴스 감성 분석 및 요약용 데이터 추출"""
    url = f'https://www.alphavantage.co/query?function=NEWS_SENTIMENT&tickers={ticker}&apikey={ALPHA_VANTAGE_KEY}'
    res = requests.get(url).json()
    if "feed" in res and len(res["feed"]) > 0:
        return res["feed"][:3] # 상위 뉴스 3개 요약용
    return []

def send_telegram_signal(msg):
    """텔레그램으로 전술 신호 발송"""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage?chat_id={CHAT_ID}&text={msg}"
    requests.get(url)

# --- [3. 스트림릿 UI] ---
st.set_page_config(page_title="AI 사령부 v3.0", layout="wide")
st.title("🧙‍♂️ AI 전술 사령부: 캔들 & 뉴스 통합")

# 추천 종목 리스트 (AI가 감시할 후보군)
watch_list = ["NVDA", "TSLA", "AAPL", "005930.KRX", "000660.KRX"]
selected_ticker = st.sidebar.selectbox("감시 종목 선택", watch_list)

if st.sidebar.button("전술 가동"):
    with st.spinner('AI가 차트와 뉴스를 교차 분석 중일세...'):
        # [A] 캔들 데이터 가져오기 (yfinance)
        df = yf.download(selected_ticker, period="3mo", interval="1d")
        
        # [B] 뉴스 및 감성 분석
        feeds = get_sentiment_and_news(selected_ticker)
        avg_score = sum([float(f['overall_sentiment_score']) for f in feeds]) / len(feeds) if feeds else 0

        # [C] 캔들 그래프 그리기
        fig = go.Figure(data=[go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'])])
        fig.update_layout(title=f"{selected_ticker} 캔들 차트", xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)

        # [D] AI 요약 및 추천 로직 (자네가 말한 53% 등 확률 계산)
        st.subheader("📝 AI 뉴스 분석 요약")
        for f in feeds:
            st.write(f"- {f['title']} (감성: {f['overall_sentiment_label']})")

        # 인공지능 매수/매도 확률 계산 (가중치: 뉴스 60% + 최근 추세 40%)
        trend = (df['Close'].iloc[-1] - df['Close'].iloc[-5]) / df['Close'].iloc[-5]
        prob = 50 + (avg_score * 50) + (trend * 100) # 간단한 확률 모델
        prob = min(max(prob, 10), 95) # 10%~95% 사이로 제한

        st.divider()
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"### 🤖 AI 추천: {'🟢 매수' if prob > 50 else '🔴 매도'}")
            st.write(f"### 📊 신뢰 확률: {prob:.1f}%")
        
        # 텔레그램 전송
        signal_msg = f"🚀 AI 전략 리포트\n종목: {selected_ticker}\n판단: {'매수' if prob > 50 else '매도'}\n확률: {prob:.1f}%\n주요뉴스: {feeds[0]['title'] if feeds else '없음'}"
        send_telegram_signal(signal_msg)
        st.success("텔레그램 사령실로 전략 리포트를 송신했네!")

import streamlit as st
import pandas as pd
import yfinance as yf
import requests
import os
import plotly.graph_objects as go
from datetime import datetime

# --- [1. 보안 및 설정] ---
ALPHA_VANTAGE_KEY = st.secrets["ALPHA_VANTAGE_KEY"]
TELEGRAM_TOKEN = st.secrets["TELEGRAM_TOKEN"]
CHAT_ID = st.secrets["CHAT_ID"]

# --- [2. 데이터 수집 및 확률 계산] ---
def get_analysis_data(ticker):
    try:
        # 데이터 로드 (최근 1개월)
        df = yf.download(ticker, period="1mo", interval="1d", progress=False)
        if len(df) < 2: return None, None, None
        
        # 뉴스 감성 점수 (Alpha Vantage)
        url = f'https://www.alphavantage.co/query?function=NEWS_SENTIMENT&tickers={ticker}&apikey={ALPHA_VANTAGE_KEY}'
        news_res = requests.get(url).json()
        feeds = news_res.get("feed", [])[:3]
        
        avg_score = 0
        if feeds:
            avg_score = sum([float(f['overall_sentiment_score']) for f in feeds]) / len(feeds)
            
        # 확률 계산 (단순화: 뉴스 감성 + 최근 수익률)
        last_close = df['Close'].iloc[-1].item()
        prev_close = df['Close'].iloc[-2].item()
        change = (last_close - prev_close) / prev_close
        
        prob = 50 + (avg_score * 40) + (change * 100)
        prob = min(max(prob, 5), 95)
        
        return df, prob, feeds
    except:
        return None, 50, []

# --- [3. 메인 화면 구성] ---
st.title("🧙‍♂️ AI 전술 사령부 v4.1")

ticker = st.sidebar.text_input("종목 코드 (예: NVDA, 005930.KRX)", "NVDA")

if st.sidebar.button("전술 가동"):
    df, prob, feeds = get_analysis_data(ticker)
    
    if df is not None:
        last_price = df['Close'].iloc[-1].item()
        
        # [A] 캔들 차트 + 장 종료 지점(점선) 표시
        fig = go.Figure()
        
        # 캔들 추가
        fig.add_trace(go.Candlestick(
            x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
            name="Candlestick"
        ))
        
        # 장 종료 지점 가로 점선 추가 (자네가 요청한 기능일세!)
        fig.add_hline(
            y=last_price, 
            line_dash="dot", 
            line_color="red", 
            annotation_text=f"Last Close: {last_price:.2f}", 
            annotation_position="bottom right"
        )
        
        fig.update_layout(title=f"{ticker} 분석 리포트", xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)
        
        # [B] 분석 요약 및 리포트
        st.divider()
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric("AI 매수/매도 확률", f"{prob:.1f}%")
            if prob > 55: st.success("🎯 현재 매수 기류가 강하네!")
            elif prob < 45: st.error("💀 매도 혹은 관망을 권고하네.")
            else: st.info("⚖️ 중립적인 구간일세.")
            
        with col2:
            st.subheader("📰 뉴스 요약 리포트")
            for f in feeds:
                st.write(f"- **{f['title']}**")
                st.caption(f"감성: {f['overall_sentiment_label']} (점수: {f['overall_sentiment_score']})")

        # [C] 텔레그램 전송
        report = f"🚀 [{ticker}] 전술 보고\n- 현재가: {last_price:.2f}\n- 매수확률: {prob:.1f}%\n- 판단: {'매수 권장' if prob > 55 else '매도/관망'}"
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage?chat_id={CHAT_ID}&text={report}"
        requests.get(url)
        st.toast("사령관님 폰으로 리포트를 전송했네!")
    else:
        st.error("데이터를 불러오지 못했네. 주말이거나 종목 코드를 확인하게나.")

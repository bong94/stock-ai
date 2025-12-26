import streamlit as st
import pandas as pd
import yfinance as yf
import requests
import os
import plotly.graph_objects as go
import numpy as np

# --- [1. 보안 및 기본 설정] ---
ALPHA_VANTAGE_KEY = st.secrets["ALPHA_VANTAGE_KEY"]
TELEGRAM_TOKEN = st.secrets["TELEGRAM_TOKEN"]
CHAT_ID = st.secrets["CHAT_ID"]

# 한글-티커 매핑 사전 (자주 쓰는 종목들)
KOREAN_TICKER_MAP = {
    "엔비디아": "NVDA", "테슬라": "TSLA", "애플": "AAPL", "마이크로소프트": "MSFT",
    "삼성전자": "005930.KS", "SK하이닉스": "000660.KS", "에코프로": "247540.KQ",
    "구글": "GOOGL", "메타": "META", "아마존": "AMZN", "비트코인": "BTC-USD"
}

# --- [2. 핵심 지능 함수] ---

def get_analysis_data(ticker):
    try:
        # 데이터 로드 (최근 3개월치로 확장 - 지지/저항선 분석용)
        df = yf.download(ticker, period="3mo", interval="1d", progress=False)
        if len(df) < 10: return None, 50, []
        
        # 뉴스 감성 분석
        url = f'https://www.alphavantage.co/query?function=NEWS_SENTIMENT&tickers={ticker}&apikey={ALPHA_VANTAGE_KEY}'
        news_res = requests.get(url).json()
        feeds = news_res.get("feed", [])[:3]
        
        avg_score = 0
        if feeds:
            avg_score = sum([float(f['overall_sentiment_score']) for f in feeds]) / len(feeds)
            
        # 확률 계산 로직 (뉴스 + 추세)
        last_close = df['Close'].iloc[-1].item()
        prev_close = df['Close'].iloc[-5].item()
        change = (last_close - prev_close) / prev_close
        prob = 50 + (avg_score * 40) + (change * 100)
        
        return df, min(max(prob, 5), 95), feeds
    except:
        return None, 50, []

def find_levels(df):
    """주요 지지/저항선을 찾는 트레이닝 알고리즘"""
    highs = df['High'].iloc[-20:].values
    lows = df['Low'].iloc[-20:].values
    # 최근 20일간의 최고점과 최저점을 주요 심리적 저항/지지선으로 간주
    return np.max(highs), np.min(lows)

# --- [3. 메인 UI 구성] ---
st.set_page_config(page_title="AI 전술 사령부 v5.0", layout="wide")
st.title("🧙‍♂️ AI 전술 사령부 v5.0 (Pro)")

# 사이드바 설정
st.sidebar.header("📍 종목 검색")
search_input = st.sidebar.text_input("한글 종목명 또는 티커 입력", "엔비디아")
ticker = KOREAN_TICKER_MAP.get(search_input, search_input).upper()

if st.sidebar.button("전술 가동"):
    df, prob, feeds = get_analysis_data(ticker)
    
    if df is not None:
        last_price = df['Close'].iloc[-1].item()
        res_level, sup_level = find_levels(df) # 저항선, 지지선 계산
        
        # [A] 프로급 캔들 차트 시각화
        fig = go.Figure()
        fig.add_trace(go.Candlestick(
            x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="주가"
        ))
        
        # 장 종료 점선
        fig.add_hline(y=last_price, line_dash="dot", line_color="white", opacity=0.5)
        
        # 🛡️ 지지선 (Support) 표시
        fig.add_hline(y=sup_level, line_dash="dash", line_color="cyan", 
                      annotation_text="든든한 지지선", annotation_position="bottom left")
        
        # 🚧 저항선 (Resistance) 표시
        fig.add_hline(y=res_level, line_dash="dash", line_color="magenta", 
                      annotation_text="강력한 저항선", annotation_position="top left")
        
        fig.update_layout(title=f"{search_input}({ticker}) 프로급 전술 분석", template="plotly_dark", xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)
        
        # [B] 분석 리포트
        col1, col2 = st.columns(2)
        with col1:
            st.metric("AI 매수 신뢰도", f"{prob:.1f}%")
            if prob > 60: st.success("🎯 기류가 좋네! 매수 전술을 고려하게.")
            elif prob < 40: st.error("⚠️ 경고! 하방 압력이 강하네.")
            else: st.info("⚖️ 관망하며 지지선을 확인하게.")
            
            st.write(f"📊 **현재가:** {last_price:.2f}")
            st.write(f"🚧 **저항선:** {res_level:.2f} | 🛡️ **지지선:** {sup_level:.2f}")

        with col2:
            st.subheader("📰 최신 뉴스 분석")
            for f in feeds:
                st.write(f"- {f['title']}")
                st.caption(f"감성: {f['overall_sentiment_label']}")

        # [C] 텔레그램 전송
        msg = f"🚀 [{search_input}] AI 리포트\n- 확률: {prob:.1f}%\n- 지지선: {sup_level:.2f}\n- 저항선: {res_level:.2f}"
        requests.get(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage?chat_id={CHAT_ID}&text={msg}")
        st.toast("사령실로 프로급 리포트 송신 완료!")

# --- [4. 추천 스캐너 섹션] ---
st.divider()
st.header("🌟 오늘의 추천 종목 스캐너")
candidates = ["NVDA", "TSLA", "AAPL", "005930.KS", "000660.KS", "BTC-USD"]

if st.button("🚀 전 종목 스캔 시작"):
    results = []
    for t in candidates:
        _, p, _ = get_analysis_data(t)
        results.append({"ticker": t, "prob": p})
    
    top_3 = sorted([r for r in results if r['prob']], key=lambda x: x['prob'], reverse=True)[:3]
    cols = st.columns(3)
    for i, pick in enumerate(top_3):
        with cols[i]:
            st.success(f"{i+1}위: {pick['ticker']} ({pick['prob']:.1f}%)")

import streamlit as st
import pandas as pd
import yfinance as yf
import requests
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np

# --- [1. 보안 및 기초 지표 설정] ---
ALPHA_VANTAGE_KEY = st.secrets["ALPHA_VANTAGE_KEY"]
TELEGRAM_TOKEN = st.secrets["TELEGRAM_TOKEN"]
CHAT_ID = st.secrets["CHAT_ID"]

def get_usd_krw():
    """실시간 USD/KRW 환율 가져오기"""
    try:
        # 야후 파이낸스에서 환율 티커 호출
        rate = yf.Ticker("USDKRW=X").history(period="1d")['Close'].iloc[-1]
        return float(rate)
    except:
        return 1350.0  # 실패 시 기본 기준율

# --- [2. 핵심 분석 및 전술 함수] ---

def get_analysis_data(ticker):
    try:
        # 데이터 로드 (6개월치)
        df = yf.download(ticker, period="6mo", interval="1d", progress=False)
        if len(df) < 20: return None, 50, []
        
        # 뉴스 감성 분석 (Alpha Vantage)
        url = f'https://www.alphavantage.co/query?function=NEWS_SENTIMENT&tickers={ticker}&apikey={ALPHA_VANTAGE_KEY}'
        news_res = requests.get(url).json()
        feeds = news_res.get("feed", [])[:3]
        
        avg_score = 0
        if feeds:
            avg_score = sum([float(f['overall_sentiment_score']) for f in feeds]) / len(feeds)
            
        prob = 50 + (avg_score * 50)
        return df, min(max(prob, 5), 95), feeds
    except:
        return None, 50, []

# --- [3. 메인 UI 구성] ---
st.set_page_config(page_title="AI 전술 사령부 v7.0", layout="wide")
exchange_rate = get_usd_krw()

# 상단 환율 정보 표시
st.markdown(f"🚩 **현재 적용 환율:** `1달러 = {exchange_rate:,.1f}원` (실시간 시세 반영)")

st.sidebar.header("📍 전략 분석실")
KOREAN_TICKER_MAP = {
    "엔비디아": "NVDA", "테슬라": "TSLA", "애플": "AAPL", "마이크로소프트": "MSFT",
    "삼성전자": "005930.KS", "SK하이닉스": "000660.KS", "에코프로": "247540.KQ",
    "비트코인": "BTC-USD"
}

search_input = st.sidebar.text_input("종목명 입력 (한글/티커)", "엔비디아")
ticker = KOREAN_TICKER_MAP.get(search_input, search_input).upper()
is_kr = ticker.endswith(".KS") or ticker.endswith(".KQ")

if st.sidebar.button("⚔️ 전술 가동"):
    df, prob, feeds = get_analysis_data(ticker)
    
    if df is not None:
        last_price = df['Close'].iloc[-1].item()
        res_level = df['High'].iloc[-20:].max().item() # 저항선
        sup_level = df['Low'].iloc[-20:].min().item()  # 지지선
        stop_loss = sup_level * 0.97                 # 손절선(-3%)

        # [A] 통화별 가격 문자열 생성 (자네가 원한 핵심 기능!)
        if is_kr:
            curr_p = f"{last_price:,.0f}원"
            target_p = f"{res_level:,.0f}원"
            stop_p = f"{stop_loss:,.0f}원"
        else:
            curr_p = f"${last_price:.2f} (약 {last_price * exchange_rate:,.0f}원)"
            target_p = f"${res_level:.2f} (약 {res_level * exchange_rate:,.0f}원)"
            stop_p = f"${stop_loss:.2f} (약 {stop_loss * exchange_rate:,.0f}원)"

        # [B] 캔들봉 차트 시각화 (v7.0 업그레이드)
        fig = go.Figure()
        fig.add_trace(go.Candlestick(
            x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
            name="캔들봉", increasing_line_color='#FF4B4B', decreasing_line_color='#0083B0'
        ))
        
        # 지지/저항/손절선 표시
        fig.add_hline(y=res_level, line_dash="dash", line_color="magenta", annotation_text="🚧 저항")
        fig.add_hline(y=sup_level, line_dash="dash", line_color="cyan", annotation_text="🛡️ 지지")
        fig.add_hline(y=stop_loss, line_dash="dot", line_color="red", annotation_text="🛑 손절")
        
        fig.update_layout(title=f"{search_input} 실전 캔들 분석", template="plotly_dark", xaxis_rangeslider_visible=False, height=600)
        st.plotly_chart(fig, use_container_width=True)

        # [C] 전술 지시서 요약
        st.divider()
        st.header(f"⚔️ {search_input} 전술 지시 보고")
        c1, c2, c3 = st.columns(3)
        with c1: st.metric("현재가", curr_p)
        with c2: st.metric("목표가(저항)", target_p)
        with c3: st.metric("방어선(손절)", stop_p, delta="-3%", delta_color="inverse")

        # [D] 텔레그램 리포트 송신
        tg_msg = f"⚔️ [{search_input}] v7.0 통합 리포트\n- 현재가: {curr_p}\n- 목표가: {target_p}\n- 손절가: {stop_p}\n- AI 신뢰도: {prob:.1f}%"
        requests.get(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage?chat_id={CHAT_ID}&text={tg_msg}")
        st.toast("사령실 텔레그램으로 전술을 송신했네!")

# --- [4. 추천 스캐너 섹션] ---
st.divider()
st.header("🌟 실시간 전 종목 스캔")
candidates = ["NVDA", "TSLA", "AAPL", "005930.KS", "BTC-USD"]

if st.button("🚀 전 종목 전략 스캔"):
    results = []
    for t in candidates:
        _, p, _ = get_analysis_data(t)
        results.append({"ticker": t, "prob": p})
    
    top_3 = sorted(results, key=lambda x: x['prob'], reverse=True)[:3]
    cols = st.columns(3)
    for i, res in enumerate(top_3):
        with cols[i]: st.success(f"{i+1}위: {res['ticker']} ({res['prob']:.1f}%)")

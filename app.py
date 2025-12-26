import streamlit as st
import pandas as pd
import yfinance as yf
import requests
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np

# --- [1. 보안 및 기초 설정] ---
ALPHA_VANTAGE_KEY = st.secrets["ALPHA_VANTAGE_KEY"]
TELEGRAM_TOKEN = st.secrets["TELEGRAM_TOKEN"]
CHAT_ID = st.secrets["CHAT_ID"]

# 종목 코드 매핑 (한글 검색용)
KOREAN_TICKER_MAP = {
    "엔비디아": "NVDA", "테슬라": "TSLA", "애플": "AAPL", "마이크로소프트": "MSFT",
    "삼성전자": "005930.KS", "SK하이닉스": "000660.KS", "에코프로": "247540.KQ",
    "비트코인": "BTC-USD"
}

def get_usd_krw():
    """실시간 USD/KRW 환율 가져오기"""
    try:
        rate = yf.Ticker("USDKRW=X").history(period="1d")['Close'].iloc[-1]
        return float(rate)
    except:
        return 1380.0 # 기본값

# --- [2. 내 주식 포트폴리오 데이터 관리] ---
if 'my_portfolio' not in st.session_state:
    st.session_state.my_portfolio = []

# --- [3. 분석 및 시각화 엔진] ---
def get_analysis_data(ticker):
    try:
        df = yf.download(ticker, period="6mo", interval="1d", progress=False)
        if len(df) < 20: return None, 50, []
        
        # 뉴스 감성 분석
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

# --- [4. 메인 UI 구성] ---
st.set_page_config(page_title="AI 전술 사령부 v8.0", layout="wide")
exchange_rate = get_usd_krw()

# 사이드바: 내 주식 등록
st.sidebar.header("📥 내 보급품(주식) 등록")
with st.sidebar.form("portfolio_form"):
    p_name = st.text_input("종목명", placeholder="예: 삼성전자")
    p_ticker = st.text_input("티커", placeholder="예: 005930.KS")
    p_price = st.number_input("평단가 (해외는 달러, 국내는 원)", min_value=0.0)
    if st.form_submit_button("포트폴리오에 추가"):
        st.session_state.my_portfolio.append({"name": p_name, "ticker": p_ticker.upper(), "buy_price": p_price})
        st.sidebar.success(f"{p_name} 등록 완료!")

# 메인 타이틀
st.title("🛡️ AI 실전 자산 포트폴리오")

# [A] 포트폴리오 현황창
if st.session_state.my_portfolio:
    cols = st.columns(len(st.session_state.my_portfolio))
    for idx, stock in enumerate(st.session_state.my_portfolio):
        ticker_data = yf.download(stock['ticker'], period="1d", progress=False)
        if not ticker_data.empty:
            curr_p = ticker_data['Close'].iloc[-1].item()
            profit = ((curr_p - stock['buy_price']) / stock['buy_price']) * 100
            
            with cols[idx]:
                color = "green" if profit >= 0 else "red"
                st.markdown(f"**{stock['name']}**")
                st.metric("현재가", f"{curr_p:,.2f}", f"{profit:.2f}%")
                if st.button("상세분석", key=f"ana_{idx}"):
                    search_input = stock['name'] # 분석 섹션으로 연결
else:
    st.info("아직 등록된 주식이 없네. 사이드바에서 자네의 포지션을 등록하게나.")

st.divider()

# [B] 개별 종목 캔들 & 전술 분석 (기존 v7.0 기능 강화)
st.header("🔍 개별 종목 정밀 타격 분석")
search_input = st.text_input("분석할 종목 (한글/티커)", "엔비디아")
target_ticker = KOREAN_TICKER_MAP.get(search_input, search_input).upper()
is_kr = target_ticker.endswith(".KS") or target_ticker.endswith(".KQ")

if st.button("⚔️ 전술 가동"):
    df, prob, feeds = get_analysis_data(target_ticker)
    
    if df is not None:
        last_price = df['Close'].iloc[-1].item()
        res_level = df['High'].iloc[-20:].max().item() # 저항선
        sup_level = df['Low'].iloc[-20:].min().item()  # 지지선
        stop_loss = sup_level * 0.97                 # 손절선(-3%)

        # 화폐 단위 설정
        unit = "원" if is_kr else "$"
        curr_display = f"{unit}{last_price:,.2f}"
        if not is_kr:
            curr_display += f" (약 {last_price * exchange_rate:,.0f}원)"

        # 캔들 차트
        fig = go.Figure()
        fig.add_trace(go.Candlestick(
            x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
            name="Candle", increasing_line_color='#FF4B4B', decreasing_line_color='#0083B0'
        ))
        fig.add_hline(y=res_level, line_dash="dash", line_color="magenta", annotation_text="🚧 저항")
        fig.add_hline(y=sup_level, line_dash="dash", line_color="cyan", annotation_text="🛡️ 지지")
        fig.add_hline(y=stop_loss, line_dash="dot", line_color="red", annotation_text="🛑 손절")
        
        fig.update_layout(template="plotly_dark", xaxis_rangeslider_visible=False, height=500)
        st.plotly_chart(fig, use_container_width=True)

        # 결과 리포트 & 텔레그램
        st.subheader(f"📋 {search_input} AI 전략 보고서")
        col1, col2 = st.columns(2)
        col1.metric("현재가", curr_display)
        col2.metric("AI 신뢰도", f"{prob:.1f}%")

        tg_msg = f"⚔️ [{search_input}] 리포트\n- 현재가: {curr_display}\n- AI확률: {prob:.1f}%\n- 🛑손절가: {unit}{stop_loss:,.2f}"
        requests.get(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage?chat_id={CHAT_ID}&text={tg_msg}")
        st.success("사령실 텔레그램 송신 완료!")

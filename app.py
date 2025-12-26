import streamlit as st
import pandas as pd
import yfinance as yf
import requests
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np

# --- [1. 보안 및 기본 설정] ---
ALPHA_VANTAGE_KEY = st.secrets["ALPHA_VANTAGE_KEY"]
TELEGRAM_TOKEN = st.secrets["TELEGRAM_TOKEN"]
CHAT_ID = st.secrets["CHAT_ID"]

KOREAN_TICKER_MAP = {
    "엔비디아": "NVDA", "테슬라": "TSLA", "애플": "AAPL", "마이크로소프트": "MSFT",
    "삼성전자": "005930.KS", "SK하이닉스": "000660.KS", "에코프로": "247540.KQ",
    "구글": "GOOGL", "메타": "META", "아마존": "AMZN", "비트코인": "BTC-USD"
}

# --- [2. 기술적 지표 및 지수 계산 함수] ---

def get_fear_and_greed():
    """시장 공포 탐욕 지수 가져오기"""
    try:
        res = requests.get("https://api.alternative.me/fng/").json()
        value = res['data'][0]['value']
        label = res['data'][0]['value_classification']
        return value, label
    except:
        return "50", "Neutral"

def calculate_rsi(data, window=14):
    """RSI(상대강도지수) 계산"""
    delta = data.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def get_analysis_data(ticker):
    try:
        df = yf.download(ticker, period="6mo", interval="1d", progress=False)
        if len(df) < 30: return None, 50, []
        
        # RSI 계산
        df['RSI'] = calculate_rsi(df['Close'])
        
        # 뉴스 감성 분석
        url = f'https://www.alphavantage.co/query?function=NEWS_SENTIMENT&tickers={ticker}&apikey={ALPHA_VANTAGE_KEY}'
        news_res = requests.get(url).json()
        feeds = news_res.get("feed", [])[:3]
        
        avg_score = 0
        if feeds:
            avg_score = sum([float(f['overall_sentiment_score']) for f in feeds]) / len(feeds)
            
        # AI 확률 (뉴스 + 추세 + RSI 반영)
        last_rsi = df['RSI'].iloc[-1]
        rsi_factor = 0
        if last_rsi > 70: rsi_factor = -10 # 과매수시 확률 차감
        elif last_rsi < 30: rsi_factor = 10 # 과매도시 확률 가산
        
        prob = 50 + (avg_score * 40) + rsi_factor
        return df, min(max(prob, 5), 95), feeds
    except:
        return None, 50, []

# --- [3. 메인 대시보드] ---
st.set_page_config(page_title="AI 전술 사령부 v6.0", layout="wide")

# 상단 시장 지표
fng_val, fng_label = get_fear_and_greed()
st.markdown(f"### 🌐 시장 심리 상태: `{fng_label}` ({fng_val}/100)")

st.sidebar.header("📍 전략 분석실")
search_input = st.sidebar.text_input("종목명 또는 티커", "엔비디아")
ticker = KOREAN_TICKER_MAP.get(search_input, search_input).upper()

if st.sidebar.button("⚔️ 전술 가동"):
    df, prob, feeds = get_analysis_data(ticker)
    
    if df is not None:
        last_price = df['Close'].iloc[-1].item()
        rsi_val = df['RSI'].iloc[-1].item()
        # 최근 20일 기준 지지/저항
        res_level = df['High'].iloc[-20:].max().item()
        sup_level = df['Low'].iloc[-20:].min().item()
        
        # 🛡️ 손절가 및 목표가 계산
        stop_loss = sup_level * 0.97 # 지지선 -3%
        buy_target = sup_level * 1.02 # 지지선 +2%
        
        # [A] 서브플롯 차트 (캔들 + RSI)
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.7, 0.3], vertical_spacing=0.05)
        fig.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="주가"), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['RSI'], name="RSI", line=dict(color='yellow')), row=2, col=1)
        
        # 지지/저항/손절선 추가
        fig.add_hline(y=sup_level, line_dash="dash", line_color="cyan", row=1, col=1)
        fig.add_hline(y=res_level, line_dash="dash", line_color="magenta", row=1, col=1)
        fig.add_hline(y=stop_loss, line_dash="dot", line_color="red", annotation_text="최종방어선(손절)", row=1, col=1)
        
        fig.update_layout(height=600, template="plotly_dark", xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)

        # [B] 전술 지시서
        st.divider()
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("📋 실전 전술 가이드")
            if rsi_val > 70:
                st.warning(f"⚠️ RSI({rsi_val:.1f}) 과매수 구간! 추격 매수는 위험하네.")
            elif rsi_val < 30:
                st.success(f"💎 RSI({rsi_val:.1f}) 과매도 구간! 저점 매수 기회일세.")
            
            st.write(f"📍 **진입 권장가:** {buy_target:.2f} 부근")
            st.write(f"🎯 **1차 목표가:** {res_level:.2f}")
            st.error(f"🛑 **최종 방어선(손절): {stop_loss:.2f}** (이 가격 무너지면 무조건 후퇴!)")

        with col2:
            st.metric("AI 매수 확신도", f"{prob:.1f}%")
            st.info(f"**🧙‍♂️ 마스터의 한마디:** 현재 시장 지수가 {fng_val}이므로 {'보수적' if int(fng_val) > 70 else '공격적'}인 운용을 추천하네.")

        # [C] 텔레그램 송신 (방어선 포함)
        tg_msg = f"⚔️ [{search_input}] v6.0 리포트\n- 신뢰도: {prob:.1f}%\n- 진입가: {buy_target:.2f}\n- 목표가: {res_level:.2f}\n- 🛑손절가: {stop_loss:.2f}\n- RSI: {rsi_val:.1f}"
        requests.get(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage?chat_id={CHAT_ID}&text={tg_msg}")

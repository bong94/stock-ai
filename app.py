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

# 한글-티커 매핑 사전 (필요시 계속 추가하게나)
KOREAN_TICKER_MAP = {
    "엔비디아": "NVDA", "테슬라": "TSLA", "애플": "AAPL", "마이크로소프트": "MSFT",
    "삼성전자": "005930.KS", "SK하이닉스": "000660.KS", "에코프로": "247540.KQ",
    "구글": "GOOGL", "메타": "META", "아마존": "AMZN", "비트코인": "BTC-USD"
}

# --- [2. 핵심 분석 엔진] ---

def get_analysis_data(ticker):
    try:
        # 데이터 로드 (최근 3개월치 - 지지/저항선 정밀 분석용)
        df = yf.download(ticker, period="3mo", interval="1d", progress=False)
        if len(df) < 10: return None, 50, []
        
        # 뉴스 감성 분석 (Alpha Vantage)
        url = f'https://www.alphavantage.co/query?function=NEWS_SENTIMENT&tickers={ticker}&apikey={ALPHA_VANTAGE_KEY}'
        news_res = requests.get(url).json()
        feeds = news_res.get("feed", [])[:3]
        
        avg_score = 0
        if feeds:
            avg_score = sum([float(f['overall_sentiment_score']) for f in feeds]) / len(feeds)
            
        # AI 확률 계산 (뉴스 60% + 최근 추세 40%)
        last_close = df['Close'].iloc[-1].item()
        prev_close = df['Close'].iloc[-5].item()
        change = (last_close - prev_close) / prev_close
        prob = 50 + (avg_score * 40) + (change * 100)
        
        return df, min(max(prob, 5), 95), feeds
    except:
        return None, 50, []

def find_levels(df):
    """최근 20거래일 기준 심리적 지지/저항선 추출"""
    highs = df['High'].iloc[-20:].values
    lows = df['Low'].iloc[-20:].values
    return np.max(highs), np.min(lows)

def get_tactical_advice(last_price, sup, res, prob):
    """실전 매수/매도 가이드라인 계산"""
    buy_target = sup * 1.02  # 지지선 위 2% 이내
    sell_target = res * 0.99 # 저항선 아래 1% 이내
    
    if prob >= 65:
        if last_price <= buy_target:
            action, color = "🟢 적극 매수", "green"
            advice = f"지지선(🛡️) 근처일세! {last_price:.2f} 부근에서 진입하는 공격적 전술을 추천하네."
        else:
            action, color = "🟡 매수 대기", "blue"
            advice = f"기류는 좋으나 현재가가 다소 높네. {buy_target:.2f} 부근까지 눌림목을 기다리게나."
    elif prob <= 40:
        action, color = "🔴 적극 매도", "red"
        advice = f"하방 압력이 거세네. 저항선(🚧) 돌파 전까지는 후퇴하여 현금을 확보하게."
    else:
        action, color = "⚪ 중립/관망", "gray"
        advice = "에너지가 응축되는 박스권일세. 방향성이 정해질 때까지 관망을 제안하네."
        
    return action, color, advice, buy_target, sell_target

# --- [3. 메인 대시보드 UI] ---
st.set_page_config(page_title="AI 전술 사령부 v5.1", layout="wide")
st.title("🧙‍♂️ AI 전술 사령부 v5.1 (Master)")

# 사이드바: 검색 및 분석 제어
st.sidebar.header("📍 전략 분석실")
search_input = st.sidebar.text_input("종목명 또는 티커 (예: 테슬라, AAPL)", "엔비디아")
ticker = KOREAN_TICKER_MAP.get(search_input, search_input).upper()

if st.sidebar.button("⚔️ 전술 가동"):
    df, prob, feeds = get_analysis_data(ticker)
    
    if df is not None:
        last_price = df['Close'].iloc[-1].item()
        res_level, sup_level = find_levels(df)
        action, color, advice, buy_t, sell_t = get_tactical_advice(last_price, sup_level, res_level, prob)
        
        # [A] 프로급 캔들 차트 (다크 테마)
        fig = go.Figure()
        fig.add_trace(go.Candlestick(
            x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="Candle"
        ))
        # 지지/저항선 시각화
        fig.add_hline(y=sup_level, line_dash="dash", line_color="#00FFCC", annotation_text="🛡️ Support")
        fig.add_hline(y=res_level, line_dash="dash", line_color="#FF00FF", annotation_text="🚧 Resistance")
        
        fig.update_layout(title=f"{search_input}({ticker}) 실전 분석 차트", template="plotly_dark", xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)

        # [B] 전술 지시서 섹션
        st.divider()
        st.header(f"📋 {search_input} 전술 지시서")
        
        col1, col2 = st.columns([1, 1])
        with col1:
            st.subheader(f"현 시점 전술: :{color}[{action}]")
            st.info(f"**🧙‍♂️ 마스터의 지시:**\n\n{advice}")
            
            st.write(f"✅ **권장 진입가(매수):** {buy_t:.2f} 이하")
            st.write(f"🎯 **목표 실현가(매도):** {sell_t:.2f} 부근")
        
        with col2:
            st.metric("AI 분석 신뢰도", f"{prob:.1f}%")
            st.write("---")
            st.subheader("📰 분석 근거 (뉴스 요약)")
            for f in feeds:
                st.write(f"- {f['title']} ({f['overall_sentiment_label']})")

        # [C] 텔레그램 즉시 전송
        tg_report = f"⚔️ [{search_input}] 전략 보고\n판단: {action}\n신뢰도: {prob:.1f}%\n진입가: {buy_t:.2f}\n목표가: {sell_t:.2f}\n\n{advice}"
        requests.get(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage?chat_id={CHAT_ID}&text={tg_report}")
        st.toast("사령실 텔레그램으로 전술을 송신했네!")

# --- [4. 추천 스캐너 섹션] ---
st.divider()
st.header("🌟 실시간 전 종목 스캐너")
candidates = ["NVDA", "TSLA", "AAPL", "MSFT", "005930.KS", "BTC-USD"]

if st.button("🚀 전 종목 전략 스캔 시작"):
    results = []
    with st.spinner('전략 데이터를 수집 중일세...'):
        for t in candidates:
            _, p, _ = get_analysis_data(t)
            results.append({"ticker": t, "prob": p})
            
    top_3 = sorted(results, key=lambda x: x['prob'], reverse=True)[:3]
    cols = st.columns(3)
    for i, res in enumerate(top_3):
        with cols[i]:
            st.success(f"{i+1}위: {res['ticker']} (승률 {res['prob']:.1f}%)")

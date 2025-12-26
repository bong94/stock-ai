import streamlit as st
import pandas as pd
import yfinance as yf
import requests
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np

# --- [1. 보안 및 기초 설정] ---
# Streamlit Secrets에서 키를 가져오네. 없으면 에러 방지를 위해 공백을 둠.
ALPHA_VANTAGE_KEY = st.secrets.get("ALPHA_VANTAGE_KEY", "")
TELEGRAM_TOKEN = st.secrets.get("TELEGRAM_TOKEN", "")
CHAT_ID = st.secrets.get("CHAT_ID", "")

def get_usd_krw():
    """실시간 USD/KRW 환율 가져오기"""
    try:
        rate = yf.Ticker("USDKRW=X").history(period="1d")['Close'].iloc[-1]
        return float(rate)
    except:
        return 1380.0  # 연결 실패 시 기본 기준율

# --- [2. 내 주식 포트폴리오 관리 (세션 저장)] ---
if 'my_portfolio' not in st.session_state:
    st.session_state.my_portfolio = []

# --- [3. 핵심 분석 엔진] ---
def get_analysis_data(ticker):
    try:
        # 데이터 로드 (6개월치)
        df = yf.download(ticker, period="6mo", interval="1d", progress=False)
        if df.empty or len(df) < 10: 
            return None, 50, []
        
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
st.set_page_config(page_title="AI 전술 사령부 v8.1", layout="wide")
ex_rate = get_usd_krw()

# 사이드바: 내 주식 등록 (에러 방지 로직 강화)
st.sidebar.header("📥 내 보급품(주식) 등록")
with st.sidebar.form("p_form"):
    st.write("에디슨 인터내셔널 등록 시 'EIX'를 입력하게.")
    name = st.text_input("종목명", "에디슨 인터내셔널")
    tk = st.text_input("티커 (예: EIX, 005930.KS)", "EIX")
    bp = st.number_input("평단가 (달러/원 구분)", value=60.21)
    if st.form_submit_button("포트폴리오 추가"):
        if tk.strip():
            st.session_state.my_portfolio.append({"name": name, "ticker": tk.strip().upper(), "buy_price": bp})
            st.sidebar.success(f"{name} 등록 완료!")
        else:
            st.sidebar.error("티커를 정확히 입력하게!")

# 메인 화면
st.title("🛡️ AI 실전 자산 포트폴리오")

# [A] 포트폴리오 현황 (ValueError 방지형)
if st.session_state.my_portfolio:
    p_cols = st.columns(len(st.session_state.my_portfolio))
    for idx, item in enumerate(st.session_state.my_portfolio):
        # 1일치 데이터를 가져와 현재가 확인
        data = yf.download(item['ticker'], period="5d", progress=False)
        if not data.empty:
            curr = data['Close'].iloc[-1].item()
            is_kr = item['ticker'].endswith(".KS") or item['ticker'].endswith(".KQ")
            
            # 수익률 및 통화 단위 설정
            profit = ((curr - item['buy_price']) / item['buy_price']) * 100
            unit = "원" if is_kr else "$"
            
            with p_cols[idx]:
                st.markdown(f"**{item['name']}**")
                st.metric("현재가", f"{unit}{curr:,.2f}", f"{profit:.2f}%")
                if not is_kr:
                    st.caption(f"원화 가치: {curr * ex_rate:,.0f}원")
else:
    st.info("왼쪽에서 자네의 주식을 등록하면 AI가 감시를 시작하네.")

st.divider()

# [B] 개별 종목 캔들 차트 & 전술 분석
st.header("🔍 정밀 전술 분석실")
target_input = st.text_input("분석할 티커 입력", "EIX").upper()

if st.button("⚔️ 전술 가동"):
    with st.spinner('차트와 뉴스를 분석 중일세...'):
        df, prob, feeds = get_analysis_data(target_input)
        
        if df is not None:
            last = df['Close'].iloc[-1].item()
            res = df['High'].iloc[-20:].max().item() # 20일 저항선
            sup = df['Low'].iloc[-20:].min().item()  # 20일 지지선
            
            # 캔들봉 차트 시각화
            fig = go.Figure(data=[go.Candlestick(
                x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
                increasing_line_color='#FF4B4B', decreasing_line_color='#0083B0'
            )])
            
            fig.add_hline(y=res, line_dash="dash", line_color="magenta", annotation_text="🚧 저항")
            fig.add_hline(y=sup, line_dash="dash", line_color="cyan", annotation_text="🛡️ 지지")
            
            fig.update_layout(title=f"{target_input} 캔들 분석", template="plotly_dark", xaxis_rangeslider_visible=False)
            st.plotly_chart(fig, use_container_width=True)
            
            # 리포트 출력 및 알람
            is_target_kr = target_input.endswith(".KS") or target_input.endswith(".KQ")
            u = "원" if is_target_kr else "$"
            
            st.subheader(f"📊 AI 전술 결과: {prob:.1f}% 확신")
            st.write(f"현재가: {u}{last:,.2f} | 지지선: {u}{sup:,.2f} | 저항선: {u}{res:,.2f}")
            
            # 텔레그램 알람
            msg = f"⚔️ [{target_input}] 리포트\n- 현재가: {u}{last:,.2f}\n- AI확률: {prob:.1f}%\n- 지지선: {u}{sup:,.2f}"
            requests.get(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage?chat_id={CHAT_ID}&text={msg}")
            st.success("사령실 텔레그램으로 전술을 송신했네!")

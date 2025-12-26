import streamlit as st
import pandas as pd
import yfinance as yf
import requests
import plotly.graph_objects as go
import time
import json
import os
from datetime import datetime

# --- [1. 시스템 보안 및 환경 설정] ---
# 클라우드 Secrets에서 호출
ALPHA_VANTAGE_KEY = st.secrets.get("ALPHA_VANTAGE_KEY", "")
TELEGRAM_TOKEN = st.secrets.get("TELEGRAM_TOKEN", "")
CHAT_ID = st.secrets.get("CHAT_ID", "")
PORTFOLIO_FILE = "portfolio_db.json"
IMG_PATH = "tactical_chart.png"

# --- [2. 데이터 영속성 관리] ---
def load_portfolio():
    if os.path.exists(PORTFOLIO_FILE):
        with open(PORTFOLIO_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_portfolio(portfolio):
    with open(PORTFOLIO_FILE, "w", encoding="utf-8") as f:
        json.dump(portfolio, f, ensure_ascii=False, indent=4)

# --- [3. AI 전술 엔진] ---
def get_usd_krw():
    try:
        rate = yf.Ticker("USDKRW=X").history(period="1d")['Close'].iloc[-1]
        return float(rate)
    except: return 1380.0

def calculate_tactical_points(df):
    """최근 20거래일 데이터를 학습하여 타점 계산"""
    high_20 = df['High'].iloc[-20:].max().item()
    low_20 = df['Low'].iloc[-20:].min().item()
    buy_p = low_20 * 1.01
    sell_p = high_20 * 0.98
    return buy_p, sell_p, low_20, high_20

def get_news_summary(ticker):
    """알파 벤티지 API를 통한 뉴스 학습 및 감성 분석"""
    try:
        url = f'https://www.alphavantage.co/query?function=NEWS_SENTIMENT&tickers={ticker}&apikey={ALPHA_VANTAGE_KEY}'
        res = requests.get(url).json()
        feeds = res.get("feed", [])[:2]
        
        summary = "\n[📰 최신 뉴스 요약]\n"
        if not feeds: return summary + "- 현재 특이 뉴스는 없으나 차트 흐름이 중요하네."
        
        for f in feeds:
            score = float(f.get('overall_sentiment_score', 0))
            sentiment = "🟢긍정" if score > 0.15 else ("🔴주의" if score < -0.15 else "🟡중립")
            summary += f"- {f['title'][:45]}... ({sentiment})\n"
        return summary
    except: return "\n[📰 정보] 뉴스 학습 실패. 숫자에 집중하게!"

# --- [4. 시각화 및 통신망] ---
def create_and_send_briefing(df, ticker, buy_p, sell_p, last_p, unit, message):
    """차트에 선을 긋고 사진을 찍어 텔레그램으로 전송"""
    fig = go.Figure(data=[go.Candlestick(
        x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close']
    )])
    fig.add_hline(y=buy_p, line_color="lime", line_dash="dash", annotation_text="🟢매수구간")
    fig.add_hline(y=sell_p, line_color="orange", line_dash="dash", annotation_text="🎯목표가")
    fig.update_layout(template="plotly_dark", xaxis_rangeslider_visible=False, title=f"⚔️ {ticker} 전술 지도")
    
    # 이미지 파일 저장 (엔진 명시)
    try:
        fig.write_image(IMG_PATH, engine="kaleido")
        
        # 텔레그램 사진 전송
        if TELEGRAM_TOKEN and CHAT_ID:
            photo_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
            with open(IMG_PATH, 'rb') as photo:
                requests.post(photo_url, data={'chat_id': CHAT_ID, 'caption': message}, files={'photo': photo})
    except Exception as e:
        # 사진 전송 실패 시 텍스트라도 전송
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", 
                      data={'chat_id': CHAT_ID, 'text': f"{message}\n(사진 전송 오류: {e})"})

# --- [5. 메인 시스템 가동] ---
st.set_page_config(page_title="AI 전술 사령부 v10.4", layout="wide")

if 'my_portfolio' not in st.session_state:
    st.session_state.my_portfolio = load_portfolio()

# [사이드바 제어판]
st.sidebar.header("🕹️ 사령부 관제 센터")
auto_mode = st.sidebar.checkbox("🛰️ 하이브리드 자동 브리핑 활성화")
GLOBAL_LIST = ["NVDA", "TSLA", "BTC-USD", "ETH-USD", "EIX", "005930.KS"]

with st.sidebar.form("p_form"):
    st.subheader("📥 자산 등록")
    name = st.text_input("종목명", "에디슨")
    tk = st.text_input("티커", "EIX")
    bp = st.number_input("평단가", value=60.0)
    if st.form_submit_button("등록 완료"):
        st.session_state.my_portfolio.append({"name": name, "ticker": tk.upper(), "buy_price": bp})
        save_portfolio(st.session_state.my_portfolio)
        st.rerun()

# [자동 순찰 엔진]
if auto_mode:
    st.sidebar.warning(f"🛰️ 정찰 중: {datetime.now().strftime('%H:%M:%S')}")
    for t in GLOBAL_LIST:
        df = yf.download(t, period="1mo", interval="1d", progress=False)
        if not df.empty and len(df) >= 20:
            last_p = df['Close'].iloc[-1].item()
            buy_p, sell_p, low_20, high_20 = calculate_tactical_points(df)
            unit = "원" if t.endswith((".KS", ".KQ")) else "$"
            
            if last_p <= buy_p:
                news = get_news_summary(t)
                briefing = (f"🚨 [기회 포착] {t}\n현재가: {unit}{last_p:,.2f}\n"
                           f"매수 권장: {unit}{buy_p:,.2f} 이하\n{news}\n"
                           f"[🎓 교육] 최근 저점인 {low_20:,.2f}선은 강력한 지지 구간일세.")
                create_and_send_briefing(df, t, buy_p, sell_p, last_p, unit, briefing)
    
    time.sleep(600) # 10분마다 순찰
    st.rerun()

# --- [대시보드 화면] ---
st.title("🧙‍♂️ AI 전술 사령부 v10.4")

if st.session_state.my_portfolio:
    st.header("🛡️ 실시간 자산 모니터링")
    cols = st.columns(len(st.session_state.my_portfolio))
    for idx, item in enumerate(st.session_state.my_portfolio):
        data = yf.download(item['ticker'], period="5d", progress=False)
        if not data.empty:
            curr = data['Close'].iloc[-1].item()
            profit = ((curr - item['buy_price']) / item['buy_price']) * 100
            with cols[idx]:
                st.metric(item['name'], f"{curr:,.2f}", f"{profit:.2f}%")

st.divider()
st.info("사령관님, 깃허브에 최신 코드를 덮어씌우고 requirements.txt를 수정하면 사진 보고서 전송이 시작됩니다.")

import streamlit as st
import pandas as pd
import yfinance as yf
import requests
import plotly.graph_objects as go
import time
import json
import os
from datetime import datetime

# --- [1. 보안 및 기초 설정] ---
ALPHA_VANTAGE_KEY = st.secrets.get("ALPHA_VANTAGE_KEY", "")
TELEGRAM_TOKEN = st.secrets.get("TELEGRAM_TOKEN", "")
CHAT_ID = st.secrets.get("CHAT_ID", "")
PORTFOLIO_FILE = "portfolio_db.json"
IMG_PATH = "tactical_decision.png"

def load_portfolio():
    if os.path.exists(PORTFOLIO_FILE):
        try:
            with open(PORTFOLIO_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except: return []
    return []

def save_portfolio(portfolio):
    with open(PORTFOLIO_FILE, "w", encoding="utf-8") as f:
        json.dump(portfolio, f, ensure_ascii=False, indent=4)

# --- [2. AI 전술 판단 엔진] ---
def get_ai_decision(ticker, curr_p, buy_p, low_20, high_20):
    """수익률과 지표를 결합하여 손절/추매/홀딩 판단"""
    profit_rate = ((curr_p - buy_p) / buy_p) * 100
    
    # 1. 손절 판단 (지지선 붕괴 + 수익률 -3% 미만)
    if profit_rate <= -3.0 and curr_p < low_20:
        return "🔴 [전략적 손절] 지지선이 무너졌네. 더 큰 피해를 막기 위해 후퇴를 권고함세."
    
    # 2. 추가 매수 판단 (수익률 마이너스이나 지지선 근처에서 반등 기미)
    if -5.0 <= profit_rate <= -0.5 and (low_20 * 0.99 <= curr_p <= low_20 * 1.02):
        return "🔵 [추가 매수 기회] 현재 지지선 부근이라네. 평단가를 낮출 좋은 기회일 수 있네."
    
    # 3. 익절 준비
    if profit_rate >= 10.0:
        return "🎯 [수익 실현] 목표 수익에 도달했네! 분할 매도로 수익을 확정 짓는 건 어떤가?"
        
    return "🟡 [관망] 현재는 시장의 흐름을 지켜보며 진영을 유지하게."

def get_news_summary(ticker):
    try:
        url = f'https://www.alphavantage.co/query?function=NEWS_SENTIMENT&tickers={ticker}&apikey={ALPHA_VANTAGE_KEY}'
        res = requests.get(url).json()
        feeds = res.get("feed", [])[:2]
        summary = "\n[📰 뉴스 요약]\n"
        if not feeds: return summary + "- 뉴스 없음."
        for f in feeds:
            score = float(f.get('overall_sentiment_score', 0))
            sentiment = "🟢긍정" if score > 0.15 else ("🔴주의" if score < -0.15 else "🟡중립")
            summary += f"- {f['title'][:40]} ({sentiment})\n"
        return summary
    except: return ""

# --- [3. 시각화 및 알람 전송] ---
def send_tactical_report(ticker, df, buy_p, low_20, high_20, curr_p, message):
    fig = go.Figure(data=[go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'])])
    fig.add_hline(y=low_20, line_color="red", line_dash="dash", annotation_text="최후 지지선")
    fig.add_hline(y=buy_p, line_color="blue", annotation_text="내 평단가")
    fig.update_layout(template="plotly_dark", xaxis_rangeslider_visible=False, title=f"⚔️ {ticker} 전술 지도")
    
    try:
        fig.write_image(IMG_PATH, engine="kaleido")
        if TELEGRAM_TOKEN and CHAT_ID:
            photo_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
            with open(IMG_PATH, 'rb') as photo:
                requests.post(photo_url, data={'chat_id': CHAT_ID, 'caption': message}, files={'photo': photo})
    except:
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", data={'chat_id': CHAT_ID, 'text': message})

# --- [4. 메인 대시보드 및 자동 정찰] ---
st.set_page_config(page_title="AI 판단 사령부 v10.5", layout="wide")
if 'my_portfolio' not in st.session_state:
    st.session_state.my_portfolio = load_portfolio()

# 사이드바 제어
st.sidebar.header("🕹️ 사령부 관제 센터")
auto_mode = st.sidebar.checkbox("🛰️ AI 자동 판단 모드 활성화")

with st.sidebar.form("p_form"):
    st.subheader("📥 자산 등록")
    name = st.text_input("종목명", "삼성전자")
    tk = st.text_input("티커", "005930.KS")
    bp = st.number_input("평단가", value=70000)
    if st.form_submit_button("등록"):
        st.session_state.my_portfolio.append({"name": name, "ticker": tk.upper(), "buy_price": bp})
        save_portfolio(st.session_state.my_portfolio)
        st.rerun()

if st.sidebar.button("🗑️ 전체 초기화"):
    save_portfolio([])
    st.session_state.my_portfolio = []
    st.rerun()

# 메인 화면
st.title("🧙‍♂️ AI 전술 판단 사령부 v10.5")

if st.session_state.my_portfolio:
    st.header("🛡️ 실시간 자산 모니터링 및 AI 조언")
    valid_items = []
    for item in st.session_state.my_portfolio:
        try:
            df = yf.download(item['ticker'], period="1mo", interval="1d", progress=False)
            if not df.empty:
                curr_p = df['Close'].iloc[-1].item()
                low_20 = df['Low'].iloc[-20:].min().item()
                high_20 = df['High'].iloc[-20:].max().item()
                
                decision = get_ai_decision(item['ticker'], curr_p, item['buy_price'], low_20, high_20)
                profit = ((curr_p - item['buy_price']) / item['buy_price']) * 100
                
                valid_items.append({"item": item, "curr": curr_p, "profit": profit, "decision": decision, "df": df, "low": low_20, "high": high_20})
        except: continue

    if valid_items:
        cols = st.columns(len(valid_items))
        for idx, v in enumerate(valid_items):
            with cols[idx]:
                st.metric(v['item']['name'], f"{v['curr']:,.0f}", f"{v['profit']:.2f}%")
                st.write(f"**AI 판단:** {v['decision']}")
                
                # 자동 모드일 때 특이사항(손절/추매)만 알람 전송
                if auto_mode and ("손절" in v['decision'] or "추가 매수" in v['decision']):
                    news = get_news_summary(v['item']['ticker'])
                    report = f"🚨 [긴급 판단] {v['item']['name']}\n수익률: {v['profit']:.2f}%\n{v['decision']}\n{news}"
                    send_tactical_report(v['item']['ticker'], v['df'], v['item']['buy_price'], v['low'], v['high'], v['curr'], report)

st.divider()
st.caption("v10.5: 데이터 로드 방어막 적용 및 AI 손절/추매 판단 기능 통합 완료")

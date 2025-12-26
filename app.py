import streamlit as st
import pandas as pd
import yfinance as yf
import requests
import plotly.graph_objects as go
import time
import json
import os
from datetime import datetime

# --- [1. 보안 및 설정] ---
ALPHA_VANTAGE_KEY = st.secrets.get("ALPHA_VANTAGE_KEY", "")
TELEGRAM_TOKEN = st.secrets.get("TELEGRAM_TOKEN", "")
CHAT_ID = st.secrets.get("CHAT_ID", "")
PORTFOLIO_FILE = "portfolio_db.json"
IMG_PATH = "tactical_briefing.png"

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
def get_ai_decision(curr_p, buy_p, low_20):
    profit_rate = ((curr_p - buy_p) / buy_p) * 100
    if profit_rate <= -3.0 and curr_p < low_20:
        return "🔴 [전략적 손절] 지지선 붕괴. 후퇴를 권고함세."
    if -5.0 <= profit_rate <= -0.5 and (low_20 * 0.99 <= curr_p <= low_20 * 1.02):
        return "🔵 [추가 매수 기회] 지지선 반등 구간이니 매복을 검토하게."
    if profit_rate >= 10.0:
        return "🎯 [수익 실현] 익절 타점일세! 전리품을 챙기게."
    return "🟡 [관망] 현재는 진영을 유지하며 지켜보게."

# --- [3. 통신 및 시각화] ---
def send_telegram_with_chart(ticker, df, buy_p, low_20, message):
    fig = go.Figure(data=[go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'])])
    fig.add_hline(y=low_20, line_color="red", line_dash="dash", annotation_text="최후 지지선")
    fig.add_hline(y=buy_p, line_color="blue", annotation_text="사령관 평단가")
    fig.update_layout(template="plotly_dark", xaxis_rangeslider_visible=False, title=f"⚔️ {ticker} 전술 지도")
    try:
        fig.write_image(IMG_PATH, engine="kaleido")
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
        with open(IMG_PATH, 'rb') as photo:
            requests.post(url, data={'chat_id': CHAT_ID, 'caption': message}, files={'photo': photo})
    except:
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", data={'chat_id': CHAT_ID, 'text': message})

# --- [4. 메인 대시보드 가동] ---
st.set_page_config(page_title="AI 전술 사령부 v10.7", layout="wide")
if 'my_portfolio' not in st.session_state:
    st.session_state.my_portfolio = load_portfolio()

# [사이드바: 관제 센터]
st.sidebar.header("🕹️ 사령부 관제 센터")
auto_mode = st.sidebar.checkbox("🛰️ AI 자동 판단 알람 가동")

with st.sidebar.form("input_form"):
    st.subheader("📥 신규 자산 배치")
    name = st.text_input("종목명", "삼성전자")
    tk = st.text_input("티커", "005930.KS")
    bp = st.number_input("평단가", value=0)
    if st.form_submit_button("배치 완료"):
        st.session_state.my_portfolio.append({"name": name, "ticker": tk.upper(), "buy_price": bp})
        save_portfolio(st.session_state.my_portfolio)
        st.rerun()

if st.sidebar.button("🗑️ 전체 데이터 초기화"):
    save_portfolio([])
    st.session_state.my_portfolio = []
    st.rerun()

# [메인 전황판]
st.title("🧙‍♂️ AI 전술 사령부 v10.7")

if st.session_state.my_portfolio:
    k_list, g_list = [], []
    
    # 데이터 수집 및 에러 방어
    for item in st.session_state.my_portfolio:
        try:
            df = yf.download(item['ticker'], period="1mo", progress=False)
            if not df.empty:
                curr_p = df['Close'].iloc[-1].item()
                low_20 = df['Low'].iloc[-20:].min().item()
                profit = ((curr_p - item['buy_price']) / item['buy_price']) * 100
                decision = get_ai_decision(curr_p, item['buy_price'], low_20)
                
                info = {"name": name_tag := item['name'], "ticker": item['ticker'], "curr": curr_p, 
                        "profit": profit, "decision": decision, "df": df, "low": low_20, "buy": item['buy_price']}
                
                if item['ticker'].endswith((".KS", ".KQ")): k_list.append(info)
                else: g_list.append(info)
        except: continue

    # 가나다 / ABC 순 정렬
    k_list.sort(key=lambda x: x['name'])
    g_list.sort(key=lambda x: x['name'])

    # 카테고리별 출력 함수
    def render_front(title, assets):
        if assets:
            st.header(title)
            cols = st.columns(min(len(assets), 4))
            for i, a in enumerate(assets):
                with cols[i % 4]:
                    f_fmt = ":,.0f" if a['ticker'].endswith((".KS", ".KQ")) else ":,.2f"
                    st.metric(a['name'], f"{a['curr']{f_fmt}}", f"{a['profit']:.2f}%")
                    st.write(f"🤖 {a['decision']}")
                    
                    # 자동 알람 (손절/추매 판단 시)
                    if auto_mode and ("손절" in a['decision'] or "추가 매수" in a['decision']):
                        msg = f"🚨 [AI 긴급 보고] {a['name']}\n{a['decision']}\n현재가: {a['curr']}\n수익률: {a['profit']:.2f}%"
                        send_telegram_with_chart(a['ticker'], a['df'], a['buy'], a['low'], msg)
            st.divider()

    render_front("🇰🇷 국내 주식 전선 (가나다순)", k_list)
    render_front("🌎 해외 주식 & 코인 전선 (ABC순)", g_list)

st.caption(f"최종 업데이트: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | v10.7")

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

# --- [3. 메인 대시보드 가동] ---
st.set_page_config(page_title="AI 전술 사령부 v10.9", layout="wide")

if 'my_portfolio' not in st.session_state:
    st.session_state.my_portfolio = load_portfolio()

# [사이드바: 관제 센터]
st.sidebar.header("🕹️ 사령부 관제 센터")
auto_mode = st.sidebar.checkbox("🛰️ AI 자동 판단 알람 가동")

with st.sidebar.form("input_form"):
    st.subheader("📥 신규 자산 배치")
    st.caption("※ 티커는 필수 입력 사항일세 (예: 삼성전자는 005930.KS)")
    new_name = st.text_input("종목명 (별명)", "삼성전자")
    new_tk = st.text_input("티커 (Ticker)", "005930.KS")
    new_bp = st.number_input("평단가", value=0)
    
    if st.form_submit_button("배치 완료"):
        if new_tk:
            st.session_state.my_portfolio.append({
                "id": str(time.time()), # 개별 삭제를 위한 고유 ID
                "name": new_name, 
                "ticker": new_tk.upper(), 
                "buy_price": new_bp
            })
            save_portfolio(st.session_state.my_portfolio)
            st.rerun()
        else:
            st.error("사령관님, 티커 없이는 분석을 시작할 수 없네!")

# [사이드바: 개별 자산 관리]
st.sidebar.divider()
st.sidebar.subheader("🗑️ 자산 개별 삭제")
if st.session_state.my_portfolio:
    for idx, item in enumerate(st.session_state.my_portfolio):
        # 이름과 티커를 함께 표시하여 삭제 실수 방지
        if st.sidebar.button(f"삭제: {item['name']}({item['ticker']})", key=f"del_{idx}"):
            st.session_state.my_portfolio.pop(idx)
            save_portfolio(st.session_state.my_portfolio)
            st.rerun()
else:
    st.sidebar.write("보유 자산이 없네.")

# [메인 전황판]
st.title("🧙‍♂️ AI 전술 사령부 v10.9")

if st.session_state.my_portfolio:
    k_list, g_list = [], []
    
    for item in st.session_state.my_portfolio:
        try:
            df = yf.download(item['ticker'], period="1mo", progress=False)
            if not df.empty:
                curr_p = float(df['Close'].iloc[-1])
                low_20 = float(df['Low'].iloc[-20:].min())
                profit = ((curr_p - item['buy_price']) / item['buy_price']) * 100
                decision = get_ai_decision(curr_p, item['buy_price'], low_20)
                
                info = {
                    "name": item['name'], 
                    "ticker": item['ticker'], 
                    "curr": curr_p, 
                    "profit": profit, 
                    "decision": decision, 
                    "df": df, 
                    "low": low_20, 
                    "buy": item['buy_price']
                }
                
                if item['ticker'].endswith((".KS", ".KQ")): k_list.append(info)
                else: g_list.append(info)
        except:
            st.error(f"⚠️ {item['name']}({item['ticker']}) 정보를 가져오지 못했네. 티커를 확인하게!")

    k_list.sort(key=lambda x: x['name'])
    g_list.sort(key=lambda x: x['name'])

    def render_front(title, assets):
        if assets:
            st.header(title)
            cols = st.columns(min(len(assets), 4))
            for i, a in enumerate(assets):
                with cols[i % 4]:
                    f_fmt = ":,.0f" if a['ticker'].endswith((".KS", ".KQ")) else ":,.2f"
                    st.metric(a['name'], f"{a['curr']:{f_fmt[1:]}}", f"{a['profit']:.2f}%")
                    st.write(f"🤖 {a['decision']}")
            st.divider()

    render_front("🇰🇷 국내 주식 전선 (가나다순)", k_list)
    render_front("🌎 해외 주식 & 코인 전선 (ABC순)", g_list)
else:
    st.info("사령관님, 종목명과 티커를 입력하여 정찰을 시작해 주시게!")

st.caption(f"최종 업데이트: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | v10.9")

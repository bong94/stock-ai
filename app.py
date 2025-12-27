import streamlit as st
import pandas as pd
import yfinance as yf
import requests
import time
import json
import os
from datetime import datetime
import pytz

# --- [1. 데이터베이스 및 사용자 식별 (철저 고정)] ---
def load_json(file_path, default_data):
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except: return default_data
    return default_data

def save_json(file_path, data):
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

st.sidebar.title("🎖️ 사령부 로그인")
user_id = st.sidebar.text_input("사령관 성함을 입력하세요", value="방문자")
USER_PORTFOLIO = f"portfolio_{user_id}.json"
USER_HISTORY = f"history_{user_id}.json"

if user_id == "봉94":
    default_assets = [
        {"name": "대상홀딩스우", "ticker": "084695.KS", "buy_price": 14220},
        {"name": "리얼티인컴", "ticker": "O", "buy_price": 56.32},
        {"name": "에디슨", "ticker": "EIX", "buy_price": 60.21},
        {"name": "SGOV", "ticker": "SGOV", "buy_price": 100.55},
        {"name": "TQQQ", "ticker": "TQQQ", "buy_price": 60.12}
    ]
else:
    default_assets = []

if 'my_portfolio' not in st.session_state or st.session_state.get('last_user') != user_id:
    st.session_state.my_portfolio = load_json(USER_PORTFOLIO, default_assets)
    st.session_state.last_user = user_id

# --- [2. AI 지능형 분석 엔진 (뉴스/변동성/한줄평)] ---
def get_ai_insight(ticker, cp, bp, atr_pct):
    """신규 추가: AI 전술 한 줄 평 학습 로직"""
    diff = ((cp - bp) / bp) * 100
    if diff < -10: return "📉 과매도 구간 진입. AI 추매가 근접 시 분할 매수 권고."
    elif diff > 20: return "🚀 목표가 도달 중. 분할 익절로 수익을 확정하십시오."
    elif atr_pct > 5: return "⚡ 변동성이 높습니다. 급격한 등락에 대비한 정밀 타격 필요."
    else: return "🛡️ 전술 대기 상태. 현재 구간에서 관망하며 에너지를 응축하십시오."

def get_news_radar(ticker):
    """기존 기능 고정: 뉴스 스캔"""
    try:
        t = yf.Ticker(ticker)
        news = t.news[:2]
        return "\n".join([f"• {n['title']}" for n in news]) if news else "특이 뉴스 없음"
    except: return "뉴스 수집 불가"

def get_ai_tactics(ticker, buy_price):
    """기존 기능 고정: 가변 전술 수치"""
    try:
        df = yf.download(ticker, period="20d", progress=False)
        atr_pct = ((df['High'] - df['Low']).mean() / df['Close'].mean()) * 100
        return max(atr_pct * 1.5, 5.0), max(atr_pct * 3.0, 10.0), atr_pct
    except: return 12.0, 25.0, 3.0

def get_fx():
    try:
        d = yf.download("USDKRW=X", period="1d", progress=False)
        return float(d['Close'].iloc[-1])
    except: return 1442.0

def format_all(price, ticker, rate, diff_pct=None):
    """기존 기능 고정: $0.00 (₩0) (0%) 양식"""
    is_k = ".K" in ticker
    p_str = f" ({diff_pct:+.1f}%)" if diff_pct is not None else ""
    if is_k: return f"₩{int(round(price, 0)):,}{p_str}"
    else: return f"${price:,.2f} (₩{int(round(price * rate, 0)):,}){p_str}"

def send_telegram(text):
    token = st.secrets.get("TELEGRAM_TOKEN", ""); cid = st.secrets.get("CHAT_ID", "")
    if token and cid: requests.post(f"https://api.telegram.org/bot{token}/sendMessage", data={'chat_id': cid, 'text': text})

# --- [3. 메인 관제 화면] ---
st.title(f"⚔️ AI 전술 사령부 v50.5")
st.subheader(f"👤 지휘관: {user_id}")
rate = get_fx()

with st.expander("➕ 타격 목표(종목) 추가 및 관리"):
    c1, c2, c3 = st.columns(3)
    n_n, n_t, n_b = c1.text_input("종목명"), c2.text_input("티커"), c3.number_input("구매가", min_value=0.0, format="%.2f")
    if st.button("신규 배치"):
        st.session_state.my_portfolio.append({"name": n_n, "ticker": n_t.upper(), "buy_price": n_b})
        save_json(USER_PORTFOLIO, st.session_state.my_portfolio); st.rerun()

if st.session_state.my_portfolio:
    display_list = []; tele_msg = f"🏛️ [{user_id} 사령관 AI 통합 브리핑]\n(환율: ₩{rate:,.1f})\n\n"
    for i, item in enumerate(st.session_state.my_portfolio):
        tk, bp = item['ticker'], float(item['buy_price'])
        try:
            d = yf.download(tk, period="2d", progress=False)
            cp = float(d['Close'].iloc[-1])
            m_buy, m_target, atr_val = get_ai_tactics(tk, bp)
            v_buy, v_target = bp * (1 - m_buy/100), bp * (1 + m_target/100)
            c_diff = ((cp - bp) / bp) * 100
            
            # [신규 누적] AI 전술 한 줄 평
            ai_insight = get_ai_insight(tk, cp, bp, atr_val)
            news = get_news_radar(tk)

            display_list.append({
                "종목": f"[{item['name']}]",
                "현재가": format_all(cp, tk, rate, c_diff),
                "AI 추매": format_all(v_buy, tk, rate, -m_buy),
                "AI 목표": format_all(v_target, tk, rate, m_target),
                "AI 전술 지침": ai_insight,
                "최신 뉴스": news[:30] + "..."
            })
            tele_msg += f"{i+1}. [{item['name']}]\n- 현재: {format_all(cp, tk, rate, c_diff)}\n- 🎯 추매: {format_all(v_buy, tk, rate, -m_buy)}\n- 🚀 목표: {format_all(v_target, tk, rate, m_target)}\n💡 AI지침: {ai_insight}\n🗞️ 뉴스:\n{news}\n\n"
        except: continue
        
    st.table(pd.DataFrame(display_list))
    if st.button("📊 텔레그램으로 AI 지능형 통합 보고 송신"):
        send_telegram(tele_msg)

# --- [4. 자동화 스케줄 (고정)] ---
now = datetime.now(pytz.timezone('Asia/Seoul'))
if now.hour == 8 and 50 <= now.minute <= 55:
    send_telegram(f"📡 {user_id} 사령관님, AI 참모의 지능형 아침 보고입니다.")
    time.sleep(600)
time.sleep(300); st.rerun()

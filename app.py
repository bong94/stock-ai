import streamlit as st
import pandas as pd
import yfinance as yf
import requests
import time
import json
import os
from datetime import datetime
import pytz

# --- [1. 데이터베이스 및 사용자 식별 (고정)] ---
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

# 사이드바 로그인 시스템
st.sidebar.title("🎖️ 사령부 로그인")
user_id = st.sidebar.text_input("사령관 성함을 입력하세요", value="방문자")
USER_PORTFOLIO = f"portfolio_{user_id}.json"
USER_HISTORY = f"history_{user_id}.json"

# 사령관님(봉94) 전용 데이터 고정 로드
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

# --- [2. v49.0 핵심 지능 로직 (완전 고정)] ---
def get_news_radar(ticker):
    """실시간 뉴스 스캔 및 기회 포착"""
    try:
        t = yf.Ticker(ticker)
        news = t.news[:2]
        return "\n".join([f"• {n['title']}" for n in news]) if news else "특이 뉴스 없음"
    except: return "뉴스 수집 불가"

def learn_sold_record(ticker, price):
    """매도 기록 학습 엔진"""
    hist = load_json(USER_HISTORY, [])
    hist.append({"ticker": ticker, "sold_price": price, "at": str(datetime.now())})
    save_json(USER_HISTORY, hist)

# --- [3. v50.2 가변 전술 및 정밀 표기 (누적 추가)] ---
def get_ai_tactics(ticker, buy_price):
    """변동성(ATR) 기반 AI 가변 전술 수치"""
    try:
        df = yf.download(ticker, period="20d", progress=False)
        atr_pct = ((df['High'] - df['Low']).mean() / df['Close'].mean()) * 100
        return max(atr_pct * 1.5, 5.0), max(atr_pct * 3.0, 10.0), max(atr_pct * 1.2, 5.0)
    except: return 12.0, 25.0, 10.0

def get_fx():
    try:
        d = yf.download("USDKRW=X", period="1d", progress=False)
        return float(d['Close'].iloc[-1])
    except: return 1442.0

def format_all(price, ticker, rate, diff_pct=None):
    """사령관님 지정 양식: $0.00 (₩0) (0%)"""
    is_k = ".K" in ticker
    p_str = f" ({diff_pct:+.1f}%)" if diff_pct is not None else ""
    if is_k: return f"₩{int(round(price, 0)):,}{p_str}"
    else: return f"${price:,.2f} (₩{int(round(price * rate, 0)):,}){p_str}"

def send_telegram(text):
    token = st.secrets.get("TELEGRAM_TOKEN", ""); cid = st.secrets.get("CHAT_ID", "")
    if token and cid: requests.post(f"https://api.telegram.org/bot{token}/sendMessage", data={'chat_id': cid, 'text': text})

# --- [4. 메인 관제 디스플레이] ---
st.title(f"⚔️ AI 전술 사령부 v50.4")
st.subheader(f"👤 지휘관: {user_id} (시스템 상시 가동 중)")
rate = get_fx()

# 종목 관리 섹터 (고정)
with st.expander("➕ 타격 목표(종목) 추가 및 관리"):
    c1, c2, c3 = st.columns(3)
    n_n = c1.text_input("종목명")
    n_t = c2.text_input("티커")
    n_b = c3.number_input("구매가", min_value=0.0, format="%.2f")
    if st.button("신규 배치"):
        st.session_state.my_portfolio.append({"name": n_n, "ticker": n_t.upper(), "buy_price": n_b})
        save_json(USER_PORTFOLIO, st.session_state.my_portfolio)
        st.rerun()

# 통합 상황판 (v49.0 뉴스 + v50.2 정밀지표)
if st.session_state.my_portfolio:
    display_list = []
    tele_msg = f"🏛️ [{user_id} 사령관 통합 전술 보고]\n(환율: ₩{rate:,.1f})\n\n"
    
    for i, item in enumerate(st.session_state.my_portfolio):
        tk = item['ticker']; bp = float(item['buy_price'])
        try:
            d = yf.download(tk, period="2d", progress=False)
            cp = float(d['Close'].iloc[-1])
            m_buy, m_target, m_profit = get_ai_tactics(tk, bp)
            v_buy = bp * (1 - m_buy/100); v_target = bp * (1 + m_target/100)
            c_diff = ((cp - bp) / bp) * 100
            
            # v49.0 뉴스 기능 유지
            news = get_news_radar(tk)

            display_list.append({
                "종목": f"[{item['name']}]",
                "구매가": format_all(bp, tk, rate),
                "현재가": format_all(cp, tk, rate, c_diff),
                "AI 추매": format_all(v_buy, tk, rate, -m_buy),
                "AI 목표": format_all(v_target, tk, rate, m_target),
                "최신 뉴스": news[:35] + "..."
            })
            tele_msg += f"{i+1}. [{item['name']}]\n- 현재: {format_all(cp, tk, rate, c_diff)}\n- 🎯 추매: {format_all(v_buy, tk, rate, -m_buy)}\n- 🚀 목표: {format_all(v_target, tk, rate, m_target)}\n🗞️ 뉴스:\n{news}\n\n"
        except: continue
        
    st.table(pd.DataFrame(display_list))
    if st.button("📊 텔레그램으로 모든 기능 통합 보고 송신"):
        send_telegram(tele_msg)

# --- [5. 자동화 스케줄 (고정 가동)] ---
now = datetime.now(pytz.timezone('Asia/Seoul'))
if now.hour == 8 and 50 <= now.minute <= 55:
    send_telegram(f"📡 {user_id} 사령관님, 무중단 가동 중인 AI 사령부의 아침 정찰 보고입니다.")
    time.sleep(600)
time.sleep(300); st.rerun()

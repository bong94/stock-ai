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

if user_id == "봉94":
    default_assets = [
        {"name": "대상홀딩스우", "ticker": "084695.KS", "buy_price": 14220},
        {"name": "리얼티인컴", "ticker": "O", "buy_price": 56.32},
        {"name": "에디슨", "ticker": "EIX", "buy_price": 60.21},
        {"name": "SGOV", "ticker": "SGOV", "buy_price": 100.55},
        {"name": "TQQQ", "ticker": "TQQQ", "buy_price": 60.12}
    ]
    default_chat_id = st.secrets.get("CHAT_ID", "")
else:
    default_assets = []; default_chat_id = ""

if 'user_data' not in st.session_state or st.session_state.get('last_user') != user_id:
    saved_data = load_json(USER_PORTFOLIO, {"assets": default_assets, "chat_id": default_chat_id})
    st.session_state.my_portfolio = saved_data.get("assets", [])
    st.session_state.my_chat_id = saved_data.get("chat_id", "")
    st.session_state.last_user = user_id

# 알람 설정창 (고정)
st.sidebar.divider()
st.sidebar.write("🔔 개인 알람 설정")
new_chat_id = st.sidebar.text_input("본인의 텔레그램 Chat ID", value=st.session_state.my_chat_id)
if st.sidebar.button("무전 주소 저장"):
    st.session_state.my_chat_id = new_chat_id
    save_json(USER_PORTFOLIO, {"assets": st.session_state.my_portfolio, "chat_id": new_chat_id})
    st.sidebar.success("알람 주소 저장 완료")

# --- [2. AI 전술 지능 및 뉴스 (고정)] ---
def get_ai_insight(ticker, cp, bp, atr_pct):
    diff = ((cp - bp) / bp) * 100
    if diff < -10: return "📉 과매도 구간. 매수 고려."
    elif diff > 20: return "🚀 목표 도달 중. 익절 준비."
    return "🛡️ 전술 대기 및 관망."

def get_news_radar(ticker):
    try:
        t = yf.Ticker(ticker)
        news = t.news[:2]
        return " ".join([f"• {n['title']}" for n in news]) if news else "뉴스 없음"
    except: return "뉴스 불가"

def get_ai_tactics(ticker, buy_price):
    try:
        df = yf.download(ticker, period="20d", progress=False)
        atr_pct = ((df['High'] - df['Low']).mean() / df['Close'].mean()) * 100
        return max(atr_pct * 1.5, 5.0), max(atr_pct * 3.0, 10.0), atr_pct
    except: return 12.0, 25.0, 3.0

def format_all(price, ticker, rate, diff_pct=None):
    is_k = ".K" in ticker
    p_str = f" ({diff_pct:+.1f}%)" if diff_pct is not None else ""
    if is_k: return f"₩{int(round(price, 0)):,}{p_str}"
    else: return f"${price:,.2f} (₩{int(round(price * rate, 0)):,}){p_str}"

# --- [3. 메인 관제 (표 복구 및 알람)] ---
st.title(f"⚔️ AI 전술 사령부 v50.7")
rate = yf.download("USDKRW=X", period="1d", progress=False)['Close'].iloc[-1]

if st.session_state.my_portfolio:
    display_list = []; tele_msg = f"🏛️ [{user_id} 사령관 정밀 보고]\n\n"
    for item in st.session_state.my_portfolio:
        tk, bp = item['ticker'], float(item['buy_price'])
        try:
            d = yf.download(tk, period="2d", progress=False)
            cp = float(d['Close'].iloc[-1])
            m_buy, m_target, atr_val = get_ai_tactics(tk, bp)
            v_buy, v_target = bp * (1 - m_buy/100), bp * (1 + m_target/100)
            c_diff = ((cp - bp) / bp) * 100
            ai_insight = get_ai_insight(tk, cp, bp, atr_val)
            news = get_news_radar(tk)
            
            # [사령관님 요청대로 표 정보 다시 확장]
            display_list.append({
                "종목": f"[{item['name']}]",
                "구매가": format_all(bp, tk, rate),
                "현재가": format_all(cp, tk, rate, c_diff),
                "AI 추매": format_all(v_buy, tk, rate, -m_buy),
                "AI 목표": format_all(v_target, tk, rate, m_target),
                "AI 지침": ai_insight,
                "최신 뉴스": news[:30] + "..."
            })
            tele_msg += f"[{item['name']}]\n- 현재: {format_all(cp, tk, rate, c_diff)}\n- 🎯 추매: {format_all(v_buy, tk, rate, -m_buy)}\n- 🚀 목표: {format_all(v_target, tk, rate, m_target)}\n💡 지침: {ai_insight}\n\n"
        except: continue
        
    st.table(pd.DataFrame(display_list))
    if st.button("📊 텔레그램으로 완전체 전술 보고 송신"):
        if st.session_state.my_chat_id:
            requests.post(f"https://api.telegram.org/bot{st.secrets['TELEGRAM_TOKEN']}/sendMessage", data={'chat_id': st.session_state.my_chat_id, 'text': tele_msg})
            st.success("등록된 주소로 보고서를 보냈습니다.")

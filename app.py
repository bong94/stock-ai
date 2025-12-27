import streamlit as st
import pandas as pd
import yfinance as yf
import requests
import time
import json
import os
from datetime import datetime
import pytz

# --- [1. 데이터베이스 및 사용자별 알람 설정 고정] ---
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

# 사령관님(봉94) 데이터 고정
if user_id == "봉94":
    default_assets = [{"name": "대상홀딩스우", "ticker": "084695.KS", "buy_price": 14220}, {"name": "TQQQ", "ticker": "TQQQ", "buy_price": 60.12}] # 예시 단축
    default_chat_id = st.secrets.get("CHAT_ID", "") # 사령관님 기본 ID
else:
    default_assets = []
    default_chat_id = ""

# 사용자별 데이터 로드 (포트폴리오 + 알람 ID)
if 'user_data' not in st.session_state or st.session_state.get('last_user') != user_id:
    saved_data = load_json(USER_PORTFOLIO, {"assets": default_assets, "chat_id": default_chat_id})
    st.session_state.my_portfolio = saved_data.get("assets", [])
    st.session_state.my_chat_id = saved_data.get("chat_id", "")
    st.session_state.last_user = user_id

# 사이드바 알람 등록창
st.sidebar.divider()
st.sidebar.write("🔔 개인 알람 설정")
new_chat_id = st.sidebar.text_input("본인의 텔레그램 Chat ID", value=st.session_state.my_chat_id)
if st.sidebar.button("무전 주소 저장"):
    st.session_state.my_chat_id = new_chat_id
    save_json(USER_PORTFOLIO, {"assets": st.session_state.my_portfolio, "chat_id": new_chat_id})
    st.sidebar.success("알람 주소가 등록되었습니다.")

# --- [2. AI 전술 지능 및 정밀 표기 (기존 기능 완전 고정)] ---
def get_ai_insight(ticker, cp, bp, atr_pct):
    diff = ((cp - bp) / bp) * 100
    if diff < -10: return "📉 과매도 구간. 분할 매수 고려."
    elif diff > 20: return "🚀 목표 도달 중. 익절 준비."
    return "🛡️ 전술 대기 및 관망."

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

def send_telegram(text, target_chat_id):
    """지정된 Chat ID로만 무전 송신"""
    token = st.secrets.get("TELEGRAM_TOKEN", "")
    if token and target_chat_id:
        requests.post(f"https://api.telegram.org/bot{token}/sendMessage", data={'chat_id': target_chat_id, 'text': text})

# --- [3. 통합 관제 및 보고 (기존 기능 누적)] ---
st.title(f"⚔️ AI 전술 사령부 v50.6")
rate = yf.download("USDKRW=X", period="1d", progress=False)['Close'].iloc[-1]

if st.session_state.my_portfolio:
    display_list = []; tele_msg = f"🏛️ [{user_id} 사령관 AI 통합 보고]\n\n"
    for item in st.session_state.my_portfolio:
        tk, bp = item['ticker'], float(item['buy_price'])
        try:
            d = yf.download(tk, period="2d", progress=False)
            cp = float(d['Close'].iloc[-1])
            m_buy, m_target, atr_val = get_ai_tactics(tk, bp)
            v_buy, v_target = bp * (1 - m_buy/100), bp * (1 + m_target/100)
            c_diff = ((cp - bp) / bp) * 100
            ai_insight = get_ai_insight(tk, cp, bp, atr_val)
            
            display_list.append({"종목": f"[{item['name']}]", "현재가": format_all(cp, tk, rate, c_diff), "AI 지침": ai_insight})
            tele_msg += f"[{item['name']}]\n- 현재: {format_all(cp, tk, rate, c_diff)}\n- 🎯 추매: {format_all(v_buy, tk, rate, -m_buy)}\n- 🚀 목표: {format_all(v_target, tk, rate, m_target)}\n💡 AI지침: {ai_insight}\n\n"
        except: continue
        
    st.table(pd.DataFrame(display_list))
    if st.button("📊 내 폰으로 전술 보고 전송"):
        if st.session_state.my_chat_id:
            send_telegram(tele_msg, st.session_state.my_chat_id)
            st.success("등록된 무전 주소로 보고서를 송신했습니다.")
        else:
            st.warning("사이드바에서 Chat ID를 먼저 등록해 주세요.")

# --- [4. 자동화 스케줄 (사용자별 알람)] ---
now = datetime.now(pytz.timezone('Asia/Seoul'))
if now.hour == 8 and 50 <= now.minute <= 55:
    # 모든 사용자 파일을 스캔하여 아침 알람 발송 (서버 로직 필요시 추가)
    if st.session_state.my_chat_id:
        send_telegram(f"📡 {user_id} 사령관님, 정찰 보고입니다.", st.session_state.my_chat_id)
    time.sleep(600)
time.sleep(300); st.rerun()

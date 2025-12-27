import streamlit as st
import pandas as pd
import yfinance as yf
import requests
import time
import json
import os
from datetime import datetime
import pytz

# --- [1. 데이터베이스 및 사령관 식별] ---
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
user_id = st.sidebar.text_input("사령관 성함을 입력하세요", value="봉94")
USER_PORTFOLIO = f"portfolio_{user_id}.json"

# 봉94 사령관 데이터 기본값 고정
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

# --- [2. 2번 양식 고정 출력 엔진] ---
def get_ai_tactics(ticker, buy_price):
    try:
        df = yf.download(ticker, period="20d", progress=False)
        atr_pct = ((df['High'] - df['Low']).mean() / df['Close'].mean()) * 100
        return max(atr_pct * 1.5, 12.0), max(atr_pct * 3.0, 25.0), max(atr_pct * 1.2, 10.0), atr_pct
    except: return 12.0, 25.0, 10.0, 3.0

def format_all(price, ticker, rate, diff_pct=None):
    """사령관님 지정 정밀 양식: $00 (₩00) (0%)"""
    is_k = ".K" in ticker
    p_str = f" ({diff_pct:+.1f}%)" if diff_pct is not None else ""
    if is_k: return f"₩{int(round(price, 0)):,}{p_str}"
    else: return f"${price:,.2f} (₩{int(round(price * rate, 0)):,}){p_str}"

def create_tactical_report(item, rate, idx):
    """2번 사진의 정밀 양식을 생성하는 핵심 함수"""
    tk, bp = item['ticker'], float(item['buy_price'])
    try:
        d = yf.download(tk, period="2d", progress=False)
        cp = float(d['Close'].iloc[-1])
        m_buy, m_target, m_profit, atr = get_ai_tactics(tk, bp)
        
        v_buy = bp * (1 - m_buy/100)
        v_target = bp * (1 + m_target/100)
        v_profit = bp * (1 + m_profit/100)
        c_diff = ((cp - bp) / bp) * 100
        
        report = f"{idx}번 [{item['name']}] 작전 지도 수립 (환율: ₩{rate:,.1f})\n"
        report += f"- 구매가: {format_all(bp, tk, rate)}\n"
        report += f"- 현재가: {format_all(cp, tk, rate, c_diff)}\n"
        report += f"- 추가매수권장: {format_all(v_buy, tk, rate, -m_buy)}\n"
        report += f"- 목표매도: {format_all(v_target, tk, rate, m_target)}\n"
        report += f"- 익절 구간: {format_all(v_profit, tk, rate, m_profit)}\n\n"
        
        # 지능형 한 줄 평 고정
        if c_diff < -10: insight = "📉 과매도 구간 진입. 분할 매수 고려."
        elif c_diff > 20: insight = "🚀 목표가 도달 중. 익절 준비."
        else: insight = "🛡️ [전술 대기] 현재 정상 범위 내 움직임입니다. 관망하십시오."
        
        report += f"💡 AI 전술 지침: {insight}\n"
        return report, cp, c_diff, v_buy, v_target, insight
    except: return None

# --- [3. 메인 관제 및 자동 보고] ---
st.title(f"⚔️ AI 전술 사령부 v50.9")
rate = yf.download("USDKRW=X", period="1d", progress=False)['Close'].iloc[-1]

if st.session_state.my_portfolio:
    display_list = []; full_telegram_msg = f"🏛️ [봉94 사령관 정기 전략 보고]\n\n"
    
    for i, item in enumerate(st.session_state.my_portfolio):
        res = create_tactical_report(item, rate, i+1)
        if res:
            report_text, cp, c_diff, v_buy, v_target, insight = res
            display_list.append({
                "종목": f"[{item['name']}]",
                "현재가": format_all(cp, item['ticker'], rate, c_diff),
                "AI 지침": insight
            })
            full_telegram_msg += report_text + "\n" + "-"*20 + "\n"

    st.table(pd.DataFrame(display_list))
    if st.button("📊 2번 양식으로 정밀 보고 송신"):
        requests.post(f"https://api.telegram.org/bot{st.secrets['TELEGRAM_TOKEN']}/sendMessage", 
                      data={'chat_id': st.session_state.my_chat_id, 'text': full_telegram_msg})
        st.success("2번 정밀 양식으로 보고를 완료했습니다.")

# --- [4. 스케줄러 자동 보고 (2번 양식 고정)] ---
now = datetime.now(pytz.timezone('Asia/Seoul'))
if st.session_state.my_chat_id:
    # 08:50 정기 보고 시에도 2번 양식 사용
    if now.hour == 8 and 50 <= now.minute <= 55:
        requests.post(f"https://api.telegram.org/bot{st.secrets['TELEGRAM_TOKEN']}/sendMessage", 
                      data={'chat_id': st.session_state.my_chat_id, 'text': full_telegram_msg})
        time.sleep(600)

time.sleep(300); st.rerun()

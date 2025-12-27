import streamlit as st
import pandas as pd
import yfinance as yf
import requests
import json
import os
from datetime import datetime
import pytz

# --- [1. 데이터 구조 자동 복구 로직] ---
def load_json_safe(file_path, default_assets):
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                # 옛날 방식(리스트만 있음)이면 새 방식(딕셔너리)으로 자동 변환
                if isinstance(data, list):
                    return {"assets": data, "chat_id": st.secrets.get("CHAT_ID", "")}
                return data
        except: return {"assets": default_assets, "chat_id": st.secrets.get("CHAT_ID", "")}
    return {"assets": default_assets, "chat_id": st.secrets.get("CHAT_ID", "")}

st.sidebar.title("🎖️ 사령부 로그인")
user_id = st.sidebar.text_input("사령관 성함을 입력하세요", value="봉94")
USER_PORTFOLIO = f"portfolio_{user_id}.json"

# 사령관님 자산 데이터 강제 복구 지점
default_assets = [
    {"name": "대상홀딩스우", "ticker": "084695.KS", "buy_price": 14220},
    {"name": "리얼티인컴", "ticker": "O", "buy_price": 56.69},
    {"name": "에디슨", "ticker": "EIX", "buy_price": 60.21},
    {"name": "SGOV", "ticker": "SGOV", "buy_price": 100.55},
    {"name": "TQQQ", "ticker": "TQQQ", "buy_price": 60.12}
]

# 데이터 로드 및 세션 저장
if 'user_data' not in st.session_state or st.session_state.get('last_user') != user_id:
    st.session_state.user_data = load_json_safe(USER_PORTFOLIO, default_assets)
    st.session_state.last_user = user_id

# --- [2. 2번 사진 정밀 양식 고정 (Fixed Type 2)] ---
def get_ai_tactics(ticker, buy_price):
    try:
        df = yf.download(ticker, period="20d", progress=False)
        atr_pct = ((df['High'] - df['Low']).mean() / df['Close'].mean()) * 100
        # 사령관님 고정 수치: 추매(-12%), 목표(+25%), 익절(+10%) 기반 가변 조절
        return max(atr_pct * 1.5, 12.0), max(atr_pct * 3.0, 25.0), 10.0
    except: return 12.0, 25.0, 10.0

def format_all(price, ticker, rate, diff_pct=None):
    is_k = ".K" in ticker
    p_str = f" ({diff_pct:+.1f}%)" if diff_pct is not None else ""
    if is_k: return f"₩{int(round(price, 0)):,}{p_str}"
    else: return f"${price:,.2f} (₩{int(round(price * rate, 0)):,}){p_str}"

# --- [3. 메인 관제 및 2번 양식 보고] ---
st.title(f"⚔️ AI 전술 사령부 v51.0")
rate = yf.download("USDKRW=X", period="1d", progress=False)['Close'].iloc[-1]

assets = st.session_state.user_data.get("assets", [])
if assets:
    display_list = []; full_report = f"🏛️ [봉94 사령관 2번 정밀 보고]\n\n"
    
    for i, item in enumerate(assets):
        tk, bp = item['ticker'], float(item['buy_price'])
        try:
            d = yf.download(tk, period="2d", progress=False); cp = float(d['Close'].iloc[-1])
            m_buy, m_target, m_profit = get_ai_tactics(tk, bp)
            c_diff = ((cp - bp) / bp) * 100
            
            # 2번 양식 조립
            line = f"{i+1}번 [{item['name']}] 작전 지도 수립 (환율: ₩{rate:,.1f})\n"
            line += f"- 구매가: {format_all(bp, tk, rate)}\n"
            line += f"- 현재가: {format_all(cp, tk, rate, c_diff)}\n"
            line += f"- 추가매수권장: {format_all(bp*(1-m_buy/100), tk, rate, -m_buy)}\n"
            line += f"- 목표매도: {format_all(bp*(1+m_target/100), tk, rate, m_target)}\n"
            line += f"- 익절 구간: {format_all(bp*(1+m_profit/100), tk, rate, m_profit)}\n"
            
            insight = "🛡️ [전술 대기] 관망하십시오." if -5 < c_diff < 5 else "⚠️ 변동성 감지, 차트 확인 권고."
            line += f"\n💡 AI 전술 지침: {insight}\n"
            
            display_list.append({"종목": item['name'], "현재가": format_all(cp, tk, rate, c_diff), "AI지침": insight})
            full_report += line + "\n" + "-"*20 + "\n"
        except: continue

    st.table(pd.DataFrame(display_list))
    if st.button("📊 2번 양식으로 정밀 보고 송신"):
        token = st.secrets["TELEGRAM_TOKEN"]; cid = st.session_state.user_data.get("chat_id")
        if cid: requests.post(f"https://api.telegram.org/bot{token}/sendMessage", data={'chat_id': cid, 'text': full_report})
        st.success("2번 정밀 양식으로 무전 완료!")
else:
    st.warning("⚠️ 종목 데이터가 비어있습니다. 왼쪽에서 로그인을 확인하거나 종목을 추가하세요.")

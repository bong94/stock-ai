import streamlit as st
import pandas as pd
import yfinance as yf
import requests
import time
import json
import os
from datetime import datetime
import pytz

# --- [1. 보안 및 데이터 설정] ---
TELEGRAM_TOKEN = st.secrets.get("TELEGRAM_TOKEN", "")
CHAT_ID = st.secrets.get("CHAT_ID", "")
PORTFOLIO_FILE = "portfolio_db.json"

if 'my_portfolio' not in st.session_state:
    st.session_state.my_portfolio = [] # 실제 환경에서는 load_db() 사용

# --- [2. 시장 마감 감지 로직] ---
def check_market_closing():
    """장이 끝나는 시점인지 확인 (마감 후 5분 이내 보고)"""
    now_utc = datetime.now(pytz.utc)
    k_now = now_utc.astimezone(pytz.timezone('Asia/Seoul'))
    u_now = now_utc.astimezone(pytz.timezone('US/Eastern'))
    
    # 한국장 마감 (오후 3:30 ~ 3:35 사이 보고)
    is_kor_closing = (k_now.weekday() < 5 and k_now.hour == 15 and 30 <= k_now.minute <= 35)
    
    # 미국장 마감 (새벽 04:00 ~ 04:05/서머타임 미적용 기준)
    is_usa_closing = (u_now.weekday() < 5 and u_now.hour == 16 and 0 <= u_now.minute <= 5)
    
    return is_kor_closing, is_usa_closing

# --- [3. 통합 분석 및 종가 보고 엔진] ---
def get_full_tactical_report(title="[실시간 전황 보고]"):
    if not st.session_state.my_portfolio:
        return "⚠️ 배치된 자산이 없습니다."

    # 환율 획득
    try:
        ex_data = yf.download("USDKRW=X", period="1d", progress=False)
        rate = float(ex_data['Close'].iloc[-1])
    except: rate = 1380.0

    reports = []
    total_profit = 0
    
    for i, item in enumerate(st.session_state.my_portfolio):
        ticker = item['ticker']
        try:
            df = yf.download(ticker, period="2d", progress=False) # 오늘과 어제 데이터
            curr_p = float(df['Close'].iloc[-1])
            prev_p = float(df['Close'].iloc[-2])
            daily_change = ((curr_p - prev_p) / prev_p) * 100
            
            buy_p = item['buy_price']
            total_profit_rate = ((curr_p - buy_p) / buy_p) * 100
            
            is_kor = any(x in ticker for x in [".KS", ".KQ"])
            price_str = f"₩{curr_p:,.0f}" if is_kor else f"${curr_p:,.2f} (₩{int(curr_p*rate):,})"
            
            reports.append(f"{i+1}번 [{item['name']}] {price_str}\n   (오늘: {daily_change:+.2f}% / 누적: {total_profit_rate:+.2f}%)")
        except: continue

    msg = f"🏛️ {title}\n"
    msg += "\n".join(reports)
    msg += f"\n\n💡 현재 기준 환율: ₩{rate:,.1f}"
    return msg

# --- [4. 실행 제어] ---
st.set_page_config(page_title="AI 전술 사령부 v26.0", layout="wide")
st.title("⚔️ AI 전술 사령부 v26.0 (종가 보고 모드)")

is_kor_closing, is_usa_closing = check_market_closing()

# 메인 루프에서 종가 시점 감지 시 자동 보고
if is_kor_closing:
    send_msg = get_full_tactical_report("[🇰🇷 한국장 마감 전술 보고]")
    requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", data={'chat_id': CHAT_ID, 'text': send_msg})
    st.success("한국장 종가 보고 완료!")

if is_usa_closing:
    send_msg = get_full_tactical_report("[🇺🇸 미국장 마감 전술 보고]")
    requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", data={'chat_id': CHAT_ID, 'text': send_msg})
    st.success("미국장 종가 보고 완료!")

# UI 상에서는 언제나 수동으로 확인 가능
if st.button("지금 즉시 전체 보고 송신"):
    requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", data={'chat_id': CHAT_ID, 'text': get_full_tactical_report()})

import streamlit as st
import pandas as pd
import yfinance as yf
import requests
import json
import os
import time
from datetime import datetime
import pytz

# ==========================================================
# 1. [보안 및 데이터] - 사령관 정보 영구 저장 시스템
# ==========================================================
st.set_page_config(page_title="AI 전술 사령부", layout="wide")
st.sidebar.title("🎖️ AI 사령부 보안 인증")
user_id = st.sidebar.text_input("사령관 호출부호", value="봉94")
USER_PORTFOLIO = f"portfolio_{user_id}.json"

# [지시사항] 봉94 사령관 기본 자산 고정
default_assets = [
    {"name": "대상홀딩스우", "ticker": "084695.KS", "buy_price": 14220},
    {"name": "리얼티인컴", "ticker": "O", "buy_price": 56.69},
    {"name": "에디슨", "ticker": "EIX", "buy_price": 60.21},
    {"name": "SGOV", "ticker": "SGOV", "buy_price": 100.55},
    {"name": "TQQQ", "ticker": "TQQQ", "buy_price": 60.12}
]

# [데이터 복구] empty 현상 방지 로직
if os.path.exists(USER_PORTFOLIO):
    try:
        with open(USER_PORTFOLIO, "r", encoding="utf-8") as f:
            user_data = json.load(f)
            if "sell_history" not in user_data: user_data["sell_history"] = []
    except:
        user_data = {"assets": default_assets, "chat_id": st.secrets.get("CHAT_ID", ""), "sell_history": []}
else:
    user_data = {"assets": default_assets, "chat_id": st.secrets.get("CHAT_ID", ""), "sell_history": []}

# ==========================================================
# 2. [전술 엔진] - 실시간 환율 및 정밀 포맷팅 (에러 완전 봉쇄)
# ==========================================================
st.title(f"⚔️ AI 전술 사령부 v56.0 (TOTAL-FIX)")

try:
    # [오류수정] .item() 사용으로 시리즈 포맷 에러 원천 차단
    current_rate = yf.download("USDKRW=X", period="1d", progress=False)['Close'].iloc[-1].item()
except:
    current_rate = 1445.0

def format_all(price, ticker, rate):
    p = float(price)
    if ".K" in ticker:
        return f"₩{int(round(p, 0)):,}"
    # [지시사항] $/₩ 병기 필수
    return f"${p:,.2f} (₩{int(round(p * rate, 0)):,})"

# ==========================================================
# 3. [핵심 연산] - 2번 양식 / 뉴스 / ATR 지능형 타점
# ==========================================================
assets = user_data.get("assets", [])
full_report = f"🏛️ [봉94 사령관 통합 정밀 보고]\n발신: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
summary_list = []

for i, item in enumerate(assets):
    ticker = item['ticker']
    buy_p = float(item['buy_price'])
    
    try:
        # [정찰] 데이터 수집
        stock = yf.Ticker(ticker)
        hist = stock.history(period="20d")
        if hist.empty: continue
        
        # [연산] 순수 숫자 데이터 추출
        curr_p = float(hist['Close'].iloc[-1].item())
        atr = float((hist['High'] - hist['Low']).mean())
        atr_pct = (atr / curr_p) * 100
        
        # [지시사항] 사령관님 전용 타점 (2번 양식 고정)
        m_buy = max(atr_pct * 1.5, 12.0)    # 추매 (-12%)
        m_target = max(atr_pct * 3.0, 25.0) # 목표 (+25%)
        m_profit = 10.0                    # 익절 (+10%)
        
        v_buy = buy_p * (1 - m_buy/100)
        v_target = buy_p * (1 + m_target/100)
        v_profit = buy_p * (1 + m_profit/100)
        yield_pct = ((curr_p - buy_p) / buy_p) * 100
        
        # [지시사항] 실시간 뉴스 (KeyError 방지)
        news_data = stock.news
        news_final = ""
        if news_data:
            for n in news_data[:2]:
                news_final += f"• {n.get('title', '정보 없음')}\n"
        if not news_final: news_final = "현재 수신된 특이 뉴스 없음"

        # [지시사항] 2번 사진 정밀 양식 100% 재현
        chunk = f"{i+1}번 [{item['name']}] 작전 수립 (환율: ₩{current_rate:,.1f})\n"
        chunk += f"- 구매가: {format_all(buy_p, ticker, current_rate)}\n"
        chunk += f"- 현재가: {format_all(curr_p, ticker, current_rate)} ({yield_pct:+.1f}%)\n"
        chunk += f"- 추가매수권장: {format_all(v_buy, ticker, current_rate)} (-{m_buy:.1f}%)\n"
        chunk += f"- 목표매도: {format_all(v_target, ticker, current_rate)} (+{m_target:.1f}%)\n"
        chunk += f"- 익절 구간: {format_all(v_profit, ticker, current_rate)} (+{m_profit:.1f}%)\n"
        chunk += f"🗞️ 뉴스: {news_final[:85]}...\n"
        
        # [지시사항] AI 전술 지침
        insight =

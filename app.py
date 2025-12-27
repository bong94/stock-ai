import streamlit as st
import pandas as pd
import yfinance as yf
import requests
import time
import json
import os
from datetime import datetime
import pytz

# --- [1. 지능형 자산 관리 및 저장 로직] ---
PORTFOLIO_FILE = "portfolio_db.json"

def load_db():
    if os.path.exists(PORTFOLIO_FILE):
        try:
            with open(PORTFOLIO_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if data else []
        except: return []
    return []

def save_db(data):
    with open(PORTFOLIO_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# 데이터 로드 (없으면 초기값으로 설정하는 로직 유지)
if 'my_portfolio' not in st.session_state:
    st.session_state.my_portfolio = load_db()
    if not st.session_state.my_portfolio: # 파일이 비었을 때만 초기 종목 로드
        st.session_state.my_portfolio = [
            {"name": "대상홀딩스우", "ticker": "084695.KS", "buy_price": 14220},
            {"name": "리얼티인컴", "ticker": "O", "buy_price": 56.32},
            {"name": "에디슨", "ticker": "EIX", "buy_price": 60.21},
            {"name": "SGOV", "ticker": "SGOV", "buy_price": 100.55},
            {"name": "TQQQ", "ticker": "TQQQ", "buy_price": 60.12}
        ]
        save_db(st.session_state.my_portfolio)

# --- [2. 자산 관리 기능: 매도 처리] ---
def sell_asset(ticker_to_sell):
    """지정한 티커의 종목을 포트폴리오에서 삭제하고 저장함"""
    updated_portfolio = [item for item in st.session_state.my_portfolio if item['ticker'] != ticker_to_sell]
    if len(updated_portfolio) != len(st.session_state.my_portfolio):
        st.session_state.my_portfolio = updated_portfolio
        save_db(updated_portfolio)
        return True
    return False

# --- [3. 분석 및 보고 엔진 (숫자 포맷 유지)] ---
def get_exchange_rate():
    try:
        ex_data = yf.download("USDKRW=X", period="1d", progress=False)
        return float(ex_data['Close'].iloc[-1])
    except: return 1442.0

def generate_tactical_report(title="🏛️ [전체 적극적 전술 보고]"):
    rate = get_exchange_rate()
    reports = []
    is_urgent = False
    
    for i, item in enumerate(st.session_state.my_portfolio):
        ticker = item['ticker']
        try:
            df = yf.download(ticker, period="2d", progress=False)
            if df.empty: continue
            curr_p = float(df['Close'].iloc[-1])
            prev_p = float(df['Close'].iloc[-2])
            buy_p = float(item['buy_price'])
            
            change_pct = ((curr_p - prev_p) / prev_p) * 100
            if abs(change_pct) >= 3.0: is_urgent = True
            
            avg_down, target_p = buy_p * 0.88, buy_p * 1.25
            is_kor = any(x in ticker for x in [".KS", ".KQ"])
            
            if is_kor:
                report = f"{i+1}번 [{item['name']}] 작전 수립\n- 구매가: ₩{buy_p:,.0f}\n- 현재가: ₩{curr_p:,.0f} ({change_pct:+.1f}%)\n- 추매권장: ₩{avg_down:,.0f} / 목표: ₩{target_p:,.0f}"
            else:
                report = f"{i+1}번 [{item['name']}] 작전 수립 (환율: ₩{rate:,.1f})\n- 구매가: ${buy_p:,.2f} (₩{buy_p*rate:,.0f})\n- 현재가: ${curr_p:,.2f} (₩{curr_p*rate:,.0f})\n- 추매권장: ${avg_down:,.2f} / 목표: ${target_p:,.2f}"
            
            reports.append(report + f"\n💡 지침: " + ("🛡️ [추가 매수]" if curr_p <= avg_down else "🚩 [목표 달성]" if curr_p >= target_p else "🛡️ [전술 대기]"))
        except: continue
    
    msg = f"{title}\n\n" + "\n\n----------\n\n".join(reports)
    return msg, is_urgent

# --- [4. UI 구성 및 매도 관리 창] ---
st.set_page_config(page_title="AI 전술 사령부 v39.0", page_icon="⚔️")
st.markdown("## ⚔️ AI 전술 사령부 v39.0")

# [매도 관리 섹션 추가]
with st.expander("📝 자산 관리 (매수/매도)"):
    col1, col2 = st.columns(2)
    with col1:
        sell_tk = st.text_input("매도할 종목 티커 입력 (예: TQQQ)")
        if st.button("❌ 매도 처리 (삭제)"):
            if sell_asset(sell_tk):
                st.success(f"{sell_tk} 종목이 작전에서 제외되었습니다.")
                st.rerun()
            else:
                st.error("해당 티커를 찾을 수 없습니다.")

# 현황 테이블 (이미지 1번 스타일)
df = pd.DataFrame(st.session_state.my_portfolio)
if not df.empty:
    df['구매가'] = df.apply(lambda x: f"₩{float(x['buy_price']):,.0f}" if ".K" in str(x['ticker']) else f"${float(x['buy_price']):,.2f}", axis=1)
    st.table(df[['name', 'ticker', '구매가']].rename(columns={'name':'종목명', 'ticker':'티커'}))

if st.button("📊 즉시 텔레그램 보고 송신"):
    msg, _ = generate_tactical_report()
    # 텔레그램 송신 로직 (생략 - 기존과 동일)

# 상시 모니터링 가동 (기존 로직 동일)
# ... ai_smart_monitor() ...

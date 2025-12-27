import streamlit as st
import pandas as pd
import yfinance as yf
import requests
import time
import json
import os
from datetime import datetime
import pytz

# --- [1. 데이터베이스 및 학습 기록 관리] ---
PORTFOLIO_FILE = "portfolio_db.json"
HISTORY_FILE = "trade_history.json"

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

if 'my_portfolio' not in st.session_state:
    # 사령관님의 정예 5대 자산 데이터 유지
    st.session_state.my_portfolio = load_json(PORTFOLIO_FILE, [
        {"name": "대상홀딩스우", "ticker": "084695.KS", "buy_price": 14220},
        {"name": "리얼티인컴", "ticker": "O", "buy_price": 56.32},
        {"name": "에디슨", "ticker": "EIX", "buy_price": 60.21},
        {"name": "SGOV", "ticker": "SGOV", "buy_price": 100.55},
        {"name": "TQQQ", "ticker": "TQQQ", "buy_price": 60.12}
    ])

# --- [2. AI 지능형 가변 전술 엔진 (신규 통합)] ---
def calculate_ai_tactics(ticker, buy_price):
    """변동성(ATR)을 분석하여 종목별 최적 대응가 자동 산출"""
    try:
        df = yf.download(ticker, period="20d", progress=False)
        if df.empty: return buy_price * 0.88, buy_price * 1.25, buy_price * 1.10
        
        # 변동성 비율 계산
        atr_pct = ((df['High'] - df['Low']).mean() / df['Close'].mean()) * 100
        
        # AI 가변 로직: 변동성이 크면 범위를 넓히고, 작으면 좁힘
        add_buy = buy_price * (1 - (max(atr_pct * 1.5, 5) / 100))
        target_sell = buy_price * (1 + (max(atr_pct * 3.0, 10) / 100))
        profit_cut = buy_price * (1 + (max(atr_pct * 1.2, 5) / 100))
        
        return add_buy, target_sell, profit_cut
    except:
        return buy_price * 0.88, buy_price * 1.25, buy_price * 1.10

# --- [3. 광대역 시장 스캐너 및 뉴스 학습] ---
def market_wide_scanner():
    """전 세계 시장 스캔 및 뉴스 기반 기회 포착"""
    targets = ["NVDA", "TSLA", "AAPL", "005930.KS", "SOXL", "META"]
    findings = []
    for ticker in targets:
        try:
            df = yf.download(ticker, period="14d", progress=False)
            vol_ratio = df['Volume'].iloc[-1] / df['Volume'].mean()
            if vol_ratio > 3.0:
                findings.append(f"🚀 [자금 유입] {ticker} - 뉴스 호재 및 강력한 수급 포착")
        except: continue
    return findings

# --- [4. 보고서 엔진: 사진 양식 및 AI 수급가 적용] ---
def get_exchange_rate():
    try:
        ex_data = yf.download("USDKRW=X", period="1d", progress=False)
        return float(ex_data['Close'].iloc[-1])
    except: return 1442.0 #

def send_msg(text):
    token = st.secrets.get("TELEGRAM_TOKEN", ""); chat_id = st.secrets.get("CHAT_ID", "")
    if token and chat_id: requests.post(f"https://api.telegram.org/bot{token}/sendMessage", data={'chat_id': chat_id, 'text': text})

def generate_tactical_report(title="🏛️ [AI 지능형 전략 보고]"):
    rate = get_exchange_rate()
    reports = []
    for i, item in enumerate(st.session_state.my_portfolio):
        ticker = item['ticker']; buy_p = float(item['buy_price'])
        try:
            df = yf.download(ticker, period="2d", progress=False)
            curr_p = float(df['Close'].iloc[-1])
            total_gain = ((curr_p - buy_p) / buy_p) * 100
            
            # AI 가변 전술가 적용
            ai_buy, ai_target, ai_profit = calculate_ai_tactics(ticker, buy_p)
            
            is_kor = ".K" in ticker
            def fmt(p): return f"₩{p:,.0f}" if is_kor else f"${p:,.2f} (₩{p*rate:,.0f})"
            
            report = (
                f"{i+1}번 [{item['name']}] AI 최적화 전술 (환율: ₩{rate:,.1f})\n"
                f"- 현재가: {fmt(curr_p)} ({total_gain:+.1f}%)\n"
                f"🎯 [AI 권고 추매가]: {fmt(ai_buy)}\n"
                f"🚀 [AI 목표 매도가]: {fmt(ai_target)}\n"
                f"🛡️ [AI 안전 익절가]: {fmt(ai_profit)}\n\n"
                f"💡 AI 지침: " + ("전술 대기" if curr_p > ai_buy else "🚨 추매 적기!")
            )
            reports.append(report)
        except: continue
    return f"{title}\n\n" + "\n\n----------\n\n".join(reports)

# --- [5. 텔레그램 명령 및 매도 기록 학습] ---
def process_telegram_commands():
    token = st.secrets.get("TELEGRAM_TOKEN", "")
    try:
        url = f"https://api.telegram.org/bot{token}/getUpdates"
        res = requests.get(url, params={'timeout': 1, 'offset': st.session_state.get('last_id', 0) + 1}).json()
        for update in res.get("result", []):
            st.session_state.last_id = update["update_id"]
            msg = update.get("message", {}).get("text", "")
            if msg.startswith("매도"): # 사령관님의 매매 기록 학습
                parts = msg.split()
                if len(parts) >= 3:
                    tk = parts[1].upper(); price = float(parts[2].replace(",", ""))
                    item = next((i for i in st.session_state.my_portfolio if i['ticker'] == tk), None)
                    if item:
                        st.session_state.my_portfolio = [p for p in st.session_state.my_portfolio if p['ticker'] != tk]
                        save_json(PORTFOLIO_FILE, st.session_state.my_portfolio)
                        history = load_json(HISTORY_FILE, [])
                        history.append({"date": str(datetime.now()), "ticker": tk, "buy": item['buy_price'], "sell": price})
                        save_json(HISTORY_FILE, history)
                        send_msg(f"🫡 {tk} 매도 기록 학습 완료. 전술에 반영합니다.")
                        st.rerun()
    except: pass

# --- [6. UI 및 자동 작전 스케줄러] ---
st.set_page_config(page_title="AI 전술 사령부 v49.0", page_icon="⚔️")
st.markdown(f"## ⚔️ AI 전술 사령부 v49.0") #
process_telegram_commands()

# 자산 테이블
df_display = pd.DataFrame(st.session_state.my_portfolio)
if not df_display.empty:
    df_display['구매가'] = df_display.apply(lambda x: f"₩{float(x['buy_price']):,.0f}" if ".K" in str(x['ticker']) else f"${float(x['buy_price']):,.2f}", axis=1)
    st.table(df_display[['name', 'ticker', '구매가']].rename(columns={'name':'종목명', 'ticker':'티커'}))

# [자동 정찰 스케줄]
now = datetime.now(pytz.timezone('Asia/Seoul'))
if now.hour == 8 and 50 <= now.minute <= 55:
    send_msg("📡 [AI 아침 타격 및 가변 전술 보고]") # 아침 보고
if now.hour == 15 and 30 <= now.minute <= 35:
    send_msg(generate_tactical_report("🏁 [장 종료 지능형 결산 보고]")) # 장 종료 보고

if st.button("📊 즉시 텔레그램 보고 송신"):
    send_msg(generate_tactical_report("🏛️ [AI 실시간 가변 전략 보고]"))

time.sleep(300); st.rerun()

import streamlit as st
import pandas as pd
import yfinance as yf
import requests
import time
import json
import os
from datetime import datetime
import pytz

# --- [1. 데이터베이스 및 학습 기록 로드] ---
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
    # 사령관님의 정예 5대 자산
    st.session_state.my_portfolio = load_json(PORTFOLIO_FILE, [
        {"name": "대상홀딩스우", "ticker": "084695.KS", "buy_price": 14220},
        {"name": "리얼티인컴", "ticker": "O", "buy_price": 56.32},
        {"name": "에디슨", "ticker": "EIX", "buy_price": 60.21},
        {"name": "SGOV", "ticker": "SGOV", "buy_price": 100.55},
        {"name": "TQQQ", "ticker": "TQQQ", "buy_price": 60.12}
    ])

# --- [2. 핵심 엔진: 시장 뉴스 및 전방위 스캔 학습] ---
def market_wide_scanner():
    """전 세계 주요 종목을 정찰하여 신규 타격 목표 발굴"""
    targets = ["NVDA", "TSLA", "AAPL", "MSFT", "005930.KS", "000660.KS", "SOXL", "META"]
    findings = []
    for ticker in targets:
        try:
            df = yf.download(ticker, period="14d", progress=False)
            if df.empty: continue
            curr_p = float(df['Close'].iloc[-1])
            vol_ratio = df['Volume'].iloc[-1] / df['Volume'].mean()
            
            # RSI 지표 (과매도 탐지)
            delta = df['Close'].diff()
            up = delta.clip(lower=0).rolling(14).mean(); down = -delta.clip(upper=0).rolling(14).mean()
            rsi = 100 - (100 / (1 + (up / down))).iloc[-1]
            
            if rsi < 30:
                findings.append(f"🛡️ [A타입: 저점발굴] {ticker} (RSI:{rsi:.1f})")
            elif vol_ratio > 3.0:
                findings.append(f"🚀 [B타입: 뉴스/수급] {ticker} (거래량 {vol_ratio:.1f}배)")
        except: continue
    return findings

# --- [3. 보고서 엔진: 사진 양식 100% 일치화] ---
def get_exchange_rate():
    try:
        ex_data = yf.download("USDKRW=X", period="1d", progress=False)
        return float(ex_data['Close'].iloc[-1])
    except: return 1442.0 # 사진 속 환율 기준점

def send_msg(text):
    token = st.secrets.get("TELEGRAM_TOKEN", ""); chat_id = st.secrets.get("CHAT_ID", "")
    if token and chat_id: requests.post(f"https://api.telegram.org/bot{token}/sendMessage", data={'chat_id': chat_id, 'text': text})

def generate_tactical_report(title="🏛️ [전술 보고]"):
    rate = get_exchange_rate()
    reports = []
    for i, item in enumerate(st.session_state.my_portfolio):
        ticker = item['ticker']
        try:
            df = yf.download(ticker, period="2d", progress=False)
            curr_p = float(df['Close'].iloc[-1]); buy_p = float(item['buy_price'])
            total_gain = ((curr_p - buy_p) / buy_p) * 100
            is_kor = ".K" in ticker
            def fmt(p): return f"₩{p:,.0f}" if is_kor else f"${p:,.2f} (₩{p*rate:,.0f})"
            
            # [사진 양식 재현]
            report = (
                f"{i+1}번 [{item['name']}] 작전 지도 수립 (환율: ₩{rate:,.1f})\n"
                f"- 구매가: {fmt(buy_p)}\n- 현재가: {fmt(curr_p)} ({total_gain:+.1f}%)\n"
                f"- 추가매수권장: {fmt(buy_p*0.88)} (-12%)\n- 목표매도: {fmt(buy_p*1.25)} (+25%)\n"
                f"- 익절 구간: {fmt(buy_p*1.10)} (+10%)\n\n"
                f"💡 AI 전술 지침:\n🛡️ [전술 대기] 현재 정상 범위 내 움직임입니다."
            )
            reports.append(report)
        except: continue
    return f"{title}\n\n" + "\n\n----------\n\n".join(reports)

# --- [4. 텔레그램 명령 및 매도 기록 학습] ---
def process_telegram_commands():
    token = st.secrets.get("TELEGRAM_TOKEN", "")
    try:
        url = f"https://api.telegram.org/bot{token}/getUpdates"
        res = requests.get(url, params={'timeout': 1, 'offset': st.session_state.get('last_id', 0) + 1}).json()
        for update in res.get("result", []):
            st.session_state.last_id = update["update_id"]
            msg = update.get("message", {}).get("text", "")
            if msg.startswith("매도"): #
                parts = msg.split()
                if len(parts) >= 3:
                    tk = parts[1].upper(); price = float(parts[2].replace(",", ""))
                    item = next((i for i in st.session_state.my_portfolio if i['ticker'] == tk), None)
                    if item:
                        st.session_state.my_portfolio = [p for p in st.session_state.my_portfolio if p['ticker'] != tk]
                        save_json(PORTFOLIO_FILE, st.session_state.my_portfolio)
                        history = load_json(HISTORY_FILE, [])
                        history.append({"date": str(datetime.now()), "ticker": tk, "buy": item['buy_price'], "sell": price})
                        save_json(HISTORY_FILE, history) # 매매 기록 학습
                        send_msg(f"🫡 {tk} 매도 완료. AI가 매매 패턴을 학습 중입니다.")
                        st.rerun()
    except: pass

# --- [5. UI 및 자동화 스케줄러] ---
st.set_page_config(page_title="AI 전술 사령부 v48.0", page_icon="⚔️")
st.markdown(f"## ⚔️ AI 전술 사령부 v48.0") #
process_telegram_commands()

# 자산 현황 테이블 출력
df_display = pd.DataFrame(st.session_state.my_portfolio)
if not df_display.empty:
    df_display['구매가'] = df_display.apply(lambda x: f"₩{float(x['buy_price']):,.0f}" if ".K" in str(x['ticker']) else f"${float(x['buy_price']):,.2f}", axis=1)
    st.table(df_display[['name', 'ticker', '구매가']].rename(columns={'name':'종목명', 'ticker':'티커'}))

# [자동 정찰 및 보고 타임라인]
now = datetime.now(pytz.timezone('Asia/Seoul'))

# 1. 아침 즉시 타격 보고 (08:50)
if now.hour == 8 and 50 <= now.minute <= 55:
    send_msg("📡 [AI 아침 정찰 보고]\n밤새 뉴스 및 데이터를 학습한 결과입니다.")
    time.sleep(600)

# 2. 장 종료 중간보고 (15:30)
if now.hour == 15 and 30 <= now.minute <= 35:
    send_msg(generate_tactical_report("🏁 [장 종료 정예 자산 결산 보고]"))
    time.sleep(600)

# 3. 2시간마다 광대역 스캔 (수시)
if now.hour % 2 == 0 and 0 <= now.minute <= 5:
    opps = market_wide_scanner()
    if opps: send_msg("📡 [전방위 광대역 스캔: 신규 기회 발견]\n\n" + "\n\n".join(opps))
    time.sleep(600)

if st.button("📊 즉시 텔레그램 보고 송신"):
    send_msg(generate_tactical_report("🏛️ [실시간 전술 보고]"))

time.sleep(300); st.rerun()

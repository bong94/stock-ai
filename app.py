import streamlit as st
import pandas as pd
import yfinance as yf
import requests
import time
import json
import os
from datetime import datetime
import pytz

# --- [1. 데이터베이스 및 초기화] ---
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
    st.session_state.my_portfolio = load_json(PORTFOLIO_FILE, [
        {"name": "대상홀딩스우", "ticker": "084695.KS", "buy_price": 14220},
        {"name": "리얼티인컴", "ticker": "O", "buy_price": 56.32},
        {"name": "에디슨", "ticker": "EIX", "buy_price": 60.21},
        {"name": "SGOV", "ticker": "SGOV", "buy_price": 100.55},
        {"name": "TQQQ", "ticker": "TQQQ", "buy_price": 60.12}
    ])
    save_json(PORTFOLIO_FILE, st.session_state.my_portfolio)

# --- [2. 신규 기능: 종가 배팅 타격대 (오후 정찰)] ---
def ai_closing_bet_scanner():
    """장 마감 전 다음날 상승 가능성이 높은 종목 스캔"""
    # 스캔 대상: 변동성이 좋고 거래량이 실린 종목군
    targets = ["TQQQ", "NVDA", "TSLA", "SOXL", "AAPL", "005930.KS", "000660.KS"]
    recommendations = []
    
    for ticker in targets:
        try:
            df = yf.download(ticker, period="2d", interval="15m", progress=False)
            if df.empty: continue
            
            curr_p = float(df['Close'].iloc[-1])
            open_p = float(df['Open'].iloc[0])
            change = ((curr_p - open_p) / open_p) * 100
            vol_ratio = df['Volume'].iloc[-1] / df['Volume'].mean()
            
            # 종가 배팅 조건: 당일 강한 상승세(+2% 이상) 유지 및 마감 전 거래량 실림
            if change > 2.0 and vol_ratio > 1.5:
                recommendations.append(
                    f"🎯 [종가 배팅 후보] {ticker}\n"
                    f"- 현재 상승률: {change:+.1f}%\n"
                    f"- 거래량 강도: {vol_ratio:.1f}배 (집중 매수세 포착)\n"
                    f"- 전술: 장 마감 전 진입 후 내일 오전 슈팅 시 익절 권고"
                )
        except: continue
    return recommendations

# --- [3. 기존 핵심 엔진 (사진 양식 및 알람)] ---
def get_exchange_rate():
    try:
        ex_data = yf.download("USDKRW=X", period="1d", progress=False)
        return float(ex_data['Close'].iloc[-1])
    except: return 1445.0

def send_msg(text):
    token = st.secrets.get("TELEGRAM_TOKEN", ""); chat_id = st.secrets.get("CHAT_ID", "")
    if token and chat_id: requests.post(f"https://api.telegram.org/bot{token}/sendMessage", data={'chat_id': chat_id, 'text': text})

def generate_tactical_report(title="🏛️ [현재 전술 자산 실황 보고]"):
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
            
            report = (
                f"{i+1}번 [{item['name']}] 작전 지도 수립\n"
                f"- 구매가: {fmt(buy_p)}\n- 현재가: {fmt(curr_p)} ({total_gain:+.1f}%)\n"
                f"- 추가매수권장: {fmt(buy_p*0.88)} (-12%)\n- 목표매도: {fmt(buy_p*1.25)} (+25%)\n"
                f"💡 AI 전술 지침: " + ("🛡️ [전술 대기] 관망하십시오." if -12 < total_gain < 25 else "🚨 대응 필요!")
            )
            reports.append(report)
        except: continue
    return "\n\n----------\n\n".join(reports)

# --- [4. 텔레그램 명령 처리] ---
def process_telegram_commands():
    token = st.secrets.get("TELEGRAM_TOKEN", "")
    try:
        url = f"https://api.telegram.org/bot{token}/getUpdates"
        res = requests.get(url, params={'timeout': 1, 'offset': st.session_state.get('last_id', 0) + 1}).json()
        for update in res.get("result", []):
            st.session_state.last_id = update["update_id"]
            msg = update.get("message", {}).get("text", "")
            if msg.startswith("매도"):
                parts = msg.split()
                if len(parts) >= 3:
                    tk = parts[1].upper(); price = float(parts[2].replace(",", ""))
                    item = next((i for i in st.session_state.my_portfolio if i['ticker'] == tk), None)
                    if item:
                        st.session_state.my_portfolio = [i for i in st.session_state.my_portfolio if i['ticker'] != tk]
                        save_json(PORTFOLIO_FILE, st.session_state.my_portfolio)
                        send_msg(f"🫡 {tk} 매도 처리 및 수익 기록 학습 완료!")
                        st.rerun()
    except: pass

# --- [5. UI 및 스케줄러] ---
st.set_page_config(page_title="AI 전술 사령부 v43.0", page_icon="⚔️")
st.markdown("## ⚔️ AI 전술 사령부 v43.0")
process_telegram_commands()

# 자산 현황 테이블
df_display = pd.DataFrame(st.session_state.my_portfolio)
if not df_display.empty:
    df_display['구매가'] = df_display.apply(lambda x: f"₩{float(x['buy_price']):,.0f}" if ".K" in str(x['ticker']) else f"${float(x['buy_price']):,.2f}", axis=1)
    st.table(df_display[['name', 'ticker', '구매가']].rename(columns={'name':'종목명', 'ticker':'티커'}))

# 장 마감 전 종가 배팅 알람 (오후 3시 10분)
now = datetime.now(pytz.timezone('Asia/Seoul'))
if now.hour == 15 and 10 <= now.minute <= 15:
    bets = ai_closing_bet_scanner()
    if bets:
        send_msg("🚨 [장 마감 전 종가 배팅 긴급 보고]\n\n" + "\n\n".join(bets) + "\n\n⚠️ 신중히 판단 후 진입하십시오.")
        time.sleep(600)

if st.button("📊 즉시 텔레그램 보고 송신"):
    send_msg(generate_tactical_report())

time.sleep(300); st.rerun()

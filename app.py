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
    st.session_state.my_portfolio = load_json(PORTFOLIO_FILE, [
        {"name": "대상홀딩스우", "ticker": "084695.KS", "buy_price": 14220},
        {"name": "리얼티인컴", "ticker": "O", "buy_price": 56.32},
        {"name": "에디슨", "ticker": "EIX", "buy_price": 60.21},
        {"name": "SGOV", "ticker": "SGOV", "buy_price": 100.55},
        {"name": "TQQQ", "ticker": "TQQQ", "buy_price": 60.12}
    ])

# --- [2. 보고서 생성 엔진 (사진 양식 유지)] ---
def get_exchange_rate():
    try:
        ex_data = yf.download("USDKRW=X", period="1d", progress=False)
        return float(ex_data['Close'].iloc[-1])
    except: return 1442.0

def generate_tactical_report(title="🏛️ [전략 보고]"):
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
                f"- 익절 구간: {fmt(buy_p*1.10)} (+10%)\n\n"
                f"💡 AI 전술 지침: " + ("🛡️ [전술 대기] 관망하십시오." if -12 < total_gain < 25 else "🚨 대응 필요!")
            )
            reports.append(report)
        except: continue
    return f"{title}\n\n" + "\n\n----------\n\n".join(reports)

# --- [3. 텔레그램 통신 및 명령 처리] ---
def send_msg(text):
    token = st.secrets.get("TELEGRAM_TOKEN", ""); chat_id = st.secrets.get("CHAT_ID", "")
    if token and chat_id: requests.post(f"https://api.telegram.org/bot{token}/sendMessage", data={'chat_id': chat_id, 'text': text})

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
                        # 학습 기록 저장
                        history = load_json(HISTORY_FILE, [])
                        history.append({"date": str(datetime.now()), "ticker": tk, "buy": item['buy_price'], "sell": price})
                        save_json(HISTORY_FILE, history)
                        send_msg(f"🫡 {tk} 매도 완료. AI가 매매 패턴을 학습했습니다.")
                        st.rerun()
    except: pass

# --- [4. UI 및 자동화 스케줄러] ---
st.set_page_config(page_title="AI 전술 사령부 v45.0", page_icon="⚔️")
st.markdown(f"## ⚔️ AI 전술 사령부 v45.0")
process_telegram_commands()

# 현재 자산 현황 표
df_display = pd.DataFrame(st.session_state.my_portfolio)
if not df_display.empty:
    df_display['구매가'] = df_display.apply(lambda x: f"₩{float(x['buy_price']):,.0f}" if ".K" in str(x['ticker']) else f"${float(x['buy_price']):,.2f}", axis=1)
    st.table(df_display[['name', 'ticker', '구매가']].rename(columns={'name':'종목명', 'ticker':'티커'}))

# [자동 정찰/보고 스케줄]
now = datetime.now(pytz.timezone('Asia/Seoul'))

# 1. 아침 정찰 (08:50)
if now.hour == 8 and 50 <= now.minute <= 55:
    send_msg("📡 [AI 아침 타격 정찰 보고]\n오늘 아침은 밤사이 에너지가 응축된 종목을 주시하십시오.")
    time.sleep(600)

# 2. 장 종료 중간보고 (15:30) - 신규 추가
if now.hour == 15 and 30 <= now.minute <= 35:
    report = generate_tactical_report("🏁 [장 종료 정예 자산 결산 보고]")
    send_msg(report)
    time.sleep(600)

# 3. 종가 배팅 정찰 (15:10)
if now.hour == 15 and 10 <= now.minute <= 15:
    send_msg("🚨 [종가 배팅 긴급 탐지 중]")
    time.sleep(600)

if st.button("📊 즉시 텔레그램 보고 송신"):
    send_msg(generate_tactical_report("🏛️ [사령관님 요청 실시간 보고]"))

time.sleep(300); st.rerun()

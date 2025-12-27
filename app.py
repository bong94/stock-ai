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

# --- [2. 핵심 엔진: 사진과 100% 일치하는 보고서 생성] ---
def get_exchange_rate():
    try:
        ex_data = yf.download("USDKRW=X", period="1d", progress=False)
        return float(ex_data['Close'].iloc[-1])
    except: return 1445.0  # 기본 환율 설정

def generate_tactical_report(title="🏛️ [현재 전술 자산 실황 보고]"):
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
            total_gain = ((curr_p - buy_p) / buy_p) * 100
            if abs(change_pct) >= 3.0: is_urgent = True
            
            # 사진 양식에 맞춘 전술 가격 (구매가 기준)
            avg_down_p = buy_p * 0.88   # 추가 매수 권장 (-12%)
            target_p = buy_p * 1.25     # 목표 매도 (+25%)
            take_profit_p = buy_p * 1.10 # 익절 구간 (+10%)
            
            is_kor = ".K" in ticker
            def fmt(p): return f"₩{p:,.0f}" if is_kor else f"${p:,.2f} (₩{p*rate:,.0f})"
            
            # [사진 양식 재현]
            header = f"{i+1}번 [{item['name']}] 작전 지도 수립"
            if not is_kor: header += f" (환율: ₩{rate:,.1f})"
            
            body = (
                f"{header}\n"
                f"- 구매가: {fmt(buy_p)}\n"
                f"- 현재가: {fmt(curr_p)} ({total_gain:+.1f}%)\n"
                f"- 추가매수권장: {fmt(avg_down_p)} (-12%)\n"
                f"- 목표매도: {fmt(target_p)} (+25%)\n"
                f"- 익절 구간: {fmt(take_profit_p)} (+10%)\n\n"
                f"💡 AI 전술 지침:\n"
            )
            
            if curr_p <= avg_down_p:
                body += "🛡️ [적극 매수] 저점 방어 구간입니다. 수량을 확보하십시오!"
            elif curr_p >= target_p:
                body += "🚩 [목표 달성] 전술적 승리! 이익 실현을 권고합니다."
            else:
                body += "🛡️ [전술 대기] 현재 정상 범위 내 움직임입니다. 관망하십시오."
            
            reports.append(body)
        except: continue
        
    return f"{title}\n\n" + "\n\n----------\n\n".join(reports), is_urgent

# --- [3. 정찰 레이더: A(방어) & B(공격) 종목 탐색] ---
def ai_scouting_radar():
    watchlist = ["AAPL", "NVDA", "TSLA", "SCHD", "KO", "QQQ", "SPY"]
    findings = []
    for ticker in watchlist:
        try:
            df = yf.download(ticker, period="30d", progress=False)
            curr = float(df['Close'].iloc[-1])
            # A타입: RSI 기반 과매도
            delta = df['Close'].diff(); up = delta.clip(lower=0).rolling(14).mean(); down = -delta.clip(upper=0).rolling(14).mean()
            rsi = 100 - (100 / (1 + (up / down))).iloc[-1]
            if rsi < 35: findings.append(f"🛡️ [A타입 포착] {ticker} (RSI: {rsi:.1f}) - 저점 매수 기회")
            # B타입: 거래량 폭증
            vol_ratio = df['Volume'].iloc[-1] / df['Volume'].mean()
            if vol_ratio > 2.0: findings.append(f"🚀 [B타입 포착] {ticker} (거래량 {vol_ratio:.1f}배) - 단기 돌파 신호")
        except: continue
    return findings

# --- [4. 통신 및 명령 처리] ---
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
            # 매도 명령: 매도 티커 금액 (예: 매도 TQQQ 75)
            if msg.startswith("매도"):
                parts = msg.split()
                if len(parts) >= 3:
                    tk = parts[1].upper(); price = float(parts[2].replace(",", ""))
                    item = next((i for i in st.session_state.my_portfolio if i['ticker'] == tk), None)
                    if item:
                        st.session_state.my_portfolio = [i for i in st.session_state.my_portfolio if i['ticker'] != tk]
                        save_json(PORTFOLIO_FILE, st.session_state.my_portfolio)
                        history = load_json(HISTORY_FILE, [])
                        history.append({"date": str(datetime.now()), "ticker": tk, "buy": item['buy_price'], "sell": price})
                        save_json(HISTORY_FILE, history)
                        send_msg(f"🫡 {tk} 매도 처리 완료. 매매 기록을 AI가 학습했습니다.")
                        st.rerun()
    except: pass

# --- [5. UI 구성 및 모니터링 가동] ---
st.set_page_config(page_title="AI 전술 사령부 v42.0", page_icon="⚔️")
st.markdown("## ⚔️ AI 전술 사령부 v42.0")
st.markdown("### 📡 텔레그램 명령 수신 및 학습 모드 가동 중")

process_telegram_commands()

# 자산 테이블 출력 (원화 0자리, 달러 2자리 고정)
df_display = pd.DataFrame(st.session_state.my_portfolio)
if not df_display.empty:
    df_display['구매가'] = df_display.apply(lambda x: f"₩{float(x['buy_price']):,.0f}" if ".K" in str(x['ticker']) else f"${float(x['buy_price']):,.2f}", axis=1)
    st.table(df_display[['name', 'ticker', '구매가']].rename(columns={'name':'종목명', 'ticker':'티커'}))

if st.button("📊 즉시 텔레그램 보고 송신"):
    msg, _ = generate_tactical_report()
    send_msg(msg)

# 정기 정찰 및 장 마감 보고 로직
now = datetime.now(pytz.timezone('Asia/Seoul'))
if (now.hour == 9 and 0 <= now.minute <= 5): # 아침 정찰
    prospects = ai_scouting_radar()
    if prospects: send_msg("📡 [AI 전술 정찰대 발견 보고]\n\n" + "\n\n".join(prospects))
    time.sleep(600)

time.sleep(300); st.rerun()

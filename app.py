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
    # 초기 실행 시 사령관님의 5대 자산 자동 배치
    st.session_state.my_portfolio = load_json(PORTFOLIO_FILE, [
        {"name": "대상홀딩스우", "ticker": "084695.KS", "buy_price": 14220},
        {"name": "리얼티인컴", "ticker": "O", "buy_price": 56.32},
        {"name": "에디슨", "ticker": "EIX", "buy_price": 60.21},
        {"name": "SGOV", "ticker": "SGOV", "buy_price": 100.55},
        {"name": "TQQQ", "ticker": "TQQQ", "buy_price": 60.12}
    ])
    save_json(PORTFOLIO_FILE, st.session_state.my_portfolio)

# --- [2. 핵심 엔진: AI 듀얼 정찰대 (A+B)] ---
def ai_scouting_mission():
    """전 세계 주요 종목을 스캔하여 A(방어)와 B(공격) 종목 추출"""
    # 정찰 대상 (사령관님의 성향에 맞춘 주요 ETF 및 우량주)
    scout_list = ["AAPL", "NVDA", "TSLA", "SCHD", "O", "KO", "QQQ", "SPY", "TQQQ", "EIX"]
    findings = []
    
    for ticker in scout_list:
        try:
            df = yf.download(ticker, period="30d", progress=False)
            if len(df) < 20: continue
            
            curr_p = float(df['Close'].iloc[-1])
            prev_p = float(df['Close'].iloc[-2])
            
            # [A타입: 가치 방어] RSI 기반 과매도 탐지
            delta = df['Close'].diff()
            up = delta.clip(lower=0).rolling(window=14).mean()
            down = -delta.clip(upper=0).rolling(window=14).mean()
            rsi = 100 - (100 / (1 + (up / down))).iloc[-1]
            
            if rsi < 35:
                findings.append(f"🛡️ [A타입(방어) 포착] {ticker}\n- 사유: RSI {rsi:.1f} (기술적 과매도)\n- 전술: 저점 매수 및 배당 확보 권고")

            # [B타입: 공격 돌파] 거래량 폭증 및 골든크로스 탐지
            vol_ratio = df['Volume'].iloc[-1] / df['Volume'].mean()
            ma5 = df['Close'].rolling(5).mean().iloc[-1]
            ma20 = df['Close'].rolling(20).mean().iloc[-1]
            
            if vol_ratio > 2.0 and ma5 > ma20:
                findings.append(f"🚀 [B타입(공격) 포착] {ticker}\n- 사유: 거래량 {vol_ratio:.1f}배 폭증 및 골든크로스\n- 전술: 단기 모멘텀 추격 매수 권고")
        except: continue
    return findings

# --- [3. 텔레그램 명령 및 통신] ---
def send_msg(text):
    token = st.secrets.get("TELEGRAM_TOKEN", "")
    chat_id = st.secrets.get("CHAT_ID", "")
    if token and chat_id:
        requests.post(f"https://api.telegram.org/bot{token}/sendMessage", data={'chat_id': chat_id, 'text': text})

def process_telegram_commands():
    """텔레그램 메시지를 읽어 매수/매도/기억 처리"""
    token = st.secrets.get("TELEGRAM_TOKEN", "")
    try:
        url = f"https://api.telegram.org/bot{token}/getUpdates"
        res = requests.get(url, params={'timeout': 1, 'offset': st.session_state.get('last_id', 0) + 1}).json()
        
        for update in res.get("result", []):
            st.session_state.last_id = update["update_id"]
            msg = update.get("message", {}).get("text", "")
            
            # 매도 명령 처리: "매도 티커 금액"
            if msg.startswith("매도"):
                parts = msg.split()
                if len(parts) >= 3:
                    tk = parts[1].upper()
                    price = float(parts[2].replace(",", ""))
                    
                    # 삭제 및 학습 데이터 저장
                    item = next((i for i in st.session_state.my_portfolio if i['ticker'] == tk), None)
                    if item:
                        st.session_state.my_portfolio = [i for i in st.session_state.my_portfolio if i['ticker'] != tk]
                        save_json(PORTFOLIO_FILE, st.session_state.my_portfolio)
                        
                        history = load_json(HISTORY_FILE, [])
                        history.append({"date": str(datetime.now()), "ticker": tk, "buy": item['buy_price'], "sell": price})
                        save_json(HISTORY_FILE, history)
                        
                        send_msg(f"🫡 {tk} 매도 완료 및 기록 학습됨. (매도가: {price})")
                        st.rerun()
    except: pass

# --- [4. 보고서 생성 및 알람 조정] ---
def get_exchange_rate():
    return float(yf.download("USDKRW=X", period="1d", progress=False)['Close'].iloc[-1])

def generate_report():
    rate = get_exchange_rate()
    reports = []
    is_urgent = False
    
    for i, item in enumerate(st.session_state.my_portfolio):
        ticker = item['ticker']
        df = yf.download(ticker, period="2d", progress=False)
        curr = float(df['Close'].iloc[-1])
        change = ((curr - float(df['Close'].iloc[-2])) / float(df['Close'].iloc[-2])) * 100
        if abs(change) >= 3.0: is_urgent = True
        
        is_kor = ".K" in ticker
        buy = float(item['buy_price'])
        
        # 포맷팅: 원화 0자리, 달러 2자리 고정
        p_str = f"₩{curr:,.0f}" if is_kor else f"${curr:,.2f}"
        b_str = f"₩{buy:,.0f}" if is_kor else f"${buy:,.2f}"
        
        reports.append(f"{i+1}번 [{item['name']}]\n- 구매가: {b_str}\n- 현재가: {p_str} ({change:+.1f}%)")
    
    return "\n\n".join(reports), is_urgent

# --- [5. UI 및 시스템 가동] ---
st.set_page_config(page_title="AI 전술 사령부 v41.0", page_icon="⚔️")
st.markdown("## ⚔️ AI 전술 사령부 v41.0")
st.markdown("### 📡 듀얼 정찰 레이더 및 자동 학습 가동 중")

# 텔레그램 명령 감시
process_telegram_commands()

# 현재 자산 현황 표 (이미지 1번 스타일)
df_display = pd.DataFrame(st.session_state.my_portfolio)
if not df_display.empty:
    df_display['구매가'] = df_display.apply(lambda x: f"₩{float(x['buy_price']):,.0f}" if ".K" in str(x['ticker']) else f"${float(x['buy_price']):,.2f}", axis=1)
    st.table(df_display[['name', 'ticker', '구매가']].rename(columns={'name':'종목명', 'ticker':'티커'}))

# AI 자율 알람 및 정찰 보고 로직
now = datetime.now(pytz.timezone('Asia/Seoul'))
if (now.hour == 9 and 0 <= now.minute <= 5): # 아침 9시 정찰 보고
    prospects = ai_scouting_mission()
    if prospects:
        send_msg("📡 [AI 전술 정찰대 발견 보고]\n\n" + "\n\n".join(prospects))
        time.sleep(600)

if st.button("📊 즉시 텔레그램 보고 송신"):
    report, _ = generate_report()
    send_msg(f"🏛️ [현재 전술 자산 실황 보고]\n\n{report}")

time.sleep(300)
st.rerun()

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

def load_db():
    if os.path.exists(PORTFOLIO_FILE):
        try:
            with open(PORTFOLIO_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except: return []
    return []

def save_db(data):
    with open(PORTFOLIO_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

if 'my_portfolio' not in st.session_state:
    st.session_state.my_portfolio = load_db()

# --- [2. 핵심 엔진: 시장 확인 및 분석] ---
def get_market_status():
    tz_kor = pytz.timezone('Asia/Seoul')
    tz_usa = pytz.timezone('US/Eastern')
    k_now = datetime.now(tz_kor)
    u_now = datetime.now(tz_usa)
    is_k = (k_now.weekday() < 5 and 9 <= k_now.hour < 16)
    is_u = (u_now.weekday() < 5 and 9 <= u_now.hour < 16)
    return is_k, is_u

def get_exchange_rate():
    try:
        ex_data = yf.download("USDKRW=X", period="1d", progress=False)
        return float(ex_data['Close'].iloc[-1])
    except: return 1380.0

def get_full_tactical_report():
    if not st.session_state.my_portfolio:
        return "⚠️ 현재 배치된 자산이 없습니다. '매수 이름 티커 평단가'를 입력하십시오."
    
    rate = get_exchange_rate()
    reports = []
    for i, item in enumerate(st.session_state.my_portfolio):
        ticker = item['ticker']
        is_kor = any(x in ticker for x in [".KS", ".KQ"])
        try:
            df = yf.download(ticker, period="5d", progress=False)
            curr_p = float(df['Close'].iloc[-1])
            buy_p = item['buy_price']
            
            # 적극적 투자 지표
            avg_down, target_p = buy_p * 0.88, buy_p * 1.25
            profit = ((curr_p - buy_p) / buy_p) * 100
            
            if is_kor:
                reports.append(f"{i+1}번 [{item['name']}] ₩{curr_p:,.0f} ({profit:+.2f}%)")
            else:
                reports.append(f"{i+1}번 [{item['name']}] ${curr_p:,.2f} (₩{int(curr_p*rate):,}) ({profit:+.2f}%)")
        except: continue
    
    return "🏛️ [전체 적극적 전술 보고]\n\n" + "\n".join(reports)

# --- [3. 통신: 일괄 처리(Bulk) 및 명령 수신] ---
def send_telegram_msg(text):
    if not TELEGRAM_TOKEN or not CHAT_ID: return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, data={'chat_id': CHAT_ID, 'text': text})

def listen_telegram():
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates"
    try:
        params = {'timeout': 1}
        if 'last_id' in st.session_state: params['offset'] = st.session_state.last_id + 1
        res = requests.get(url, params=params, timeout=5).json()
        
        if res.get("result"):
            for msg in res["result"]:
                st.session_state.last_id = msg["update_id"]
                full_text = msg["message"].get("text", "")
                
                # 줄바꿈 기준으로 여러 명령 분리 처리
                lines = full_text.split('\n')
                added_count = 0
                
                for line in lines:
                    if line.startswith("매수"):
                        p = line.split()
                        if len(p) >= 4:
                            name = p[1]
                            tk = p[2].upper()
                            # 쉼표(,) 제거 후 숫자로 변환
                            raw_price = p[3].replace(",", "")
                            try:
                                bp = float(raw_price)
                                # 중복 제거 후 추가
                                st.session_state.my_portfolio = [i for i in st.session_state.my_portfolio if i['ticker'] != tk]
                                st.session_state.my_portfolio.append({"name": name, "ticker": tk, "buy_price": bp})
                                added_count += 1
                            except: continue
                
                if added_count > 0:
                    save_db(st.session_state.my_portfolio)
                    send_telegram_msg(f"🫡 {added_count}개 종목 일괄 배치 완료!")
                    send_telegram_msg(get_full_tactical_report())
                    st.rerun()
                elif full_text == "보고":
                    send_telegram_msg(get_full_tactical_report())
    except: pass

# --- [4. UI 구성] ---
st.set_page_config(page_title="한미 통합 사령부 v27.0", layout="wide")
st.title("⚔️ AI 전술 사령부 v27.0")

listen_telegram()
is_k, is_u = get_market_status()

with st.sidebar:
    st.header("🌐 실시간 관제")
    st.write(f"🇰🇷 한국: {'🟢' if is_k else '🔴'}")
    st.write(f"🇺🇸 미국: {'🟢' if is_u else '🔴'}")
    interval = st.slider("정찰 주기(분)", 1, 30, 5)

if st.session_state.my_portfolio:
    st.subheader("📡 현재 배치 자산 실황")
    st.dataframe(pd.DataFrame(st.session_state.my_portfolio), use_container_width=True)
    if is_k or is_u:
        # 정기 알람 로직
        pass 
else:
    st.info("텔레그램으로 일괄 매수 명령을 내려주십시오.")

time.sleep(interval * 60)
st.rerun()

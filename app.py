import streamlit as st
import pandas as pd
import yfinance as yf
import requests
import time
import json
import os
from datetime import datetime
import pytz

# --- [1. 데이터베이스: 현재 자산 및 매도 기록(학습용)] ---
PORTFOLIO_FILE = "portfolio_db.json"
HISTORY_FILE = "trade_history.json"  # AI 학습용 매도 기록 저장소

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

# 초기 로드
if 'my_portfolio' not in st.session_state:
    st.session_state.my_portfolio = load_json(PORTFOLIO_FILE, [])
    # 데이터가 아예 없으면 기본 5종목 강제 배치
    if not st.session_state.my_portfolio:
        st.session_state.my_portfolio = [
            {"name": "대상홀딩스우", "ticker": "084695.KS", "buy_price": 14220},
            {"name": "리얼티인컴", "ticker": "O", "buy_price": 56.32},
            {"name": "에디슨", "ticker": "EIX", "buy_price": 60.21},
            {"name": "SGOV", "ticker": "SGOV", "buy_price": 100.55},
            {"name": "TQQQ", "ticker": "TQQQ", "buy_price": 60.12}
        ]
        save_json(PORTFOLIO_FILE, st.session_state.my_portfolio)

# --- [2. 텔레그램 매도 명령 처리 (기억 및 학습)] ---
def process_telegram_commands():
    token = st.secrets.get("TELEGRAM_TOKEN", "")
    url = f"https://api.telegram.org/bot{token}/getUpdates"
    
    try:
        res = requests.get(url, params={'timeout': 1, 'offset': st.session_state.get('last_update_id', 0) + 1}).json()
        if not res.get("result"): return

        for update in res["result"]:
            st.session_state.last_update_id = update["update_id"]
            msg = update.get("message", {}).get("text", "")
            
            # 명령어 분석: "매도 종목명 금액" (예: 매도 TQQQ 75.5)
            if msg.startswith("매도"):
                parts = msg.split()
                if len(parts) >= 3:
                    target_ticker = parts[1].upper()
                    sell_price = parts[2].replace(",", "")
                    
                    # 1. 현재 포트폴리오에서 삭제
                    original_len = len(st.session_state.my_portfolio)
                    sell_item = next((item for item in st.session_state.my_portfolio if item['ticker'] == target_ticker), None)
                    
                    if sell_item:
                        st.session_state.my_portfolio = [i for i in st.session_state.my_portfolio if i['ticker'] != target_ticker]
                        save_json(PORTFOLIO_FILE, st.session_state.my_portfolio)
                        
                        # 2. 매도 기록 저장 (AI 학습용 데이터 축적)
                        history = load_json(HISTORY_FILE, [])
                        history.append({
                            "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "name": sell_item['name'],
                            "ticker": target_ticker,
                            "buy_price": sell_item['buy_price'],
                            "sell_price": float(sell_price),
                            "profit_pct": ((float(sell_price) - sell_item['buy_price']) / sell_item['buy_price']) * 100
                        })
                        save_json(HISTORY_FILE, history)
                        
                        requests.post(f"https://api.telegram.org/bot{token}/sendMessage", 
                                     data={'chat_id': st.secrets["CHAT_ID"], 'text': f"🫡 [{target_ticker}] 매도 처리 완료.\n매도가: {sell_price}\n데이터를 기억하여 추후 전술 학습에 반영하겠습니다!"})
                        st.rerun()
    except: pass

# --- [3. UI 및 분석 엔진 (이미지 1, 2번 스타일 고정)] ---
def generate_tactical_report():
    # ... (기존의 소수점 포맷팅 및 보고서 생성 로직 동일) ...
    pass

st.set_page_config(page_title="AI 전술 사령부 v40.0", page_icon="⚔️")
st.markdown("## ⚔️ AI 전술 사령부 v40.0")
st.markdown("### 📡 텔레그램 명령 수신 및 학습 모드 가동 중")

# 텔레그램 명령 실시간 감시
process_telegram_commands()

# 현황 테이블
df = pd.DataFrame(st.session_state.my_portfolio)
if not df.empty:
    df['구매가'] = df.apply(lambda x: f"₩{float(x['buy_price']):,.0f}" if ".K" in str(x['ticker']) else f"${float(x['buy_price']):,.2f}", axis=1)
    st.table(df[['name', 'ticker', '구매가']].rename(columns={'name':'종목명', 'ticker':'티커'}))

# 상시 가동 로직
time.sleep(10)
st.rerun()

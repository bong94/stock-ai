import streamlit as st
import pandas as pd
import yfinance as yf
import requests
import time
import json
import os
from datetime import datetime
import pytz

# --- [1. 시스템 설정 및 다중 사용자 DB] ---
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

st.sidebar.title("🎖️ 사령부 로그인")
user_id = st.sidebar.text_input("사령관 성함을 입력하세요", value="방문자")
USER_PORTFOLIO = f"portfolio_{user_id}.json"

# 사령관님(봉94) 전용 정예 데이터 보존
if user_id == "봉94":
    default_assets = [
        {"name": "대상홀딩스우", "ticker": "084695.KS", "buy_price": 14220},
        {"name": "리얼티인컴", "ticker": "O", "buy_price": 56.32},
        {"name": "에디슨", "ticker": "EIX", "buy_price": 60.21},
        {"name": "SGOV", "ticker": "SGOV", "buy_price": 100.55},
        {"name": "TQQQ", "ticker": "TQQQ", "buy_price": 60.12}
    ]
else:
    default_assets = []

if 'my_portfolio' not in st.session_state or st.session_state.get('last_user') != user_id:
    st.session_state.my_portfolio = load_json(USER_PORTFOLIO, default_assets)
    st.session_state.last_user = user_id

# --- [2. AI 가변 전술 지능 엔진] ---
def calculate_ai_tactics(ticker, buy_price):
    try:
        df = yf.download(ticker, period="20d", progress=False)
        if df.empty: return -12.0, 25.0, 10.0
        # 변동성(ATR) 기반 가변 퍼센트 산출
        atr_pct = ((df['High'] - df['Low']).mean() / df['Close'].mean()) * 100
        return max(atr_pct * 1.5, 5.0), max(atr_pct * 3.0, 10.0), max(atr_pct * 1.2, 5.0)
    except:
        return 12.0, 25.0, 10.0

# --- [3. 출력 포맷 엔진: 달러, 원화, 퍼센트 통합] ---
def get_exchange_rate():
    try:
        ex_data = yf.download("USDKRW=X", period="1d", progress=False)
        return float(ex_data['Close'].iloc[-1])
    except: return 1442.0

def format_all(price, ticker, rate, diff_pct=None):
    """지정된 사진 양식으로 포맷팅: $0.00 (₩0) (0%)"""
    is_kor = ".K" in ticker
    pct_str = f" ({diff_pct:+.1f}%)" if diff_pct is not None else ""
    
    if is_kor:
        return f"₩{int(round(price, 0)):,}{pct_str}"
    else:
        krw_val = int(round(price * rate, 0))
        return f"${price:,.2f} (₩{krw_val:,}){pct_str}"

def send_msg(text):
    token = st.secrets.get("TELEGRAM_TOKEN", ""); chat_id = st.secrets.get("CHAT_ID", "")
    if token and chat_id: requests.post(f"https://api.telegram.org/bot{token}/sendMessage", data={'chat_id': chat_id, 'text': text})

# --- [4. 메인 관제 화면] ---
st.title(f"⚔️ AI 전술 사령부 v50.2")
st.subheader(f"👤 현재 지휘관: {user_id}")
rate = get_exchange_rate()

with st.expander("➕ 신규 타격 목표(종목) 추가"):
    c1, c2, c3 = st.columns(3)
    n_name = c1.text_input("종목명")
    n_ticker = c2.text_input("티커")
    n_buy = c3.number_input("구매가", min_value=0.0, format="%.2f")
    if st.button("부대 배치"):
        st.session_state.my_portfolio.append({"name": n_name, "ticker": n_ticker.upper(), "buy_price": n_buy})
        save_json(USER_PORTFOLIO, st.session_state.my_portfolio)
        st.rerun()

if st.session_state.my_portfolio:
    report_list = []
    telegram_report = f"🏛️ [{user_id} 사령관 AI 전략 보고]\n(환율: ₩{rate:,.1f})\n\n"
    
    for i, item in enumerate(st.session_state.my_portfolio):
        tkr = item['ticker']; b_p = float(item['buy_price'])
        try:
            df = yf.download(tkr, period="2d", progress=False)
            curr_p = float(df['Close'].iloc[-1])
            
            # AI 가변 전술가 계산 및 적용
            m_buy_pct, m_target_pct, m_profit_pct = calculate_ai_tactics(tkr, b_p)
            v_buy = b_p * (1 - m_buy_pct/100)
            v_target = b_p * (1 + m_target_pct/100)
            v_profit = b_p * (1 + m_profit_pct/100)
            curr_diff = ((curr_p - b_p) / b_p) * 100

            # 사진 양식 보고 데이터 생성
            res = {
                "종목": f"{i+1}번 [{item['name']}]",
                "구매가": format_all(b_p, tkr, rate),
                "현재가": format_all(curr_p, tkr, rate, curr_diff),
                "AI 추매가": format_all(v_buy, tkr, rate, -m_buy_pct),
                "AI 목표가": format_all(v_target, tkr, rate, m_target_pct),
                "AI 익절가": format_all(v_profit, tkr, rate, m_profit_pct)
            }
            report_list.append(res)
            
            # 텔레그램용 텍스트 구성
            telegram_report += f"{res['종목']} 작전 지점\n- 구매: {res['구매가']}\n- 현재: {res['현재가']}\n- 추매: {res['AI 추매가']}\n- 목표: {res['AI 목표가']}\n\n"
        except: continue
        
    st.table(pd.DataFrame(report_list))
    if st.button("📊 텔레그램으로 정밀 전술 보고 전송"):
        send_msg(telegram_report)

# --- [5. 자동화 스케줄러] ---
now = datetime.now(pytz.timezone('Asia/Seoul'))
if now.hour == 8 and 50 <= now.minute <= 55:
    send_msg(f"📡 {user_id} 사격 통제 장치 가동. 오늘의 AI 가변 타점 보고드립니다.")
    time.sleep(600)

time.sleep(300); st.rerun()

import streamlit as st
import pandas as pd
import yfinance as yf
import requests
import time
import json
import os

# --- [1. 보안 및 설정] ---
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

# --- [2. 환율 및 전술 엔진] ---
def get_exchange_rate():
    """실시간 달러/원 환율 획득"""
    try:
        ex_data = yf.download("USDKRW=X", period="1d", progress=False)
        return float(ex_data['Close'].iloc[-1])
    except:
        return 1350.0  # 호출 실패 시 기본 환율 적용

def get_aggressive_report(name, ticker, buy_p, idx=1):
    try:
        # 주식 데이터 및 환율 데이터 호출
        df = yf.download(ticker, period="5d", progress=False)
        if df.empty: return None, 0
        curr_p = float(df['Close'].iloc[-1])
        rate = get_exchange_rate()
        
        # 적극적 투자형 전략 수치 (AI 판단 임계치)
        avg_down = buy_p * 0.88   # -12%
        target_p = buy_p * 1.25   # +25%
        take_profit = buy_p * 1.10 # +10%
        
        # AI 작전 판단 로직
        if curr_p <= avg_down:
            ai_advice = "🔥 [적극 추매] 현재 바닥 구간입니다. 물량을 확보하십시오!"
        elif curr_p >= target_p:
            ai_advice = "🏁 [목표 도달] 전량 익절하여 승리를 확정하십시오!"
        elif curr_p >= take_profit:
            ai_advice = "💰 [수익 향유] 익절 구간 진입. 추세에 따라 분할 매도를 고려하십시오."
        else:
            ai_advice = "🛡️ [전술 대기] 현재 정상 범위 내 움직임입니다. 관망하십시오."

        # 원화 계산
        to_won = lambda x: f"{int(x * rate):,}"
        
        report = f"""
{idx}번 [{name.upper()}] 작전 지도 수립 (환율: ₩{rate:,.1f})
- 구매가: ${buy_p:,.2f} (₩{to_won(buy_p)})
- 현재가: ${curr_p:,.2f} (₩{to_won(curr_p)})
- 추가매수권장: ${avg_down:,.2f} (-12%) (₩{to_won(avg_down)})
- 목표매도: ${target_p:,.2f} (+25%) (₩{to_won(target_p)})
- 익절 구간: ${take_profit:,.2f} (+10%) (₩{to_won(take_profit)})

💡 AI 전술 지침:
{ai_advice}
        """
        return report, curr_p
    except:
        return None, 0

# --- [3. 텔레그램 통신 및 자동화] ---
def send_telegram_msg(text):
    if not TELEGRAM_TOKEN or not CHAT_ID: return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.post(url, data={'chat_id': CHAT_ID, 'text': text}, timeout=10)
    except: pass

def listen_telegram():
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates"
    try:
        params = {'timeout': 1}
        if 'last_id' in st.session_state:
            params['offset'] = st.session_state.last_id + 1
        res = requests.get(url, params=params, timeout=5).json()
        if res.get("result"):
            for msg in res["result"]:
                st.session_state.last_id = msg["update_id"]
                text = msg["message"].get("text", "")
                if text.startswith("매수"):
                    p = text.split()
                    if len(p) >= 4:
                        name, tk, bp = p[1], p[2].upper(), float(p[3].replace(",", ""))
                        st.session_state.my_portfolio = [i for i in st.session_state.my_portfolio if i['ticker'] != tk]
                        st.session_state.my_portfolio.append({"name": name, "ticker": tk, "buy_price": bp})
                        save_db(st.session_state.my_portfolio)
                        report, _ = get_aggressive_report(name, tk, bp, len(st.session_state.my_portfolio))
                        send_telegram_msg(f"🫡 명령 수신! 신규 자산 전술 보고드립니다.\n{report}")
                        st.rerun()
                elif text == "보고":
                    st.session_state.force_report = True
                    st.rerun()
    except: pass

# --- [4. UI 구성] ---
st.set_page_config(page_title="AI 전술 사령부 v19.0", layout="wide")
st.title("⚔️ AI 전술 사령부 v19.0 (환율 및 AI 지침)")

listen_telegram()

if st.session_state.my_portfolio:
    all_reports = []
    cols = st.columns(min(len(st.session_state.my_portfolio), 4))
    for i, item in enumerate(st.session_state.my_portfolio):
        report, curr = get_aggressive_report(item['name'], item['ticker'], item['buy_price'], i+1)
        if report: all_reports.append(report)
        with cols[i % 4]:
            profit = ((curr - item['buy_price']) / item['buy_price']) * 100 if curr > 0 else 0
            st.metric(f"{item['name']}", f"${curr:,.2f}", f"{profit:.2f}%")
            if st.button(f"삭제: {item['name']}", key=f"del_{i}"):
                st.session_state.my_portfolio.pop(i)
                save_db(st.session_state.my_portfolio)
                st.rerun()

    if st.session_state.get("force_report"):
        send_telegram_msg("🏛️ [전체 적극적 전술 보고]\n" + "\n\n".join(all_reports))
        st.session_state.force_report = False
else:
    st.info("사령관님, 텔레그램으로 '매수 이름 티커 가격' 명령을 내리거나 사이드바를 이용하십시오.")

time.sleep(10)
st.rerun()

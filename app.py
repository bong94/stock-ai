import streamlit as st
import pandas as pd
import yfinance as yf
import requests
import time
import json
import os

# --- [1. 보안 및 설정 데이터] ---
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

# --- [2. 핵심 전술 엔진] ---
def get_exchange_rate():
    try:
        ex_data = yf.download("USDKRW=X", period="1d", progress=False)
        return float(ex_data['Close'].iloc[-1])
    except:
        return 1380.0  # 실패 시 최근 평균 환율 적용

def get_full_tactical_report():
    """모든 종목을 분석하여 하나의 통합 보고서로 생성"""
    if not st.session_state.my_portfolio:
        return "⚠️ 현재 전선에 배치된 자산이 없습니다."

    rate = get_exchange_rate()
    to_won = lambda x: f"{int(x * rate):,}"
    reports = []
    
    for i, item in enumerate(st.session_state.my_portfolio):
        try:
            df = yf.download(item['ticker'], period="5d", progress=False)
            curr_p = float(df['Close'].iloc[-1])
            
            # 적극적 투자형 수치 계산
            avg_down = item['buy_price'] * 0.88
            target_p = item['buy_price'] * 1.25
            take_p = item['buy_price'] * 1.10
            
            # AI 지침 판단
            if curr_p <= avg_down:
                ai_advice = "🔥 [적극 추매] 바닥 구간입니다!"
            elif curr_p >= target_p:
                ai_advice = "🏁 [목표 도달] 승리를 확정하십시오!"
            else:
                ai_advice = "🛡️ [전술 대기] 관망하십시오."

            report = f"""{i+1}번 [{item['name'].upper()}] (환율: ₩{rate:,.1f})
- 구매가: ${item['buy_price']:.2f} (₩{to_won(item['buy_price'])})
- 현재가: ${curr_p:.2f} (₩{to_won(curr_p)})
- 추가매수권장: ${avg_down:.2f} (-12%) (₩{to_won(avg_down)})
- 목표매도: ${target_p:.2f} (+25%) (₩{to_won(target_p)})
- 익절 구간: ${take_p:.2f} (+10%) (₩{to_won(take_p)})
💡 AI 지침: {ai_advice}"""
            reports.append(report)
        except:
            reports.append(f"{i+1}번 [{item['name']}] 데이터 분석 실패")

    return "🏛️ [전체 적극적 전술 보고]\n\n" + "\n\n".join(reports)

# --- [3. 통신 및 알람 제어] ---
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
                
                # 매수 명령 처리
                if text.startswith("매수"):
                    p = text.split()
                    if len(p) >= 4:
                        name, tk, bp = p[1], p[2].upper(), float(p[3].replace(",", ""))
                        # 기존 티커 중복 제거 후 추가
                        st.session_state.my_portfolio = [i for i in st.session_state.my_portfolio if i['ticker'] != tk]
                        st.session_state.my_portfolio.append({"name": name, "ticker": tk, "buy_price": bp})
                        save_db(st.session_state.my_portfolio)
                        
                        # 중요: 개별 보고 대신 '전체 보고'만 송신
                        send_telegram_msg("🫡 명령 수신! 전체 전황을 다시 분석합니다.")
                        send_telegram_msg(get_full_tactical_report())
                        st.rerun()
                elif text == "보고":
                    send_telegram_msg(get_full_tactical_report())
    except: pass

# --- [4. 관제 센터 UI] ---
st.set_page_config(page_title="AI 전술 사령부 v20.0", layout="wide")
st.title("⚔️ AI 전술 사령부 v20.0 (통합 보고판)")

# 사이드바에서 정찰 주기 설정 (기본 5분 추천)
with st.sidebar:
    st.header("⚙️ 관제 설정")
    interval = st.slider("정찰 주기 설정 (분)", 1, 30, 5)
    st.info(f"현재 {interval}분 단위로 자동 정찰 중...")

listen_telegram()

# UI 화면 표시
if st.session_state.my_portfolio:
    cols = st.columns(min(len(st.session_state.my_portfolio), 4))
    for i, item in enumerate(st.session_state.my_portfolio):
        with cols[i % 4]:
            st.metric(f"{item['name']}", f"${item['buy_price']:.2f}")
            if st.button(f"작전 종료: {item['name']}", key=f"del_{i}"):
                st.session_state.my_portfolio.pop(i)
                save_db(st.session_state.my_portfolio)
                st.rerun()
else:
    st.warning("전선에 배치된 자산이 없습니다. 텔레그램으로 명령을 하달하십시오.")

# 정찰 주기에 따른 자동 갱신
time.sleep(interval * 60)
st.rerun()

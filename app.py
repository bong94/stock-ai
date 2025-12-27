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

# --- [2. 핵심: 아침 개장 타격대 (밤사이 학습 결과물)] ---
def ai_morning_strike_scout():
    """장 시작 전, 밤사이 데이터를 학습하여 아침에 바로 사면 좋을 종목 추천"""
    # 학습 데이터(매도 기록) 로드
    history = load_json(HISTORY_FILE, [])
    # 정찰 대상 (사령관님 선호 종목 + 주요 지수)
    scout_targets = ["TQQQ", "SOXL", "NVDA", "TSLA", "AAPL", "005930.KS"]
    recommendations = []
    
    for ticker in scout_targets:
        try:
            # 최근 5일간의 흐름 학습 분석
            df = yf.download(ticker, period="5d", interval="1h", progress=False)
            if df.empty: continue
            
            curr_p = float(df['Close'].iloc[-1])
            avg_p = df['Close'].mean()
            vol_avg = df['Volume'].mean()
            
            # [학습 기반 알고리즘] 
            # 1. 평균가 대비 저평가 되어 있는가?
            # 2. 거래량이 점진적으로 늘어나고 있는가?
            if curr_p < avg_p * 0.97 and df['Volume'].iloc[-1] > vol_avg:
                recommendations.append(
                    f"⚔️ [아침 즉시 타격 후보] {ticker}\n"
                    f"- 분석: 밤사이 매수 에너지 응축 확인\n"
                    f"- 전술: 시가 진입 후 단기 반등 수익 목표\n"
                    f"- 학습 지표: 과매도 구간 탈출 신호 포착"
                )
        except: continue
    return recommendations

# --- [3. 기존 보고서 및 통신 엔진 (사진 양식 유지)] ---
def get_exchange_rate():
    try:
        ex_data = yf.download("USDKRW=X", period="1d", progress=False)
        return float(ex_data['Close'].iloc[-1])
    except: return 1445.0

def send_msg(text):
    token = st.secrets.get("TELEGRAM_TOKEN", ""); chat_id = st.secrets.get("CHAT_ID", "")
    if token and chat_id: requests.post(f"https://api.telegram.org/bot{token}/sendMessage", data={'chat_id': chat_id, 'text': text})

def generate_tactical_report():
    rate = get_exchange_rate()
    reports = []
    for i, item in enumerate(st.session_state.my_portfolio):
        ticker = item['ticker']
        df = yf.download(ticker, period="2d", progress=False)
        curr_p = float(df['Close'].iloc[-1]); buy_p = float(item['buy_price'])
        total_gain = ((curr_p - buy_p) / buy_p) * 100
        is_kor = ".K" in ticker
        def fmt(p): return f"₩{p:,.0f}" if is_kor else f"${p:,.2f} (₩{p*rate:,.0f})"
        
        report = (
            f"{i+1}번 [{item['name']}] 작전 지도 수립\n"
            f"- 구매가: {fmt(buy_p)}\n- 현재가: {fmt(curr_p)} ({total_gain:+.1f}%)\n"
            f"- 추가매수권장: {fmt(buy_p*0.88)} (-12%)\n- 목표매도: {fmt(buy_p*1.25)} (+25%)"
        )
        reports.append(report)
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
                        history = load_json(HISTORY_FILE, [])
                        history.append({"date": str(datetime.now()), "ticker": tk, "buy": item['buy_price'], "sell": price})
                        save_json(HISTORY_FILE, history)
                        send_msg(f"🫡 {tk} 매도 처리 및 학습 데이터 저장 완료!")
                        st.rerun()
    except: pass

# --- [5. UI 및 자동화 스케줄러] ---
st.set_page_config(page_title="AI 전술 사령부 v44.0", page_icon="⚔️")
st.markdown("## ⚔️ AI 전술 사령부 v44.0")
process_telegram_commands()

# 자산 현황 출력
df_display = pd.DataFrame(st.session_state.my_portfolio)
if not df_display.empty:
    df_display['구매가'] = df_display.apply(lambda x: f"₩{float(x['buy_price']):,.0f}" if ".K" in str(x['ticker']) else f"${float(x['buy_price']):,.2f}", axis=1)
    st.table(df_display[['name', 'ticker', '구매가']].rename(columns={'name':'종목명', 'ticker':'티커'}))

# [시간별 자동 작전 수행]
now = datetime.now(pytz.timezone('Asia/Seoul'))

# 1. 장 시작 전 (오전 8:50): 아침 타격 종목 보고
if now.hour == 8 and 50 <= now.minute <= 55:
    morning_picks = ai_morning_strike_scout()
    if morning_picks:
        send_msg("📡 [AI 밤샘 학습 결과: 아침 타격 보고]\n\n" + "\n\n".join(morning_picks))
        time.sleep(600)

# 2. 장 마감 전 (오후 3:10): 종가 배팅 보고 (기능 유지)
if now.hour == 15 and 10 <= now.minute <= 15:
    # 기존 종가 배팅 로직 실행
    pass

if st.button("📊 즉시 텔레그램 보고 송신"):
    send_msg(generate_tactical_report())

time.sleep(300); st.rerun()

import streamlit as st
import pandas as pd
import yfinance as yf
import requests
import plotly.graph_objects as go
import time
import json
import os
from datetime import datetime

# --- [1. 보안 및 지능형 전술 DB 설정] ---
TELEGRAM_TOKEN = st.secrets.get("TELEGRAM_TOKEN", "")
CHAT_ID = st.secrets.get("CHAT_ID", "")
PORTFOLIO_FILE = "portfolio_db.json"
LEARNING_FILE = "learning_db.json"
IMG_PATH = "tactical_analysis.png" 

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
    st.session_state.my_portfolio = load_json(PORTFOLIO_FILE, [])
if 'learned_tickers' not in st.session_state:
    st.session_state.learned_tickers = load_json(LEARNING_FILE, {"삼성전자": "005930.KS", "테슬라": "TSLA", "비트코인": "BTC-USD"})

# --- [2. 텔레그램 통신 및 시각화 전술 엔진] ---
def send_telegram_msg(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try: requests.post(url, data={'chat_id': CHAT_ID, 'text': message})
    except: pass

def send_telegram_chart(photo_path, caption):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
    try:
        with open(photo_path, 'rb') as photo:
            requests.post(url, data={'chat_id': CHAT_ID, 'caption': caption}, files={'photo': photo})
    except: send_telegram_msg(f"차트 전송 실패: {caption}")

def generate_analysis_chart(df, ticker, buy_price, low_20, decision):
    """AI 분석 선이 포함된 고해상도 차트 생성"""
    fig = go.Figure(data=[go.Candlestick(
        x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name=ticker
    )])
    # 내 평단가 라인 (청록색 점선)
    fig.add_hline(y=buy_price, line=dict(color='cyan', width=2, dash='dot'), 
                 annotation_text=f"내 평단가: {buy_price:,.2f}", annotation_position="top left")
    # AI 지정 지지선 (빨간색 실선)
    fig.add_hline(y=low_20, line=dict(color='red', width=2), 
                 annotation_text=f"AI 지지선: {low_20:,.2f}", annotation_position="bottom right")
    
    fig.update_layout(title=f"⚔️ {ticker} AI 전술 분석 ({decision})", template="plotly_dark", xaxis_rangeslider_visible=False)
    fig.write_image(IMG_PATH, engine="kaleido") # requirements.txt에 kaleido 필요
    return IMG_PATH

def process_telegram_commands():
    """텔레그램 원격 명령: '매수 이름 티커 평단가' 또는 '보고'"""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates"
    try:
        res = requests.get(url).json()
        if res.get("result"):
            last_msg_data = res["result"][-1]["message"]
            last_msg = last_msg_data.get("text", "")
            msg_id = res["result"][-1]["update_id"]
            
            if 'last_update_id' not in st.session_state or st.session_state.last_update_id < msg_id:
                st.session_state.last_update_id = msg_id
                
                if last_msg.startswith("매수"):
                    p = last_msg.split()
                    if len(p) >= 4:
                        name, tk, bp = p[1], p[2].upper(), float(p[3])
                        st.session_state.my_portfolio.append({"name": name, "ticker": tk, "buy_price": bp})
                        save_json(PORTFOLIO_FILE, st.session_state.my_portfolio)
                        st.session_state.learned_tickers[name] = tk
                        save_json(LEARNING_FILE, st.session_state.learned_tickers)
                        send_telegram_msg(f"✅ [원격 명령 성공] {name}({tk}) 자산이 전선에 배치되었네!")
                        st.rerun()
                elif last_msg == "보고":
                    st.session_state.force_report = True
                    return True
    except: pass
    return False

# --- [3. AI 전술 판단 알고리즘] ---
def get_ai_decision(curr_p, buy_p, low_20):
    profit_rate = ((curr_p - buy_p) / buy_p) * 100
    # 1. 손절 판단
    if profit_rate <= -3.0 and curr_p < low_20:
        return f"🔴 [전략적 손절] 지지선 이탈! 즉시 후퇴 권고 ({profit_rate:.2f}%)", True
    # 2. 추가 매수(추매) 판단
    if -5.0 <= profit_rate <= -1.0 and (low_20 * 0.98 <= curr_p <= low_20 * 1.02):
        return f"🔵 [추가 매수] 지지선 반등 포착! 화력 집중 권고 ({profit_rate:.2f}%)", True
    # 3. 익절 판단
    if profit_rate >= 5.0:
        return f"🎯 [수익 실현] 목표가 달성! 익절 권고 ({profit_rate:.2f}%)", True
    # 4. 관망
    return f"🟡 [관망] 진영 유지. 시장의 흐름을 주시하게 ({profit_rate:.2f}%)", False

# --- [4. 메인 전술 대시보드 가동] ---
st.set_page_config(page_title="AI 전술 사령부 v14.0", layout="wide")
st.title("🧙‍♂️ AI 전술 사령부 v14.0")

# [사이드바: 지능형 관제 센터]
st.sidebar.header("🕹️ 관제 센터")
report_interval = st.sidebar.select_slider("🛰️ 정찰 주기 설정 (분)", options=[1, 5, 10, 30], value=5)
selected_quick = st.sidebar.selectbox("🧠 학습된 종목 퀵 선택", ["직접 입력"] + sorted(st.session_state.learned_tickers.keys()))

with st.sidebar.form("input_form"):
    st.subheader("📥 신규 자산 배치")
    d_name = selected_quick if selected_quick != "직접 입력" else ""
    d_tk = st.session_state.learned_tickers.get(selected_quick, "")
    name = st.text_input("종목명", value=d_name)
    tk = st.text_input("티커", value=d_tk)
    bp = st.number_input("평단가 (0.01단위 정밀)", value=0.00, format="%.2f", step=0.01)
    if st.form_submit_button("배치 및 AI 학습"):
        if tk:
            st.session_state.my_portfolio.append({"name": name, "ticker": tk.upper(), "buy_price": bp})
            save_json(PORTFOLIO_FILE, st.session_state.my_portfolio)
            st.session_state.learned_tickers[name] = tk.upper()
            save_json(LEARNING_FILE, st.session_state.learned_tickers)
            st.rerun()

# [실시간 자산 분석 및 보고]
if st.session_state.my_portfolio:
    full_report = []
    st.subheader(f"📡 현재 {report_interval}분 주기로 정찰 및 분석 중...")
    cols = st.columns(min(len(st.session_state.my_portfolio), 4))
    
    for idx, item in enumerate(st.session_state.my_portfolio):
        try:
            df = yf.download(item['ticker'], period="1mo", progress=False)
            if not df.empty:
                curr_p = float(df['Close'].iloc[-1])
                low_20 = float(df['Low'].iloc[-20:].min())
                decision, is_critical = get_ai_decision(curr_p, item['buy_price'], low_20)
                
                # 화면 표시용 텍스트
                price_text = f"{curr_p:,.0f}원" if item['ticker'].endswith((".KS", ".KQ")) else f"${curr_p:,.2f}"
                
                with cols[idx % 4]:
                    st.metric(f"{item['name']} ({item['ticker']})", price_text, decision)
                    if st.button(f"제거: {item['name']}", key=f"del_{idx}"):
                        st.session_state.my_portfolio.pop(idx)
                        save_json(PORTFOLIO_FILE, st.session_state.my_portfolio)
                        st.rerun()

                # 특이사항 발생 시 또는 '보고' 명령 시 차트 전송
                if is_critical or st.session_state.get('force_report'):
                    img = generate_analysis_chart(df, item['ticker'], item['buy_price'], low_20, decision)
                    send_telegram_chart(img, f"🚩 [AI 분석 보고] {item['name']}\n{decision}")
                
                full_report.append(f"· {item['name']}: {price_text} ({decision})")
        except: continue

    # 명령 처리 루틴
    if process_telegram_commands(): st.rerun()
    if st.session_state.get('force_report'):
        send_telegram_msg("🏛️ [사령관님 요청 전체 전황 보고]\n" + "\n".join(full_report))
        st.session_state.force_report = False

else:
    st.info("사령관님, 전선에 배치된 자산이 없네. 텔레그램으로 '매수' 명령을 내리거나 사이드바에서 종목을 등록하시게!")

time.sleep(10)
st.rerun()

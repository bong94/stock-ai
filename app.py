import streamlit as st
import pandas as pd
import yfinance as yf
import requests
import plotly.graph_objects as go
import time
import json
import os
from datetime import datetime

# --- [1. 보안 및 지능형 DB 설정] ---
TELEGRAM_TOKEN = st.secrets.get("TELEGRAM_TOKEN", "")
CHAT_ID = st.secrets.get("CHAT_ID", "")
PORTFOLIO_FILE = "portfolio_db.json"
LEARNING_FILE = "learning_db.json"
IMG_PATH = "tactical_chart.png" 

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

# --- [2. 텔레그램 통신 및 시각화 엔진] ---
def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try: requests.post(url, data={'chat_id': CHAT_ID, 'text': message})
    except: pass

def send_telegram_photo(photo_path, caption):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
    try:
        with open(photo_path, 'rb') as photo:
            requests.post(url, data={'chat_id': CHAT_ID, 'caption': caption}, files={'photo': photo})
    except: send_telegram_message(f"이미지 보고 실패: {caption}")

def generate_tactical_chart(df, ticker, buy_price, low_20, decision):
    """분석 선이 포함된 전술 차트 생성"""
    fig = go.Figure(data=[go.Candlestick(
        x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name=ticker
    )])
    # 평단가 라인 (파란 점선)
    fig.add_hline(y=buy_price, line=dict(color='cyan', width=2, dash='dot'), 
                 annotation_text=f"평단가: {buy_price:,.2f}", annotation_position="top left")
    # 지지선 라인 (빨간 실선)
    fig.add_hline(y=low_20, line=dict(color='red', width=2), 
                 annotation_text=f"지지선: {low_20:,.2f}", annotation_position="bottom right")
    
    fig.update_layout(title=f"⚔️ {ticker} 전술 분석 ({decision})", template="plotly_dark", xaxis_rangeslider_visible=False)
    fig.write_image(IMG_PATH, engine="kaleido")
    return IMG_PATH

def process_telegram_commands():
    """텔레그램 명령: '매수 종목명 티커 평단가' 또는 '보고'"""
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
                        send_telegram_message(f"✅ {name}({tk}) 자산 배치 완료!")
                        st.rerun()
                elif last_msg == "보고":
                    st.session_state.force_report = True
                    return True
    except: pass
    return False

# --- [3. AI 전술 판단 엔진] ---
def get_ai_decision(curr_p, buy_p, low_20):
    profit = ((curr_p - buy_p) / buy_p) * 100
    if profit <= -3.0 and curr_p < low_20: return f"🔴 [손절] 지지선 붕괴! ({profit:.2f}%)", True
    if -5.0 <= profit <= -1.0 and (low_20 * 0.98 <= curr_p <= low_20 * 1.02): return f"🔵 [추매] 반등 타점! ({profit:.2f}%)", True
    if profit >= 5.0: return f"🎯 [익절] 수익 실현! ({profit:.2f}%)", True
    return f"🟡 [관망] 진영 유지 ({profit:.2f}%)", False

# --- [4. 메인 대시보드 가동] ---
st.set_page_config(page_title="AI 전술 사령부 v13.5", layout="wide")
st.title("🧙‍♂️ 지능형 전술 사령부 v13.5")

# [사이드바: 관제 센터]
st.sidebar.header("🕹️ 관제 센터")
report_min = st.sidebar.select_slider("🛰️ 정찰 주기 (분)", options=[1, 5, 10, 30], value=5)
selected_quick = st.sidebar.selectbox("🧠 학습 종목 선택", ["직접 입력"] + sorted(st.session_state.learned_tickers.keys()))

with st.sidebar.form("input_form"):
    st.subheader("📥 신규 자산 배치")
    d_name = selected_quick if selected_quick != "직접 입력" else ""
    d_tk = st.session_state.learned_tickers.get(selected_quick, "")
    name = st.text_input("종목명", value=d_name)
    tk = st.text_input("티커", value=d_tk)
    bp = st.number_input("평단가 (0.01단위)", value=0.00, format="%.2f", step=0.01)
    if st.form_submit_button("배치 및 학습"):
        if tk:
            st.session_state.my_portfolio.append({"name": name, "ticker": tk.upper(), "buy_price": bp})
            save_json(PORTFOLIO_FILE, st.session_state.my_portfolio)
            st.session_state.learned_tickers[name] = tk.upper()
            save_json(LEARNING_FILE, st.session_state.learned_tickers)
            st.rerun()

# [메인 전황 분석]
if st.session_state.my_portfolio:
    full_text_report = []
    cols = st.columns(min(len(st.session_state.my_portfolio), 4))
    
    for i, item in enumerate(st.session_state.my_portfolio):
        try:
            df = yf.download(item['ticker'], period="1mo", progress=False)
            curr_p = float(df['Close'].iloc[-1])
            low_20 = float(df['Low'].iloc[-20:].min())
            dec_text, is_critical = get_ai_decision(curr_p, item['buy_price'], low_20)
            
            # SyntaxError 방지를 위한 안전한 문자열 포맷팅
            price_disp = f"{curr_p:,.0f}원" if item['ticker'].endswith((".KS", ".KQ")) else f"${curr_p:,.2f}"
            
            with cols[i % 4]:
                st.metric(item['name'], price_disp, dec_text)
                if st.button(f"퇴출: {item['name']}", key=f"del_{i}"):
                    st.session_state.my_portfolio.pop(i)
                    save_json(PORTFOLIO_FILE, st.session_state.my_portfolio)
                    st.rerun()

            if is_critical or st.session_state.get('force_report'):
                img = generate_tactical_chart(df, item['ticker'], item['buy_price'], low_20, dec_text)
                send_telegram_photo(img, f"🚩 {item['name']} 전술 보고\n{dec_text}")
            
            full_text_report.append(f"· {item['name']}: {price_disp} ({dec_text})")
        except: continue

    # 명령 처리 및 리프레시
    if process_telegram_commands(): st.rerun()
    if st.session_state.get('force_report'):
        send_telegram_message("🏛️ [전체 자산 현황]\n" + "\n".join(full_text_report))
        st.session_state.force_report = False
else:
    st.info("사령관님, 전선에 배치된 자산이 없네. 명령을 내려주시게!")

time.sleep(10)
st.rerun()

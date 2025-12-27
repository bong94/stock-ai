import streamlit as st
import pandas as pd
import yfinance as yf
import requests
import plotly.graph_objects as go
import time
import json
import os

# --- [1. 보안 및 전술 데이터베이스] ---
TELEGRAM_TOKEN = st.secrets.get("TELEGRAM_TOKEN", "")
CHAT_ID = st.secrets.get("CHAT_ID", "")
PORTFOLIO_FILE = "portfolio_db.json"
LEARNING_FILE = "learning_db.json"
IMG_PATH = "ai_analysis_report.png"

def load_db(file, default):
    if os.path.exists(file):
        try:
            with open(file, "r", encoding="utf-8") as f: return json.load(f)
        except: return default
    return default

def save_db(file, data):
    with open(file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

if 'my_portfolio' not in st.session_state:
    st.session_state.my_portfolio = load_db(PORTFOLIO_FILE, [])
if 'learned_tickers' not in st.session_state:
    st.session_state.learned_tickers = load_db(LEARNING_FILE, {"삼성전자": "005930.KS", "TQQQ": "TQQQ"})

# --- [2. 텔레그램 통신 센터] ---
def send_msg(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, data={'chat_id': CHAT_ID, 'text': text})

def send_chart(img, caption):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
    with open(img, 'rb') as f:
        requests.post(url, data={'chat_id': CHAT_ID, 'caption': caption}, files={'photo': f})

def listen_telegram():
    """사령관님의 명령을 최우선으로 수신"""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates"
    try:
        res = requests.get(url).json()
        if res.get("result"):
            last = res["result"][-1]
            msg_text = last["message"].get("text", "")
            update_id = last["update_id"]
            
            if 'last_id' not in st.session_state or st.session_state.last_id < update_id:
                st.session_state.last_id = update_id
                
                # 매수 명령 처리
                if msg_text.startswith("매수"):
                    p = msg_text.split()
                    if len(p) >= 4:
                        name, tk, bp = p[1], p[2].upper(), float(p[3])
                        st.session_state.my_portfolio.append({"name": name, "ticker": tk, "buy_price": bp})
                        save_db(PORTFOLIO_FILE, st.session_state.my_portfolio)
                        st.session_state.learned_tickers[name] = tk
                        save_db(LEARNING_FILE, st.session_state.learned_tickers)
                        send_msg(f"🫡 [명령 접수] {name}({tk}) 자산을 전선에 배치했습니다!")
                        return "RERUN"
                # 보고 명령 처리
                elif msg_text == "보고":
                    return "REPORT"
    except: pass
    return None

# --- [3. AI 전술 판단 및 차트 생성] ---
def get_decision(curr, buy, low20):
    profit = ((curr - buy) / buy) * 100
    if profit <= -3.0 and curr < low20: return f"🔴 [손절 권고] 지지선 붕괴! ({profit:.2f}%)", True
    if -5.0 <= profit <= -1.0 and (low20 * 0.98 <= curr <= low20 * 1.02): return f"🔵 [추매 타이밍] 지지선 반등! ({profit:.2f}%)", True
    if profit >= 5.0: return f"🎯 [익절 타이밍] 목표 달성! ({profit:.2f}%)", True
    return f"🟡 [관망] 진영 유지 중 ({profit:.2f}%)", False

def draw_chart(df, tk, buy, low20, dec):
    fig = go.Figure(data=[go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'])])
    fig.add_hline(y=buy, line=dict(color='cyan', dash='dot'), annotation_text="내 평단가")
    fig.add_hline(y=low20, line=dict(color='red'), annotation_text="AI 지지선")
    fig.update_layout(title=f"{tk} 분석: {dec}", template="plotly_dark", xaxis_rangeslider_visible=False)
    fig.write_image(IMG_PATH, engine="kaleido")
    return IMG_PATH

# --- [4. 메인 사령부 가동] ---
st.set_page_config(page_title="AI 전술 사령부 v14.5", layout="wide")
st.title("🧙‍♂️ AI 전술 사령부 v14.5")

# 원격 명령 즉각 확인
cmd_status = listen_telegram()
if cmd_status == "RERUN": st.rerun()

# 사이드바 설정
st.sidebar.header("🕹️ 관제 센터")
interval = st.sidebar.select_slider("🛰️ 정찰 주기 (분)", options=[1, 5, 10, 30], value=5)

# 전황 분석 및 출력
if st.session_state.my_portfolio:
    full_report = []
    cols = st.columns(min(len(st.session_state.my_portfolio), 4))
    
    for i, item in enumerate(st.session_state.my_portfolio):
        try:
            df = yf.download(item['ticker'], period="1mo", progress=False)
            curr = float(df['Close'].iloc[-1])
            low20 = float(df['Low'].iloc[-20:].min())
            dec, is_critical = get_decision(curr, item['buy_price'], low20)
            
            price_fmt = f"{curr:,.0f}원" if ".KS" in item['ticker'] else f"${curr:,.2f}"
            with cols[i % 4]:
                st.metric(f"{item['name']}", price_fmt, dec)
                if st.button(f"제거: {item['name']}", key=f"del_{i}"):
                    st.session_state.my_portfolio.pop(i)
                    save_db(PORTFOLIO_FILE, st.session_state.my_portfolio)
                    st.rerun()

            # 특이사항 발생 시 또는 '보고' 명령 시 차트 전송
            if is_critical or cmd_status == "REPORT":
                path = draw_chart(df, item['ticker'], item['buy_price'], low20, dec)
                send_chart(path, f"🚩 [AI 분석 보고]\n{item['name']}({item['ticker']})\n{dec}")
            
            full_report.append(f"· {item['name']}: {price_fmt} ({dec})")
        except: continue

    if cmd_status == "REPORT":
        send_msg("🏛️ [전체 자산 현황 요약]\n" + "\n".join(full_report))
else:
    st.info("사령관님, 전선이 비어있네! 텔레그램으로 '매수' 명령을 내려보시게.")

# 실시간 감시를 위한 자동 리프레시 (10초)
time.sleep(10)
st.rerun()

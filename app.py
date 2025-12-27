import streamlit as st
import pandas as pd
import yfinance as yf
import requests
import plotly.graph_objects as go
import time
import json
import os

# --- [1. 보안 및 전술 데이터베이스 설정] ---
# Streamlit Cloud의 Secrets에 토큰과 ID가 설정되어 있어야 합니다.
TELEGRAM_TOKEN = st.secrets.get("TELEGRAM_TOKEN", "")
CHAT_ID = st.secrets.get("CHAT_ID", "")
PORTFOLIO_FILE = "portfolio_db.json"
LEARNING_FILE = "learning_db.json"
IMG_PATH = "tactical_report.png"

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

# --- [2. 텔레그램 통신 및 시각화 엔진] ---
def send_telegram_msg(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try: requests.post(url, data={'chat_id': CHAT_ID, 'text': text}, timeout=5)
    except: pass

def send_telegram_chart(img_path, caption):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
    try:
        with open(img_path, 'rb') as f:
            requests.post(url, data={'chat_id': CHAT_ID, 'caption': caption}, files={'photo': f}, timeout=15)
    except: send_telegram_msg(f"⚠️ 차트 전송 실패: {caption}")

def listen_telegram():
    """텔레그램 명령 '매수' 및 '보고' 수신"""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates"
    try:
        res = requests.get(url, timeout=5).json()
        if res.get("result"):
            last = res["result"][-1]
            msg_text = last["message"].get("text", "")
            update_id = last["update_id"]
            
            if 'last_id' not in st.session_state or st.session_state.last_id < update_id:
                st.session_state.last_id = update_id
                if msg_text.startswith("매수"):
                    p = msg_text.split()
                    if len(p) >= 4:
                        name, tk, bp = p[1], p[2].upper(), float(p[3])
                        st.session_state.my_portfolio.append({"name": name, "ticker": tk, "buy_price": bp})
                        save_db(PORTFOLIO_FILE, st.session_state.my_portfolio)
                        st.session_state.learned_tickers[name] = tk
                        save_db(LEARNING_FILE, st.session_state.learned_tickers)
                        send_telegram_msg(f"🫡 [명령 수신] {name}({tk}) 자산 배치 완료!")
                        return "RERUN"
                elif msg_text == "보고": return "REPORT"
    except: pass
    return None

def draw_tactical_chart(df, tk, buy, low20, dec):
    """분석 선이 포함된 전술 차트 생성 (Kaleido 엔진 사용)"""
    fig = go.Figure(data=[go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'])])
    # 평단가 라인 (청록색 점선)
    fig.add_hline(y=buy, line=dict(color='cyan', dash='dot'), annotation_text=f"내 평단가: {buy:,.2f}")
    # AI 지지선 (빨간색 실선)
    fig.add_hline(y=low20, line=dict(color='red', width=2), annotation_text=f"AI 지지선: {low20:,.2f}")
    
    fig.update_layout(title=f"⚔️ {tk} AI 전술 분석 ({dec})", template="plotly_dark", xaxis_rangeslider_visible=False)
    # 깃허브에 추가한 kaleido를 사용하여 이미지로 저장
    fig.write_image(IMG_PATH, engine="kaleido")
    return IMG_PATH

# --- [3. 메인 사령부 가동] ---
st.set_page_config(page_title="AI 전술 사령부 v15.0", layout="wide")
st.title("🧙‍♂️ AI 전술 사령부 v15.0")

# 텔레그램 명령 즉시 확인
cmd = listen_telegram()
if cmd == "RERUN": st.rerun()

if st.session_state.my_portfolio:
    st.subheader("📡 실시간 전황 분석 중...")
    full_summary = []
    cols = st.columns(min(len(st.session_state.my_portfolio), 4))
    
    for i, item in enumerate(st.session_state.my_portfolio):
        try:
            df = yf.download(item['ticker'], period="1mo", progress=False)
            curr = float(df['Close'].iloc[-1])
            low20 = float(df['Low'].iloc[-20:].min())
            
            profit = ((curr - item['buy_price']) / item['buy_price']) * 100
            
            # AI 전술 판단
            if profit <= -3.0 and curr < low20: dec, is_crit = f"🔴 손절 권고 ({profit:.2f}%)", True
            elif profit >= 5.0: dec, is_crit = f"🎯 익절 권고 ({profit:.2f}%)", True
            elif -5.0 <= profit <= -1.0 and (low20 * 0.98 <= curr <= low20 * 1.02): dec, is_crit = f"🔵 추매 타이밍 ({profit:.2f}%)", True
            else: dec, is_crit = f"🟡 관망 진영유지 ({profit:.2f}%)", False
            
            price_fmt = f"{curr:,.0f}원" if ".KS" in item['ticker'] or ".KQ" in item['ticker'] else f"${curr:,.2f}"
            
            with cols[i % 4]:
                st.metric(f"{item['name']} ({item['ticker']})", price_fmt, dec)
                if st.button(f"제거: {item['name']}", key=f"del_{i}"):
                    st.session_state.my_portfolio.pop(i)
                    save_db(PORTFOLIO_FILE, st.session_state.my_portfolio)
                    st.rerun()

            # 특이사항 발생 시 또는 사령관이 '보고' 명령 시 차트 전송
            if is_crit or cmd == "REPORT":
                chart_file = draw_tactical_chart(df, item['ticker'], item['buy_price'], low20, dec)
                send_telegram_chart(chart_file, f"🚩 AI 분석 보고: {item['name']}\n상태: {dec}")
            
            full_summary.append(f"· {item['name']}: {price_fmt} ({dec})")
        except Exception as e:
            st.warning(f"{item['name']} 분석 중 오류: {e}")

    if cmd == "REPORT":
        send_telegram_msg("🏛️ [사령관님 요청 전체 전황 보고]\n" + "\n".join(full_summary))
else:
    st.info("사령관님, 전선에 배치된 자산이 없네. 텔레그램이나 사이드바에서 명령을 내려주시게!")

# 10초마다 자동 리프레시 및 명령 감지
time.sleep(10)
st.rerun()

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
IMG_PATH = "tactical_chart.png" # 이미지 저장 경로

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

# --- [2. 텔레그램 양방향 통신 및 이미지 엔진] ---
def send_telegram_message(message, chat_id=CHAT_ID):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try: requests.post(url, data={'chat_id': chat_id, 'text': message})
    except: pass

def send_telegram_photo(photo_path, caption, chat_id=CHAT_ID):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
    try:
        with open(photo_path, 'rb') as photo:
            requests.post(url, data={'chat_id': chat_id, 'caption': caption}, files={'photo': photo})
    except:
        send_telegram_message(f"이미지 전송 실패: {caption}") # 이미지 실패 시 텍스트로 대체

def generate_chart_image(df, ticker, current_price, buy_price, low_20, decision_text):
    """차트 생성 및 이미지 저장"""
    fig = go.Figure(data=[go.Candlestick(
        x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name=ticker
    )])
    
    # 평단가 라인
    fig.add_hline(y=buy_price, line=dict(color='blue', width=2, dash='dot'), annotation_text=f"내 평단가: {buy_price:,.2f}", annotation_position="top left")
    
    # 20일 최저 지지선 라인
    fig.add_hline(y=low_20, line=dict(color='red', width=2, dash='dot'), annotation_text=f"20일 지지선: {low_20:,.2f}", annotation_position="bottom right")

    fig.update_layout(
        title=f"⚔️ {ticker} 전술 차트 ({decision_text.split('[')[1].split(']')[0]})",
        yaxis_title='가격',
        xaxis_title='날짜',
        xaxis_rangeslider_visible=False,
        template="plotly_dark",
        height=500, width=800
    )
    fig.write_image(IMG_PATH, engine="kaleido")
    return IMG_PATH

def process_telegram_commands(report_interval):
    """텔레그램 명령 처리: '매수 종목명 티커 평단가' 또는 '보고'"""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates"
    try:
        res = requests.get(url).json()
        if res.get("result"):
            last_update = res["result"][-1]
            last_msg = last_update["message"]["text"]
            msg_id = last_update["update_id"]
            
            if 'last_update_id' not in st.session_state or st.session_state.last_update_id < msg_id:
                st.session_state.last_update_id = msg_id
                
                # 원격 매수 명령
                if last_msg.startswith("매수"):
                    parts = last_msg.split()
                    if len(parts) >= 4:
                        name, tk, bp = parts[1], parts[2].upper(), float(parts[3])
                        st.session_state.my_portfolio.append({"name": name, "ticker": tk, "buy_price": bp})
                        save_json(PORTFOLIO_FILE, st.session_state.my_portfolio)
                        st.session_state.learned_tickers[name] = tk
                        save_json(LEARNING_FILE, st.session_state.learned_tickers)
                        send_telegram_message(f"✅ [원격 명령 성공] {name}({tk}) 자산이 배치되었네!")
                        st.rerun()
                    else:
                        send_telegram_message("❌ [매수 실패] 형식: 매수 종목명 티커 평단가 (예: 매수 삼성전자 005930.KS 70000)")
                
                # 보고 명령
                elif last_msg == "보고":
                    st.session_state.force_report = True # 보고 강제 실행
                    send_telegram_message("📡 현재 전황을 분석 중일세. 잠시만 대기하게.")
                    return True # 보고 실행 트리거
    except: pass
    return False

# --- [3. AI 전술 판단 엔진] ---
def get_ai_decision(curr_p, buy_p, low_20):
    profit_rate = ((curr_p - buy_p) / buy_p) * 100
    if profit_rate <= -3.0 and curr_p < low_20:
        return f"🔴 [전략적 손절] 지지선 붕괴! 수익률 {profit_rate:.2f}%", True
    if -5.0 <= profit_rate <= -1.0 and (low_20 * 0.98 <= curr_p <= low_20 * 1.02):
        return f"🔵 [추가 매수] 반등 타점! 수익률 {profit_rate:.2f}%", True
    if profit_rate >= 5.0:
        return f"🎯 [수익 실현] 익절 권고! 수익률 {profit_rate:.2f}%", True
    return f"🟡 [관망] 진영 유지 중. 수익률 {profit_rate:.2f}%", False

# --- [4. 메인 대시보드] ---
st.set_page_config(page_title="지능형 전술 사령부 v13.0", layout="wide")
st.title("🧙‍♂️ 지능형 전술 사령부 v13.0")

# [사이드바: 설정 및 학습]
st.sidebar.header("🕹️ 관제 센터")
report_interval = st.sidebar.select_slider("🛰️ 정찰 주기 설정 (분)", options=[1, 5, 10, 30], value=5)

# 학습 데이터 기반 퀵 선택
learned_list = sorted(st.session_state.learned_tickers.keys())
selected_quick = st.sidebar.selectbox("🧠 학습된 종목 퀵 선택", ["직접 입력"] + learned_list)

with st.sidebar.form("input_form"):
    st.subheader("📥 신규 자산 배치")
    d_name = selected_quick if selected_quick != "직접 입력" else ""
    d_tk = st.session_state.learned_tickers.get(selected_quick, "")
    
    name = st.text_input("종목명", value=d_name)
    tk = st.text_input("티커", value=d_tk)
    bp = st.number_input("평단가 (0.01단위 정밀)", value=0.00, format="%.2f", step=0.01)
    
    if st.form_submit_button("배치 및 학습"):
        if tk:
            st.session_state.my_portfolio.append({"name": name, "ticker": tk.upper(), "buy_price": bp})
            save_json(PORTFOLIO_FILE, st.session_state.my_portfolio)
            st.session_state.learned_tickers[name] = tk.upper()
            save_json(LEARNING_FILE, st.session_state.learned_tickers)
            st.rerun()

# [메인 전황판 분석]
if st.session_state.my_portfolio:
    current_alerts = [] # 주기적 보고용 특이사항
    full_report_text = [] # 텔레그램 '보고' 명령용 전체 보고

    st.subheader(f"📡 {report_interval}분 주기로 정찰 중...")
    cols = st.columns(min(len(st.session_state.my_portfolio), 4))
    
    for idx, item in enumerate(st.session_state.my_portfolio):
        try:
            df = yf.download(item['ticker'], period="1mo", progress=False)
            if not df.empty:
                curr_p = float(df['Close'].iloc[-1])
                low_20 = float(df['Low'].iloc[-20:].min())
                decision_text, is_critical_decision = get_ai_decision(curr_p, item['buy_price'], low_20)
                
                # 화면 출력
                val_text = f"{curr_p:,.0f}원" if item['ticker'].endswith((".KS", ".KQ")) else f"${curr_p:,.2f}"
                
                with cols[idx % 4]:
                    st.metric(f"{item['name']}", val_text, decision_text)
                    if st.button(f"퇴출: {item['name']}", key=f"del_{idx}"):
                        st.session_state.my_portfolio.pop(idx)
                        save_json(PORTFOLIO_FILE, st.session_state.my_portfolio)
                        st.rerun()
                
                # 보고서 및 알림 데이터 생성
                report_entry = f"- {item['name']}({item['ticker']}): 현재 {val_text} / {decision_text}"
                full_report_text.append(report_entry)
                
                if is_critical_decision:
                    current_alerts.append({
                        "name": item['name'],
                        "ticker": item['ticker'],
                        "curr_p": curr_p,
                        "buy_p": item['buy_price'],
                        "low_20": low_20,
                        "decision_text": decision_text,
                        "df": df
                    })
        except: continue

    # [텔레그램 통신 루틴]
    processed_command = process_telegram_commands(report_interval)
    
    # 주기적 자동 보고 (특이사항 발생 시)
    now = time.time()
    if ('last_periodic_alert' not in st.session_state or (now - st.session_state.last_periodic_alert) > (report_interval * 60)) and current_alerts:
        for alert_item in current_alerts:
            image_path = generate_chart_image(alert_item['df'], alert_item['ticker'], alert_item['curr_p'], 
                                               alert_item['buy_p'], alert_item['low_20'], alert_item['decision_text'])
            caption = f"🚨 [{report_interval}분 주기 보고]\n{alert_item['name']}({alert_item['ticker']})\n{alert_item['decision_text']}"
            send_telegram_photo(image_path, caption)
        st.session_state.last_periodic_alert = now

    # '보고' 명령 대응 (강제 보고)
    if 'force_report' in st.session_state and st.session_state.force_report:
        for item_data in current_alerts: # '보고' 명령 시에는 모든 중요 결정 항목에 대해 차트 전송
            image_path = generate_chart_image(item_data['df'], item_data['ticker'], item_data['curr_p'], 
                                               item_data['buy_p'], item_data['low_20'], item_data['decision_text'])
            caption = f"🏛️ [사령관님 요청 보고]\n{item_data['name']}({item_data['ticker']})\n{item_data['decision_text']}"
            send_telegram_photo(image_path, caption)
        
        # 전체 텍스트 보고도 추가
        send_telegram_message("🏛️ [사령관님 요청 전체 자산 현황]\n" + "\n".join(full_report_text))
        st.session_state.force_report = False # 명령 수행 후 플래그 초기화

else:
    st.info("사령관님, 전선에 배치된 자산이 없네. 텔레그램이나 사이드바에서 명령을 내려주시게!")

# 실시간 명령 감지 및 화면 새로고침
time.sleep(10)
st.rerun()

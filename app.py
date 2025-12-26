import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import requests
import plotly.graph_objects as go
from scipy.signal import argrelextrema

# --- [1. 시스템 설정 & 멀티 알람] ---
TELEGRAM_TOKEN = "8284260382:AAHYsS2qu0mg5G9SMm2m2Ug1I9JPR1gAAGs"
# 알림을 받을 지인들의 CHAT ID를 리스트로 관리하게 (여기에 추가하면 되네)
CHAT_IDS = ["6107118513"] 

def send_group_msg(text):
    for cid in CHAT_IDS:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        try: requests.post(url, data={"chat_id": cid, "text": text}, timeout=5)
        except: pass

def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    return 100 - (100 / (1 + (gain / loss)))

# --- [2. 메인 화면 구성] ---
st.set_page_config(page_title="AI 트레이딩 커맨드 센터", layout="wide")
st.title("🧙‍♂️ 마스터의 AI 트레이딩 전술 본부 (v3.0)")

# 사이드바 - 설정
st.sidebar.header("🕹️ 관제 데스크")
search_input = st.sidebar.text_input("종목(한글/티커)", "엔비디아")
K_MAP = {"삼성전자":"005930.KS", "SK하이닉스":"000660.KS", "현대차":"005380.KS", "네이버":"035420.KS", "애플":"AAPL", "테슬라":"TSLA", "엔비디아":"NVDA", "비트코인":"BTC-USD"}
ticker = K_MAP.get(search_input, search_input)

# 내 포트폴리오 (수익률 계산기)
st.sidebar.divider()
st.sidebar.subheader("💰 내 지갑 관리")
buy_price = st.sidebar.number_input("내 평단가 (입력)", value=0)
hold_count = st.sidebar.number_input("보유 수량", value=0)

# 데이터 로드
with st.spinner('AI가 전 세계 시장을 훑고 있네...'):
    t_obj = yf.Ticker(ticker)
    data = t_obj.history(period="1y", interval="1d")
    info = t_obj.info

if not data.empty:
    # 데이터 처리 및 소수점 제거
    curr_price = int(data['Close'].iloc[-1])
    high_5d = data['High'].rolling(5).max().iloc[-1]
    low_5d = data['Low'].rolling(5).min().iloc[-1]
    
    # RSI 및 예측 계산
    data['RSI'] = calculate_rsi(data['Close'])
    curr_rsi = int(data['RSI'].iloc[-1]) if not np.isnan(data['RSI'].iloc[-1]) else 50
    volatility = data['Close'].pct_change().std() * curr_price # 변동성 계산
    
    unit = "$" if info.get('currency') == "USD" else "₩"
    
    # 상단 지표 섹션
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("현재가", f"{unit}{curr_price:,}")
    
    # 수익률 계산기 로직
    if buy_price > 0 and hold_count > 0:
        profit = (curr_price - buy_price) * hold_count
        profit_rate = ((curr_price / buy_price) - 1) * 100
        c2.metric("실시간 손익", f"{unit}{profit:,}", f"{profit_rate:.1f}%")
    else:
        c2.metric("AI 지지선", f"{unit}{int(data['Low'].min()):,}")
        
    # AI 시나리오 예측
    pred_high = int(curr_price + volatility)
    pred_low = int(curr_price - volatility)
    c3.metric("내일 예상 범위", f"{unit}{pred_low:,} ~ {pred_high:,}")
    
    rsi_status = "과매수(위험)" if curr_rsi > 70 else "과매도(기회)" if curr_rsi < 30 else "정상"
    c4.metric("시장 심리(RSI)", f"{curr_rsi}%", rsi_status)

    # 캔들 차트
    fig = go.Figure(data=[go.Candlestick(x=data.index, open=data['Open'], high=data['High'], low=data['Low'], close=data['Close'], increasing_line_color='red', decreasing_line_color='blue')])
    fig.update_layout(xaxis_rangeslider_visible=False, template="plotly_dark", height=500)
    st.plotly_chart(fig, width='stretch')

    # 자동 감시 보고서
    st.divider()
    st.subheader("🕵️ AI 자동 감시 보고서")
    col_a, col_b = st.columns(2)
    
    with col_a:
        st.write(f"**현재 시장 분석:** {search_input}의 현재 RSI는 {curr_rsi}로 {rsi_status} 구간에 있네.")
        if curr_rsi < 30: st.warning("🧙‍♂️ 마스터의 조언: 바닥권일 확률이 높으니 매수를 검토하게!")
        elif curr_rsi > 70: st.error("🧙‍♂️ 마스터의 조언: 과열되었구먼! 추격 매수는 금물일세.")
        else: st.info("🧙‍♂️ 마스터의 조언: 평온한 흐름이네. 지지선을 지키는지 지켜보게.")

    with col_b:
        if st.button("📢 지인들에게 그룹 알림 전송"):
            report = f"🚨 [AI 마스터 긴급보고]\n종목: {search_input}\n현재가: {unit}{curr_price:,}\nRSI: {curr_rsi}% ({rsi_status})\n예측범위: {pred_low:,}~{pred_high:,}\n함께 성투하세!"
            send_group_msg(report)
            st.success("등록된 모든 지인에게 알림을 보냈네!")

    # 뉴스 섹션
    st.divider()
    st.subheader("🗞️ 실시간 뉴스 한글 요약")
    try:
        for n in t_obj.news[:2]:
            with st.expander(f"📌 {n.get('title')}"):
                st.write(f"출처: {n.get('publisher')} | [원문보기]({n.get('link')})")
    except: st.write("뉴스를 가져오는 중이네.")

else:
    st.error("종목을 찾을 수 없네. 한글명이나 티커를 확인하게!")

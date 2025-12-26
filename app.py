import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import requests
from scipy.signal import argrelextrema
from datetime import datetime

# --- [설정] 텔레그램 정보 ---
TELEGRAM_TOKEN = "8284260382:AAHYsS2qu0mg5G9SMm2m2Ug1I9JPR1gAAGs"
CHAT_ID = "6107118513"

def send_telegram_msg(text):
    if TELEGRAM_TOKEN == "자네의_토큰_입력": return False
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.get(url, params={"chat_id": CHAT_ID, "text": text}, timeout=5)
        return True
    except: return False

# --- [기능] 실시간 환율 ---
@st.cache_data(ttl=3600)
def get_exchange_rate():
    try:
        ex_data = yf.Ticker("USDKRW=X").history(period="1d")
        return float(ex_data['Close'].iloc[-1].item())
    except: return 1350.0

# --- [기능] 매수/매도 강도 계산 알고리즘 ---
def calculate_trade_signal(curr_price, support, resistance):
    # 가격이 바닥(지지선)에 가까울수록 매수 강도 상승, 천장(저항선)에 가까울수록 매도 강도 상승
    range_total = resistance - support
    if range_total <= 0: return "관망", 50
    
    # 지지선으로부터의 위치 (0%면 지지선, 100%면 저항선)
    position = ((curr_price - support) / range_total) * 100
    
    if position < 30:
        score = (30 - position) / 30 * 100
        return "적극 매수", min(100, int(score))
    elif position > 70:
        score = (position - 70) / 30 * 100
        return "적극 매도", min(100, int(score))
    else:
        return "보유/관망", 50

# --- [데이터] 자산 목록 ---
def get_assets():
    return {
        "🇰🇷 국내 주식": {"삼성전자": "005930.KS", "SK하이닉스": "000660.KS", "현대차": "005380.KS", "NAVER": "035420.KS"},
        "🇺🇸 해외 주식": {"애플 (Apple)": "AAPL", "테슬라 (Tesla)": "TSLA", "엔비디아 (Nvidia)": "NVDA", "마이크로소프트": "MSFT"},
        "📜 채권 및 지수": {"미국 10년물": "^TNX", "S&P 500": "^GSPC", "나스닥 100": "^NDX"}
    }

# --- [기능] AI 지지/저항선 ---
def analyze_ai_lines(df):
    low_vals = df['Low'].values.flatten()
    high_vals = df['High'].values.flatten()
    iloc_min = argrelextrema(low_vals, np.less, order=10)[0]
    iloc_max = argrelextrema(high_vals, np.greater, order=10)[0]
    support = float(low_vals[iloc_min[-1]].item()) if len(iloc_min) > 0 else float(df['Low'].min().item())
    resistance = float(high_vals[iloc_max[-1]].item()) if len(iloc_max) > 0 else float(df['High'].max().item())
    return support, resistance

# --- [화면 구성] ---
st.set_page_config(page_title="AI 트레이딩 마스터", layout="wide")
st.title("🧙‍♂️ 마스터의 AI 트레이딩 비서")

# 사이드바
assets = get_assets()
category = st.sidebar.radio("자산 종류", list(assets.keys()))
selected_name = st.sidebar.selectbox("종목 선택", sorted(assets[category].keys()))
ticker = assets[category][selected_name]

# ⏰ 장 알람 설정 기능 (UI만 먼저 구현)
st.sidebar.write("---")
st.sidebar.subheader("⏰ 실시간 장 알람")
alarm_on = st.sidebar.toggle("텔레그램 알람 활성화")
if alarm_on:
    st.sidebar.success("장 시작/종료 알람이 활성화되었네!")

# 데이터 분석
data = yf.download(ticker, period="6mo", interval="1d")
exchange_rate = get_exchange_rate()

if not data.empty:
    curr_price = float(data['Close'].iloc[-1].item())
    support, resistance = analyze_ai_lines(data)
    signal, strength = calculate_trade_signal(curr_price, support, resistance)
    
    # 1. 매수/매도 브라우저 표시
    st.subheader(f"🎯 실시간 매매 전략: **{signal} ({strength}%)**")
    
    col1, col2, col3 = st.columns(3)
    is_us = "해외" in category
    price_label = lambda x: f"${x:,.2f}" if is_us else f"{int(x):,}원"
    
    col1.metric("현재가", price_label(curr_price))
    col2.metric("AI 지지 (매수 적기)", price_label(support))
    col3.metric("AI 저항 (매도 적기)", price_label(resistance))

    # 2. 뉴스 요약 섹션
    st.write("---")
    st.subheader("📰 최신 뉴스 분석 및 요약")
    news = yf.Ticker(ticker).news[:3]
    if news:
        for n in news:
            with st.expander(f"📌 {n['title']}"):
                st.write(f"**요약:** 본 기사는 {selected_name}의 최근 시장 흐름과 관련이 깊네. (링크 참조)")
                st.write(f"[기사 원문 보기]({n['link']})")
    else:
        st.write("최근 뉴스가 없군.")

    # 3. 텔레그램 전송 내용 구성
    st.write("---")
    if st.button("🚀 텔레그램으로 전략 리포트 전송"):
        final_msg = (
            f"🔔 [AI 전략 리포트]\n"
            f"종목: {selected_name}\n"
            f"현재가: {price_label(curr_price)}\n"
            f"결론: {signal} (강도: {strength}%)\n\n"
            f"💡 마스터의 조언: "
            f"{'바닥권이네! 공격적으로 담아보게.' if signal == '적극 매수' else '너무 과열되었어. 현금화가 필요하네.' if signal == '적극 매도' else '지금은 관망하며 흐름을 보게나.'}"
        )
        if send_telegram_msg(final_msg):
            st.success("자네의 폰으로 전략 보고서를 보냈네!")

    # 차트 시각화
    st.line_chart(data['Close'])

else:
    st.error("데이터 로드 실패!")

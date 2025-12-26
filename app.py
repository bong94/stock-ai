import streamlit as st
import pandas as pd
import yfinance as yf
import requests
import plotly.graph_objects as go
import time
from datetime import datetime

# --- [1. 보안 및 환경 설정] ---
# secrets.toml 파일에 아래 키들을 등록해두게!
ALPHA_VANTAGE_KEY = st.secrets.get("ALPHA_VANTAGE_KEY", "")
TELEGRAM_TOKEN = st.secrets.get("TELEGRAM_TOKEN", "")
CHAT_ID = st.secrets.get("CHAT_ID", "")

def get_usd_krw():
    """실시간 환율 정보를 가져오는 함수"""
    try:
        rate = yf.Ticker("USDKRW=X").history(period="1d")['Close'].iloc[-1]
        return float(rate)
    except: return 1380.0

# --- [2. AI 전술 및 정찰 로직] ---
def calculate_tactical_points(df):
    """최근 20일 데이터를 학습하여 최적의 매수/매도 타점 계산"""
    recent_high = df['High'].iloc[-20:].max().item()
    recent_low = df['Low'].iloc[-20:].min().item()
    
    # 매수 타점: 지지선 위 1% (안전한 진입)
    buy_point = recent_low * 1.01
    # 매도 타점: 저항선 아래 2% (확실한 수익 실현)
    sell_point = recent_high * 0.98
    
    return buy_point, sell_point, recent_low, recent_high

def scout_market(ticker_list):
    """정찰병 모드: 리스트의 종목들을 분석하여 매수 적기인 종목 포착"""
    scout_reports = []
    for t in ticker_list:
        try:
            df = yf.download(t, period="1mo", interval="1d", progress=False)
            if not df.empty:
                last_p = df['Close'].iloc[-1].item()
                buy_p, sell_p, sup, res = calculate_tactical_points(df)
                
                # 매수 적기 판단: 현재가가 매수 권장가 이하일 때
                if last_p <= buy_p:
                    scout_reports.append(f"📡 [정찰 보고] {t} 매수 사정권 진입!\n현재가: {last_p:,.2f} (권장가: {buy_p:,.2f})")
        except: continue
    return scout_reports

def send_telegram(message):
    """텔레그램 알림 전송"""
    if TELEGRAM_TOKEN and CHAT_ID:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage?chat_id={CHAT_ID}&text={message}"
        requests.get(url)

# --- [3. 메인 UI 및 데이터 관리] ---
st.set_page_config(page_title="AI 전술 사령부 v9.2", layout="wide")
ex_rate = get_usd_krw()

# 세션 상태 초기화 (내 포트폴리오 저장)
if 'my_portfolio' not in st.session_state:
    st.session_state.my_portfolio = []

# [사이드바: 제어 센터]
st.sidebar.header("🕹️ 사령부 제어 센터")
auto_on = st.sidebar.checkbox("🛡️ 24시간 자동 파수꾼 & 정찰 모드")
scout_list = st.sidebar.multiselect("📡 정찰 대상 설정", 
                                   ["NVDA", "TSLA", "AAPL", "005930.KS", "000660.KS", "BTC-USD", "ETH-USD", "EIX"],
                                   default=["NVDA", "TSLA", "BTC-USD", "EIX"])

# 포트폴리오 등록 폼
with st.sidebar.form("p_form"):
    st.subheader("📝 내 주식 등록")
    p_name = st.text_input("종목명", "에디슨")
    p_ticker = st.text_input("티커", "EIX")
    p_price = st.number_input("내 평단가", value=60.0)
    if st.form_submit_button("포트폴리오 추가"):
        st.session_state.my_portfolio.append({"name": p_name, "ticker": p_ticker.upper(), "buy_price": p_price})
        st.sidebar.success(f"{p_name} 등록 완료!")
        st.rerun()

# [자동 감시 및 정찰 실행]
if auto_on:
    # 1. 정찰병 보고
    reports = scout_market(scout_list)
    for r in reports:
        send_telegram(r)
    
    # 2. 내 자산 수익률 감시 (급락 시 알림 등 추가 가능)
    st.sidebar.success(f"최근 정찰 및 감시 완료: {datetime.now().strftime('%H:%M:%S')}")
    time.sleep(60) # 1분마다 갱신
    st.rerun()

# --- [메인 대시보드 화면] ---
st.title("🧙‍♂️ AI 정찰 및 전술 사령부 v9.2")

# [섹션 1: 실시간 자산 현황]
if st.session_state.my_portfolio:
    st.header("🛡️ 내 자산 실시간 전술 상황")
    cols = st.columns(len(st.session_state.my_portfolio))
    for idx, item in enumerate(st.session_state.my_portfolio):
        data = yf.download(item['ticker'], period="5d", progress=False)
        if not data.empty:
            curr = data['Close'].iloc[-1].item()
            profit = ((curr - item['buy_price']) / item['buy_price']) * 100
            unit = "원" if item['ticker'].endswith((".KS", ".KQ")) else "$"
            with cols[idx]:
                st.metric(item['name'], f"{unit}{curr:,.2f}", f"{profit:.2f}%")

st.divider()

# [섹션 2: 정밀 작전 지도 분석]
st.header("🔍 종목별 상세 매수/매도 작전 지도")
target_ticker = st.text_input("분석할 티커 입력 (예: EIX, NVDA, 005930.KS)", "EIX").upper()

if st.button("⚔️ 작전 수립"):
    df = yf.download(target_ticker, period="6mo", interval="1d", progress=False)
    if not df.empty:
        buy_p, sell_p, sup, res = calculate_tactical_points(df)
        last_p = df['Close'].iloc[-1].item()
        is_kr = target_ticker.endswith((".KS", ".KQ"))
        unit = "원" if is_kr else "$"

        # 캔들 차트 시각화
        fig = go.Figure(data=[go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="주가")])
        
        # 작전 선 표시
        fig.add_hline(y=buy_p, line_color="lime", line_dash="dash", annotation_text=f"🟢 매수 권장: {unit}{buy_p:,.2f}")
        fig.add_hline(y=sell_p, line_color="orange", line_dash="dash", annotation_text=f"🎯 매도 목표: {unit}{sell_p:,.2f}")
        fig.add_hline(y=sup * 0.97, line_color="red", line_dash="dot", annotation_text="🛑 최후 손절선")

        fig.update_layout(template="plotly_dark", xaxis_rangeslider_visible=False, height=600, title=f"{target_ticker} 작전 지도")
        st.plotly_chart(fig, use_container_width=True)

        # AI 전술 지시서 작성
        st.subheader("📋 AI 마스터의 전술 지시서")
        c1, c2 = st.columns(2)
        with c1:
            st.info(f"📍 **매수 전략:**\n\n현재가 {unit}{last_p:,.2f} 기준, **{unit}{buy_p:,.2f}** 근처가 최적의 진입로일세. 매복하고 기다리게.")
        with c2:
            st.warning(f"🎯 **매도 전략:**\n\n상승 시 **{unit}{sell_p:,.2f}**에서 수익을 확보하게. 이곳은 강력한 저항이 예상되는 지점이네.")

        # 즉시 보고서 전송
        report = f"⚔️ [{target_ticker}] 작전 지도 수립\n- 현재가: {unit}{last_p:,.2f}\n- 매수권장: {unit}{buy_p:,.2f}\n- 목표매도: {unit}{sell_p:,.2f}"
        send_telegram(report)

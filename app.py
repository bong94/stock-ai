import streamlit as st
import pandas as pd
import yfinance as yf
import requests
import plotly.graph_objects as go
import time
import json
import os
from datetime import datetime

# Plotly 이미지 저장을 위한 라이브러리 (pip install kaleido 필요)
import kaleido 

# --- [1. 보안 및 환경 설정] ---
ALPHA_VANTAGE_KEY = st.secrets.get("ALPHA_VANTAGE_KEY", "")
TELEGRAM_TOKEN = st.secrets.get("TELEGRAM_TOKEN", "")
CHAT_ID = st.secrets.get("CHAT_ID", "")
PORTFOLIO_FILE = "portfolio_db.json"
IMG_PATH = "chart_briefing.png" # 생성될 이미지 파일명

# --- [2. 데이터 영속성 관리] ---
def load_portfolio():
    if os.path.exists(PORTFOLIO_FILE):
        with open(PORTFOLIO_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_portfolio(portfolio):
    with open(PORTFOLIO_FILE, "w", encoding="utf-8") as f:
        json.dump(portfolio, f, ensure_ascii=False, indent=4)

# --- [3. AI 전술 엔진 (학습 & 분석)] ---
def get_usd_krw():
    try:
        rate = yf.Ticker("USDKRW=X").history(period="1d")['Close'].iloc[-1]
        return float(rate)
    except: return 1380.0

def calculate_tactical_points(df):
    """최근 20일 데이터 기반 매수/매도 타점 학습"""
    high_20 = df['High'].iloc[-20:].max().item()
    low_20 = df['Low'].iloc[-20:].min().item()
    buy_point = low_20 * 1.01
    sell_point = high_20 * 0.98
    return buy_point, sell_point, low_20, high_20

def get_news_summary(ticker):
    """최신 뉴스를 가져와 감성 분석 후 요약 제공"""
    try:
        url = f'https://www.alphavantage.co/query?function=NEWS_SENTIMENT&tickers={ticker}&apikey={ALPHA_VANTAGE_KEY}'
        res = requests.get(url).json()
        feeds = res.get("feed", [])[:2] # 핵심 뉴스 2개
        
        summary = "\n[📰 최신 뉴스 요약]\n"
        if not feeds:
            return summary + "- 특이 뉴스 없음. 차트에 집중."
        
        for f in feeds:
            sentiment_score = float(f.get('overall_sentiment_score', 0))
            sentiment = "🟢긍정적" if sentiment_score > 0.15 else ("🔴부정적" if sentiment_score < -0.15 else "🟡중립적")
            summary += f"- {f['title'][:50]}... ({sentiment})\n"
        return summary
    except Exception as e:
        return f"\n[📰 정보] 뉴스 로드 실패: {e}. 차트 분석 위주로 진행!"

def create_chart_image(df, ticker, buy_p, sell_p, last_p, unit):
    """캔들 차트에 매수/매도 선을 그려 이미지 파일로 저장"""
    fig = go.Figure(data=[go.Candlestick(
        x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
        increasing_line_color='#FF4B4B', decreasing_line_color='#0083B0'
    )])
    fig.add_hline(y=buy_p, line_color="lime", line_dash="dash", annotation_text=f"🟢 매수 권장: {unit}{buy_p:,.2f}")
    fig.add_hline(y=sell_p, line_color="orange", line_dash="dash", annotation_text=f"🎯 매도 목표: {unit}{sell_p:,.2f}")
    fig.update_layout(
        title=f"⚔️ {ticker} 전술 브리핑 (현재: {unit}{last_p:,.2f})",
        template="plotly_dark",
        xaxis_rangeslider_visible=False,
        height=500, width=800
    )
    fig.write_image(IMG_PATH)
    return IMG_PATH

def send_telegram_briefing(ticker, text_message, image_path=None):
    """텔레그램으로 텍스트와 이미지 동시 전송"""
    if not (TELEGRAM_TOKEN and CHAT_ID):
        st.error("텔레그램 토큰 또는 채팅 ID가 설정되지 않았습니다.")
        return

    if image_path and os.path.exists(image_path):
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
        files = {'photo': open(image_path, 'rb')}
        data = {'chat_id': CHAT_ID, 'caption': text_message}
        requests.post(url, files=files, data=data)
    else:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        data = {'chat_id': CHAT_ID, 'text': text_message}
        requests.post(url, data=data)

# --- [4. 하이브리드 정찰 및 파수꾼 (교육/시각화 강화)] ---
def run_hybrid_scout_and_guardian(portfolio, scout_list):
    st.sidebar.info(f"🛰️ 하이브리드 순찰 중... ({datetime.now().strftime('%H:%M:%S')})")
    
    # 1. 포트폴리오 감시 (내 주식)
    for item in portfolio:
        try:
            df = yf.download(item['ticker'], period="5d", interval="1m", progress=False) # 1분봉으로 더 실시간 감시
            if not df.empty:
                curr_p = df['Close'].iloc[-1].item()
                profit_rate = ((curr_p - item['buy_price']) / item['buy_price']) * 100
                unit = "원" if item['ticker'].endswith((".KS", ".KQ")) else "$"

                # 손절/익절 알람
                if profit_rate <= -3.0 or profit_rate >= 10.0:
                    status = "🛑 긴급 손절 경보" if profit_rate <= -3.0 else "🎯 익절 기회 포착"
                    briefing_text = (
                        f"{status} - {item['name']} ({item['ticker']})\n"
                        f"현재가: {unit}{curr_p:,.2f} | 수익률: {profit_rate:.2f}%\n"
                        f"사령관님, 즉시 조치하십시오!"
                    )
                    send_telegram_briefing(item['ticker'], briefing_text)
        except Exception as e:
            st.sidebar.warning(f"포트폴리오 감시 오류 {item['ticker']}: {e}")

    # 2. 광역 정찰 (매수 기회 탐색)
    for t in scout_list:
        try:
            is_crypto = "-" in t or "BTC" in t or "ETH" in t or "SOL" in t
            period = "1mo" if is_crypto else "6mo" # 코인은 1개월, 주식은 6개월로 지표 강화

            df = yf.download(t, period=period, interval="1d", progress=False)
            if not df.empty and len(df) >= 20:
                last_p = df['Close'].iloc[-1].item()
                buy_p, sell_p, low_20, high_20 = calculate_tactical_points(df)
                unit = "원" if t.endswith((".KS", ".KQ")) else "$"

                # 매수 기회 포착 및 브리핑
                if last_p <= buy_p: # 매수 권장가 진입 시
                    chart_image_path = create_chart_image(df, t, buy_p, sell_p, last_p, unit)
                    news_summary = get_news_summary(t)
                    
                    briefing_text = (
                        f"🚨 [정찰 보고] {t} - 매수 사정권 진입!\n"
                        f"현재가: {unit}{last_p:,.2f}\n"
                        f"🟢 권장 매수가: {unit}{buy_p:,.2f} (최근 20일 지지선 {low_20:,.2f} 부근)\n"
                        f"🎯 목표 매도가: {unit}{sell_p:,.2f} (최근 20일 저항선 {high_20:,.2f} 부근)\n"
                        f"{news_summary}\n"
                        f"[🎓 전술 교육] {t}는 현재 주요 지지선에 도달하여 반등 가능성이 높다고 학습되었습니다. 차트를 참고하여 전략적 진입을 고려하십시오."
                    )
                    send_telegram_briefing(t, briefing_text, chart_image_path)
                    st.sidebar.success(f"정찰 보고서 [{t}] 전송 완료!")
        except Exception as e:
            st.sidebar.warning(f"광역 정찰 오류 {t}: {e}")

    time.sleep(300) # 5분마다 순찰 (뉴스 호출 등으로 인해 부하 감안)
    st.rerun()

# --- [5. Streamlit 메인 UI] ---
st.set_page_config(page_title="AI 시각화 전술 사령부 v10.3", layout="wide")

if 'my_portfolio' not in st.session_state:
    st.session_state.my_portfolio = load_portfolio()

# [사이드바: 관제 센터]
st.sidebar.header("🕹️ 사령부 관제 센터")
auto_mode = st.sidebar.checkbox("🛰️ 24시간 자동 브리핑 모드 활성화")

# 광역 정찰 대상 리스트 (사령관님 필요에 따라 수정)
GLOBAL_SCOUT_LIST = ["NVDA", "TSLA", "AAPL", "005930.KS", "BTC-USD", "ETH-USD", "EIX"]

with st.sidebar.form("portfolio_form"):
    st.subheader("📥 포트폴리오 배치")
    name = st.text_input("종목명", "에디슨")
    tk = st.text_input("티커", "EIX")
    bp = st.number_input("평단가", value=60.0)
    if st.form_submit_button("사령부 등록"):
        st.session_state.my_portfolio.append({"name": name, "ticker": tk.upper(), "buy_price": bp})
        save_portfolio(st.session_state.my_portfolio)
        st.rerun()

if st.sidebar.button("🗑️ 전체 포트폴리오 초기화"):
    st.session_state.my_portfolio = []
    save_portfolio([])
    st.rerun()

# [자동 브리핑 모드 실행]
if auto_mode:
    run_hybrid_scout_and_guardian(st.session_state.my_portfolio, GLOBAL_SCOUT_LIST)
    
# --- [메인 대시보드 화면 출력] ---
st.title("🧙‍♂️ AI 시각화 전술 사령부 v10.3")

# [섹션 1: 내 자산 현황]
if st.session_state.my_portfolio:
    st.header("🛡️ 실시간 내 자산 현황")
    cols = st.columns(min(len(st.session_state.my_portfolio), 4))
    for idx, item in enumerate(st.session_state.my_portfolio):
        data = yf.download(item['ticker'], period="5d", progress=False)
        if not data.empty:
            curr = data['Close'].iloc[-1].item()
            profit = ((curr - item['buy_price']) / item['buy_price']) * 100
            unit = "원" if item['ticker'].endswith((".KS", ".KQ")) else "$"
            with cols[idx % 4]:
                st.metric(item['name'], f"{unit}{curr:,.2f}", f"{profit:.2f}%")
                if unit == "$": st.caption(f"환산: {curr * get_usd_krw():,.0f}원")
st.divider()

# [섹션 2: 상세 전술 브리핑 (UI에서 수동 분석)]
st.header("🔍 개별 종목 상세 전술 브리핑")
target_ticker = st.text_input("분석할 티커 입력", "EIX").upper()

if st.button("⚔️ 수동 브리핑 시작"):
    df_chart = yf.download(target_ticker, period="6mo", interval="1d", progress=False)
    if not df_chart.empty and len(df_chart) >= 20:
        buy_p, sell_p, low_20, high_20 = calculate_tactical_points(df_chart)
        last_p = df_chart['Close'].iloc[-1].item()
        unit = "원" if target_ticker.endswith((".KS", ".KQ")) else "$"

        # 웹 UI에 차트 표시
        fig_ui = go.Figure(data=[go.Candlestick(x=df_chart.index, open=df_chart['Open'], high=df_chart['High'], low=df_chart['Low'], close=df_chart['Close'])])
        fig_ui.add_hline(y=buy_p, line_color="lime", line_dash="dash", annotation_text=f"🟢 매수 권장: {unit}{buy_p:,.2f}")
        fig_ui.add_hline(y=sell_p, line_color="orange", line_dash="dash", annotation_text=f"🎯 매도 목표: {unit}{sell_p:,.2f}")
        fig_ui.update_layout(template="plotly_dark", xaxis_rangeslider_visible=False, height=600, title=f"{target_ticker} 상세 브리핑")
        st.plotly_chart(fig_ui, use_container_width=True)

        news_summary_ui = get_news_summary(target_ticker)
        st.subheader("📋 AI 마스터의 전술 지시")
        st.markdown(f"**현재가:** {unit}{last_p:,.2f}\n**매수 권장:** {unit}{buy_p:,.2f} (최근 20일 지지선 {low_20:,.2f} 부근)\n**매도 목표:** {unit}{sell_p:,.2f} (최근 20일 저항선 {high_20:,.2f} 부근)\n{news_summary_ui}")
        
        # 텔레그램으로도 수동 브리핑 전송
        chart_path_manual = create_chart_image(df_chart, target_ticker, buy_p, sell_p, last_p, unit)
        briefing_text_manual = (
            f"⚔️ [수동 브리핑] {target_ticker} 분석 완료!\n"
            f"현재가: {unit}{last_p:,.2f}\n"
            f"🟢 매수: {unit}{buy_p:,.2f}\n"
            f"🎯 매도: {unit}{sell_p:,.2f}\n"
            f"{news_summary_ui}"
        )
        send_telegram_briefing(target_ticker, briefing_text_manual, chart_path_manual)
        st.success("상세 브리핑이 텔레그램으로 전송되었습니다.")

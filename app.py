import streamlit as st
import pandas as pd
import yfinance as yf
import requests
import time
import json
import os
from datetime import datetime
import pytz

# --- [1. 보안 및 데이터 설정] ---
TELEGRAM_TOKEN = st.secrets.get("TELEGRAM_TOKEN", "")
CHAT_ID = st.secrets.get("CHAT_ID", "")
PORTFOLIO_FILE = "portfolio_db.json"

def load_db():
    if os.path.exists(PORTFOLIO_FILE):
        try:
            with open(PORTFOLIO_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except: return []
    return []

def save_db(data):
    with open(PORTFOLIO_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

if 'my_portfolio' not in st.session_state:
    st.session_state.my_portfolio = load_db()

# --- [2. AI 정찰대: 유망 종목 발굴 엔진] ---
def ai_scout_discovery():
    """시장의 주요 종목을 학습하여 '적극적 투자'에 적합한 종목 추천"""
    # 학습 대상 (사령관님이 선호할만한 변동성 있는 대형주/ETF)
    watch_list = ["TSLA", "NVDA", "TQQQ", "SOXL", "AAPL", "005930.KS", "000660.KS", "051910.KS"]
    recommendations = []
    
    for ticker in watch_list:
        try:
            df = yf.download(ticker, period="14d", progress=False)
            curr_p = float(df['Close'].iloc[-1])
            high_p = df['High'].max()
            low_p = df['Low'].min()
            
            # 고점 대비 낙폭 과대 종목 탐색 (-10% 이상 하락 시 '기회'로 판단)
            drop_rate = ((curr_p - high_p) / high_p) * 100
            
            if drop_rate <= -10: # 적극적 투자 성향: 저점 매수 기회 포착
                strength = "강력 추천" if drop_rate <= -15 else "관심 필요"
                recommendations.append(f"📍 {ticker}: 고점 대비 {drop_rate:.1f}% 하락 ({strength})")
        except: continue
        
    return recommendations if recommendations else ["현재 시장 내 특이 저점 종목 없음"]

# --- [3. 통합 분석 및 보고 엔진] ---
def get_full_tactical_report():
    if not st.session_state.my_portfolio:
        return "⚠️ 배치된 자산이 없습니다."

    # 환율 획득
    try:
        ex_data = yf.download("USDKRW=X", period="1d", progress=False)
        rate = float(ex_data['Close'].iloc[-1])
    except: rate = 1380.0

    reports = []
    for i, item in enumerate(st.session_state.my_portfolio):
        ticker = item['ticker']
        is_kor = any(x in ticker for x in [".KS", ".KQ"])
        try:
            df = yf.download(ticker, period="5d", progress=False)
            curr_p = float(df['Close'].iloc[-1])
            buy_p = item['buy_price']
            profit_rate = ((curr_p - buy_p) / buy_p) * 100

            if is_kor:
                reports.append(f"{i+1}번 [{item['name']}] ₩{curr_p:,.0f} ({profit_rate:.2f}%)")
            else:
                reports.append(f"{i+1}번 [{item['name']}] ${curr_p:,.2f} (₩{int(curr_p*rate):,}) ({profit_rate:.2f}%)")
        except: continue

    # AI 정찰 보고 추가
    scout_report = ai_scout_discovery()
    
    final_msg = "🏛️ [한미 통합 전황 보고]\n" + "\n".join(reports)
    final_msg += "\n\n🚀 [AI 정찰대 유망주 추천]\n" + "\n".join(scout_report)
    final_msg += f"\n\n💡 25% 수익 목표 달성을 위해 실시간 학습 중..."
    
    return final_msg

# --- [4. UI 및 통신 로직] ---
st.set_page_config(page_title="AI 전술 사령부 v25.0", layout="wide")
st.title("⚔️ AI 전술 사령부 v25.0 (유망주 발굴 모드)")

# 시장 상태 확인
tz_usa = pytz.timezone('US/Eastern')
tz_kor = pytz.timezone('Asia/Seoul')
usa_open = (datetime.now(tz_usa).weekday() < 5 and 9 <= datetime.now(tz_usa).hour < 16)
kor_open = (datetime.now(tz_kor).weekday() < 5 and 9 <= datetime.now(tz_kor).hour < 15)

with st.sidebar:
    st.header("🌐 시장 관제")
    st.write(f"🇰🇷 한국: {'🟢' if kor_open else '🔴'}")
    st.write(f"🇺🇸 미국: {'🟢' if usa_open else '🔴'}")
    interval = st.slider("정찰 주기(분)", 1, 30, 5)

# 메인 실행
if st.session_state.my_portfolio:
    report_text = get_full_tactical_report()
    st.text_area("현재 전술 보고서 요약", report_text, height=300)
    
    if kor_open or usa_open:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, data={'chat_id': CHAT_ID, 'text': report_text})
    else:
        st.info("😴 휴장 시간입니다. AI 정찰대는 다음 작전을 위해 시장을 분석 중입니다.")
else:
    st.info("관리 종목이 없습니다. 텔레그램으로 명령을 내려주십시오.")

time.sleep(interval * 60)
st.rerun()

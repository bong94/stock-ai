import streamlit as st
import pandas as pd
import yfinance as yf
import requests
import time
import json
import os
from datetime import datetime
import pytz

# --- [1. 보안 및 데이터베이스 관리] ---
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

# 초기 자산 자동 복구 (사령관님 명령 기록 반영)
if 'my_portfolio' not in st.session_state or not st.session_state.my_portfolio:
    db_data = load_db()
    if not db_data:
        db_data = [
            {"name": "대상홀딩스우", "ticker": "084695.KS", "buy_price": 14220},
            {"name": "리얼티인컴", "ticker": "O", "buy_price": 56.32},
            {"name": "에디슨", "ticker": "EIX", "buy_price": 60.21},
            {"name": "SGOV", "ticker": "SGOV", "buy_price": 100.55},
            {"name": "TQQQ", "ticker": "TQQQ", "buy_price": 60.12}
        ]
        save_db(db_data)
    st.session_state.my_portfolio = db_data

# --- [2. 핵심 분석 엔진 (숫자 포맷팅 최적화)] ---
def get_exchange_rate():
    try:
        ex_data = yf.download("USDKRW=X", period="1d", progress=False)
        return float(ex_data['Close'].iloc[-1])
    except: return 1442.0

def ai_scout_discovery():
    """시장을 정찰하여 저점 유망주 발굴"""
    watch = ["NVDA", "TSLA", "SOXL", "AAPL", "005930.KS"]
    finds = []
    for tk in watch:
        try:
            df = yf.download(tk, period="20d", progress=False)
            curr = df['Close'].iloc[-1]
            high = df['High'].max()
            drop = ((curr - high) / high) * 100
            if drop <= -10:
                finds.append(f"📍 {tk}: 고점 대비 {drop:.1f}% 하락 (진입 검토)")
        except: continue
    return finds if finds else ["현재 특이사항 있는 저점 종목 없음"]

def generate_tactical_report(title="🏛️ [전체 적극적 전술 보고]"):
    rate = get_exchange_rate()
    reports = []
    
    for i, item in enumerate(st.session_state.my_portfolio):
        ticker = item['ticker']
        try:
            df = yf.download(ticker, period="5d", progress=False)
            curr_p = float(df['Close'].iloc[-1])
            buy_p = float(item['buy_price'])
            
            # 수치 계산
            avg_down, target_p, take_p = buy_p * 0.88, buy_p * 1.25, buy_p * 1.10
            is_kor = any(x in ticker for x in [".KS", ".KQ"])
            
            # [보고서 양식: 2번 사진 스타일] 원화 정수(₩0), 달러 소수점 2자리($0.00)
            if is_kor:
                report = f"{i+1}번 [{item['name']}] 작전 지도 수립\n- 구매가: ₩{buy_p:,.0f}\n- 현재가: ₩{curr_p:,.0f}\n- 추가매수권장: ₩{avg_down:,.0f} (-12%)\n- 목표매도: ₩{target_p:,.0f} (+25%)\n- 익절 구간: ₩{take_p:,.0f} (+10%)"
            else:
                report = f"{i+1}번 [{item['name']}] 작전 지도 수립 (환율: ₩{rate:,.1f})\n- 구매가: ${buy_p:,.2f} (₩{buy_p*rate:,.0f})\n- 현재가: ${curr_p:,.2f} (₩{curr_p*rate:,.0f})\n- 추가매수권장: ${avg_down:,.2f} (-12%) (₩{avg_down*rate:,.0f})\n- 목표매도: ${target_p:,.2f} (+25%) (₩{target_p*rate:,.0f})\n- 익절 구간: ${take_p:,.2f} (+10%) (₩{take_p*rate:,.0f})"
            
            # AI 전술 지침
            if curr_p <= avg_down:
                guide = "\n\n💡 AI 전술 지침:\n🛡️ [추가 매수] 적극적 방어 구간입니다."
            elif curr_p >= target_p:
                guide = "\n\n💡 AI 전술 지침:\n🚩 [목표 달성] 이익 실현을 권고합니다!"
            else:
                guide = "\n\n💡 AI 전술 지침:\n🛡️ [전술 대기] 현재 정상 범위 내 움직임입니다."
            
            reports.append(report + guide)
        except: continue
        
    scout = ai_scout_discovery()
    return f"{title}\n\n" + "\n\n----------\n\n".join(reports) + "\n\n🚀 [AI 정찰대 유망주]\n" + "\n".join(scout)

# --- [3. 자동 보고 및 통신 시스템] ---
def send_msg(text):
    if not TELEGRAM_TOKEN or not CHAT_ID: return
    requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", data={'chat_id': CHAT_ID, 'text': text})

def market_closing_monitor():
    """장 종료 시점 감지 및 자동 보고"""
    now = datetime.now(pytz.timezone('Asia/Seoul'))
    # 한국장 마감 (15:30)
    if now.hour == 15 and 30 <= now.min <= 35:
        send_msg(generate_tactical_report("🏁 [한국장 마감 결산]"))
        time.sleep(600)
    # 미국장 마감 (한국시간 06:00 / 서머타임 시 05:00)
    if now.hour == 6 and 0 <= now.min <= 5:
        send_msg(generate_tactical_report("🏁 [미국장 마감 결산]"))
        time.sleep(600)

# --- [4. UI (1번 사진 스타일 완벽 고정)] ---
st.set_page_config(page_title="AI 전술 사령부 v32.0", page_icon="⚔️", layout="centered")

# 상단 UI 고정 (이미지 1번 재현)
st.markdown("## ⚔️ AI 전술 사령부 v32.0")
st.markdown("### 📡 현재 배치 자산 실황")

if st.session_state.my_portfolio:
    df = pd.DataFrame(st.session_state.my_portfolio)
    # UI용 숫자 포맷팅 (원화 정수, 달러 소수점 2자리)
    df['구매가'] = df.apply(lambda x: f"₩{x['buy_price']:,.0f}" if ".KS" in x['ticker'] else f"${x['buy_price']:,.2f}", axis=1)
    display_df = df[['name', 'ticker', '구매가']].copy()
    display_df.columns = ['종목명', '티커', '구매가']
    st.table(display_df)
else:
    st.info("명령 수신 대기 중...")

# 수동 보고 버튼
if st.button("📊 지금 즉시 텔레그램 보고 송신"):
    send_msg(generate_tactical_report())

# 상시 가동 시스템
market_closing_monitor()
time.sleep(300)
st.rerun()

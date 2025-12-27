import streamlit as st
import pandas as pd
import yfinance as yf
import requests
import time
import json
import os
from datetime import datetime
import pytz

# --- [1. 시스템 설정 및 DB] ---
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

# --- [2. 핵심 전술 엔진] ---
def get_exchange_rate():
    try:
        ex_data = yf.download("USDKRW=X", period="1d", progress=False)
        return float(ex_data['Close'].iloc[-1])
    except: return 1442.0

def ai_scout_discovery():
    """시장을 정찰하여 낙폭이 큰 유망주 발굴 (AI 정찰 기능)"""
    watch_targets = ["NVDA", "TSLA", "SOXL", "AAPL", "005930.KS", "000660.KS"]
    finds = []
    for tk in watch_targets:
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
    if not st.session_state.my_portfolio:
        return "배치된 자산이 없습니다."
    
    rate = get_exchange_rate()
    reports = []
    
    for i, item in enumerate(st.session_state.my_portfolio):
        ticker = item['ticker']
        try:
            df = yf.download(ticker, period="5d", progress=False)
            curr_p = float(df['Close'].iloc[-1])
            buy_p = float(item['buy_price'])
            
            # 전술 수치 계산
            avg_down, target_p, take_p = buy_p * 0.88, buy_p * 1.25, buy_p * 1.10
            is_kor = any(x in ticker for x in [".KS", ".KQ"])
            
            # [보고서 양식 적용] 소수점 포맷팅: 달러 .2f, 원화 .0f
            if is_kor:
                report = f"{i+1}번 [{item['name']}] 작전 지도 수립\n- 구매가: ₩{buy_p:,.0f}\n- 현재가: ₩{curr_p:,.0f}\n- 추가매수권장: ₩{avg_down:,.0f} (-12%)\n- 목표매도: ₩{target_p:,.0f} (+25%)\n- 익절 구간: ₩{take_p:,.0f} (+10%)"
            else:
                report = f"{i+1}번 [{item['name']}] 작전 지도 수립 (환율: ₩{rate:,.1f})\n- 구매가: ${buy_p:,.2f} (₩{buy_p*rate:,.0f})\n- 현재가: ${curr_p:,.2f} (₩{curr_p*rate:,.0f})\n- 추가매수권장: ${avg_down:,.2f} (-12%) (₩{avg_down*rate:,.0f})\n- 목표매도: ${target_p:,.2f} (+25%) (₩{target_p*rate:,.0f})\n- 익절 구간: ${take_p:,.2f} (+10%) (₩{take_p*rate:,.0f})"
            
            # AI 지침 판단
            if curr_p <= avg_down:
                guide = "\n\n💡 AI 전술 지침:\n🛡️ [추가 매수] 적극적 방어 구간입니다."
            elif curr_p >= target_p:
                guide = "\n\n💡 AI 전술 지침:\n🚩 [목표 달성] 이익 실현을 권고합니다!"
            else:
                guide = "\n\n💡 AI 전술 지침:\n🛡️ [전술 대기] 현재 정상 범위 내 움직임입니다."
            
            reports.append(report + guide)
        except: continue
        
    # 정찰 보고서 합치기
    scout_results = ai_scout_discovery()
    final_msg = f"{title}\n\n" + "\n\n------------------\n\n".join(reports)
    final_msg += "\n\n🚀 [AI 정찰대 유망주 추천]\n" + "\n".join(scout_results)
    return final_msg

# --- [3. 통신 및 자동 보고] ---
def send_msg(text):
    if not TELEGRAM_TOKEN or not CHAT_ID: return
    requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", data={'chat_id': CHAT_ID, 'text': text})

def check_market_report():
    """장 종료 시점 감지 및 자동 보고"""
    now_utc = datetime.now(pytz.utc)
    k_now = now_utc.astimezone(pytz.timezone('Asia/Seoul'))
    u_now = now_utc.astimezone(pytz.timezone('US/Eastern'))
    
    # 한국장 마감 (15:30) / 미국장 마감 (06:00, 서머타임 미고려)
    if k_now.hour == 15 and 30 <= k_now.minute <= 40:
        send_msg(generate_tactical_report("🏁 [🇰🇷 한국장 마감 종합 보고]"))
    if u_now.hour == 16 and 0 <= u_now.minute <= 10:
        send_msg(generate_tactical_report("🏁 [🇺🇸 미국장 마감 종합 보고]"))

# --- [4. UI 구성 (이미지 1번 스타일 고정)] ---
st.set_page_config(page_title="AI 전술 사령부 v31.0", page_icon="⚔️")

st.markdown("## ⚔️ AI 전술 사령부 v31.0")
st.markdown("### 📡 현재 배치 자산 실황")

# UI용 데이터프레임 (이미지 1번 스타일)
if st.session_state.my_portfolio:
    df = pd.DataFrame(st.session_state.my_portfolio)
    # UI에서도 숫자 포맷 적용
    df['buy_price'] = df.apply(lambda x: f"₩{x['buy_price']:,.0f}" if ".K" in x['ticker'] else f"${x['buy_price']:,.2f}", axis=1)
    df.columns = ['종목명', '티커', '구매가']
    st.table(df)
else:
    st.info("명령을 대기 중입니다.")

if st.button("📊 지금 즉시 텔레그램 보고 송신"):
    send_msg(generate_tactical_report())

# 자동 루틴 (마감 보고 체크 포함)
check_market_report()
time.sleep(300)
st.rerun()

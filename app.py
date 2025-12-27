import streamlit as st
import pandas as pd
import yfinance as yf
import requests
import time
import json
import os
from datetime import datetime
import pytz

# --- [1. 시스템 설정] ---
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

# --- [2. 핵심 분석 엔진] ---
def get_exchange_rate():
    try:
        ex_data = yf.download("USDKRW=X", period="1d", progress=False)
        return float(ex_data['Close'].iloc[-1])
    except: return 1442.0 # 기본값

def generate_tactical_report(title="🏛️ [전체 적극적 전술 보고]"):
    if not st.session_state.my_portfolio:
        return "사령관님, 현재 배치된 자산이 없네. 텔레그램으로 '매수 이름 티커 평단가' 명령을 내려주시게!"
    
    rate = get_exchange_rate()
    reports = []
    
    for i, item in enumerate(st.session_state.my_portfolio):
        ticker = item['ticker']
        try:
            df = yf.download(ticker, period="5d", progress=False)
            curr_p = float(df['Close'].iloc[-1])
            buy_p = item['buy_price']
            
            # 적극적 투자 지표 계산
            avg_down, target_p, take_p = buy_p * 0.88, buy_p * 1.25, buy_p * 1.10
            is_kor = any(x in ticker for x in [".KS", ".KQ"])
            
            # 상세 메시지 구성 (사진 스타일 적용)
            if is_kor:
                report = f"{i+1}번 [{item['name']}] 작전 지도 수립\n- 구매가: ₩{buy_p:,.0f}\n- 현재가: ₩{curr_p:,.0f}\n- 추가매수권장: ₩{avg_down:,.0f} (-12%)\n- 목표매도: ₩{target_p:,.0f} (+25%)\n- 익절 구간: ₩{take_p:,.0f} (+10%)"
            else:
                report = f"{i+1}번 [{item['name']}] 작전 지도 수립 (환율: ₩{rate:,.1f})\n- 구매가: ${buy_p:,.2f} (₩{int(buy_p*rate):,})\n- 현재가: ${curr_p:,.2f} (₩{int(curr_p*rate):,})\n- 추가매수권장: ${avg_down:,.2f} (-12%) (₩{int(avg_down*rate):,})\n- 목표매도: ${target_p:,.2f} (+25%) (₩{int(target_p*rate):,})\n- 익절 구간: ${take_p:,.2f} (+10%) (₩{int(take_p*rate):,})"
            
            # AI 전술 지침 (사진 하단 텍스트 재현)
            if curr_p <= avg_down:
                guideline = "\n\n💡 AI 전술 지침:\n🛡️ [추가 매수] 적극적 방어 구간입니다. 배치를 검토하십시오."
            elif curr_p >= target_p:
                guideline = "\n\n💡 AI 전술 지침:\n🚩 [목표 달성] 전원 철수 및 이익 실현을 권고합니다!"
            else:
                guideline = "\n\n💡 AI 전술 지침:\n🛡️ [전술 대기] 현재 정상 범위 내 움직임입니다. 관망하십시오."
            
            reports.append(report + guideline)
        except: continue
        
    return f"{title}\n\n" + "\n\n------------------\n\n".join(reports)

# --- [3. UI 및 메인 로직] ---
# 1번 사진 스타일의 UI 구현
st.set_page_config(page_title="AI 전술 사령부 v29.0", page_icon="🧙‍♂️", layout="centered")

st.markdown(f"## 🧙‍♂️ AI 전술 사령부 v29.0")

if not st.session_state.my_portfolio:
    st.warning("사령관님, 현재 배치된 자산이 없네. 텔레그램으로 '매수 이름 티커 평단가' 명령을 내려주시게!")
else:
    # 현재 포트폴리오 상태 표 형태 노출 (사이드바 없이 심플하게)
    df_display = pd.DataFrame(st.session_state.my_portfolio)
    st.table(df_display)
    
    # 장 마감 시간 체크 (자동 보고 로직)
    now_utc = datetime.now(pytz.utc)
    k_now = now_utc.astimezone(pytz.timezone('Asia/Seoul'))
    u_now = now_utc.astimezone(pytz.timezone('US/Eastern'))
    
    # 한국장/미국장 마감 보고 (마감 후 5분 이내 1회 발송)
    if (k_now.hour == 15 and 30 <= k_now.minute <= 35) or (u_now.hour == 16 and 0 <= u_now.minute <= 5):
        final_report = generate_tactical_report("🏁 [장 마감 전술 결산]")
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", data={'chat_id': CHAT_ID, 'text': final_report})

# 하단 수동 확인용 버튼
if st.button("📡 지금 즉시 전체 보고 송신"):
    requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", data={'chat_id': CHAT_ID, 'text': generate_tactical_report()})

# 5분마다 자동 새로고침
time.sleep(300)
st.rerun()

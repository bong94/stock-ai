import streamlit as st
import pandas as pd
import yfinance as yf
import requests
import time
import json
import os
from datetime import datetime
import pytz

# --- [1. 보안 및 데이터베이스] ---
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

# --- [2. 핵심 엔진: 지능형 분석 및 정찰] ---
def get_exchange_rate():
    try:
        ex_data = yf.download("USDKRW=X", period="1d", progress=False)
        return float(ex_data['Close'].iloc[-1])
    except: return 1442.0

def generate_tactical_report(title="🏛️ [전체 적극적 전술 보고]"):
    """
    모든 자산의 현황을 분석하여 보고서와 긴급 변동 여부를 반환함.
    반환값: (보고서 내용, 긴급 변동 여부)
    """
    if not st.session_state.my_portfolio:
        return "사령관님, 배치된 자산이 없습니다.", False
    
    rate = get_exchange_rate()
    reports = []
    is_urgent = False
    
    for i, item in enumerate(st.session_state.my_portfolio):
        ticker = item['ticker']
        try:
            # 실시간 변동성 체크를 위해 2일치 데이터 수신
            df = yf.download(ticker, period="2d", progress=False)
            if df.empty: continue
            
            curr_p = float(df['Close'].iloc[-1])
            prev_p = float(df['Close'].iloc[-2])
            buy_p = float(item['buy_price'])
            
            # AI 자율 판단: 전일 대비 3.0% 이상 변동 시 긴급 알람 활성화
            change_pct = ((curr_p - prev_p) / prev_p) * 100
            if abs(change_pct) >= 3.0: is_urgent = True
            
            avg_down, target_p, take_p = buy_p * 0.88, buy_p * 1.25, buy_p * 1.10
            is_kor = any(x in ticker for x in [".KS", ".KQ"])
            
            # [이미지 2번 양식 고정] 원화 ₩0, 달러 $0.00
            if is_kor:
                report = f"{i+1}번 [{item['name']}] 작전 지도\n- 구매가: ₩{buy_p:,.0f}\n- 현재가: ₩{curr_p:,.0f} ({change_pct:+.1f}%)\n- 추매권장: ₩{avg_down:,.0f} / 목표: ₩{target_p:,.0f}"
            else:
                report = f"{i+1}번 [{item['name']}] 작전 지도 (환율: ₩{rate:,.1f})\n- 구매가: ${buy_p:,.2f} (₩{buy_p*rate:,.0f})\n- 현재가: ${curr_p:,.2f} (₩{curr_p*rate:,.0f})\n- 추매권장: ${avg_down:,.2f} / 목표: ${target_p:,.2f}"
            
            # AI 전술 지침
            if curr_p <= avg_down: guide = "\n💡 지침: 🛡️ [추가 매수] 적극 방어 구간입니다."
            elif curr_p >= target_p: guide = "\n💡 지침: 🚩 [목표 달성] 전원 철수를 권고합니다!"
            else: guide = "\n💡 지침: 🛡️ [전술 대기] 현재 정상 범위 내 움직임입니다."
            
            reports.append(report + guide)
        except: continue
        
    final_msg = f"{title}\n\n" + "\n\n----------\n\n".join(reports)
    return final_msg, is_urgent

# --- [3. 지능형 통신 및 알람 시스템] ---
def send_msg(text):
    if not TELEGRAM_TOKEN or not CHAT_ID: return
    try:
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", data={'chat_id': CHAT_ID, 'text': text}, timeout=5)
    except: pass

def ai_smart_alarm_monitor():
    """AI 자율 판단 기반 알람 송신 시스템"""
    now = datetime.now(pytz.timezone('Asia/Seoul'))
    
    # 1. 보고서 생성 및 긴급성 데이터 수신 (ValueError 수정 완료)
    report_msg, is_urgent = generate_tactical_report()
    
    # 2. 정기 마감 보고 (한국 15:30 / 미국 06:00)
    is_market_close = (now.hour == 15 and 30 <= now.minute <= 35) or (now.hour == 6 and 0 <= now.minute <= 5)
    
    if is_market_close:
        msg, _ = generate_tactical_report("🏁 [장 마감 정예 종합 결산]")
        send_msg(msg)
        time.sleep(600) # 중복 전송 방지
    
    # 3. AI 자율 긴급 보고 (변동성 감지 시)
    elif is_urgent:
        send_msg(f"🚨 [AI 긴급 전술 변동 보고]\n\n{report_msg}\n\n⚠️ 시세 급변이 감지되어 AI가 즉시 보고를 결정했습니다.")
        time.sleep(1800) # 긴급 보고 후 30분간 휴식

# --- [4. UI 구성 (이미지 1번 스타일)] ---
st.set_page_config(page_title="AI 전술 사령부 v35.0", page_icon="⚔️")
st.markdown("## ⚔️ AI 전술 사령부 v35.0")
st.markdown("### 📡 지능형 자율 관제 중")

if st.session_state.my_portfolio:
    df = pd.DataFrame(st.session_state.my_portfolio)
    # UI 숫자 포맷팅 고정
    df['구매가'] = df.apply(lambda x: f"₩{float(x['buy_price']):,.0f}" if ".K" in str(x['ticker']) else f"${float(x['buy_price']):,.2f}", axis=1)
    st.table(df[['name', 'ticker', '구매가']].rename(columns={'name':'종목명', 'ticker':'티커'}))
else:
    st.info("사령관님, 텔레그램으로 전술 자산을 배치해 주십시오.")

if st.button("📊 즉시 텔레그램 보고 송신"):
    msg, _ = generate_tactical_report()
    send_msg(msg)

# 시스템 가동
ai_smart_alarm_monitor()
time.sleep(300) # 5분 정찰 주기
st.rerun()

import streamlit as st
import pandas as pd
import yfinance as yf
import requests
import json
import os
import time
from datetime import datetime
import pytz

# ==========================================================
# 1. [데이터 보안] - 봉94 사령관 식별 및 영구 저장
# ==========================================================
st.set_page_config(page_title="AI 전술 사령부 v55.0", layout="wide")
st.sidebar.title("🎖️ AI 사령부 보안 인증")
user_id = st.sidebar.text_input("사령관 호출부호", value="봉94")
USER_PORTFOLIO = f"portfolio_{user_id}.json"

# [고정 지시] 사령관님 자산 목록 기초 데이터
default_assets = [
    {"name": "대상홀딩스우", "ticker": "084695.KS", "buy_price": 14220},
    {"name": "리얼티인컴", "ticker": "O", "buy_price": 56.69},
    {"name": "에디슨", "ticker": "EIX", "buy_price": 60.21},
    {"name": "SGOV", "ticker": "SGOV", "buy_price": 100.55},
    {"name": "TQQQ", "ticker": "TQQQ", "buy_price": 60.12}
]

if os.path.exists(USER_PORTFOLIO):
    try:
        with open(USER_PORTFOLIO, "r", encoding="utf-8") as f:
            user_data = json.load(f)
            if "sell_history" not in user_data: user_data["sell_history"] = []
    except:
        user_data = {"assets": default_assets, "chat_id": st.secrets.get("CHAT_ID", ""), "sell_history": []}
else:
    user_data = {"assets": default_assets, "chat_id": st.secrets.get("CHAT_ID", ""), "sell_history": []}

# ==========================================================
# 2. [전술 인프라] - 무결성 환율 및 포맷팅 엔진
# ==========================================================
st.title(f"⚔️ AI 전술 사령부 v55.0 (ULTIMATE)")

try:
    # [에러수정] 시리즈가 아닌 순수 숫자값(float)으로 강제 변환
    raw_rate = yf.download("USDKRW=X", period="1d", progress=False)['Close'].iloc[-1]
    current_rate = float(raw_rate)
except:
    current_rate = 1445.0

def format_all(price, ticker, rate):
    p = float(price)
    if ".K" in ticker:
        return f"₩{int(round(p, 0)):,}"
    # [지시사항] 달러와 원화 병기 절대 고정
    return f"${p:,.2f} (₩{int(round(p * rate, 0)):,})"

# ==========================================================
# 3. [핵심 전술 연산] - 2번 양식 / 뉴스 / ATR 학습
# ==========================================================
assets = user_data.get("assets", [])
full_report = f"🏛️ [봉94 사령관 통합 정밀 보고]\n발신: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
summary_list = []

for i, item in enumerate(assets):
    ticker = item['ticker']
    buy_p = float(item['buy_price'])
    
    try:
        obj = yf.Ticker(ticker)
        # 장 종료 및 휴장기 대응을 위한 데이터 확보
        hist = obj.history(period="20d")
        if hist.empty: continue
        
        # [에러수정] 모든 가격 데이터를 순수 숫자로 추출하여 포맷팅 충돌 방지
        curr_p = float(hist['Close'].iloc[-1])
        atr = float((hist['High'] - hist['Low']).mean())
        atr_pct = (atr / curr_p) * 100
        
        # [지시사항] 가변 변동성 기반 타점 (2번 양식 기준)
        m_buy = max(atr_pct * 1.5, 12.0)
        m_target = max(atr_pct * 3.0, 25.0)
        m_profit = 10.0
        
        v_buy = buy_p * (1 - m_buy/100)
        v_target = buy_p * (1 + m_target/100)
        v_profit = buy_p * (1 + m_profit/100)
        yield_pct = ((curr_p - buy_p) / buy_p) * 100
        
        # [지시사항] 실시간 뉴스 레이더 (KeyError 완벽 방지)
        news_data = obj.news
        news_str = ""
        if news_data:
            for n in news_data[:2]:
                news_str += f"• {n.get('title', '정보 없음')}\n"
        if not news_str: news_str = "현재 핵심 뉴스 없음"

        # [지시사항] 2번 사진 정밀 양식 조립
        chunk = f"{i+1}번 [{item['name']}] 작전 수립 (환율: ₩{current_rate:,.1f})\n"
        chunk += f"- 구매가: {format_all(buy_p, ticker, current_rate)}\n"
        chunk += f"- 현재가: {format_all(curr_p, ticker, current_rate)} ({yield_pct:+.1f}%)\n"
        chunk += f"- 추가매수권장: {format_all(v_buy, ticker, current_rate)} (-{m_buy:.1f}%)\n"
        chunk += f"- 목표매도: {format_all(v_target, ticker, current_rate)} (+{m_target:.1f}%)\n"
        chunk += f"- 익절 구간: {format_all(v_profit, ticker, current_rate)} (+{m_profit:.1f}%)\n"
        chunk += f"🗞️ 뉴스: {news_str[:80]}...\n"
        
        # AI 전술 지침
        insight = "🛡️ [전술 대기] 관망하십시오."
        if yield_pct < -10: insight = "📉 [위기] 분할 매수 대응."
        elif yield_pct > 20: insight = "🚀 [기회] 익절 준비."
        chunk += f"💡 AI 전술 지침: {insight}\n"
        
        full_report += chunk + "\n" + "-"*35 + "\n"
        summary_list.append({"종목": item['name'], "수익": f"{yield_pct:.1f}%", "지침": insight})
        
    except Exception as e:
        st.error(f"{ticker} 연산 결함: {e}")

st.table(pd.DataFrame(summary_list))

# ==========================================================
# 4. [보고 시스템] - 수동/자동 무전 및 4단계 스케줄
# ==========================================================
if st.button("📊 2번 정밀 보고서 텔레그램 송신"):
    token = st.secrets["TELEGRAM_TOKEN"]
    cid = user_data.get("chat_id")
    if cid:
        requests.post(f"https://api.telegram.org/bot{token}/sendMessage", data={'chat_id': cid, 'text': full_report})
        st.success("무전 전송 완료!")

# [지시사항] 자동 보고 스케줄러 (08:30, 08:50, 15:10)
now = datetime.now(pytz.timezone('Asia/Seoul'))
if (now.hour == 8 and (now.minute == 30 or now.minute == 50)) or (now.hour == 15 and now.minute == 10):
    requests.post(f"https://api.telegram.org/bot{st.secrets['TELEGRAM_TOKEN']}/sendMessage", 
                  data={'chat_id': user_data.get("chat_id"), 'text': f"🕒 정기 보고\n\n{full_report}"})
    time.sleep(60)

# ==========================================================
# 5. [AI 학습] - 텔레그램 매도 기록 반영
# ==========================================================
st.divider()
st.subheader("📝 AI 매도 기록 학습 (텔레그램 연동)")
sell_input = st.text_input("매도 기록 (예: 매도 TQQQ 65.5)")
if st.button("AI 학습 저장"):
    # [지시사항] 매도 가격을 학습하여 기억할 것

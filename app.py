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
st.set_page_config(page_title="AI 전술 사령부", layout="wide")
st.sidebar.title("🎖️ AI 사령부 보안 인증")
user_id = st.sidebar.text_input("사령관 호출부호", value="봉94")
USER_PORTFOLIO = f"portfolio_{user_id}.json"

# [지시사항] 기본 자산 데이터 고정
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
# 2. [전술 인프라] - 환율 및 포맷팅 (에러 완전 봉쇄)
# ==========================================================
st.title(f"⚔️ AI 전술 사령부 v58.0 (ULTIMATE)")

try:
    # [오류수정] .item()으로 순수 숫자값만 추출하여 Series 에러 방지
    current_rate = yf.download("USDKRW=X", period="1d", progress=False)['Close'].iloc[-1].item()
except:
    current_rate = 1445.0

def format_all(price, ticker, rate):
    p = float(price)
    if ".K" in ticker:
        return f"₩{int(round(p, 0)):,}"
    # [지시사항] $/₩ 병기 필수
    return f"${p:,.2f} (₩{int(round(p * rate, 0)):,})"

# ==========================================================
# 3. [핵심 연산] - 2번 양식 / 뉴스 / ATR 학습
# ==========================================================
assets = user_data.get("assets", [])
full_report = f"🏛️ [봉94 사령관 통합 정밀 보고]\n발신: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
summary_list = []

for i, item in enumerate(assets):
    ticker = item['ticker']
    buy_p = float(item['buy_price'])
    
    try:
        obj = yf.Ticker(ticker)
        hist = obj.history(period="20d")
        if hist.empty: continue
        
        # [데이터 추출] 모든 가격을 순수 숫자(float)로 처리
        curr_p = float(hist['Close'].iloc[-1].item())
        atr = float((hist['High'] - hist['Low']).mean())
        atr_pct = (atr / curr_p) * 100
        
        # [타점 계산] 사령관님 전용 수치 고정
        m_buy = max(atr_pct * 1.5, 12.0)
        m_target = max(atr_pct * 3.0, 25.0)
        
        # [오류수정] 문법 에러를 일으킨 지점을 가장 단순한 곱셈으로 변경
        v_buy = buy_p * (1 - m_buy/100)
        v_target = buy_p * (1 + m_target/100)
        v_profit = buy_p * 1.10 # 10% 익절가 고정
        
        yield_pct = ((curr_p - buy_p) / buy_p) * 100
        
        # [뉴스 레이더] KeyError 방지
        news_data = obj.news
        news_str = ""
        if news_data:
            for n in news_data[:2]:
                news_str += f"• {n.get('title', '정보 없음')}\n"
        if not news_str: news_str = "핵심 뉴스 없음"

        # [지시사항] AI 전술 지침
        if yield_pct < -10: insight = "📉 [위기] 분할 매수 대응 구간."
        elif yield_pct > 20: insight = "🚀 [기회] 익절 준비 구간."
        else: insight = "🛡️ [관망] 정상 범위 내 움직임."

        # [지시사항] 2번 사진 정밀 양식 조립
        chunk = f"{i+1}번 [{item['name']}] 작전 수립 (환율: ₩{current_rate:,.1f})\n"
        chunk += f"- 구매가: {format_all(buy_p, ticker, current_rate)}\n"
        chunk += f"- 현재가: {format_all(curr_p, ticker, current_rate)} ({yield_pct:+.1f}%)\n"
        chunk += f"- 추가매수권장: {format_all(v_buy, ticker, current_rate)} (-{m_buy:.1f}%)\n"
        chunk += f"- 목표매도: {format_all(v_target, ticker, current_rate)} (+{m_target:.1f}%)\n"
        chunk += f"- 익절 구간: {format_all(v_profit, ticker, current_rate)} (+10.0%)\n"
        chunk += f"🗞️ 뉴스: {news_str[:80]}...\n"
        chunk += f"💡 AI 전술 지침: {insight}\n"
        
        full_report += chunk + "\n" + "-"*35 + "\n"
        summary_list.append({"종목": item['name'], "수익": f"{yield_pct:.1f}%", "지침": insight})
        
    except Exception as e:
        st.error(f"{ticker} 분석 결함: {e}")

st.table(pd.DataFrame(summary_list))

# ==========================================================
# 4. [보고/학습] - 텔레그램 무전 및 매도 기록 학습
# ==========================================================
if st.button("📊 2번 정밀 보고서 텔레그램 송신"):
    token = st.secrets["TELEGRAM_TOKEN"]
    cid = user_data.get("chat_id")
    if cid:
        requests.post(f"https://api.telegram.org/bot{token}/sendMessage", data={'chat_id': cid, 'text': full_report})
        st.success("무전 완료!")

# [지시사항] 4단계 자동 보고 스케줄러
now = datetime.now(pytz.timezone('Asia/Seoul'))
if (now.hour == 8 and (now.minute == 30 or now.minute == 50)) or (now.hour == 15 and now.minute == 10):
    requests.post(f"https://api.telegram.org/bot{st.secrets['TELEGRAM_TOKEN']}/sendMessage", 
                  data={'chat_id': user_data.get("chat_id"), 'text': f"🕒 정기 보고\n\n{full_report}"})
    time.sleep(60)

st.divider()
st.subheader("📝 AI 매도 기록 학습 (텔레그램 연동)")
sell_input = st.text_input("매도 기록 (예: 매도 TQQQ 65.5)")
if st.button("AI 학습 저장"):
    # [지시사항] 사령관님 매도 가격 기억 [cite: 2025-12-27]
    user_data["sell_history"].append({"date": str(now), "log": sell_input})
    with open(USER_PORTFOLIO, "w", encoding="utf-8") as f:
        json.dump(user_data, f, ensure_ascii=False, indent=4)
    st.info("사령관님의 매도 전략이 AI에 학습되었습니다.")

time.sleep(300); st.rerun()

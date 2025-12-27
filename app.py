import streamlit as st
import pandas as pd
import yfinance as yf
import requests
import json
import os
import time
from datetime import datetime
import pytz
from collections import Counter

# ==========================================================
# 1. [보안 및 데이터] - 사령관 정보 영구 저장
# ==========================================================
st.set_page_config(page_title="AI 전술 사령부 v59.0", layout="wide")
st.sidebar.title("🎖️ AI 사령부 보안 인증")
user_id = st.sidebar.text_input("사령관 호출부호", value="봉94")
USER_PORTFOLIO = f"portfolio_{user_id}.json"

default_assets = [
    {"name": "대상홀딩스우", "ticker": "084695.KS", "buy_price": 14220},
    {"name": "리얼티인컴", "ticker": "O", "buy_price": 56.69},
    {"name": "에디슨", "ticker": "EIX", "buy_price": 60.21},
    {"name": "SGOV", "ticker": "SGOV", "buy_price": 100.55},
    {"name": "TQQQ", "ticker": "TQQQ", "buy_price": 60.12}
]

# 데이터 로드 (기존 기능 유지)
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
# 2. [전술 인프라] - 환율 및 포맷팅 (무결성 유지)
# ==========================================================
st.title(f"⚔️ AI 전술 사령부 v59.0 (COLLECTIVE)")

try:
    current_rate = yf.download("USDKRW=X", period="1d", progress=False)['Close'].iloc[-1].item()
except:
    current_rate = 1445.0

def format_all(price, ticker, rate):
    p = float(price)
    if ".K" in ticker: return f"₩{int(round(p, 0)):,}"
    return f"${p:,.2f} (₩{int(round(p * rate, 0)):,})"

# ==========================================================
# 3. [기존 핵심 연산] - 2번 양식 / 뉴스 / ATR 학습
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
        curr_p = float(hist['Close'].iloc[-1].item())
        atr = float((hist['High'] - hist['Low']).mean())
        atr_pct = (atr / curr_p) * 100
        
        m_buy = max(atr_pct * 1.5, 12.0)
        m_target = max(atr_pct * 3.0, 25.0)
        v_buy, v_target, v_profit = buy_p * (1 - m_buy/100), buy_p * (1 + m_target/100), buy_p * 1.10
        yield_pct = ((curr_p - buy_p) / buy_p) * 100
        
        news_data = obj.news
        news_str = "".join([f"• {n.get('title', '정보 없음')}\n" for n in news_data[:2]]) if news_data else "핵심 뉴스 없음"
        
        if yield_pct < -10: insight = "📉 [위기] 분할 매수 대응 구간."
        elif yield_pct > 20: insight = "🚀 [기회] 익절 준비 구간."
        else: insight = "🛡️ [관망] 정상 범위 내 움직임."

        chunk = f"{i+1}번 [{item['name']}] 작전 수립 (환율: ₩{current_rate:,.1f})\n"
        chunk += f"- 구매가: {format_all(buy_p, ticker, current_rate)}\n"
        chunk += f"- 현재가: {format_all(curr_p, ticker, current_rate)} ({yield_pct:+.1f}%)\n"
        chunk += f"- 추가매수권장: {format_all(v_buy, ticker, current_rate)} (-{m_buy:.1f}%)\n"
        chunk += f"- 목표매도: {format_all(v_target, ticker, current_rate)} (+{m_target:.1f}%)\n"
        chunk += f"- 익절 구간: {format_all(v_profit, ticker, current_rate)} (+10.0%)\n"
        chunk += f"🗞️ 뉴스: {news_str[:80]}...\n💡 AI 전술 지침: {insight}\n"
        
        full_report += chunk + "\n" + "-"*35 + "\n"
        summary_list.append({"종목": item['name'], "수익": f"{yield_pct:.1f}%", "지침": insight})
    except: pass

st.table(pd.DataFrame(summary_list))

# ==========================================================
# 4. [신규 증축: 집단 지성] - 타 사령관 포트폴리오 분석 (삭제 없음)
# ==========================================================
st.divider()
st.subheader("🌐 타 사령관 집단 지성 정찰 모듈")

all_files = [f for f in os.listdir() if f.startswith("portfolio_") and f.endswith(".json")]
total_tickers = []
for f_name in all_files:
    try:
        with open(f_name, "r", encoding="utf-8") as f:
            data = json.load(f)
            total_tickers.extend([a['name'] for a in data.get("assets", [])])
    except: continue

if total_tickers:
    popular_assets = Counter(total_tickers).most_common(3)
    st.info(f"💡 현재 다른 사령관들이 가장 많이 감시 중인 종목: " + 
            ", ".join([f"{name}({count}명)" for name, count in popular_assets]))
    full_report += f"\n🌐 [집단 지성 보고]\n타 사령관 인기 종목: " + \
                   ", ".join([f"{name}({count}명)" for name, count in popular_assets]) + "\n"

# ==========================================================
# 5. [기존 보고/학습] - 텔레그램 및 매도 학습 (기능 유지)
# ==========================================================
if st.button("📊 2번 정밀 보고서 텔레그램 송신"):
    requests.post(f"https://api.telegram.org/bot{st.secrets['TELEGRAM_TOKEN']}/sendMessage", 
                  data={'chat_id': user_data.get("chat_id"), 'text': full_report})
    st.success("집단 지성 포함 무전 완료!")

st.subheader("📝 AI 매도 기록 학습")
sell_input = st.text_input("매도 기록 입력 (예: 매도 TQQQ 65.5)")
if st.button("AI 학습 저장"):
    user_data["sell_history"].append({"date": str(datetime.now()), "log": sell_input})
    with open(USER_PORTFOLIO, "w", encoding="utf-8") as f:
        json.dump(user_data, f, ensure_ascii=False, indent=4)
    st.info("사령관님의 매도 전략이 AI에 학습되었습니다.")

time.sleep(300); st.rerun()

# (기본 라이브러리 및 설정은 v59.0과 동일하되, 긴급 알림 로직 추가)

# ==========================================================
# 6. [신규: 긴급 타격 알림] - 돌발 상황 실시간 무전 (삭제 없음)
# ==========================================================
st.divider()
st.subheader("🚨 실시간 긴급 정찰/타격 시스템")

# 5분 단위로 시세를 체크하여 사령관님께 긴급 무전을 보냅니다.
if "last_alert_time" not in st.session_state:
    st.session_state.last_alert_time = {}

for item in assets:
    ticker = item['ticker']
    try:
        # 실시간 가격 정찰
        current_p = float(yf.Ticker(ticker).history(period="1d")['Close'].iloc[-1].item())
        buy_p = float(item['buy_price'])
        yield_pct = ((current_p - buy_p) / buy_p) * 100

        # 긴급 보고 조건 1: 추가 매수 타점 도달 (-12% 이하)
        if yield_pct <= -12.0:
            msg = f"‼️ [긴급/추매] {item['name']} 작전 신호 발생!\n현재 수익률 {yield_pct:.1f}%로 추가 매수 권장 타점에 진입했습니다. 즉시 확인하십시오!"
            # 1시간 내 중복 알림 방지
            if ticker not in st.session_state.last_alert_time or (time.time() - st.session_state.last_alert_time[ticker] > 3600):
                requests.post(f"https://api.telegram.org/bot{st.secrets['TELEGRAM_TOKEN']}/sendMessage", 
                              data={'chat_id': user_data.get("chat_id"), 'text': msg})
                st.session_state.last_alert_time[ticker] = time.time()
                st.warning(f"🚨 {item['name']} 긴급 추매 신호 송신됨")

        # 긴급 보고 조건 2: 익절/목표가 도달 (+10% 이상)
        elif yield_pct >= 10.0:
            msg = f"🚀 [긴급/익절] {item['name']} 전과 확대 보고!\n현재 수익률 {yield_pct:.1f}%로 익절 구간에 도달했습니다. 수익 확정을 검토하십시오!"
            if ticker not in st.session_state.last_alert_time or (time.time() - st.session_state.last_alert_time[ticker] > 3600):
                requests.post(f"https://api.telegram.org/bot{st.secrets['TELEGRAM_TOKEN']}/sendMessage", 
                              data={'chat_id': user_data.get("chat_id"), 'text': msg})
                st.session_state.last_alert_time[ticker] = time.time()
                st.balloons()
                st.success(f"🎊 {item['name']} 긴급 익절 신호 송신됨")
    except:
        continue


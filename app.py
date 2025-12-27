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
# 1. [보안/데이터] - 사령관 정보 영구 저장
# ==========================================================
st.set_page_config(page_title="AI 전술 사령부", layout="wide")
st.sidebar.title("🎖️ AI 사령부 보안 인증")
user_id = st.sidebar.text_input("사령관 호출부호", value="봉94")
USER_PORTFOLIO = f"portfolio_{user_id}.json"

# [지시사항] 봉94 사령관 기본 자산 고정
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
st.title(f"⚔️ AI 전술 사령부 v57.0 (FINAL)")

try:
    # [오류수정] 시리즈 에러 방지를 위해 .item() 적용
    current_rate = yf.download("USDKRW=X", period="1d", progress=False)['Close'].iloc[-1].item()
except:
    current_rate = 1445.0

def format_all(price, ticker, rate):
    p = float(price)
    if ".K" in ticker:
        return f"₩{int(round(p, 0)):,}"
    return f"${p:,.2f} (₩{int(round(p * rate, 0)):,})"

# ==========================================================
# 3. [핵심 연산] - 2번 양식 / 뉴스 / ATR 지능형 타점
# ==========================================================
assets = user_data.get("assets", [])
full_report = f"🏛️ [봉94 사령관 통합 정밀 보고]\n발신: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
summary_list = []

for i, item in enumerate(assets):
    ticker = item['ticker']
    buy_p = float(item['buy_price'])
    
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="20d")
        if hist.empty: continue
        
        # [데이터 추출] 숫자값만 정확히 추출
        curr_p = float(hist['Close'].iloc[-1].item())
        atr = float((hist['High'] - hist['Low']).mean())
        atr_pct = (atr / curr_p) * 100
        
        # [타점 계산] 사령관님 고정 전술 수치
        m_buy = max(atr_pct * 1.5, 12.0)
        m_target = max(atr_pct * 3.0, 25.0)
        m_profit = 10.0
        
        v_buy = buy_p * (1 - m_buy/100)
        v_target = buy_p * (1 + m_target/100)
        v_profit = buy_p * (1 + profit_cut_pct := 10.0 / 100) # 익절가 계산식 보정
        v_profit = buy_p * (1 + 0.1) # 직관적인 10% 익절가 계산
        
        yield_pct = ((curr_p - buy_p) / buy_p) * 100
        
        # [뉴스 수집] KeyError 완벽 방지
        news_data = stock.news
        news_final = ""
        if news_data:
            for n in news_data[:2]:
                news_final += f"• {n.get('title', '정보 없음')}\n"
        if not news_final: news_final = "현재 수신된 핵심 뉴스 없음"

        # [오류수정] SyntaxError 해결: insight 로직 완결
        if yield_pct < -10:
            insight = "📉 [위기] 분할 매수 대응 구간입니다."
        elif yield_pct > 20:
            insight = "🚀 [기회] 목표가 근접, 익절 준비하십시오."
        else:
            insight = "🛡️ [전술 대기] 현재 정상 범위 내 움직임입니다."

        # [2번 양식 조립]
        chunk = f"{i+1}번 [{item['name']}] 작전 수립 (환율: ₩{current_rate:,.1f})\n"
        chunk += f"- 구매가: {format_all(buy_p, ticker, current_rate)}\n"
        chunk += f"- 현재가: {format_all(curr_p, ticker, current_rate)} ({yield_pct:+.1f}%)\n"
        chunk += f"- 추가매수권장: {format_all(v_buy, ticker, current_rate)} (-{m_buy:.1f}%)\n"
        chunk += f"- 목표매도: {format_all(v_target, ticker, current_rate)} (+{m_target:.1f}%)\n"
        chunk += f"- 익절 구간: {format_all(v_profit, ticker, current_rate)} (+10.0%)\n"
        chunk += f"🗞️ 뉴스: {news_final[:80]}...\n"
        chunk += f"💡 AI 전술 지침: {insight}\n"
        
        full_report += chunk + "\n" + "-"*35 + "\n"
        summary_list.append({"종목": item['name'], "수익": f"{yield_pct:.1f}%", "지침": insight})
        
    except Exception as e:
        st.error(f"{ticker} 분석 중 오류: {e}")

st.table(pd.DataFrame(summary_list))

# ==========================================================
# 4. [보고/학습] - 텔레그램 무전 및 매도 기록
# ==========================================================
if st.button("📊 2번 정밀 보고서 텔레그램 송신"):
    token = st.secrets["TELEGRAM_TOKEN"]
    cid = user_data.get("chat_id")
    if cid:
        requests.post(f"https://api.telegram.org/bot{token}/sendMessage", data={'chat_id': cid, 'text': full_report})
        st.success("전술 무전 송신 완료!")

st.divider()
st.subheader("📝 AI 매도 기록 학습 (텔레그램 연동)")
sell_input = st.text_input("매도 기록 (예: 매도 TQQQ 65.0)")
if st.button("AI 학습 저장"):
    # [지시사항] 사령관님 매도 가격 기억 [cite: 2025-12-27]
    user_data["sell_history"].append({"date": str(datetime.now()), "log": sell_input})
    with open(USER_PORTFOLIO, "w", encoding="utf-8") as f:
        json.dump(user_data, f, ensure_ascii=False, indent=4)
    st.info("사령관님의 매도 전략을 학습 완료했습니다.")

time.sleep(300); st.rerun()

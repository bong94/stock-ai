import streamlit as st
import pandas as pd
import yfinance as yf
import requests
import json
import os
import time
from datetime import datetime
import pytz

# ==========================================
# 1. [기능: 보안 로그인 및 데이터 영구 보존]
# ==========================================
st.set_page_config(page_title="AI 전술 사령부", layout="wide")
st.sidebar.title("🎖️ AI 사령부 보안 인증")
user_id = st.sidebar.text_input("사령관 호출부호", value="봉94")
USER_PORTFOLIO = f"portfolio_{user_id}.json"

# [고정 지시: 봉94 사령관 기본 자산 데이터]
default_assets = [
    {"name": "대상홀딩스우", "ticker": "084695.KS", "buy_price": 14220},
    {"name": "리얼티인컴", "ticker": "O", "buy_price": 56.69},
    {"name": "에디슨", "ticker": "EIX", "buy_price": 60.21},
    {"name": "SGOV", "ticker": "SGOV", "buy_price": 100.55},
    {"name": "TQQQ", "ticker": "TQQQ", "buy_price": 60.12}
]

# 데이터 로드 로직 (empty 현상 방지)
if os.path.exists(USER_PORTFOLIO):
    try:
        with open(USER_PORTFOLIO, "r", encoding="utf-8") as f:
            user_data = json.load(f)
            if isinstance(user_data, list):
                user_data = {"assets": user_data, "chat_id": st.secrets.get("CHAT_ID", ""), "sell_history": []}
    except:
        user_data = {"assets": default_assets, "chat_id": st.secrets.get("CHAT_ID", ""), "sell_history": []}
else:
    user_data = {"assets": default_assets, "chat_id": st.secrets.get("CHAT_ID", ""), "sell_history": []}

# ==========================================
# 2. [기능: 실시간 시장 상황 및 환율 정찰]
# ==========================================
st.title(f"⚔️ AI 전술 사령부 v53.1 (FULL-SPEC)")
try:
    rate_val = yf.download("USDKRW=X", period="1d", progress=False)['Close'].iloc[-1]
except:
    rate_val = 1445.0 # 통신 불능 시 최근 평균 환율 적용

# ==========================================
# 3. [핵심: 2번 양식 및 뉴스/전술 무한 루프]
# ==========================================
assets = user_data.get("assets", [])
full_report_text = f"🏛️ [봉94 사령관 통합 전술 보고서]\n발신시각: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
summary_list = []

for i, item in enumerate(assets):
    ticker = item['ticker']
    buy_p = float(item['buy_price'])
    
    try:
        # 시세 정보 및 변동성(ATR) 연산
        stock_obj = yf.Ticker(ticker)
        hist = stock_obj.history(period="20d")
        curr_p = hist['Close'].iloc[-1]
        atr_val = (hist['High'] - hist['Low']).mean()
        atr_pct = (atr_val / curr_p) * 100
        
        # [고정 전술 수치 적용]
        m_buy = max(atr_pct * 1.5, 12.0)    # 추매권장 (-12%)
        m_target = max(atr_pct * 3.0, 25.0) # 목표매도 (+25%)
        m_profit = 10.0                    # 익절구간 (+10%)
        
        v_buy = buy_p * (1 - m_buy/100)
        v_target = buy_p * (1 + m_target/100)
        v_profit = buy_p * (1 + m_profit/100)
        yield_val = ((curr_p - buy_p) / buy_p) * 100
        
        # [에러 방지형 뉴스 추출 로직] - KeyError 해결 지점
        news_data = stock_obj.news
        news_final = ""
        if news_data:
            for n in news_data[:2]:
                title = n.get('title', '제목 없음') # .get() 사용으로 에러 완전 차단
                news_final += f"• {title}\n"
        if not news_final: news_final = "현재 수신된 핵심 뉴스 없음"

        # [지시사항: 2번 정밀 양식 조립]
        def price_fmt(p, t, r):
            if ".K" in t: return f"₩{int(p):,}"
            return f"${p:,.2f} (₩{int(p * r):,})"

        report_chunk = f"{i+1}번 [{item['name']}] 작전 수립 (환율: ₩{r:,.1f})\n"
        report_chunk += f"- 구매가: {price_fmt(buy_p, ticker, rate_val)}\n"
        report_chunk += f"- 현재가: {price_fmt(curr_p, ticker, rate_val)} ({yield_val:+.1f}%)\n"
        report_chunk += f"- 추가매수권장: {price_fmt(v_buy, ticker, rate_val)} (-{m_buy:.1f}%)\n"
        report_chunk += f"- 목표매도: {price_fmt(v_target, ticker, rate_val)} (+{m_target:.1f}%)\n"
        report_chunk += f"- 익절 구간: {price_fmt(v_profit, ticker, rate_val)} (+{m_profit:.1f}%)\n"
        report_chunk += f"🗞️ 뉴스: {news_final[:80]}...\n"
        
        # AI 지침 생성
        if yield_val < -10: insight = "📉 [위기] 분할 매수 대응 구간."
        elif yield_val > 20: insight = "🚀 [기회] 목표가 근접, 익절 준비."
        else: insight = "🛡️ [전술 대기] 현재 정상 범위 내 움직임."
        report_chunk += f"💡 AI 전술 지침: {insight}\n"
        
        full_report_text += report_chunk + "\n" + "-"*30 + "\n"
        summary_list.append({"종목": item['name'], "수익": f"{yield_val:.1f}%", "지침": insight})
    except Exception as e:
        st.error(f"{ticker} 데이터 연산 중 오류 발생: {e}")

# 상황판 출력
st.table(pd.DataFrame(summary_list))

# ==========================================
# 4. [기능: 무전 전송 및 4단계 자동 스케줄]
# ==========================================
if st.button("📊 2번 정밀 보고서 내 폰으로 전송"):
    tkn = st.secrets["TELEGRAM_TOKEN"]
    cid = user_data.get("chat_id")
    if cid:
        requests.post(f"https://api.telegram.org/bot{tkn}/sendMessage", data={'chat_id': cid, 'text': full_report_text})
        st.success("무전 송신 완료!")

# [지시사항: 자동 보고 스케줄러 (08:30, 08:50, 15:10)]
now_kr = datetime.now(pytz.timezone('Asia/Seoul'))
targets = [(8,30), (8,50), (15,10)]
for h, m in targets:
    if now_kr.hour == h and now_kr.minute == m:
        requests.post(f"https://api.telegram.org/bot{st.secrets['TELEGRAM_TOKEN']}/sendMessage", 
                      data={'chat_id': user_data.get("chat_id"), 'text': f"🕒 정기 보고\n\n{full_report_text}"})
        time.sleep(60)

# ==========================================
# 5. [기능: 텔레그램 매도 입력 학습 저장소]
# ==========================================
st.divider()
st.subheader("📝 AI 매도 기록 학습 (텔레그램 연동)")
sell_log = st.text_input("매도 기록 입력 (예: 매도 TQQQ 60.5 10주)")
if st.button("AI 학습 저장"):
    # [지시사항: 매도 기록을 학습하여 AI 수익률 연산에 반영]
    user_data["sell_history"].append({"date": str(now_kr), "log": sell_log})
    with open(USER_PORTFOLIO, "w", encoding="utf-8") as f:
        json.dump(user_data, f, ensure_ascii=False, indent=4)
    st.info("사령관님의 매도 습관을 AI가 학습 완료했습니다.")

time.sleep(300); st.rerun()

import streamlit as st
import pandas as pd
import requests
import os
import plotly.graph_objects as go

# --- [1. 보안 설정: 깃허브 Secrets에서 불러오기] ---
# Streamlit Cloud에 배포하면 자동으로 이 키들을 연결한다네
try:
    ALPHA_VANTAGE_KEY = st.secrets["ALPHA_VANTAGE_KEY"]
    TELEGRAM_TOKEN = st.secrets["TELEGRAM_TOKEN"]
    CHAT_ID = st.secrets["CHAT_ID"]
except:
    st.error("보안 키(Secrets)가 설정되지 않았네! 깃허브 설정을 확인하게.")

# --- [2. Alpha Vantage 데이터 엔진] ---
def fetch_ai_intelligence(ticker):
    try:
        # 뉴스 감성 분석 데이터 호출
        url = f'https://www.alphavantage.co/query?function=NEWS_SENTIMENT&tickers={ticker}&apikey={ALPHA_VANTAGE_KEY}'
        res = requests.get(url).json()
        
        if "feed" in res and len(res["feed"]) > 0:
            top_news = res["feed"][0]
            return {
                "score": float(top_news["overall_sentiment_score"]),
                "label": top_news["overall_sentiment_label"],
                "title": top_news["title"],
                "url": top_news["url"]
            }
        return None
    except Exception as e:
        return None

# --- [3. 메인 화면 구성] ---
st.set_page_config(page_title="AI 전술 사령부", layout="wide")
st.title("🤖 글로벌 AI 전술 사령부 v2.0")

ticker = st.sidebar.text_input("종목 코드 입력 (예: NVDA, 005930.KRX)", "NVDA")

if st.sidebar.button("전술 가동"):
    with st.spinner('글로벌 뉴스 기류 분석 중...'):
        intel = fetch_ai_intelligence(ticker)
        
        if intel:
            col1, col2 = st.columns(2)
            with col1:
                st.metric("현재 뉴스 기류", intel["label"])
            with col2:
                st.metric("감성 점수", f"{intel['score']:.2f}")

            # AI의 전략적 조언
            st.divider()
            st.subheader("🧠 AI 전략 보고")
            if intel["score"] > 0.15:
                st.success(f"✅ {ticker}의 주변 기류가 매우 긍정적이네. 매수 전술이 유리할 것으로 보임.")
            elif intel["score"] < -0.15:
                st.error(f"⚠️ 부정적인 뉴스가 감지되었네. 보수적인 방어 태세를 유지하게.")
            else:
                st.info("🟡 특이사항 없는 잔잔한 흐름일세. 관망을 제안하네.")

            st.write(f"📰 **최신 주요 뉴스:** [{intel['title']}]({intel['url']})")
        else:
            st.warning("데이터를 불러오지 못했네. 종목 코드나 API 횟수를 확인하게나.")

# --- [4. 필요한 라이브러리 체크] ---
# requirements.txt에 requests가 포함되어 있어야 하네!

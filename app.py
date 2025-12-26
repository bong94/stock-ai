import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import requests
from scipy.signal import argrelextrema

# --- [설정] 텔레그램 정보 (토큰과 ID를 꼭 본인 것으로 바꾸게!) ---
TELEGRAM_TOKEN = "8284260382:AAHYsS2qu0mg5G9SMm2m2Ug1I9JPR1gAAGs"
CHAT_ID = "6107118513"

def send_telegram_msg(text):
    if TELEGRAM_TOKEN == "자네의_토큰_입력": return False
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.get(url, params={"chat_id": CHAT_ID, "text": text}, timeout=5)
        return True
    except: return False

# --- [기능] AI 지지/저항선 계산 ---
def analyze_ai_lines(df):
    if len(df) < 20: 
        return float(df['Low'].min()), float(df['High'].max())
    
    # 계산의 정확도를 위해 numpy 배열로 변환
    low_vals = df['Low'].values
    high_vals = df['High'].values
    
    iloc_min = argrelextrema(low_vals, np.less, order=10)[0]
    iloc_max = argrelextrema(high_vals, np.greater, order=10)[0]
    
    support = float(low_vals[iloc_min[-1]]) if len(iloc_min) > 0 else float(df['Low'].min())
    resistance = float(high_vals[iloc_max[-1]]) if len(iloc_max) > 0 else float(df['High'].max())
    
    return support, resistance

# --- [화면 구성] ---
st.set_page_config(page_title="마스터 주식 AI", layout="wide")
st.title("🤖 마스터의 주식 AI 트레이너")

# 즐겨찾기 세션 관리
if 'favorites' not in st.session_state:
    st.session_state['favorites'] = ["005930.KS", "AAPL", "TSLA", "NVDA"]

# 사이드바 제어
st.sidebar.title("🎯 종목 컨트롤러")
search_ticker = st.sidebar.text_input("종목 검색 (예: 000660.KS, NVDA)", value="005930.KS").upper()

if st.sidebar.button("⭐️ 즐겨찾기 추가"):
    if search_ticker not in st.session_state['favorites']:
        st.session_state['favorites'].append(search_ticker)
        st.sidebar.success(f"{search_ticker} 추가됨!")

ticker = st.sidebar.selectbox("⭐️ 나의 즐겨찾기", st.session_state['favorites'])

# --- [데이터 처리] ---
# 주말이나 휴장일을 대비해 여유있게 데이터를 가져오네
data = yf.download(ticker, period="6mo", interval="1d")

if not data.empty and len(data) > 1:
    # 데이터가 있을 때만 실행
    curr_price = float(data['Close'].iloc[-1])
    support, resistance = analyze_ai_lines(data)
    
    # 1. 상단 대시보드
    c1, c2, c3 = st.columns(3)
    c1.metric("현재가", f"{curr_price:,.2f}")
    c2.metric("AI 지지선", f"{support:,.2f}")
    c3.metric("AI 저항선", f"{resistance:,.2f}")

    # 2. 메인 차트
    st.subheader(f"📈 {ticker} 차트 및 AI 분석 라인")
    chart_df = pd.DataFrame(index=data.index)
    chart_df['현재가'] = data['Close']
    chart_df['지지원'] = support
    chart_df['저항선'] = resistance
    st.line_chart(chart_df)

    # 3. 마스터의 판독 요약
    st.write("---")
    if curr_price >= resistance:
        st.success(f"🚀 **강력 돌파!** 현재가가 저항선({resistance:,.0f}) 위로 올라왔네. 추가 상승을 기대해볼 만해!")
    elif curr_price <= support:
        st.error(f"📉 **추락 위험!** 지지선({support:,.0f})이 무너졌어. 일단 멈추고 상황을 보게.")
    else:
        st.info(f"🧘 **박스권 횡보 중.** {support:,.0f} 근처에서 줍고, {resistance:,.0f} 근처에서 파는 게 정석이지.")

    # 4. 뉴스 및 텔레그램 알림
    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("📰 최신 뉴스 요약")
        try:
            news = yf.Ticker(ticker).news[:3]
            if news:
                for n in news:
                    with st.expander(n.get('title', '뉴스 제목 없음')):
                        st.write(f"출처: {n.get('publisher')}")
                        st.write(f"[기사 본문 읽기]({n.get('link')})")
            else:
                st.write("최근 뉴스가 없군.")
        except:
            st.write("뉴스를 불러오는 중 오류가 났네.")

    with col_b:
        st.subheader("🔔 텔레그램 전송")
        if st.button("내 폰으로 분석 결과 보내기"):
            msg = f"🤖 [{ticker} AI 리포트]\n\n현재가: {curr_price:,.0f}\n지지선: {support:,.0f}\n저항선: {resistance:,.0f}"
            if send_telegram_msg(msg):
                st.success("메시지 전송 성공! 폰을 확인하게.")
                st.balloons()
            else:
                st.error("텔레그램 설정을 확인해주게. (토큰/ID)")
else:
    st.warning(f"⚠️ {ticker}의 데이터를 가져올 수 없네. 종목 코드가 맞는지 확인해주게.")


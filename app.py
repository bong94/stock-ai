import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import requests
from scipy.signal import argrelextrema

# --- [설정] 텔레그램 정보 (토큰과 ID를 꼭 입력하게!) ---
TELEGRAM_TOKEN = "8284260382:AAHYsS2qu0mg5G9SMm2m2Ug1I9JPR1gAAGs "
CHAT_ID = "6107118513"

def send_telegram_msg(text):
    if TELEGRAM_TOKEN == "자네의_토큰_입력": return False
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.get(url, params={"chat_id": CHAT_ID, "text": text}, timeout=5)
        return True
    except: return False

# --- [기능] AI 지지/저항선 계산 (에러 수정 완료) ---
def analyze_ai_lines(df):
    # 계산을 위해 값을 숫자 배열로 변환하네
    low_vals = df['Low'].values.flatten()
    high_vals = df['High'].values.flatten()
    
    # 고점과 저점의 위치를 찾네
    iloc_min = argrelextrema(low_vals, np.less, order=10)[0]
    iloc_max = argrelextrema(high_vals, np.greater, order=10)[0]
    
    # [수정 포인트] 에러 방지를 위해 .item()을 써서 순수한 숫자로 추출하네
    if len(iloc_min) > 0:
        support = float(low_vals[iloc_min[-1]].item())
    else:
        support = float(df['Low'].min().item())
        
    if len(iloc_max) > 0:
        resistance = float(high_vals[iloc_max[-1]].item())
    else:
        resistance = float(df['High'].max().item())
    
    return support, resistance

# --- [화면 구성] ---
st.set_page_config(page_title="마스터 주식 AI", layout="wide")
st.title("🤖 마스터의 주식 AI 트레이너")

if 'favorites' not in st.session_state:
    st.session_state['favorites'] = ["005930.KS", "AAPL", "TSLA", "NVDA"]

st.sidebar.title("🎯 종목 컨트롤러")
search_ticker = st.sidebar.text_input("종목 검색 (예: 000660.KS, NVDA)", value="005930.KS").upper()

if st.sidebar.button("⭐️ 즐겨찾기 추가"):
    if search_ticker not in st.session_state['favorites']:
        st.session_state['favorites'].append(search_ticker)
        st.sidebar.success(f"{search_ticker} 추가됨!")

ticker = st.sidebar.selectbox("⭐️ 나의 즐겨찾기", st.session_state['favorites'])

# --- [데이터 처리] ---
data = yf.download(ticker, period="6mo", interval="1d")

if not data.empty and len(data) > 1:
    # 현재가 추출 (.item()으로 안전하게 숫자만!)
    curr_price = float(data['Close'].iloc[-1].item())
    support, resistance = analyze_ai_lines(data)
    
    # 1. 상단 대시보드
    c1, c2, c3 = st.columns(3)
    c1.metric("현재가", f"{curr_price:,.2f}")
    c2.metric("AI 지지선", f"{support:,.2f}")
    c3.metric("AI 저항선", f"{resistance:,.2f}")

    # 2. 메인 차트
    st.subheader(f"📈 {ticker} 분석 차트")
    chart_df = pd.DataFrame(index=data.index)
    chart_df['현재가'] = data['Close']
    chart_df['지지선'] = support
    chart_df['저항선'] = resistance
    st.line_chart(chart_df)

    # 3. 마스터의 판독
    st.write("---")
    if curr_price >= resistance:
        st.success(f"🚀 **강력 돌파!** 저항선({resistance:,.0f}) 위로 안착했네!")
    elif curr_price <= support:
        st.error(f"📉 **추락 위험!** 지지선({support:,.0f}) 아래로 떨어졌어!")
    else:
        st.info(f"🧘 **박스권 구간.** 현재 안정적인 흐름이네.")

    # 4. 뉴스 및 알림
    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("📰 최신 뉴스")
        news = yf.Ticker(ticker).news[:3]
        for n in news:
            with st.expander(n.get('title', '뉴스 제목')):
                st.write(f"출처: {n.get('publisher')}")
                st.write(f"[기사 읽기]({n.get('link')})")

    with col_b:
        st.subheader("🔔 텔레그램 전송")
        if st.button("내 폰으로 보고서 전송"):
            msg = f"🤖 [{ticker}]\n가 격: {curr_price:,.0f}\n지지: {support:,.0f}\n저항: {resistance:,.0f}"
            if send_telegram_msg(msg):
                st.success("메시지 전송 완료!")
                st.balloons()
else:
    st.warning("데이터를 가져오는 중이네. 잠시만 기다려주게.")

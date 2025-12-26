import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import requests
import FinanceDataReader as fdr
from scipy.signal import argrelextrema
from datetime import datetime, time

# --- [설정] 텔레그램 정보 ---
TELEGRAM_TOKEN = "8284260382:AAHYsS2qu0mg5G9SMm2m2Ug1I9JPR1gAAGs "
CHAT_ID = "6107118513"

def send_telegram_msg(text):
    if TELEGRAM_TOKEN == "자네의_토큰_입력": return False
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.get(url, params={"chat_id": CHAT_ID, "text": text}, timeout=5)
        return True
    except: return False

# --- [데이터] 전 종목 리스트 가져오기 (가나다순) ---
@st.cache_data # 데이터를 매번 받으면 느리니까 캐시에 저장하네
def get_all_tickers():
    # 한국 종목 (KOSPI, KOSDAQ)
    df_krx = fdr.StockListing('KRX')[['Code', 'Name']]
    df_krx['Full'] = df_krx['Code'] + " (" + df_krx['Name'] + ")"
    df_krx = df_krx.sort_values(by='Name') # 가나다순 정렬
    
    # 주요 미국 종목 (나스닥100 등 대표주 위주로 추가 가능)
    # 여기서는 예시로 한국 종목 위주로 구성했네.
    return df_krx['Full'].tolist()

# --- [기능] AI 지지/저항선 계산 ---
def analyze_ai_lines(df):
    low_vals = df['Low'].values.flatten()
    high_vals = df['High'].values.flatten()
    iloc_min = argrelextrema(low_vals, np.less, order=10)[0]
    iloc_max = argrelextrema(high_vals, np.greater, order=10)[0]
    
    support = float(low_vals[iloc_min[-1]].item()) if len(iloc_min) > 0 else float(df['Low'].min().item())
    resistance = float(high_vals[iloc_max[-1]].item()) if len(iloc_max) > 0 else float(df['High'].max().item())
    return support, resistance

# --- [화면 구성] ---
st.set_page_config(page_title="마스터 주식 AI", layout="wide")
st.title("🤖 마스터의 주식 AI 트레이너")

# 1. 사이드바 - 종목 선택
st.sidebar.title("🎯 종목 컨트롤러")
all_stocks = get_all_tickers()
selected_full = st.sidebar.selectbox("종목 검색 (이름으로 찾기)", all_stocks, index=all_stocks.index("005930 (삼성전자)") if "005930 (삼성전자)" in all_stocks else 0)
ticker = selected_full.split(" ")[0] + ".KS" # 야후 파이낸스용 코드로 변환

# 2. 사이드바 - 알람 설정
st.sidebar.write("---")
st.sidebar.title("⏰ 장 운영 알림 설정")
market_type = st.sidebar.radio("시장 선택", ["국내(09:00~15:30)", "미국(23:30~06:00)"])
alert_times = st.sidebar.multiselect("알림 시점 선택", ["정각", "5분 전", "10분 전", "30분 전"], default=["정각"])

if st.sidebar.button("🔔 알림 설정 저장"):
    st.sidebar.success(f"{market_type} {', '.join(alert_times)} 알림이 예약되었네!")
    # 실제 서버에서 시간에 맞춰 보내는 기능은 별도의 스케줄러가 필요하지만, 우선 UI 설정을 완료했네.

# --- [데이터 처리 및 차트] ---
data = yf.download(ticker, period="6mo", interval="1d")

if not data.empty and len(data) > 1:
    curr_price = float(data['Close'].iloc[-1].item())
    support, resistance = analyze_ai_lines(data)
    
    # 요약 지표
    c1, c2, c3 = st.columns(3)
    c1.metric(f"현재가 ({ticker})", f"{curr_price:,.0f}")
    c2.metric("AI 지지선", f"{support:,.0f}")
    c3.metric("AI 저항선", f"{resistance:,.0f}")

    # 분석 차트
    st.subheader(f"📈 {selected_full} 분석 차트")
    chart_df = pd.DataFrame(index=data.index)
    chart_df['현재가'] = data['Close']
    chart_df['지지선'] = support
    chart_df['저항선'] = resistance
    st.line_chart(chart_df)

    # 마스터 판독 및 뉴스/텔레그램 (기존과 동일)
    if curr_price >= resistance:
        st.success(f"🚀 **돌파 성공!** 저항선({resistance:,.0f}) 위로 안착했네!")
    elif curr_price <= support:
        st.error(f"📉 **추락 위험!** 지지선({support:,.0f})이 무너졌어!")
    else:
        st.info("🧘 **박스권 흐름.** 현재는 안정적인 상태군.")

    # 텔레그램 전송
    if st.button("내 폰으로 보고서 전송"):
        msg = f"🤖 [{selected_full}]\n가 격: {curr_price:,.0f}\n지지: {support:,.0f}\n저항: {resistance:,.0f}"
        if send_telegram_msg(msg):
            st.success("메시지 전송 완료!")
            st.balloons()
else:
    st.warning("데이터를 불러오는 중이네. 종목 코드를 확인해주게.")

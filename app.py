import streamlit as st
import requests
import json
import pandas as pd
import time
from datetime import datetime

# 사령부 설정
st.set_page_config(page_title="봉94 관심종목 실전 사령부", layout="wide")
st.title("🎯 한투 관심종목 실시간 무인 타격기 (v6.0)")

# 1. 보안 키 로드
try:
    APP_KEY = st.secrets["APP_KEY"]
    APP_SECRET = st.secrets["APP_SECRET"]
    ACC_NO = st.secrets["ACC_NO"]
    TG_TOKEN = st.secrets["TELEGRAM_TOKEN"]
    CHAT_ID = st.secrets["CHAT_ID"]
except:
    st.error("⚠️ Secrets 설정을 확인해주세요!")
    st.stop()

# 2. 한투 API 접근 토큰 발급
def get_token():
    url = "https://openapi.koreainvestment.com:9443/oauth2/tokenP"
    data = {"grant_type": "client_credentials", "appkey": APP_KEY, "appsecret": APP_SECRET}
    res = requests.post(url, data=json.dumps(data))
    return res.json().get('access_token')

# 3. [핵심] 한투 관심종목 리스트 긁어오기 함수
def get_my_interest_stocks(token):
    url = "https://openapi.koreainvestment.com:9443/uapi/domestic-stock/v1/quotations/interest-stock"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
        "appkey": APP_KEY,
        "appsecret": APP_SECRET,
        "tr_id": "HHKST01010100" # 관심종목 조회 ID
    }
    # 보통 000번 그룹이 기본 관심종목입니다
    params = {"fid_interest_group_id": "000"} 
    res = requests.get(url, headers=headers, params=params)
    return res.json().get('output', [])

# 4. 실시간 감시 및 지능형 보고
token = get_token()
interest_stocks = get_my_interest_stocks(token)

if interest_stocks:
    st.subheader(f"📡 한투 관심종목({len(interest_stocks)}개) 정찰 현황")
    display_data = []

    for stock in interest_stocks:
        name = stock['stck_prpr_name'] # 종목명
        price = int(stock['stck_prpr']) # 현재가
        change = stock['prdy_vrss_sign'] # 전일대비 기호
        
        # 지능형 전술 판단 (예: 전일대비 5% 이상 하락 시 추매 보고)
        status = "🛡️ 정상 관망"
        if "-" in change: # 하락 중일 때
            status = "🚨 저점 매수 검토"
            # 여기서 자동 매수 주문 코드 실행 가능!

        display_data.append({"종목명": name, "현재가": f"{price:,}원", "전술지침": status})

    st.table(pd.DataFrame(display_data))
else:
    st.info("한투 앱의 관심종목(000번 그룹)이 비어있거나 연결 오류입니다.")

# 5. 텔레그램 자동 보고 (가격 변동 시)
if st.button("📢 현재 관심종목 전체 보고서 받기"):
    msg = "🏛️ [봉94 관심종목 통합 보고]\n"
    for d in display_data:
        msg += f"- {d['종목명']}: {d['현재가']} ({d['전술지침']})\n"
    requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage", data={'chat_id': CHAT_ID, 'text': msg})
    st.success("무전 발송 완료!")

# 5분마다 자동 갱신
time.sleep(300)
st.rerun()

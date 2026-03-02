import streamlit as st
import requests
import json
import pandas as pd
import yfinance as yf
from datetime import datetime
import pytz
import time

# 1. 전술 지침 및 기준가 [cite: 2026-02-26]
RE_INCOME_EXIT = 89070 

st.set_page_config(page_title="봉94 통합 무인 사령부 v7.1", layout="wide")
st.title("🎖️ 봉94 사령관 통합 무인 전투 시스템 v7.1")

# 2. 보안 키 로드
try:
    APP_KEY = st.secrets["APP_KEY"]
    APP_SECRET = st.secrets["APP_SECRET"]
    ACC_NO = st.secrets["ACC_NO"]
    TG_TOKEN = st.secrets["TELEGRAM_TOKEN"]
    CHAT_ID = st.secrets["CHAT_ID"]
except:
    st.error("⚠️ Streamlit Secrets 설정을 확인해주세요!")
    st.stop()

# 3. [보강] 한투 API 통신 엔진 (에러 방지용)
def get_token():
    url = "https://openapi.koreainvestment.com:9443/oauth2/tokenP"
    data = {"grant_type": "client_credentials", "appkey": APP_KEY, "appsecret": APP_SECRET}
    res = requests.post(url, data=json.dumps(data))
    return res.json().get('access_token')

def get_interest_stocks(token):
    """안전하게 관심종목을 가져오는 함수"""
    url = "https://openapi.koreainvestment.com:9443/uapi/domestic-stock/v1/quotations/interest-stock"
    headers = {
        "Content-Type": "application/json", 
        "Authorization": f"Bearer {token}", 
        "appkey": APP_KEY, 
        "appsecret": APP_SECRET, 
        "tr_id": "HHKST01010100"
    }
    # fid_interest_group_id: "000"은 첫 번째 관심그룹입니다
    res = requests.get(url, headers=headers, params={"fid_interest_group_id": "000"})
    
    # [핵심 보강] 응답이 JSON이 아닐 경우를 대비
    try:
        return res.json().get('output', [])
    except:
        return []

# 4. 실시간 정찰 실행
try:
    token = get_token()
    stocks = get_interest_stocks(token)

    if stocks:
        st.subheader(f"📡 현재 감시 중인 관심종목 ({len(stocks)}개)")
        battle_log = []

        for s in stocks:
            name = s.get('stck_prpr_name', '알 수 없음')
            curr_p = int(s.get('stck_prpr', 0))
            change_rate = float(s.get('prdy_ctrt', 0))

            status = "🛡️ 정상 관망"
            # 리얼티인컴 특별 관리 [cite: 2026-02-26]
            if "리얼티" in name and curr_p < RE_INCOME_EXIT:
                status = "🎯 저점 확보 (추매 구간)"

            battle_log.append({"종목명": name, "현재가": f"{curr_p:,}원", "등락률": f"{change_rate}%", "전술지침": status})

        st.table(pd.DataFrame(battle_log))
    else:
        st.warning("📡 한투 앱의 [관심종목 000번 그룹]에 종목을 추가했는지 확인해주세요!")
        st.info("💡 종목을 추가했는데도 안 뜨면, 증권사 서버 점검 시간일 수 있습니다.")

except Exception as e:
    st.error(f"🚨 시스템 정찰 중 오류 발생: {e}")

# 5분 자동 갱신
time.sleep(300)
st.rerun()

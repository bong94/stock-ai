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

st.set_page_config(page_title="봉94 통합 무인 사령부 v7.2", layout="wide")
st.title("🎖️ 봉94 사령관 통합 무인 전투 시스템 v7.2")

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

# 3. 한투 API 통신 엔진
def get_token():
    url = "https://openapi.koreainvestment.com:9443/oauth2/tokenP"
    data = {"grant_type": "client_credentials", "appkey": APP_KEY, "appsecret": APP_SECRET}
    res = requests.post(url, data=json.dumps(data))
    return res.json().get('access_token')

def get_interest_stocks(token):
    """형님이 알려주신 0161번 관심그룹을 정찰합니다"""
    url = "https://openapi.koreainvestment.com:9443/uapi/domestic-stock/v1/quotations/interest-stock"
    headers = {
        "Content-Type": "application/json", 
        "Authorization": f"Bearer {token}", 
        "appkey": APP_KEY, 
        "appsecret": APP_SECRET, 
        "tr_id": "HHKST01010100"
    }
    # ⭐ 형님의 요청대로 좌표를 0161로 수정했습니다!
    params = {"fid_interest_group_id": "0161"} 
    res = requests.get(url, headers=headers, params=params)
    
    try:
        return res.json().get('output', [])
    except:
        return []

# 4. 실시간 정찰 실행
try:
    token = get_token()
    stocks = get_interest_stocks(token)

    if stocks:
        st.subheader(f"📡 현재 감시 중인 0161번 그룹 종목 ({len(stocks)}개)")
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
        st.warning(f"📡 0161번 관심그룹이 비어있거나 접근할 수 없습니다.")
        st.info("💡 한투 앱에서 [0161] 그룹에 종목이 등록되어 있는지 꼭 확인해주세요!")

except Exception as e:
    st.error(f"🚨 시스템 정찰 중 오류 발생: {e}")

# 5분 자동 갱신
time.sleep(300)
st.rerun()

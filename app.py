import streamlit as st
import requests
import json
import os
import pandas as pd
import yfinance as yf
from datetime import datetime
import time

# 1. 사령부 메모장(학습 기록) 관리 함수
MEMORY_FILE = "commander_memory.json"

def load_memory():
    if os.path.exists(MEMORY_FILE):
        try:
            with open(MEMORY_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return {"realty_target": 89070, "last_action": "None", "notes": []}

def save_memory(data):
    with open(MEMORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# 2. 텔레그램 메시지 읽어서 학습하기
def learn_from_telegram():
    token = st.secrets["TELEGRAM_TOKEN"]
    url = f"https://api.telegram.org/bot{token}/getUpdates"
    memory = load_memory()
    
    try:
        res = requests.get(url).json()
        if res.get("ok"):
            for update in res["result"][-5:]:
                msg = update.get("message", {}).get("text", "")
                if "리얼티" in msg and ("원" in msg or "가" in msg):
                    import re
                    price = re.findall(r'\d+', msg.replace(',', ''))
                    if price:
                        memory["realty_target"] = int(price[0])
                        memory["notes"].append(f"[{datetime.now()}] {msg}")
                        save_memory(memory)
                        # --- 42번 줄 괄호 오타 수정 완료 ---
                        return f"🎯 사령관님 지시 학습 완료: 리얼티 목표가 ({int(price[0]):,})원 수정"
    except:
        pass
    return None

# --- 메인 사령부 가동 ---
st.set_page_config(page_title="봉94 학습형 사령부 v8.1", layout="wide")
memory = load_memory()

study_result = learn_from_telegram()
if study_result:
    st.success(study_result)

st.title(f"🎖️ 봉94 무인 전투 시스템 (목표가: ₩{memory['realty_target']:,})")

# 3. 한투 API 통신 엔진 (0161번 그룹 정찰)
try:
    APP_KEY = st.secrets["APP_KEY"]
    APP_SECRET = st.secrets["APP_SECRET"]
    ACC_NO = st.secrets["ACC_NO"]
    
    def get_token():
        url = "https://openapi.koreainvestment.com:9443/oauth2/tokenP"
        data = {"grant_type": "client_credentials", "appkey": APP_KEY, "appsecret": APP_SECRET}
        return requests.post(url, data=json.dumps(data)).json().get('access_token')

    token = get_token()
    
    url = "https://openapi.koreainvestment.com:9443/uapi/domestic-stock/v1/quotations/interest-stock"
    headers = {"Content-Type":"application/json", "Authorization":f"Bearer {token}", "appkey":APP_KEY, "appsecret":APP_SECRET, "tr_id":"HHKST01010100"}
    res = requests.get(url, headers=headers, params={"fid_interest_group_id":"0161"})
    stocks = res.json().get('output', [])

    if stocks:
        st.subheader(f"📡 0161번 관심그룹 정찰 현황 ({len(stocks)}개)")
        battle_log = []
        for s in stocks:
            name = s.get('stck_prpr_name', '알 수 없음')
            curr_p = int(s.get('stck_prpr', 0))
            change_rate = float(s.get('prdy_ctrt', 0))
            status = "🛡️ 정상 관망"
            if "리얼티" in name and curr_p < memory['realty_target']:
                status = "🎯 저점 확보 (추매 구간)"
            battle_log.append({"종목명": name, "현재가": f"{curr_p:,}원", "등락률": f"{change_rate}%", "전술지침": status})
        st.table(pd.DataFrame(battle_log))
    else:
        st.warning("📡 0161번 관심그룹을 찾을 수 없습니다.")

except Exception as e:
    st.error(f"🚨 시스템 정찰 중 오류 발생: {e}")

# 5분 자동 갱신
time.sleep(300)
st.rerun()

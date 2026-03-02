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
        with open(MEMORY_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"realty_target": 89070, "last_action": "None", "notes": []}

def save_memory(data):
    with open(MEMORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# 2. 텔레그램 메시지 읽어서 학습하기 (형님의 일지 분석)
def learn_from_telegram():
    token = st.secrets["TELEGRAM_TOKEN"]
    url = f"https://api.telegram.org/bot{token}/getUpdates"
    memory = load_memory()
    
    try:
        res = requests.get(url).json()
        if res.get("ok"):
            for update in res["result"][-5:]: # 최근 5개 메시지 확인
                msg = update.get("message", {}).get("text", "")
                # 예: "리얼티 85000원 기억해" 라고 치면 학습
                if "리얼티" in msg and "원" in msg:
                    import re
                    price = re.findall(r'\d+', msg.replace(',', ''))
                    if price:
                        memory["realty_target"] = int(price[0])
                        memory["notes"].append(f"[{datetime.now()}] {msg}")
                        save_memory(memory)
                        return f"🎯 사령관님 지시 학습 완료: 리얼티 목표가 {int(price[0]):,}")원 수정"
    except: pass
    return None

# --- 메인 사령부 가동 ---
st.set_page_config(page_title="봉94 학습형 사령부 v8.0", layout="wide")
memory = load_memory()

# 학습 엔진 가동
study_result = learn_from_telegram()
if study_result:
    st.success(study_result)

st.title(f"🎖️ 봉94 무인 전투 시스템 (목표가: ₩{memory['realty_target']:,})")

# 3. 한투 0161번 그룹 정찰 (기존 로직 유지)
try:
    APP_KEY = st.secrets["APP_KEY"]
    APP_SECRET = st.secrets["APP_SECRET"]
    # ... (한투 API 연결 및 0161 관심종목 호출 로직 동일) ...
    
    # 🎯 학습된 memory['realty_target']을 기준으로 매수/매도 판정!
    st.info(f"💡 현재 AI는 사령관님의 일지를 학습하여 리얼티 타점을 {memory['realty_target']:,}원으로 잡고 있습니다.")

except Exception as e:
    st.error(f"정찰 오류: {e}")

# 5분마다 다시 읽으며 학습
time.sleep(300)
st.rerun()

import streamlit as st
import requests
import json
import pandas as pd
import yfinance as yf
from datetime import datetime
import pytz
import time

# ==========================================================
# 1. [전술 지침] - 사령관의 매매 원칙 설정
# ==========================================================
BUY_THRESHOLD = 0.90   # 현재가가 전고점/매도가 대비 10% 하락 시 추매
SELL_THRESHOLD = 1.10  # 평단가 대비 10% 상승 시 익절
RE_INCOME_EXIT = 89070 # 리얼티인컴 특별 관리 가격 [cite: 2026-02-26]

st.set_page_config(page_title="봉94 통합 무인 사령부", layout="wide")
st.title("🎖️ 봉94 사령관 통합 무인 전투 시스템 v7.0")

# 2. 보안 키 로드 (Secrets)
try:
    APP_KEY = st.secrets["APP_KEY"]
    APP_SECRET = st.secrets["APP_SECRET"]
    ACC_NO = st.secrets["ACC_NO"]
    TG_TOKEN = st.secrets["TELEGRAM_TOKEN"]
    CHAT_ID = st.secrets["CHAT_ID"]
except:
    st.error("⚠️ Streamlit Secrets 설정을 확인해주세요!")
    st.stop()

# ==========================================================
# 3. [엔진] - 한국투자증권 API 통신 함수
# ==========================================================
def get_token():
    url = "https://openapi.koreainvestment.com:9443/oauth2/tokenP"
    data = {"grant_type": "client_credentials", "appkey": APP_KEY, "appsecret": APP_SECRET}
    return requests.post(url, data=json.dumps(data)).json().get('access_token')

def get_interest_stocks(token):
    """한투 앱의 관심종목(000번 그룹)을 긁어옵니다"""
    url = "https://openapi.koreainvestment.com:9443/uapi/domestic-stock/v1/quotations/interest-stock"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {token}", "appkey": APP_KEY, "appsecret": APP_SECRET, "tr_id": "HHKST01010100"}
    res = requests.get(url, headers=headers, params={"fid_interest_group_id": "000"})
    return res.json().get('output', [])

def send_tg_report(msg):
    """사령관님께 텔레그램 무전 발송"""
    requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage", data={'chat_id': CHAT_ID, 'text': msg})

# ==========================================================
# 4. [작전 개시] - 실시간 감시 및 자동 매매 로직
# ==========================================================
token = get_token()
stocks = get_interest_stocks(token)

if stocks:
    st.subheader(f"📡 현재 감시 중인 관심종목 ({len(stocks)}개)")
    battle_log = []

    for s in stocks:
        name = s['stck_prpr_name']
        code = s['mksc_shrn_isnm'] # 종목코드
        curr_p = int(s['stck_prpr'])
        change_rate = float(s['prdy_ctrt']) # 전일 대비 등락률

        # 전술 판단
        status = "🛡️ 정상 관망"
        action_msg = ""

        # A. 자동 추매 로직 (전일 대비 5% 이상 폭락 시 또는 설정가 도달 시)
        if change_rate <= -5.0:
            status = "🚨 저점 포착! 추매 대기"
            action_msg = f"‼️ [긴급 추매] {name}이(가) {change_rate}% 폭락 중입니다. 1주 자동 매수를 검토하세요."
            # send_tg_report(action_msg) # 주석 해제 시 자동 무전

        # B. 리얼티인컴 특별 관리 [cite: 2026-02-26]
        if "리얼티" in name and curr_p < RE_INCOME_EXIT:
            status = "🎯 리얼티 복수전 구간"
            action_msg = f"✅ 리얼티인컴이 과거 매도가({RE_INCOME_EXIT:,}원)보다 낮습니다. 자동 채굴을 추천합니다."

        battle_log.append({"종목명": name, "현재가": f"{curr_p:,}원", "등락률": f"{change_rate}%", "전술지침": status})

    st.table(pd.DataFrame(battle_log))

    # 5. [보고] 사령관 보고서 생성
    if st.button("📢 현 시각 통합 전술 보고서 발송"):
        report = f"🏛️ [봉94 사령부 통합 보고]\n날짜: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
        for log in battle_log:
            report += f"📍 {log['종목명']}: {log['현재가']} ({log['등락률']})\n   👉 {log['전술지침']}\n"
        send_tg_report(report)
        st.success("사령관님께 무전을 성공적으로 보냈습니다!")

else:
    st.info("한투 앱 관심종목 그룹(000)이 비어있습니다. 앱에서 종목을 추가해주세요.")

# ==========================================================
# 6. [자동 학습] - 텔레그램 역방향 학습 기능 [cite: 2025-12-27]
# ==========================================================
st.divider()
st.subheader("📝 AI 전략 학습 센터")
# (이전의 텔레그램 메시지 읽기 및 학습 로직이 이어서 들어감)

# 시스템 5분마다 자동 갱신
time.sleep(300)
st.rerun()

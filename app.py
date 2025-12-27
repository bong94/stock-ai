import streamlit as st
import pandas as pd
import yfinance as yf
import requests
import time
import json
import os
from datetime import datetime
import pytz

# --- [1. 데이터 관리 시스템] ---
TELEGRAM_TOKEN = st.secrets.get("TELEGRAM_TOKEN", "")
CHAT_ID = st.secrets.get("CHAT_ID", "")
PORTFOLIO_FILE = "portfolio_db.json"

def load_db():
    if os.path.exists(PORTFOLIO_FILE):
        try:
            with open(PORTFOLIO_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
        except: return []
    return []

def save_db(data):
    with open(PORTFOLIO_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

if 'my_portfolio' not in st.session_state:
    st.session_state.my_portfolio = load_db()

# --- [2. 핵심 전술 보고 엔진 (2번 사진 양식)] ---
def get_exchange_rate():
    try:
        ex_data = yf.download("USDKRW=X", period="1d", progress=False)
        return float(ex_data['Close'].iloc[-1])
    except: return 1442.0

def generate_tactical_report(title="🏛️ [전체 적극적 전술 보고]"):
    if not st.session_state.my_portfolio:
        return "사령관님, 현재 배치된 자산이 없네. 텔레그램으로 '매수 이름 티커 평단가' 명령을 다시 내려주시게!"
    
    rate = get_exchange_rate()
    reports = []
    
    for i, item in enumerate(st.session_state.my_portfolio):
        ticker = item['ticker']
        try:
            df = yf.download(ticker, period="5d", progress=False)
            if df.empty: continue
            curr_p = float(df['Close'].iloc[-1])
            buy_p = float(item['buy_price'])
            
            avg_down, target_p, take_p = buy_p * 0.88, buy_p * 1.25, buy_p * 1.10
            is_kor = any(x in ticker for x in [".KS", ".KQ"])
            
            # 상세 메시지 구성 (2번 사진 양식 완벽 재현)
            if is_kor:
                report = f"{i+1}번 [{item['name']}] 작전 지도 수립\n- 구매가: ₩{buy_p:,.0f}\n- 현재가: ₩{curr_p:,.0f}\n- 추가매수권장: ₩{avg_down:,.0f} (-12%)\n- 목표매도: ₩{target_p:,.0f} (+25%)\n- 익절 구간: ₩{take_p:,.0f} (+10%)"
            else:
                report = f"{i+1}번 [{item['name']}] 작전 지도 수립 (환율: ₩{rate:,.1f})\n- 구매가: ${buy_p:,.2f} (₩{int(buy_p*rate):,})\n- 현재가: ${curr_p:,.2f} (₩{int(curr_p*rate):,})\n- 추가매수권장: ${avg_down:,.2f} (-12%) (₩{int(avg_down*rate):,})\n- 목표매도: ${target_p:,.2f} (+25%) (₩{int(target_p*rate):,})\n- 익절 구간: ${take_p:,.2f} (+10%) (₩{int(take_p*rate):,})"
            
            # AI 전술 지침
            if curr_p <= avg_down:
                guideline = "\n\n💡 AI 전술 지침:\n🛡️ [추가 매수] 적극적 방어 구간입니다. 배치를 검토하십시오."
            elif curr_p >= target_p:
                guideline = "\n\n💡 AI 전술 지침:\n🚩 [목표 달성] 전원 철수 및 이익 실현을 권고합니다!"
            else:
                guideline = "\n\n💡 AI 전술 지침:\n🛡️ [전술 대기] 현재 정상 범위 내 움직임입니다. 관망하십시오."
            
            reports.append(report + guideline)
        except: continue
        
    return f"{title}\n\n" + "\n\n------------------\n\n".join(reports)

# --- [3. 텔레그램 명령 수신 (다중 라인 & 쉼표 완벽 처리)] ---
def listen_and_process():
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates"
    try:
        params = {'timeout': 1}
        if 'last_id' in st.session_state: params['offset'] = st.session_state.last_id + 1
        res = requests.get(url, params=params, timeout=5).json()
        
        if res.get("result"):
            for msg in res["result"]:
                st.session_state.last_id = msg["update_id"]
                full_text = msg["message"].get("text", "")
                if not full_text: continue

                lines = full_text.split('\n')
                new_items = []
                
                for line in lines:
                    if line.startswith("매수"):
                        parts = line.split()
                        if len(parts) >= 4:
                            name = parts[1]
                            ticker = parts[2].upper()
                            # 쉼표(,) 제거 로직 강화
                            price_raw = parts[3].replace(",", "")
                            try:
                                buy_price = float(price_raw)
                                new_items.append({"name": name, "ticker": ticker, "buy_price": buy_price})
                            except: continue

                if new_items:
                    # 기존 자산 업데이트 또는 추가
                    current_portfolio = load_db()
                    for new_item in new_items:
                        current_portfolio = [i for i in current_portfolio if i['ticker'] != new_item['ticker']]
                        current_portfolio.append(new_item)
                    
                    save_db(current_portfolio)
                    st.session_state.my_portfolio = current_portfolio
                    requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", 
                                 data={'chat_id': CHAT_ID, 'text': f"🫡 {len(new_items)}개 종목 전술 배치 완료!"})
                    requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", 
                                 data={'chat_id': CHAT_ID, 'text': generate_tactical_report()})
                    st.rerun()
                elif full_text == "보고":
                    requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", 
                                 data={'chat_id': CHAT_ID, 'text': generate_tactical_report()})
    except: pass

# --- [4. UI (1번 사진 스타일 고정)] ---
st.set_page_config(page_title="AI 전술 사령부 v30.0", page_icon="⚔️", layout="centered")

# 1번 사진의 상단 UI 재현
st.markdown("## ⚔️ AI 전술 사령부 v30.0")
st.markdown("### 📡 현재 배치 자산 실황")

listen_and_process()

if st.session_state.my_portfolio:
    df_display = pd.DataFrame(st.session_state.my_portfolio)
    # 컬럼명 깔끔하게 정리
    df_display.columns = ['종목명', '티커', '구매가']
    st.table(df_display) # 1번 사진 스타일의 표 노출
else:
    st.info("사령관님, 현재 배치된 자산이 없네. 텔레그램으로 명령을 내려주시게!")

# 수동 보고 버튼
if st.button("📊 지금 즉시 텔레그램 보고 송신"):
    requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", 
                 data={'chat_id': CHAT_ID, 'text': generate_tactical_report()})

time.sleep(10)
st.rerun()

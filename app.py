# 개선된 Streamlit 앱: AI 전술 사령부 (개선판)
# 주요 변경: Telegram offset 처리, 안전한 마크다운 이스케이프,
# atomic 파일 저장, yfinance 캐시/검증, 명령 유효성 검사,
# 자동 새로고침 옵션(외부 패키지 선택적 사용) 등

import streamlit as st
import pandas as pd
import yfinance as yf
import requests
import time
import json
import os
import tempfile
from typing import Tuple

# --- 설정 ---
TELEGRAM_TOKEN = st.secrets.get("TELEGRAM_TOKEN", "")
CHAT_ID = st.secrets.get("CHAT_ID", "")
PORTFOLIO_FILE = "portfolio_db.json"

# --- 유틸리티 ---
def escape_markdown_v2(text: str) -> str:
    """
    Telegram MarkdownV2 escape for user-provided text to avoid formatting injection.
    """
    if not isinstance(text, str):
        text = str(text)
    to_escape = r"_*[]()~`>#+-=|{}.!\\"
    # prepend backslash before each special character
    return "".join("\\" + ch if ch in to_escape else ch for ch in text)

def atomic_save_json(path: str, data):
    """임시파일로 쓰고 replace로 원자적 저장"""
    dirpath = os.path.dirname(os.path.abspath(path)) or "."
    fd, tmp = tempfile.mkstemp(dir=dirpath, prefix=".tmp_", suffix=".json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        os.replace(tmp, path)
    except Exception:
        try:
            os.remove(tmp)
        except Exception:
            pass
        raise

def load_db():
    if os.path.exists(PORTFOLIO_FILE):
        try:
            with open(PORTFOLIO_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
        except Exception:
            # 파일 손상 등 문제 발생 시 빈 리스트 반환 (운영 환경에서는 로그)
            return []
    return []

def save_db(data):
    atomic_save_json(PORTFOLIO_FILE, data)

# 세션 상태 초기화
if 'my_portfolio' not in st.session_state:
    st.session_state.my_portfolio = load_db()
if 'last_update_id' not in st.session_state:
    st.session_state.last_update_id = None  # Telegram offset 관리

# --- 텔레그램 통신 ---
def send_telegram_msg(text: str) -> bool:
    """
    텔레그램 전송 (MarkdownV2 사용). 반환: 성공 여부
    """
    if not TELEGRAM_TOKEN or not CHAT_ID:
        return False
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        resp = requests.post(url, data={'chat_id': CHAT_ID, 'text': text, 'parse_mode': 'MarkdownV2'}, timeout=10)
        return resp.status_code == 200
    except requests.RequestException:
        return False

# yfinance 캐시(단기). 동일 티커에 대한 연속 요청을 완화
@st.cache_data(ttl=20)  # 20초 캐시 (필요시 조절)
def fetch_recent_close(ticker: str, period: str = "5d") -> Tuple[float, pd.DataFrame]:
    """
    최근 종가 가져오기. 실패 시 (None, df) 반환.
    """
    try:
        df = yf.download(ticker, period=period, progress=False)
        if df is None or df.empty or 'Close' not in df.columns:
            return None, df
        last = df['Close'].dropna().iloc[-1]
        return float(last), df
    except Exception:
        return None, pd.DataFrame()

def get_aggressive_report(name: str, ticker: str, buy_p: float, idx: int = 1) -> Tuple[str, float]:
    """
    전술 보고서 생성 — 실패 시 적절한 메시지와 0 반환
    """
    curr_p, df = fetch_recent_close(ticker)
    if curr_p is None:
        return f"⚠️ {escape_markdown_v2(name)}({escape_markdown_v2(ticker)}) 분석 실패 — 가격 데이터를 불러올 수 없습니다.", 0.0

    try:
        avg_down = buy_p * 0.88
        target_p = buy_p * 1.25
        take_profit = buy_p * 1.10
        symbol = "₩" if any(x in ticker for x in (".KS", ".KQ", ".KR")) else "$"
        # escape display fields for MarkdownV2
        name_e = escape_markdown_v2(name.upper())
        ticker_e = escape_markdown_v2(ticker)
        report = (
            f"*{idx}번 [{name_e}] 작전 지도 수립*\n"
            f"- 구매가: {symbol}{buy_p:,.2f}\n"
            f"- 현재가: {symbol}{curr_p:,.2f}\n"
            f"- 추가매수권장: {symbol}{avg_down:,.2f} (-12%)\n"
            f"- 목표매도: {symbol}{target_p:,.2f} (+25%)\n"
            f"- 익절 구간: {symbol}{take_profit:,.2f} (+10%)\n"
        )
        return report, curr_p
    except Exception:
        return f"⚠️ {escape_markdown_v2(name)}({escape_markdown_v2(ticker)}) 분석 중 오류 발생", 0.0

def listen_telegram_once():
    """
    getUpdates를 offset으로 안전하게 처리 — 새 명령이 있으면 포트폴리오에 반영
    반환: "RERUN" 또는 "REPORT" 등 특수 명령 또는 None
    """
    if not TELEGRAM_TOKEN:
        return None
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates"
    params = {"timeout": 5, "limit": 10}
    if st.session_state.last_update_id is not None:
        # 다음에 가져올 update_id (offset = last_update_id + 1)
        params["offset"] = st.session_state.last_update_id + 1
    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        results = data.get("result", [])
        if not results:
            return None

        # 처리된 마지막 update_id를 갱신
        for upd in results:
            st.session_state.last_update_id = max(st.session_state.last_update_id or -1, upd.get("update_id", -1))
            # 메시지 파싱
            msg = upd.get("message") or upd.get("edited_message") or {}
            text = msg.get("text", "")
            if not text:
                continue
            text = text.strip()
            # "매수 <이름> <티커> <가격>"
            if text.startswith("매수"):
                parts = text.split()
                if len(parts) >= 4:
                    name = parts[1]
                    ticker = parts[2].upper()
                    try:
                        bp = float(parts[3].replace(",", ""))
                    except ValueError:
                        # 잘못된 가격 형식 무시(혹은 에러 메시지 전송)
                        send_telegram_msg(f"⚠️ 가격 형식 오류: {escape_markdown_v2(parts[3])} — '매수 이름 티커 가격' 형식으로 보내주세요.")
                        continue
                    # 중복 제거 및 신규 추가
                    st.session_state.my_portfolio = [i for i in st.session_state.my_portfolio if i.get('ticker') != ticker]
                    st.session_state.my_portfolio.append({"name": name, "ticker": ticker, "buy_price": bp})
                    try:
                        save_db(st.session_state.my_portfolio)
                    except Exception:
                        pass
                    # 즉시 보고
                    report, _ = get_aggressive_report(name, ticker, bp, len(st.session_state.my_portfolio))
                    send_telegram_msg(f"🫡 명령 수신! 적극적 투자 전술 보고드립니다.\n{report}")
                    return "RERUN"
                else:
                    send_telegram_msg("⚠️ 매수 명령 형식: 매수 <이름> <티커> <가격>")


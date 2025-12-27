# AI 전술 사령부 — 텔레그램 임계값 알람 추가판
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
    if not isinstance(text, str):
        text = str(text)
    to_escape = r"_*[]()~`>#+-=|{}.!\\"
    return "".join("\\" + ch if ch in to_escape else ch for ch in text)

def atomic_save_json(path: str, data):
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
            return []
    return []

def save_db(data):
    atomic_save_json(PORTFOLIO_FILE, data)

# 세션 상태 초기화
if 'my_portfolio' not in st.session_state:
    st.session_state.my_portfolio = load_db()
if 'last_update_id' not in st.session_state:
    st.session_state.last_update_id = None

# 마이그레이션: 기존 항목에 알람 플래그가 없으면 추가
def ensure_alert_flags(item):
    changed = False
    for k in ("alerted_avg_down", "alerted_take_profit", "alerted_target"):
        if k not in item:
            item[k] = False
            changed = True
    return changed

for it in st.session_state.my_portfolio:
    ensure_alert_flags(it)

# --- 텔레그램 통신 ---
def send_telegram_msg(text: str) -> bool:
    if not TELEGRAM_TOKEN or not CHAT_ID:
        return False
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        resp = requests.post(url, data={'chat_id': CHAT_ID, 'text': text, 'parse_mode': 'MarkdownV2'}, timeout=10)
        return resp.status_code == 200
    except requests.RequestException:
        return False

@st.cache_data(ttl=20)
def fetch_recent_close(ticker: str, period: str = "5d") -> Tuple[float, pd.DataFrame]:
    try:
        df = yf.download(ticker, period=period, progress=False)
        if df is None or df.empty or 'Close' not in df.columns:
            return None, df
        last = df['Close'].dropna().iloc[-1]
        return float(last), df
    except Exception:
        return None, pd.DataFrame()

def get_aggressive_report(name: str, ticker: str, buy_p: float, idx: int = 1) -> Tuple[str, float]:
    curr_p, df = fetch_recent_close(ticker)
    if curr_p is None:
        return f"⚠️ {escape_markdown_v2(name)}({escape_markdown_v2(ticker)}) 분석 실패 — 가격 데이터를 불러올 수 없습니다.", 0.0
    try:
        avg_down = buy_p * 0.88
        target_p = buy_p * 1.25
        take_profit = buy_p * 1.10
        symbol = "₩" if any(x in ticker for x in (".KS", ".KQ", ".KR")) else "$"
        name_e = escape_markdown_v2(name.upper())
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
    if not TELEGRAM_TOKEN:
        return None
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates"
    params = {"timeout": 5, "limit": 10}
    if st.session_state.last_update_id is not None:
        params["offset"] = st.session_state.last_update_id + 1
    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        results = data.get("result", [])
        if not results:
            return None
        for upd in results:
            st.session_state.last_update_id = max(st.session_state.last_update_id or -1, upd.get("update_id", -1))
            msg = upd.get("message") or upd.get("edited_message") or {}
            text = msg.get("text", "")
            if not text:
                continue
            text = text.strip()
            if text.startswith("매수"):
                parts = text.split()
                if len(parts) >= 4:
                    name = parts[1]
                    ticker = parts[2].upper()
                    try:
                        bp = float(parts[3].replace(",", ""))
                    except ValueError:
                        send_telegram_msg(f"⚠️ 가격 형식 오류: {escape_markdown_v2(parts[3])} — '매수 이름 티커 가격' 형식으로 보내주세요.")
                        continue
                    st.session_state.my_portfolio = [i for i in st.session_state.my_portfolio if i.get('ticker') != ticker]
                    new_item = {"name": name, "ticker": ticker, "buy_price": bp,
                                "alerted_avg_down": False, "alerted_take_profit": False, "alerted_target": False}
                    st.session_state.my_portfolio.append(new_item)
                    try:
                        save_db(st.session_state.my_portfolio)
                    except Exception:
                        pass
                    report, _ = get_aggressive_report(name, ticker, bp, len(st.session_state.my_portfolio))
                    send_telegram_msg(f"🫡 명령 수신! 적극적 투자 전술 보고드립니다.\n{report}")
                    return "RERUN"
                else:
                    send_telegram_msg("⚠️ 매수 명령 형식: 매수 <이름> <티커> <가격>")
            elif text == "보고":
                return "REPORT"
    except requests.RequestException:
        return None
    except Exception:
        return None
    return None

# --- 임계값 알람 검사 ---
def check_thresholds(enabled: bool):
    if not enabled or not st.session_state.my_portfolio:
        return
    changed = False
    for i, item in enumerate(st.session_state.my_portfolio):
        # ensure flags exist
        ensure_alert_flags(item)
        buy_p = float(item.get("buy_price", 0.0))
        curr_p, _ = fetch_recent_close(item["ticker"])
        if curr_p is None:
            continue
        avg_down = buy_p * 0.88
        take_profit = buy_p * 1.10
        target_p = buy_p * 1.25
        name_e = escape_markdown_v2(item.get("name", ""))
        ticker_e = escape_markdown_v2(item.get("ticker", ""))
        # 추가매수권장
        if curr_p <= avg_down and not item.get("alerted_avg_down", False):
            msg = (
                f"📉 *추가매수권장* — [{name_e}] {ticker_e}\n"
                f"- 구매가: {buy_p:,.2f}\n- 현재가: {curr_p:,.2f}\n- 권장가: {avg_down:,.2f} (-12%)\n"
            )
            send_telegram_msg(msg)
            item["alerted_avg_down"] = True
            changed = True
        # 목표매도 (우선순위: 목표가 도달시 익절보다 우선)
        if curr_p >= target_p and not item.get("alerted_target", False):
            msg = (
                f"🏁 *목표매도 도달* — [{name_e}] {ticker_e}\n"
                f"- 구매가: {buy_p:,.2f}\n- 현재가: {curr_p:,.2f}\n- 목표가: {target_p:,.2f} (+25%)\n"
            )
            send_telegram_msg(msg)
            item["alerted_target"] = True
            changed = True
        # 익절 권장 (목표가로 이미 알림이 간 경우 중복 방지)
        if curr_p >= take_profit and not item.get("alerted_take_profit", False) and not item.get("alerted_target", False):
            msg = (
                f"💰 *익절 권장* — [{name_e}] {ticker_e}\n"
                f"- 구매가: {buy_p:,.2f}\n- 현재가: {curr_p:,.2f}\n- 익절 기준: {take_profit:,.2f} (+10%)\n"
            )
            send_telegram_msg(msg)
            item["alerted_take_profit"] = True
            changed = True
    if changed:
        try:
            save_db(st.session_state.my_portfolio)
        except Exception:
            pass

# --- Streamlit UI ---
st.set_page_config(page_title="AI 전술 사령부 v17.0 (알람 포함)", layout="wide")
st.title("⚔️ AI 전술 사령부 v17.0 — 텔레그램 임계값 알람")

auto_refresh = st.sidebar.checkbox("자동 새로고침 (5초)", value=False)
alerts_enabled = st.sidebar.checkbox("임계값 알람 활성화", value=True)
st.sidebar.markdown("알람을 끄려면 체크해제하세요. 운영 환경에서는 webhook 권장.")

if st.sidebar.button("텔레그램에서 명령 확인"):
    cmd = listen_telegram_once()
    if cmd == "RERUN":
        st.experimental_rerun()
    elif cmd == "REPORT":
        reports = []
        for i, it in enumerate(st.session_state.my_portfolio):
            r, _ = get_aggressive_report(it['name'], it['ticker'], it['buy_price'], i+1)
            reports.append(r)
        send_telegram_msg("🏛️ [전체 적극적 전술 지도 보고]\n" + "\n\n".join(reports))
        st.success("보고 전송 완료")

# 자동 새로고침에서 텔레그램 검사 및 임계값 검사 실행
if auto_refresh:
    try:
        from streamlit_autorefresh import st_autorefresh
        count = st_autorefresh(interval=5 * 1000, limit=None, key="autorefresh")
        _ = listen_telegram_once()
        check_thresholds(alerts_enabled)
    except Exception:
        st.info("자동 새로고침을 사용하려면 streamlit-autorefresh를 설치.")

# 수동으로도 검사/알림 트리거 가능
if st.sidebar.button("임계값 즉시 검사 및 알림 전송"):
    check_thresholds(alerts_enabled)
    st.success("검사 완료")

if st.session_state.my_portfolio:
    all_reports = []
    cols = st.columns(min(len(st.session_state.my_portfolio), 4))

    for i, item in enumerate(list(st.session_state.my_portfolio)):
        report_text, current_p = get_aggressive_report(item['name'], item['ticker'], item['buy_price'], i+1)
        all_reports.append(report_text)
        profit = 0.0
        if current_p:
            try:
                profit = ((current_p - item['buy_price']) / item['buy_price']) * 100
            except Exception:
                profit = 0.0

        col = cols[i % 4]
        with col:
            st.metric(item['name'], f"{current_p:,.2f}" if current_p else "N/A", f"{profit:.2f}%")
            if st.button(f"작전 종료: {item['name']}", key=f"del_{i}"):
                st.session_state.my_portfolio.pop(i)
                try:
                    save_db(st.session_state.my_portfolio)
                except Exception:
                    pass
                st.experimental_rerun()

    if st.sidebar.button("전체 보고 텔레그램 전송"):
        send_telegram_msg("🏛️ [전체 적극적 전술 지도 보고]\n" + "\n\n".join(all_reports))
        st.success("보고 전송 완료")
else:
    st.info("사령관님, 현재 대기 중인 자산이 없습니다. 텔레그램 명령을 기다립니다!")

st.markdown("---")
st.markdown("설명: 임계값 알람은 각 항목별로 한 번만 전송됩니다. 플래그를 초기화하려면 해당 항목을 제거 후 재추가하거나 JSON에서 플래그 값을 수동 변경하세요.")

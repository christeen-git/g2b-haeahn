import sys
import os
import json
import requests
import xml.etree.ElementTree as ET
import subprocess
from urllib.parse import unquote, quote
from datetime import datetime, timedelta, timezone

sys.stdout.reconfigure(line_buffering=True)

KST = timezone(timedelta(hours=9))
now = datetime.now(KST)

order_bgn_ym = now.strftime("%Y%m")
order_end_ym = f"{now.year + 1}{now.month:02d}"

inqryBgnDate12 = now.strftime("%Y%m%d") + "0000"
today_str12 = now.strftime("%Y%m%d") + "2359"

RAW_SERVICE_KEY = unquote(unquote(os.environ.get("SERVICE_KEY", "").strip()))

SENT_FILE = "sent_notices.json"
WEB_JSON_FILE = "notices.json"

P1_KEYWORDS = ["설계", "건립", "신축", "개발"]
P2_KEYWORDS = ["타당성", "마스터", "기본계획", "기본구상", "공모관리", "공모 관리"]
EXCLUDE_KEYWORDS = ["건설사업관리용역", "폐기물", "감리자", "내진보강"]

def save_web_dashboard_json(items):
    formatted_list = []
    for idx, item in enumerate(items, 1):
        raw_price = item.get('raw_price', 0)
        notice_dt = item.get('notice_dt', '-')
        expl_info = item.get('expl_info', '-')
        reg_close = item.get('reg_close_dt', '-')
        bid_close = item.get('bid_close_dt', '-')
        open_dt = item.get('open_dt', '-')

        formatted_list.append({
            "id": f"AUTO_{idx:03d}",
            "ntceKindNm": item.get('source_type'),
            "ntceNm": item.get('title'),
            "organ": item.get('notice_instt'),
            "price": raw_price,
            "dateNotice": notice_dt,
            "dateBrief": expl_info,
            "dateLimit": bid_close if bid_close != '-' else reg_close,
            "dateOpen": open_dt,
            "chgRsn": item.get('chg_rsn', ''),
            "isImportant": False,
            "url": item.get('url', ''),
            "comments": [],
            "files": [att['name'] for att in item.get('attachments', [])]
        })

    try:
        with open(WEB_JSON_FILE, "w", encoding="utf-8") as f:
            json.dump(formatted_list, f, ensure_ascii=False, indent=4)
        print(f"웹 대시보드 연동 파일({WEB_JSON_FILE}) 생성 완료.")
        
        if os.environ.get("GITHUB_ACTIONS") == "true":
            subprocess.run(["git", "config", "--global", "user.name", "github-actions[bot]"], check=True)
            subprocess.run(["git", "config", "--global", "user.email", "github-actions[bot]@users.noreply.github.com"], check=True)
            subprocess.run(["git", "add", WEB_JSON_FILE], check=True)
            status = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True)
            if status.stdout.strip():
                subprocess.run(["git", "commit", "-m", "Auto-update notices.json via bot [skip ci]"], check=True)
                subprocess.run(["git", "push"], check=True)
                print("notices.json 깃허브 자동 푸시 완료!")
    except Exception as e:
        print(f"웹 대시보드 JSON 저장 및 푸시 중 오류: {e}")

def fetch_api_data(base_url, query_params):
    if not RAW_SERVICE_KEY: return None
    try:
        encoded_key = quote(RAW_SERVICE_KEY, safe='')
        query_str = "&".join([f"{k}={v}" for k, v in query_params.items()])
        response = requests.get(f"{base_url}?{query_str}&ServiceKey={encoded_key}", timeout=15)
        if response.status_code != 200: return None
        if "<errMsg>" in response.text or "SERVICE ERROR" in response.text: return None
        return ET.fromstring(response.text)
    except Exception:
        return None

def format_datetime_str(dt_str):
    if not dt_str or dt_str == '-': return '-'
    clean_str = "".join(filter(str.isdigit, dt_str))
    try:
        if len(clean_str) >= 12: return f"{clean_str[:4]}-{clean_str[4:6]}-{clean_str[6:8]}"
        elif len(clean_str) == 8: return f"{clean_str[:4]}-{clean_str[4:6]}-{clean_str[6:8]}"
    except Exception: pass
    return dt_str

def check_bids():
    now = datetime.now(KST)
    inqryBgnDt14 = (now - timedelta(hours=12)).strftime("%Y%m%d%H%M00")
    inqryEndDt14 = now.strftime("%Y%m%d%H%M59")

    matched_bids, matched_plans, matched_specs = [], [], []

    # 본공고 조회
    for _, base_url in [("용역", "http://apis.data.go.kr/1230000/ad/BidPublicInfoService/getBidPblancListInfoServc"), ("공사", "http://apis.data.go.kr/1230000/ad/BidPublicInfoService/getBidPblancListInfoCnstwk")]:
        root = fetch_api_data(base_url, {"inqryDiv": "1", "inqryBgnDt": inqryBgnDt14, "inqryEndDt": inqryEndDt14, "pageNo": "1", "numOfRows": "100"})
        items = root.findall(".//item") if root is not None else []
        for item in items:
            bid_nm = item.findtext('bidNtceNm') or '-'
            if any(ex in bid_nm for ex in EXCLUDE_KEYWORDS): continue
            if not (any(k in bid_nm for k in P1_KEYWORDS) or any(k in bid_nm for k in P2_KEYWORDS)): continue

            presmpt_prce = item.findtext('presmptPrce') or item.findtext('asignBdgAmt') or '0'
            price_val = float(presmpt_prce.replace(',', '').strip()) if presmpt_prce.replace(',', '').strip().isdigit() else 0

            if (any(k in bid_nm for k in P1_KEYWORDS) and price_val >= 500000000) or any(k in bid_nm for k in P2_KEYWORDS):
                matched_bids.append({
                    'source_type': '본공고',
                    'title': bid_nm,
                    'notice_instt': item.findtext('ntceInsttNm') or '-',
                    'raw_price': price_val,
                    'notice_dt': format_datetime_str(item.findtext('bidNtceDt', '-')),
                    'expl_info': format_datetime_str(item.findtext('dcmtgOprtnDt') or '-'),
                    'reg_close_dt': format_datetime_str(item.findtext('bidQlfctRgstDt') or '-'),
                    'bid_close_dt': format_datetime_str(item.findtext('bidClseDt') or '-'),
                    'open_dt': format_datetime_str(item.findtext('opengDt') or '-'),
                    'url': item.findtext('bidNtceDtlUrl', ''),
                    'attachments': [],
                    'chg_rsn': item.findtext('chgNtceRsn') or ''
                })

    all_matched_items = matched_bids + matched_plans + matched_specs
    save_web_dashboard_json(all_matched_items)

if __name__ == "__main__":
    check_bids()

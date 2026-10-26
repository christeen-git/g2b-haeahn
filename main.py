import sys
import os
import json
import requests
import xml.etree.ElementTree as ET
import smtplib
import subprocess
from urllib.parse import unquote, quote
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta, timezone

# 콘솔 출력 버퍼링 해제 (GitHub Actions 실시간 로그 출력)
sys.stdout.reconfigure(line_buffering=True)

# 한국 표준시(KST: UTC+9) 고정
KST = timezone(timedelta(hours=9))
now = datetime.now(KST)

# 날짜 및 기간 설정
order_bgn_ym = now.strftime("%Y%m")
order_end_ym = f"{now.year + 1}{now.month:02d}"

inqryBgnDate12 = now.strftime("%Y%m%d") + "0000"
today_str12 = now.strftime("%Y%m%d") + "2359"

RAW_SERVICE_KEY = unquote(unquote(os.environ.get("SERVICE_KEY", "").strip()))

GMAIL_USER = os.environ.get("GMAIL_USER")
GMAIL_APP_KEY = os.environ.get("GMAIL_APP_KEY")
TO_EMAIL = os.environ.get("TO_EMAIL")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
FORWARD_CHAT_ID = os.environ.get("FORWARD_CHAT_ID")

SENT_FILE = "sent_notices.json"
WEB_JSON_FILE = "notices.json" # 웹 대시보드 연동용 파일

P1_KEYWORDS = ["설계", "건립", "신축", "개발"]
P2_KEYWORDS = ["타당성", "마스터", "기본계획", "기본구상", "공모관리", "공모 관리"]
EXCLUDE_KEYWORDS = ["건설사업관리용역", "폐기물", "감리자", "내진보강"]

def load_sent_notices():
    if os.path.exists(SENT_FILE):
        try:
            with open(SENT_FILE, "r", encoding="utf-8") as f:
                return set(json.load(f))
        except Exception:
            return set()
    return set()

def save_sent_notices(sent_set):
    try:
        limited_list = list(sent_set)[-1000:]
        with open(SENT_FILE, "w", encoding="utf-8") as f:
            json.dump(limited_list, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"중복 방지 파일 저장 중 오류: {e}")

# 웹 대시보드(index.html) 형식에 맞춰 notices.json 저장 및 깃허브 자동 푸시
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

def get_item_key(item):
    return f"{item.get('source_type')}_{item.get('title')}_{item.get('notice_dt')}"

def fetch_api_data(base_url, query_params):
    if not RAW_SERVICE_KEY:
        print("    [경고] SERVICE_KEY가 설정되지 않았습니다.")
        return None

    try:
        encoded_key = quote(RAW_SERVICE_KEY, safe='')
        query_str = "&".join([f"{k}={v}" for k, v in query_params.items()])
        full_url = f"{base_url}?{query_str}&ServiceKey={encoded_key}"
        response = requests.get(full_url, timeout=15)
        if response.status_code != 200: return None
        if "<errMsg>" in response.text or "<returnAuthMsg>" in response.text or "SERVICE ERROR" in response.text: return None
        return ET.fromstring(response.text)
    except Exception as e:
        return None

def format_datetime_str(dt_str):
    if not dt_str or dt_str == '-': return '-'
    clean_str = "".join(filter(str.isdigit, dt_str))
    try:
        if len(clean_str) >= 12: return f"{clean_str[:4]}-{clean_str[4:6]}-{clean_str[6:8]}"
        elif len(clean_str) == 8: return f"{clean_str[:4]}-{clean_str[4:6]}-{clean_str[6:8]}"
    except Exception: pass
    return dt_str

def extract_attachments(item):
    attachments_map = {}
    for child in item:
        tag, val = child.tag, (child.text or "").strip()
        if not val: continue
        if "url" in tag.lower():
            digits = "".join(filter(str.isdigit, tag)) or "1"
            attachments_map.setdefault(digits, {'name': '', 'url': ''})['url'] = val
        elif "filenm" in tag.lower() or "specfile" in tag.lower() or "docnm" in tag.lower():
            digits = "".join(filter(str.isdigit, tag)) or "1"
            attachments_map.setdefault(digits, {'name': '', 'url': ''})['name'] = val
    return [{'name': info['name'] or f"첨부문서_{idx}", 'url': info['url']} for idx, info in sorted(attachments_map.items()) if info['url']]

def send_telegram_single(text):
    try:
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", data={"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "HTML"}, timeout=10)
    except Exception: pass

def check_bids():
    now = datetime.now(KST)
    weekday, hour, minute = now.weekday(), now.hour, now.minute
    lookback_minutes = 40
    if weekday == 0 and hour == 8 and minute < 30: lookback_minutes = 3730
    elif hour == 8: lookback_minutes = 780

    past_time = now - timedelta(minutes=lookback_minutes)
    inqryBgnDt14 = past_time.strftime("%Y%m%d%H%M00")
    inqryEndDt14 = now.strftime("%Y%m%d%H%M59")

    matched_bids, matched_plans, matched_specs = [], [], []

    # 1. 본공고 API
    for category_name, base_url in [("용역", "http://apis.data.go.kr/1230000/ad/BidPublicInfoService/getBidPblancListInfoServc"), ("공사", "http://apis.data.go.kr/1230000/ad/BidPublicInfoService/getBidPblancListInfoCnstwk")]:
        page_no = 1
        while True:
            root = fetch_api_data(base_url, {"inqryDiv": "1", "inqryBgnDt": inqryBgnDt14, "inqryEndDt": inqryEndDt14, "pageNo": str(page_no), "numOfRows": "100"})
            items = root.findall(".//item") if root is not None else []
            if not items: break
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
                        'demand_instt': item.findtext('dminsttNm', '-'),
                        'raw_price': price_val,
                        'price': f"{int(price_val):,}원",
                        'notice_dt': format_datetime_str(item.findtext('bidNtceDt', '-')),
                        'expl_info': format_datetime_str(item.findtext('dcmtgOprtnDt') or '-'),
                        'reg_close_dt': format_datetime_str(item.findtext('bidQlfctRgstDt') or '-'),
                        'bid_close_dt': format_datetime_str(item.findtext('bidClseDt') or '-'),
                        'open_dt': format_datetime_str(item.findtext('opengDt') or '-'),
                        'url': item.findtext('bidNtceDtlUrl', ''),
                        'attachments': extract_attachments(item),
                        'chg_rsn': item.findtext('chgNtceRsn') or ''
                    })
            if len(items) < 100: break
            page_no += 1

    # 2. 발주계획 API
    for category_name, base_url in [("용역", "http://apis.data.go.kr/1230000/ao/OrderPlanSttusService/getOrderPlanSttusListServc"), ("공사", "http://apis.data.go.kr/1230000/ao/OrderPlanSttusService/getOrderPlanSttusListCnstwk")]:
        root = fetch_api_data(base_url, {"inqryDiv": "1", "orderBgnYm": order_bgn_ym, "orderEndYm": order_end_ym, "inqryBgnDt": inqryBgnDate12, "inqryEndDt": today_str12, "numOfRows": "500"})
        if root is not None:
            for item in root.findall(".//item"):
                biz_nm = item.findtext('bizNm') or item.findtext('orderPlanNm') or '-'
                if any(ex in biz_nm for ex in EXCLUDE_KEYWORDS): continue
                if not (any(k in biz_nm for k in P1_KEYWORDS) or any(k in biz_nm for k in P2_KEYWORDS)): continue

                sum_order_amt = item.findtext('sumOrderAmt') or '0'
                price_val = float(sum_order_amt.replace(',', '').strip()) if sum_order_amt.replace(',', '').strip().isdigit() else 0

                if (any(k in biz_nm for k in P1_KEYWORDS) and price_val >= 500000000) or any(k in biz_nm for k in P2_KEYWORDS):
                    matched_plans.append({
                        'source_type': '발주계획',
                        'title': biz_nm,
                        'notice_instt': item.findtext('orderInsttNm') or '-',
                        'demand_instt': '-',
                        'raw_price': price_val,
                        'price': f"{int(price_val):,}원",
                        'notice_dt': format_datetime_str(item.findtext('nticeDt', '-')),
                        'expl_info': f"{item.findtext('orderYear', '')}년 {item.findtext('orderMnth', '')}월",
                        'reg_close_dt': '-',
                        'bid_close_dt': '-',
                        'open_dt': '-',
                        'url': item.findtext('orderPlanDtlUrl', ''),
                        'attachments': [],
                        'chg_rsn': ''
                    })

    # 3. 사전규격 API
    for category_name, base_url in [("용역", "http://apis.data.go.kr/1230000/ao/HrcspSsstndrdInfoService/getPublicPrcureThngInfoServc"), ("공사", "http://apis.data.go.kr/1230000/ao/HrcspSsstndrdInfoService/getPublicPrcureThngInfoCnstwk")]:
        for inqry_div in ["1", "2"]:
            root = fetch_api_data(base_url, {"inqryDiv": inqry_div, "inqryBgnDt": inqryBgnDate12, "inqryEndDt": today_str12, "numOfRows": "500"})
            if root is not None:
                for item in root.findall(".//item"):
                    product_nm = item.findtext('prdctClsfcNoNm') or item.findtext('ntceNm') or '-'
                    if any(ex in product_nm for ex in EXCLUDE_KEYWORDS): continue
                    if not (any(k in product_nm for k in P1_KEYWORDS) or any(k in product_nm for k in P2_KEYWORDS)): continue

                    assign_budget = item.findtext('asignBdgtAmt') or '0'
                    price_val = float(assign_budget.replace(',', '').strip()) if assign_budget.replace(',', '').strip().isdigit() else 0

                    if (any(k in product_nm for k in P1_KEYWORDS) and price_val >= 500000000) or any(k in product_nm for k in P2_KEYWORDS):
                        matched_specs.append({
                            'source_type': '사전규격',
                            'title': product_nm,
                            'notice_instt': item.findtext('orderInsttNm') or '-',
                            'demand_instt': item.findtext('rlDminsttNm') or '-',
                            'raw_price': price_val,
                            'price': f"{int(price_val):,}원",
                            'notice_dt': format_datetime_str(item.findtext('rcptDt') or '-'),
                            'expl_info': '-',
                            'reg_close_dt': '-',
                            'bid_close_dt': format_datetime_str(item.findtext('opninRgstClseDt', '-')),
                            'open_dt': '-',
                            'url': '',
                            'attachments': extract_attachments(item),
                            'chg_rsn': ''
                        })

    all_matched_items = matched_bids + matched_plans + matched_specs

    # 웹 대시보드 연동 파일 생성 및 푸시 수행
    save_web_dashboard_json(all_matched_items)

    sent_notices = load_sent_notices()
    new_matched_items = [item for item in all_matched_items if get_item_key(item) not in sent_notices]
    for item in new_matched_items: sent_notices.add(get_item_key(item))

    if new_matched_items:
        save_sent_notices(sent_notices)
    else:
        send_telegram_single("<b>[나라장터 알림]</b>\n\n신규 공고 없음")

if __name__ == "__main__":
    check_bids()

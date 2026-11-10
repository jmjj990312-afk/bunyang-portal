"""청약홈(공공데이터포털) 분양정보를 받아 data/cheongyak.json 으로 저장한다.

환경변수 APPLYHOME_KEY 에 공공데이터포털 '한국부동산원_청약홈 분양정보 조회 서비스'
일반 인증키(Decoding)를 넣고 실행한다. 깃허브 Actions 가 매일 자동 실행한다.
"""
import json, os, sys, urllib.parse, urllib.request
from datetime import datetime, timedelta, timezone

KEY = os.environ.get("APPLYHOME_KEY", "").strip()
if not KEY:
    sys.exit("APPLYHOME_KEY 가 없습니다.")

BASE = "https://api.odcloud.kr/api/ApplyhomeInfoDetailSvc/v1/"
KST = timezone(timedelta(hours=9))
today = datetime.now(KST).date()
since = (today - timedelta(days=3)).isoformat()

# (엔드포인트, 표시 종류 기본값)
APIS = [
    ("getAPTLttotPblancDetail", None),            # 아파트 (민영/국민)
    ("getUrbtyOfctlLttotPblancDetail", "오피스텔·도시형"),
    ("getRemndrLttotPblancDetail", "무순위·잔여세대"),
]


def fetch(op):
    rows, page = [], 1
    while True:
        q = urllib.parse.urlencode({
            "page": page, "perPage": 200, "serviceKey": KEY,
            "cond[RCEPT_ENDDE::GTE]": since,
        })
        with urllib.request.urlopen(f"{BASE}{op}?{q}", timeout=30) as r:
            d = json.load(r)
        rows += d.get("data", [])
        if page * 200 >= d.get("matchCount", 0):
            return rows
        page += 1


def pick(row, *keys):
    for k in keys:
        if row.get(k):
            return str(row[k]).strip()
    return ""


items = []
for op, kind in APIS:
    try:
        for r in fetch(op):
            start = pick(r, "RCEPT_BGNDE", "SUBSCRPT_RCEPT_BGNDE")
            end = pick(r, "RCEPT_ENDDE", "SUBSCRPT_RCEPT_ENDDE")
            if not start or not end:
                continue
            units = pick(r, "TOT_SUPLY_HSHLDCO")
            items.append({
                "name": pick(r, "HOUSE_NM"),
                "region": pick(r, "SUBSCRPT_AREA_CODE_NM") or pick(r, "HSSPLY_ADRES")[:2],
                "kind": kind or pick(r, "HOUSE_DTL_SECD_NM", "HOUSE_SECD_NM") or "아파트",
                "start": start[:10], "end": end[:10],
                "units": int(units) if units.isdigit() else None,
                "url": pick(r, "PBLANC_URL"),
            })
    except Exception as e:  # 한 종류가 실패해도 나머지는 저장
        print(op, "실패:", e)

seen, uniq = set(), []
for it in sorted(items, key=lambda x: (x["start"], x["name"])):
    k = (it["name"], it["start"])
    if k not in seen:
        seen.add(k)
        uniq.append(it)

out = os.path.join(os.path.dirname(__file__), "..", "data", "cheongyak.json")
with open(out, "w", encoding="utf-8") as f:
    json.dump({"updated": datetime.now(KST).isoformat(timespec="minutes"), "items": uniq},
              f, ensure_ascii=False, indent=1)
print(len(uniq), "건 저장")

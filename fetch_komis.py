# -*- coding: utf-8 -*-
"""희소금속 수집 - KOMIS 한국자원정보서비스 (월별, 최근 3년).

로그인 불필요. getChartData(POST) 로 월별 시계열을 받아 data/<id>.csv (date,value) 누적.
config 의 src=="komis" 아이템(mcode/crtr/spec)을 사용한다.
"""
import csv
import json
import os
import sys
import http.cookiejar
import urllib.request
import urllib.parse
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
sys.path.insert(0, HERE)
from config import ITEMS  # noqa: E402

PAGE = "https://www.komis.or.kr/Komis/RsrcPrice/MinorMetals"
AJAX = "https://www.komis.or.kr/Komis/RsrcPrice/ajax/getChartData"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")


def _path(item_id):
    return os.path.join(DATA, item_id + ".csv")


def _write(item_id, pairs):
    """pairs: [(date,value), ...] 정렬 후 덮어쓰기."""
    with open(_path(item_id), "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["date", "value"])
        for d, v in sorted(pairs):
            w.writerow([d, v])


def _window():
    """현재월 기준 과거 3년 (YYYYMM, YYYYMM)."""
    t = date.today()
    end = f"{t.year}{t.month:02d}"
    start = f"{t.year - 3}{t.month:02d}"
    return start, end


def fetch_all(start=None, end=None):
    """모든 komis 아이템을 '최근부터 과거 3년' 일별로 받아 CSV 덮어쓰기. {id: n} 반환.
    Playwright 불필요 — stdlib(urllib)로 쿠키 받고 POST."""
    if not start or not end:
        start, end = _window()
    komis = [it for it in ITEMS if it.get("src") == "komis"]
    result = {}
    cj = http.cookiejar.CookieJar()
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    op.addheaders = [("User-Agent", UA)]
    op.open(PAGE, timeout=30).read()                  # 세션/쿠키 확보
    for it in komis:
        form = urllib.parse.urlencode({
            "mnrkndUnqRadioCd": it["sym"], "srchMnrkndUnqCd": it["sym"],
            "srchPrcCrtr": it["crtr"], "spcfct": it["spec"],
            "srchAvgOpt": "DAY", "srchField": "month",     # 일별
            "srchStartDate": start, "srchEndDate": end,   # YYYYMM (대시 없음!)
            "srchCompareMnrkndUnqCd": "", "srchComparePrcCrtr": "[선택]",
            "lmeInvt": "Y", "HP000": "HP002",
        }).encode()
        req = urllib.request.Request(AJAX, data=form, headers={
            "User-Agent": UA, "X-Requested-With": "XMLHttpRequest", "Referer": PAGE})
        try:
            d = json.loads(op.open(req, timeout=30).read().decode("utf-8", "ignore"))["data"]
            xax, ser = d["xaxis"], d["series"][0]["data"]
            pairs = [(x.replace(".", "-"), v) for x, v in zip(xax, ser)
                     if v not in (None, "", "-")]
            _write(it["id"], pairs)                    # 최신 3년 창으로 덮어쓰기
            result[it["id"]] = len(pairs)
        except Exception as e:
            result[it["id"]] = f"ERR {type(e).__name__}"
    return result


if __name__ == "__main__":
    os.makedirs(DATA, exist_ok=True)
    print("KOMIS 희소금속 수집:", fetch_all())
    try:
        import build
        build.build()
    except Exception as e:
        print("build skip:", e)

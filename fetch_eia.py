# -*- coding: utf-8 -*-
"""미국 주간 소매 휘발유 가격 수집 - EIA (Energy Information Administration).

Weekly U.S. All Grades All Formulations Retail Gasoline Prices (EMM_EPM0_PTE_NUS_DPG).
API 키 불필요 — dnav 페이지의 데이터 표를 stdlib(urllib)로 파싱한다.
'갱신 기준 최근 3년'만 남겨 data/eia_gas.csv (date,value) 로 덮어쓴다.
"""
import csv
import os
import re
import urllib.request
from datetime import date, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
URL = ("https://www.eia.gov/dnav/pet/hist/LeafHandler.ashx"
       "?n=PET&s=EMM_EPM0_PTE_NUS_DPG&f=W")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
YEARS = 3  # 최근 3년


def _parse(html):
    """dnav 표에서 {YYYY-MM-DD: value} 추출. 행 앞의 'YYYY-Mon' 마커로 연도를 잡는다."""
    txt = re.sub(r"<[^>]+>", " ", html).replace("&nbsp;", " ")
    txt = re.sub(r"\s+", " ", txt)
    out, year = {}, None
    pat = (r"(\d{4})-(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)"
           r"|(\d{2})/(\d{2})\s+(\d+\.\d+)")
    for m in re.finditer(pat, txt):
        if m.group(1):
            year = int(m.group(1))
        elif year:
            mm, dd, val = int(m.group(2)), int(m.group(3)), m.group(4)
            out[f"{year:04d}-{mm:02d}-{dd:02d}"] = val
    return out


def fetch():
    """최근 3년 주간 데이터를 CSV로 덮어쓰고 (행수, 최신일, 최신값) 반환."""
    os.makedirs(DATA, exist_ok=True)
    req = urllib.request.Request(URL, headers={"User-Agent": UA})
    html = urllib.request.urlopen(req, timeout=40).read().decode("utf-8", "ignore")
    series = _parse(html)
    if not series:
        raise ValueError("EIA 표 파싱 실패")
    cutoff = (date.today() - timedelta(days=365 * YEARS + 1)).isoformat()
    pairs = sorted((d, v) for d, v in series.items() if d >= cutoff)
    with open(os.path.join(DATA, "eia_gas.csv"), "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["date", "value"])
        w.writerows(pairs)
    return len(pairs), (pairs[-1] if pairs else ("", ""))


if __name__ == "__main__":
    n, last = fetch()
    print(f"EIA 주간 휘발유: {n}주 (최신 {last[0]} = ${last[1]}/gal)")

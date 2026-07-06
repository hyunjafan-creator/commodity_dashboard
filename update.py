# -*- coding: utf-8 -*-
"""원자재 데이터 수집기.

각 아이템을 소스별로 수집해 data/{id}.csv 에 누적 저장한다.
- OHLC(sina/yahoo): 전체 일봉 히스토리를 받아 날짜 기준 병합.
- snapshot(dram/snap): 당일값을 한 행씩 누적(같은 날 재실행 시 갱신).
표준 라이브러리만 사용한다.
"""
import csv
import json
import os
import re
import sys
import urllib.request
from datetime import datetime, date, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
os.makedirs(DATA, exist_ok=True)

sys.path.insert(0, HERE)
from config import ITEMS  # noqa: E402

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"


def _get(url, decode="utf-8", referer=None):
    headers = {"User-Agent": UA}
    if referer:
        headers["Referer"] = referer
    req = urllib.request.Request(url, headers=headers)
    return urllib.request.urlopen(req, timeout=30).read().decode(decode, "ignore")


# ── 저장 헬퍼 ───────────────────────────────────────────────────
def _path(item_id):
    return os.path.join(DATA, item_id + ".csv")


def read_rows(item_id):
    p = _path(item_id)
    if not os.path.exists(p):
        return []
    with open(p, "r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def write_rows(item_id, rows, fields):
    p = _path(item_id)
    with open(p, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow(r)


def merge_ohlc(item_id, fetched):
    """fetched: list of dict(date,open,high,low,close). 날짜 기준 병합."""
    by_date = {r["date"]: r for r in read_rows(item_id)}
    for r in fetched:
        by_date[r["date"]] = r
    rows = [by_date[d] for d in sorted(by_date)]
    write_rows(item_id, rows, ["date", "open", "high", "low", "close"])
    return len(rows)


def append_snapshot(item_id, value, fields=("date", "value")):
    """오늘 날짜 한 행 누적. 같은 날 재실행 시 갱신."""
    today = date.today().isoformat()
    by_date = {r["date"]: r for r in read_rows(item_id)}
    by_date[today] = {"date": today, "value": value}
    rows = [by_date[d] for d in sorted(by_date)]
    write_rows(item_id, rows, list(fields))
    return len(rows)


def append_snapshot3(item_id, high, low, avg):
    """오늘 날짜에 High/Low/Avg 한 행 누적(date,high,low,avg)."""
    today = date.today().isoformat()
    by_date = {r["date"]: r for r in read_rows(item_id)}
    by_date[today] = {"date": today, "high": high, "low": low, "avg": avg}
    rows = [by_date[d] for d in sorted(by_date)]
    write_rows(item_id, rows, ["date", "high", "low", "avg"])
    return len(rows)


# ── 소스별 수집기 ───────────────────────────────────────────────
def fetch_sina(sym):
    url = ("https://stock2.finance.sina.com.cn/futures/api/jsonp.php/var%20t=/"
           "InnerFuturesNewService.getDailyKLine?symbol=" + sym)
    raw = _get(url, decode="gbk", referer="https://finance.sina.com.cn/")
    m = re.search(r"=\((\[.*\])\);", raw, re.S)
    if not m:
        raise ValueError("Sina 응답 파싱 실패")
    arr = json.loads(m.group(1))
    out = []
    for d in arr:
        out.append(dict(date=d["d"], open=d["o"], high=d["h"], low=d["l"], close=d["c"]))
    return out


def fetch_yahoo(sym):
    url = ("https://query1.finance.yahoo.com/v8/finance/chart/" + urllib.parse.quote(sym)
           + "?interval=1d&range=2y")
    j = json.loads(_get(url))
    res = j["chart"]["result"]
    if not res:
        raise ValueError("Yahoo 빈 응답")
    r = res[0]
    ts = r["timestamp"]
    q = r["indicators"]["quote"][0]
    out = []
    for i, t in enumerate(ts):
        o, h, l, c = q["open"][i], q["high"][i], q["low"][i], q["close"][i]
        if c is None:
            continue
        d = datetime.fromtimestamp(t, timezone.utc).date().isoformat()
        out.append(dict(date=d,
                        open=round(o, 4) if o else c,
                        high=round(h, 4) if h else c,
                        low=round(l, 4) if l else c,
                        close=round(c, 4)))
    return out


def fetch_dram():
    """DRAMeXchange 홈페이지에서 제품별 현물가 파싱. 당일 스냅샷 누적(long format)."""
    html = _get("https://www.dramexchange.com/")
    # 행(tr) 단위로 제품명(앵커) + tab_tr_gray 가격셀(마지막=대표 평균가) 추출.
    # DDR3/DDR4/DDR5·GDDR·LPDDR·TLC/MLC/SLC 모두 포함.
    pat_name = re.compile(r'<a[^>]*>(.*?)</a>', re.S)
    pat_gray = re.compile(r'tab_tr_gray[^>]*>\s*([0-9]+\.[0-9]+)\s*<')
    types = re.compile(r'(DDR3|DDR4|DDR5|GDDR\d?|LPDDR|TLC|MLC|SLC)', re.I)
    today = date.today().isoformat()
    found = {}
    for r in re.split(r"<tr", html):
        nm = pat_name.search(r)
        if not nm:
            continue
        name = re.sub(r"<[^>]+>", "", nm.group(1))
        name = re.sub(r"\s+", " ", name).strip()
        if not types.search(name) or "Spot Price" in name:
            continue
        vals = pat_gray.findall(r)
        if vals:
            found[name] = vals[-1]  # 대표값(평균) = 행의 마지막 gray 셀
    # long format 누적: data/dram.csv (date,product,value)
    rows = read_rows("dram")
    keyed = {(r["date"], r["product"]): r for r in rows}
    for name, price in found.items():
        keyed[(today, name)] = {"date": today, "product": name, "value": price}
    allrows = [keyed[k] for k in sorted(keyed)]
    write_rows("dram", allrows, ["date", "product", "value"])
    return len(found)


import urllib.parse  # noqa: E402  (fetch_yahoo 에서 사용)


def main():
    print(f"=== 수집 시작 {datetime.now().isoformat(timespec='seconds')} ===")
    ok, fail = 0, 0
    dram_state = {"done": False, "total": 0}  # DRAM 수집 1회만
    # 반도체 DB(semiconductor_data.db) 히스토리 백필 (idempotent)
    if any(it.get("src") == "dram" for it in ITEMS):
        try:
            import import_db
            n = import_db.import_spot()
            print(f"  [DB ] semiconductor_data.db 백필 +{n} rows")
        except Exception as e:
            print(f"  [ERR] DB 백필 {type(e).__name__}: {e}")
    # KOMIS 희소금속은 한 번에 배치 수집(브라우저 1회)
    komis_res = {}
    if any(it.get("src") == "komis" for it in ITEMS):
        try:
            import fetch_komis
            komis_res = fetch_komis.fetch_all()
        except Exception as e:
            print(f"  [ERR] komis batch {type(e).__name__}: {e}")
    for it in ITEMS:
        try:
            if it["src"] == "komis":
                n = komis_res.get(it["id"])
                if isinstance(n, int):
                    print(f"  [OK ] {it['id']:9} {it['name'][:22]:22} {n} days")
                    ok += 1
                else:
                    print(f"  [ERR] {it['id']:9} {it['name'][:22]:22} {n}")
                    fail += 1
                continue
            if it["src"] == "sina":
                n = merge_ohlc(it["id"], fetch_sina(it["sym"]))
                print(f"  [OK ] {it['id']:9} {it['name'][:22]:22} {n} rows")
            elif it["src"] == "yahoo":
                n = merge_ohlc(it["id"], fetch_yahoo(it["sym"]))
                print(f"  [OK ] {it['id']:9} {it['name'][:22]:22} {n} rows")
            elif it["src"] == "dram":
                if not dram_state["done"]:
                    dram_state["total"] = fetch_dram()
                    dram_state["done"] = True
                today = date.today().isoformat()
                cnt = sum(1 for r in read_rows("dram")
                          if r["date"] == today and re.search(it["match"], r["product"]))
                print(f"  [OK ] {it['id']:9} {it['name'][:22]:22} {cnt} products (snapshot)")
            elif it["src"] == "snap":
                if it["id"] == "topcon":
                    try:
                        import fetch_topcon
                        d = fetch_topcon.fetch()
                    except Exception as e:
                        d = None
                        print(f"  [ERR] topcon fetch {type(e).__name__}: {e}")
                    if d and d.get("avg"):
                        n = append_snapshot3("topcon", d["high"], d["low"], d["avg"])
                        print(f"  [OK ] {it['id']:9} {it['name'][:22]:22} H{d['high']}/L{d['low']}/A{d['avg']} ({n} rows)")
                        ok += 1
                    else:
                        if not os.path.exists(_path(it["id"])):
                            write_rows(it["id"], [], ["date", "value"])
                        print(f"  [SKIP] {it['id']:9} {it['name'][:22]:22} (세션 만료? login 재실행 필요)")
                    continue
                if it["id"] == "lipf6":
                    # 저장된 metal.com 세션으로 헤드리스 수집(재로그인 불필요)
                    try:
                        import fetch_lipf6
                        d = fetch_lipf6.fetch()
                    except Exception as e:
                        d = None
                        print(f"  [ERR] lipf6 fetch {type(e).__name__}: {e}")
                    if d and d.get("avg"):
                        n = append_snapshot("lipf6", d["avg"])
                        print(f"  [OK ] {it['id']:9} {it['name'][:22]:22} {d['avg']} ({n} rows)")
                        ok += 1
                    else:
                        if not os.path.exists(_path(it["id"])):
                            write_rows(it["id"], [], ["date", "value"])
                        print(f"  [SKIP] {it['id']:9} {it['name'][:22]:22} (세션 만료? login 재실행 필요)")
                    continue
                # 기타 로그인/무료없음 소스: 자동수집 불가. 파일만 보장.
                if not os.path.exists(_path(it["id"])):
                    write_rows(it["id"], [], ["date", "value"])
                print(f"  [SKIP] {it['id']:9} {it['name'][:22]:22} (수동/브라우저 수집 필요)")
                continue
            ok += 1
        except Exception as e:
            fail += 1
            print(f"  [ERR] {it['id']:9} {it['name'][:22]:22} {type(e).__name__}: {e}")
    print(f"=== 수집 완료: 성공 {ok} / 실패 {fail} ===")


if __name__ == "__main__":
    main()

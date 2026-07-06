# -*- coding: utf-8 -*-
# =====================================================================
#  원자재 대시보드 (Google Colab 단일 스크립트) - 최종본
#  - '원자재 대시보드.html' 파일을 생성
#  - 평일 오전 8시 / 12시(KST) 자동 실행 루프 포함
#
#  [Colab 사용법]
#   1) 이 코드를 셀에 통째로 붙여넣고 실행.
#   2) 기본은 requests 만으로 35개 항목 수집(Sina/Yahoo/DRAMeXchange/KOMIS).
#   3) (선택) 반도체 과거 히스토리(2022~)를 붙이려면 'semiconductor_data.db' 를
#      BASE 폴더에 업로드. 있으면 DRAM 차트가 DB 일별 히스토리로 채워짐(없으면 당일 누적만).
#   4) (선택) TOPCon·LiPF6 까지 원하면 맨 위 셀에서 한 번:
#         !pip -q install playwright && playwright install chromium
#      LiPF6 는 로그인 세션 파일(.pw_state.json)을 BASE 폴더에 올려야 함.
#   5) (선택) 결과를 영구 보관하려면 USE_DRIVE=True 로.
#
#  ※ Colab 세션은 일정 시간 후 끊깁니다. 스케줄 루프는 '셀이 켜져 있는 동안'만
#    도는 점 참고. 완전 무인 운영은 GitHub Actions/클라우드 권장.
# =====================================================================
import os, sys, csv, json, re, time, sqlite3, subprocess
from datetime import datetime, date, timezone, timedelta

# ---------- 환경 ----------
USE_DRIVE = False          # True 면 구글 드라이브에 저장(영구 보관)
if USE_DRIVE:
    from google.colab import drive
    drive.mount('/content/drive')
    BASE = "/content/drive/MyDrive/원자재대시보드"
else:
    BASE = "/content/원자재대시보드"
DATA = os.path.join(BASE, "data")
os.makedirs(DATA, exist_ok=True)
OUT_HTML = os.path.join(BASE, "원자재 대시보드.html")
STATE = os.path.join(BASE, ".pw_state.json")           # LiPF6 로그인 세션(선택)
DB_PATH = os.path.join(BASE, "semiconductor_data.db")  # 반도체 과거 히스토리(선택)
WINDOW = 200                                           # 선물 차트 표시 영업일
KST = timezone(timedelta(hours=9))
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"

# requests (Colab 기본 탑재) — 없으면 설치
try:
    import requests
except ImportError:
    subprocess.run([sys.executable, "-m", "pip", "install", "-q", "requests"])
    import requests

# Playwright(선택): 있으면 TOPCon/LiPF6 활성화
try:
    from playwright.sync_api import sync_playwright
    HAS_PW = True
except Exception:
    HAS_PW = False

SESS = requests.Session()
SESS.headers.update({"User-Agent": UA})

# =====================================================================
#  설정: 전체 아이템
# =====================================================================
ITEMS = [
    # 1. 반도체 (DRAMeXchange 스냅샷 + semiconductor_data.db 히스토리, 타입별)
    dict(id="dram_ddr4", cat="반도체", name="DDR4 현물가", src="dram", match=r"^DDR4",
         unit="USD", source="DRAMeXchange · DRAM Spot (+DB 히스토리)"),
    dict(id="dram_ddr5", cat="반도체", name="DDR5 현물가", src="dram", match=r"^DDR5",
         unit="USD", source="DRAMeXchange · DRAM Spot (+DB 히스토리)"),
    dict(id="dram_mlc", cat="반도체", name="MLC NAND 현물가", src="dram", match=r"^MLC",
         unit="USD", source="DRAMeXchange · NAND Flash Spot (+DB 히스토리)"),
    dict(id="dram_slc", cat="반도체", name="SLC NAND 현물가", src="dram", match=r"^SLC",
         unit="USD", source="DRAMeXchange · NAND Flash Spot (+DB 히스토리)"),
    dict(id="dram_tlc", cat="반도체", name="TLC NAND 현물가", src="dram", match=r"TLC",
         unit="USD", source="DRAMeXchange · NAND Flash Spot"),
    dict(id="dram_gddr", cat="반도체", name="GDDR 현물가", src="dram", match=r"^GDDR",
         unit="USD", source="DRAMeXchange · GDDR Spot"),
    # 2. 배터리
    dict(id="lc0", cat="배터리", name="탄산리튬 (Lithium Carbonate)", src="sina", sym="LC0",
         unit="CNY/톤", source="Sina Finance · GFEX 탄산리튬 LC0"),
    dict(id="lipf6", cat="배터리", name="육불화인산리튬 LiPF6", src="lipf6",
         unit="USD/톤", source="Shanghai Metals Market (metal.com) · 로그인 세션"),
    dict(id="copper", cat="배터리", name="구리 (Copper)", src="yahoo", sym="HG=F",
         unit="USD/lb", source="Yahoo Finance · COMEX HG=F"),
    dict(id="alu", cat="배터리", name="알루미늄 (Aluminum)", src="yahoo", sym="ALI=F",
         unit="USD/톤", source="Yahoo Finance · COMEX ALI=F"),
    dict(id="ni_bat", cat="배터리", name="니켈 (Nickel)", src="sina", sym="NI0",
         unit="CNY/톤", source="Sina Finance · SHFE 니켈 NI0"),
    # 3. 에너지
    dict(id="wti", cat="에너지", name="WTI 원유", src="yahoo", sym="CL=F",
         unit="USD/배럴", source="Yahoo Finance · NYMEX CL=F"),
    dict(id="natgas", cat="에너지", name="천연가스 (Natural Gas)", src="yahoo", sym="NG=F",
         unit="USD/MMBtu", source="Yahoo Finance · NYMEX NG=F"),
    dict(id="rbob", cat="에너지", name="가솔린 RBOB", src="yahoo", sym="RB=F",
         unit="USD/갤런", source="Yahoo Finance · NYMEX RB=F"),
    dict(id="jm0", cat="에너지", name="코크스(코킹콜)", src="sina", sym="JM0",
         unit="CNY/톤", source="Sina Finance · DCE 코킹콜 JM0"),
    # 4. 태양광
    dict(id="ps0", cat="태양광", name="폴리실리콘 (Polysilicon)", src="sina", sym="PS0",
         unit="CNY/톤", source="Sina Finance · GFEX 폴리실리콘 PS0"),
    dict(id="topcon", cat="태양광", name="미국 TOPCon 모듈 (US assembled, DDP)", src="topcon",
         unit="USD/W", source="InfoLink PV Spot Price"),
    # 5. 화학/철강
    dict(id="sh0", cat="화학/철강", name="가성소다 (Caustic Soda)", src="sina", sym="SH0",
         unit="CNY/톤", source="Sina Finance · 가성소다 SH0"),
    dict(id="px0", cat="화학/철강", name="파라자일렌 PX", src="sina", sym="PX0",
         unit="CNY/톤", source="Sina Finance · 파라자일렌 PX0"),
    dict(id="v0", cat="화학/철강", name="PVC", src="sina", sym="V0",
         unit="CNY/톤", source="Sina Finance · DCE PVC V0"),
    dict(id="pp0", cat="화학/철강", name="PP (폴리프로필렌)", src="sina", sym="PP0",
         unit="CNY/톤", source="Sina Finance · DCE PP0"),
    dict(id="br0", cat="화학/철강", name="부타디엔 고무 (BR)", src="sina", sym="BR0",
         unit="CNY/톤", source="Sina Finance · 부타디엔고무 BR0"),
    dict(id="i0", cat="화학/철강", name="철광석 (Iron Ore)", src="sina", sym="I0",
         unit="CNY/톤", source="Sina Finance · DCE 철광석 I0"),
    dict(id="rb0", cat="화학/철강", name="철근 (Rebar)", src="sina", sym="RB0",
         unit="CNY/톤", source="Sina Finance · SHFE 철근 RB0"),
    dict(id="ss0", cat="화학/철강", name="스테인리스 스틸", src="sina", sym="SS0",
         unit="CNY/톤", source="Sina Finance · SHFE 스테인리스 SS0"),
    dict(id="hc0", cat="화학/철강", name="열연강판 (HRC)", src="sina", sym="HC0",
         unit="CNY/톤", source="Sina Finance · SHFE 열연 HC0"),
    dict(id="ad0", cat="화학/철강", name="주조 알루미늄 합금", src="sina", sym="AD0",
         unit="CNY/톤", source="Sina Finance · SHFE 알루미늄합금 AD0"),
    dict(id="sn0", cat="화학/철강", name="주석 (Tin)", src="sina", sym="SN0",
         unit="CNY/톤", source="Sina Finance · SHFE 주석 SN0"),
    dict(id="ni0", cat="화학/철강", name="니켈 (Nickel, SHFE)", src="sina", sym="NI0",
         unit="CNY/톤", source="Sina Finance · SHFE 니켈 NI0"),
    # 6. 식료품
    dict(id="p0", cat="식료품", name="팜유 (Palm Oil)", src="sina", sym="P0",
         unit="CNY/톤", source="Sina Finance · DCE 팜유 P0"),
    dict(id="wheat", cat="식료품", name="미국 소맥 (Wheat)", src="yahoo", sym="ZW=F",
         unit="USc/부셸", source="Yahoo Finance · CBOT ZW=F"),
    dict(id="corn", cat="식료품", name="미국 옥수수 (Corn)", src="yahoo", sym="ZC=F",
         unit="USc/부셸", source="Yahoo Finance · CBOT ZC=F"),
    dict(id="soybean", cat="식료품", name="미국 대두 (Soybeans)", src="yahoo", sym="ZS=F",
         unit="USc/부셸", source="Yahoo Finance · CBOT ZS=F"),
    # 7. 희소금속 (KOMIS · 일별 · 최근 3년)
    dict(id="komis_w", cat="희소금속", name="텅스텐 (Ferro-tungsten 75%)", src="komis",
         sym="MNRL0018", crtr="796", spec="75", unit="USD/kg",
         source="KOMIS · Ferro-tungsten 75%min FOB China"),
    dict(id="komis_nd", cat="희소금속", name="네오디뮴 (Neodymium Oxide)", src="komis",
         sym="MNRL1001", crtr="757", spec="99.5", unit="USD/kg",
         source="KOMIS · Neodymium Oxide 99.5%min FOB China"),
    dict(id="komis_dy", cat="희소금속", name="디스프로슘 (Dysprosium Oxide)", src="komis",
         sym="MNRL1004", crtr="803", spec="99.5", unit="USD/kg",
         source="KOMIS · Dysprosium Oxide 99.5%min FOB China"),
    dict(id="komis_ti", cat="희소금속", name="티타늄 (Ferro-titanium 70%)", src="komis",
         sym="MNRL0017", crtr="761", spec="70", unit="USD/kg",
         source="KOMIS · Ferro-titanium 70%min Rotterdam"),
    dict(id="komis_mo", cat="희소금속", name="몰리브덴 (Ferro-molybdenum 60%)", src="komis",
         sym="MNRL0012", crtr="763", spec="60", unit="USD/mt",
         source="KOMIS · Ferro-molybdenum 60%min EXW China"),
]
CATEGORIES = ["반도체", "배터리", "에너지", "태양광", "화학/철강", "식료품", "희소금속"]

# DB(semiconductor_data.db) 제품명 → 대시보드(스냅샷) 제품명 매핑 (연속 시계열로 잇기)
DB_NAME_MAP = {
    "DDR4_16Gb_(2Gx8)_3200": "DDR4 16Gb (2Gx8) 3200",
    "DDR4_16Gb_(2Gx8)_eTT": "DDR4 16Gb (2Gx8) eTT",
    "DDR4_8Gb_(1Gx8)_3200": "DDR4 8Gb (1Gx8) 3200",
    "DDR4_8Gb_(1Gx8)_eTT_": "DDR4 8Gb (1Gx8) eTT",
    "DDR5_16Gb_(2Gx8)_4800_5600": "DDR5 16Gb (2Gx8) 4800/5600",
    "DDR5_16Gb_(2Gx8)_eTT": "DDR5 16Gb (2Gx8) eTT",
    "MLC_32Gb_4GBx8": "MLC 32Gb 4GBx8",
    "MLC_64Gb_8GBx8": "MLC 64Gb 8GBx8",
    "SLC_1Gb_128MBx8": "SLC 1Gb 128MBx8",
    "SLC_2Gb_256MBx8": "SLC 2Gb 256MBx8",
}

# =====================================================================
#  저장 헬퍼 (CSV)
# =====================================================================
def _p(id_): return os.path.join(DATA, id_ + ".csv")

def read_rows(id_):
    if not os.path.exists(_p(id_)): return []
    with open(_p(id_), encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))

def write_rows(id_, rows, fields):
    with open(_p(id_), "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader()
        for r in rows: w.writerow(r)

def merge_ohlc(id_, fetched):
    by = {r["date"]: r for r in read_rows(id_)}
    for r in fetched: by[r["date"]] = r
    rows = [by[d] for d in sorted(by)]
    write_rows(id_, rows, ["date", "open", "high", "low", "close"]); return len(rows)

def write_pairs(id_, pairs):                         # KOMIS 덮어쓰기
    with open(_p(id_), "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f); w.writerow(["date", "value"])
        for d, v in sorted(pairs): w.writerow([d, v])

def append_snapshot(id_, value):                     # LiPF6/단일 스냅샷
    today = datetime.now(KST).date().isoformat()
    by = {r["date"]: r for r in read_rows(id_)}
    by[today] = {"date": today, "value": value}
    write_rows(id_, [by[d] for d in sorted(by)], ["date", "value"]); return len(by)

def append_snapshot3(id_, high, low, avg):           # TOPCon High/Low/Avg
    today = datetime.now(KST).date().isoformat()
    by = {r["date"]: r for r in read_rows(id_)}
    by[today] = {"date": today, "high": high, "low": low, "avg": avg}
    write_rows(id_, [by[d] for d in sorted(by)], ["date", "high", "low", "avg"]); return len(by)

def db_backfill():
    """semiconductor_data.db(있으면) 일별 spot 히스토리를 dram.csv 에 병합. 기존값 보존."""
    if not os.path.exists(DB_PATH): return 0
    con = sqlite3.connect(DB_PATH)
    rows = con.execute(
        "SELECT p.product_name,o.observed_date,o.average FROM price_observations o "
        "JOIN products p ON p.product_id=o.product_id "
        "WHERE p.market_type='spot' AND p.frequency='daily' AND o.average IS NOT NULL").fetchall()
    con.close()
    keyed = {(r["date"], r["product"]): r["value"] for r in read_rows("dram")}
    added = 0
    for name, d, avg in rows:
        disp = DB_NAME_MAP.get(name)
        if disp and (d, disp) not in keyed:
            keyed[(d, disp)] = f"{avg:g}"; added += 1
    with open(_p("dram"), "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f); w.writerow(["date", "product", "value"])
        for d, prod in sorted(keyed): w.writerow([d, prod, keyed[(d, prod)]])
    return added

# =====================================================================
#  수집기
# =====================================================================
def fetch_sina(sym):
    url = ("https://stock2.finance.sina.com.cn/futures/api/jsonp.php/var%20t=/"
           "InnerFuturesNewService.getDailyKLine?symbol=" + sym)
    raw = SESS.get(url, headers={"Referer": "https://finance.sina.com.cn/"}, timeout=30).content.decode("gbk", "ignore")
    arr = json.loads(re.search(r"=\((\[.*\])\);", raw, re.S).group(1))
    return [dict(date=d["d"], open=d["o"], high=d["h"], low=d["l"], close=d["c"]) for d in arr]

def fetch_yahoo(sym):
    url = "https://query1.finance.yahoo.com/v8/finance/chart/" + sym.replace("=", "%3D") + "?interval=1d&range=2y"
    r = SESS.get(url, timeout=30).json()["chart"]["result"][0]
    ts, q = r["timestamp"], r["indicators"]["quote"][0]
    out = []
    for i, t in enumerate(ts):
        c = q["close"][i]
        if c is None: continue
        d = datetime.fromtimestamp(t, timezone.utc).date().isoformat()
        out.append(dict(date=d, open=round(q["open"][i] or c, 4), high=round(q["high"][i] or c, 4),
                        low=round(q["low"][i] or c, 4), close=round(c, 4)))
    return out

def fetch_dram():
    html = SESS.get("https://www.dramexchange.com/", timeout=30).text
    pat_name = re.compile(r"<a[^>]*>(.*?)</a>", re.S)
    pat_gray = re.compile(r"tab_tr_gray[^>]*>\s*([0-9]+\.[0-9]+)\s*<")
    types = re.compile(r"(DDR3|DDR4|DDR5|GDDR\d?|LPDDR|TLC|MLC|SLC)", re.I)
    today = datetime.now(KST).date().isoformat()
    found = {}
    for r in re.split(r"<tr", html):
        nm = pat_name.search(r)
        if not nm: continue
        name = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", nm.group(1))).strip()
        if not types.search(name) or "Spot Price" in name: continue
        vals = pat_gray.findall(r)
        if vals: found[name] = vals[-1]
    keyed = {(x["date"], x["product"]): x for x in read_rows("dram")}
    for name, price in found.items():
        keyed[(today, name)] = {"date": today, "product": name, "value": price}
    write_rows("dram", [keyed[k] for k in sorted(keyed)], ["date", "product", "value"])
    return len(found)

def fetch_komis():
    """KOMIS 희소금속 5종 일별 최근 3년(현재월 기준) 덮어쓰기."""
    t = datetime.now(KST)
    start, end = f"{t.year-3}{t.month:02d}", f"{t.year}{t.month:02d}"
    SESS.get("https://www.komis.or.kr/Komis/RsrcPrice/MinorMetals", timeout=30)
    res = {}
    for it in [x for x in ITEMS if x["src"] == "komis"]:
        form = {"mnrkndUnqRadioCd": it["sym"], "srchMnrkndUnqCd": it["sym"], "srchPrcCrtr": it["crtr"],
                "spcfct": it["spec"], "srchAvgOpt": "DAY", "srchField": "month",
                "srchStartDate": start, "srchEndDate": end, "srchCompareMnrkndUnqCd": "",
                "srchComparePrcCrtr": "[선택]", "lmeInvt": "Y", "HP000": "HP002"}
        r = SESS.post("https://www.komis.or.kr/Komis/RsrcPrice/ajax/getChartData", data=form,
                      headers={"X-Requested-With": "XMLHttpRequest",
                               "Referer": "https://www.komis.or.kr/Komis/RsrcPrice/MinorMetals"}, timeout=30)
        d = r.json()["data"]
        pairs = [(x.replace(".", "-"), v) for x, v in zip(d["xaxis"], d["series"][0]["data"]) if v not in (None, "", "-")]
        write_pairs(it["id"], pairs); res[it["id"]] = len(pairs)
    return res

def fetch_topcon():
    """InfoLink 'US assembled' High/Low/Avg (Playwright 필요)."""
    if not HAS_PW: return None
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True, args=["--no-sandbox"])
        pg = b.new_context(user_agent=UA).new_page()
        pg.goto("https://www.infolink-group.com/spot-price/", wait_until="networkidle", timeout=70000)
        for _ in range(8):
            body = pg.inner_text("body")
            i = body.find("US assembled")
            if i >= 0 and "\U0001f512" not in body[i:i+160]:
                m = re.findall(r"\d+\.\d{1,3}", body[i:i+160])
                if len(m) >= 3:
                    b.close(); return dict(high=m[0], low=m[1], avg=m[2])
            pg.wait_for_timeout(1500)
        b.close(); return None

def fetch_lipf6():
    """metal.com LiPF6 평균가 (Playwright + 저장된 로그인 세션 필요)."""
    if not HAS_PW or not os.path.exists(STATE): return None
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True, args=["--no-sandbox"])
        pg = b.new_context(user_agent=UA, storage_state=STATE).new_page()
        pg.goto("https://www.metal.com/Lithium/202110220001", wait_until="networkidle", timeout=70000)
        avg = None
        for _ in range(8):
            body = pg.inner_text("body")
            top = body[:body.find("Price Details") if "Price Details" in body else 1200]
            if "Sign in to view" not in top and "로그인하여 보기" not in top:
                m = re.search(r"(?:수집|Collect)\s+([\d,]+(?:\.\d+)?)", top)
                if m: avg = m.group(1).replace(",", ""); break
            pg.wait_for_timeout(1500)
        b.close(); return avg

# =====================================================================
#  대시보드 HTML 생성
# =====================================================================
def _f(x):
    try: return float(x)
    except: return None

def _chg(last, prev):
    if last is None or prev in (None, 0): return None
    return dict(abs=round(last-prev, 4), pct=round((last-prev)/prev*100, 2))

def build_payload():
    out = []
    for it in ITEMS:
        rows = read_rows(it["id"]); src = it["src"]
        p = dict(id=it["id"], name=it["name"], cat=it["cat"], unit=it["unit"], source=it["source"])
        if src == "dram":
            # 공통 dram.csv 에서 타입(match) 제품만 멀티라인. DB 연결 시 전체기간 표시.
            rows = [r for r in read_rows("dram") if re.search(it["match"], r["product"])]
            dates = sorted({r["date"] for r in rows}); dset = set(dates)
            prods = {}
            for r in rows:
                if r["date"] in dset: prods.setdefault(r["product"], {})[r["date"]] = _f(r["value"])
            if not prods: p.update(type="empty"); out.append(p); continue
            p.update(type="multiline", dates=dates,
                     series=[dict(name=n, data=[prods[n].get(d) for d in dates]) for n in sorted(prods)],
                     last_date=dates[-1] if dates else "", summary=f"{len(prods)}개 제품")
        elif src == "komis":
            if not rows: p.update(type="empty"); out.append(p); continue
            dates = [r["date"] for r in rows]; vals = [_f(r["value"]) for r in rows]
            p.update(type="line", dates=dates, values=vals, last=vals[-1], last_date=dates[-1],
                     change=_chg(vals[-1], vals[-2] if len(vals) > 1 else None))
        elif src == "topcon":
            if not rows: p.update(type="empty"); out.append(p); continue
            rows = rows[-WINDOW:]; dates = [r["date"] for r in rows]; last = rows[-1]
            p.update(type="multiline", dates=dates, last_date=dates[-1],
                     series=[dict(name="High", data=[_f(r.get("high")) for r in rows]),
                             dict(name="Low", data=[_f(r.get("low")) for r in rows]),
                             dict(name="Average", data=[_f(r.get("avg")) for r in rows])],
                     summary=f"평균 {last.get('avg')} (H {last.get('high')} / L {last.get('low')})")
        elif src == "lipf6":
            if not rows: p.update(type="empty"); out.append(p); continue
            rows = rows[-WINDOW:]; dates = [r["date"] for r in rows]; vals = [_f(r["value"]) for r in rows]
            p.update(type="line", dates=dates, values=vals, last=vals[-1], last_date=dates[-1],
                     change=_chg(vals[-1], vals[-2] if len(vals) > 1 else None))
        else:  # sina / yahoo : OHLC 캔들 (최근 WINDOW 영업일)
            if not rows: p.update(type="empty"); out.append(p); continue
            rows = rows[-WINDOW:]; dates = [r["date"] for r in rows]
            ohlc = [[_f(r["open"]), _f(r["close"]), _f(r["low"]), _f(r["high"])] for r in rows]
            closes = [_f(r["close"]) for r in rows]
            p.update(type="ohlc", dates=dates, ohlc=ohlc, last=closes[-1], last_date=dates[-1],
                     change=_chg(closes[-1], closes[-2] if len(closes) > 1 else None))
        out.append(p)
    return out

def _fmt(n):
    if n is None: return "-"
    return (f"{n:,.4f}".rstrip("0").rstrip(".")) if abs(n) < 10 else f"{n:,.2f}"

def _card(p):
    if p["type"] in ("ohlc", "line"):
        chg = p.get("change"); chip = ""
        if chg:
            up = chg["pct"] >= 0; cls = "chg-up" if up else "chg-dn"
            chip = (f'<span class="chip {cls}">{"▲" if up else "▼"} {abs(chg["pct"]):.2f}% '
                    f'({"+" if up else ""}{_fmt(chg["abs"])})</span>')
        head = f'<div class="val">{_fmt(p.get("last"))}<span class="unit"> {p["unit"]}</span>{chip}</div>'
        sub = f'기준일 {p.get("last_date","")}'
    elif p["type"] == "multiline":
        head = f'<div class="val" style="font-size:13px;color:#8b97a7">{p.get("summary","")}</div>'
        sub = f'기준일 {p.get("last_date","") or "수집 대기"}'
    else:
        head = '<div class="val" style="font-size:13px;color:#8b97a7">수집 대기</div>'; sub = ""
    body = ('<div class="empty">데이터 수집 대기 중</div>' if p["type"] == "empty"
            else f'<div class="chart" data-id="{p["id"]}"></div>')
    return (f'<div class="card"><div class="top"><div class="nm">{p["name"]}</div>{head}</div>'
            f'{body}<div class="src"><b>출처</b> {p["source"]} · {sub}</div></div>')

HTML = """<!DOCTYPE html><html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="refresh" content="1800"><title>원자재 대시보드</title>
<script src="https://cdn.jsdelivr.net/npm/echarts@5/dist/echarts.min.js"></script>
<style>
:root{--bg:#0f1419;--card:#1a212b;--bd:#2a333f;--tx:#e6edf3;--mut:#8b97a7;--up:#e5534b;--dn:#3fb950;--ac:#4493f8;}
*{box-sizing:border-box;} body{margin:0;background:var(--bg);color:var(--tx);font-family:'Segoe UI','Malgun Gothic',sans-serif;}
header{padding:20px 28px;border-bottom:1px solid var(--bd);position:sticky;top:0;background:var(--bg);z-index:10;}
header h1{margin:0 0 4px;font-size:20px;} header .meta{color:var(--mut);font-size:13px;}
nav{display:flex;gap:8px;flex-wrap:wrap;margin-top:12px;}
nav a{color:var(--ac);text-decoration:none;font-size:13px;padding:4px 10px;border:1px solid var(--bd);border-radius:14px;}
.cat{padding:8px 28px 0;} .cat h2{font-size:16px;border-left:3px solid var(--ac);padding-left:10px;margin:22px 0 12px;}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(420px,1fr));gap:16px;}
.card{background:var(--card);border:1px solid var(--bd);border-radius:10px;padding:14px 16px;}
.card .top{display:flex;justify-content:space-between;align-items:baseline;gap:8px;}
.card .nm{font-size:15px;font-weight:600;} .card .val{font-size:18px;font-weight:700;text-align:right;white-space:nowrap;}
.card .unit{color:var(--mut);font-size:11px;font-weight:400;} .chg-up{color:var(--up);} .chg-dn{color:var(--dn);}
.chip{font-size:11px;padding:1px 6px;border-radius:4px;margin-left:6px;}
.chart{width:100%;height:240px;margin-top:6px;} .src{color:var(--mut);font-size:11px;margin-top:8px;line-height:1.5;}
.src b{color:#aeb8c4;} .empty{height:200px;display:flex;align-items:center;justify-content:center;color:var(--mut);
font-size:13px;border:1px dashed var(--bd);border-radius:8px;margin-top:8px;}
</style></head><body>
<header><h1>📊 원자재 대시보드</h1>
<div class="meta">최종 갱신: __UPDATED__ · 차트 기간: 선물 최근 __WINDOW__영업일 · 반도체/희소금속 전체기간 · 갱신: 평일 08·12시 · 30분마다 자동 새로고침</div>
<nav>__NAV__</nav></header>
__BODY__
<script>
const PAYLOAD = __PAYLOAD__; const charts = [];
function mkChart(el,p){const c=echarts.init(el,'dark');const grid={left:58,right:14,top:14,bottom:24};
const base={backgroundColor:'transparent',grid,tooltip:{trigger:'axis'},
xAxis:{type:'category',data:p.dates,axisLabel:{color:'#8b97a7',fontSize:10},axisLine:{lineStyle:{color:'#2a333f'}}},
yAxis:{scale:true,axisLabel:{color:'#8b97a7',fontSize:10},splitLine:{lineStyle:{color:'#222b36'}}}};let opt;
if(p.type==='ohlc'){opt=Object.assign({},base,{series:[{type:'candlestick',data:p.ohlc,
itemStyle:{color:'#e5534b',color0:'#3fb950',borderColor:'#e5534b',borderColor0:'#3fb950'}}]});}
else if(p.type==='line'){opt=Object.assign({},base,{series:[{type:'line',data:p.values,smooth:true,
showSymbol:p.values.length<3,lineStyle:{color:'#4493f8'},areaStyle:{color:'rgba(68,147,248,0.12)'}}]});}
else if(p.type==='multiline'){opt=Object.assign({},base,{legend:{type:'scroll',top:0,textStyle:{color:'#8b97a7',fontSize:9}},
grid:{left:58,right:14,top:30,bottom:24},series:p.series.map(s=>({name:s.name,type:'line',data:s.data,
showSymbol:p.dates.length<3,connectNulls:true}))});}
c.setOption(opt);charts.push(c);}
window.addEventListener('resize',()=>charts.forEach(c=>c.resize()));
document.querySelectorAll('.chart').forEach(el=>{const p=PAYLOAD.find(x=>x.id===el.dataset.id);if(p&&p.type!=='empty')mkChart(el,p);});
</script></body></html>"""

def build_html():
    payload = build_payload()
    by = {c: [] for c in CATEGORIES}
    for p in payload: by.setdefault(p["cat"], []).append(p)
    nav = " ".join(f'<a href="#c{i}">{c}</a>' for i, c in enumerate(CATEGORIES))
    body = "".join(f'<section class="cat" id="c{i}"><h2>{c}</h2><div class="grid">'
                   + "".join(_card(p) for p in by.get(c, [])) + '</div></section>'
                   for i, c in enumerate(CATEGORIES))
    html = (HTML.replace("__UPDATED__", datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S KST"))
                .replace("__WINDOW__", str(WINDOW))
                .replace("__NAV__", nav).replace("__BODY__", body)
                .replace("__PAYLOAD__", json.dumps(payload, ensure_ascii=False)))
    with open(OUT_HTML, "w", encoding="utf-8") as f: f.write(html)
    print("  ->", OUT_HTML)

# =====================================================================
#  실행
# =====================================================================
def run_once():
    print(f"=== 수집 시작 {datetime.now(KST).strftime('%Y-%m-%d %H:%M:%S')} (Playwright={HAS_PW}) ===")
    dram_done = False
    try:
        n = db_backfill()
        if n: print(f"  [DB ] semiconductor_data.db 백필 +{n} rows")
    except Exception as e:
        print("  [ERR] DB 백필", e)
    if any(x["src"] == "komis" for x in ITEMS):
        try:
            r = fetch_komis(); print(f"  [OK ] KOMIS 5종 {min(r.values())}~{max(r.values())}일")
        except Exception as e: print("  [ERR] komis", e)
    for it in ITEMS:
        try:
            s = it["src"]
            if s == "sina": merge_ohlc(it["id"], fetch_sina(it["sym"]))
            elif s == "yahoo": merge_ohlc(it["id"], fetch_yahoo(it["sym"]))
            elif s == "dram":
                if not dram_done: fetch_dram(); dram_done = True
            elif s == "komis": pass
            elif s == "topcon":
                d = fetch_topcon()
                if d: append_snapshot3("topcon", d["high"], d["low"], d["avg"])
            elif s == "lipf6":
                v = fetch_lipf6()
                if v: append_snapshot("lipf6", v)
        except Exception as e:
            print(f"  [ERR] {it['id']}: {e}")
    build_html()
    print("=== 완료 ===")

def next_run(now):
    cands = []
    for add in range(0, 8):
        d = (now + timedelta(days=add))
        if d.weekday() >= 5: continue            # 토(5)·일(6) 제외
        for h, m in [(8, 0), (12, 0)]:
            t = now.replace(year=d.year, month=d.month, day=d.day, hour=h, minute=m, second=0, microsecond=0)
            if t > now: cands.append(t)
    return min(cands)

def scheduler():
    run_once()                                   # 시작 즉시 1회
    while True:
        now = datetime.now(KST); nxt = next_run(now)
        wait = (nxt - now).total_seconds()
        print(f"다음 실행: {nxt.strftime('%Y-%m-%d %H:%M')} (대기 {int(wait//3600)}시간 {int(wait%3600//60)}분)")
        time.sleep(max(30, wait))
        run_once()

if __name__ == "__main__":
    # 한 번만 생성하려면 run_once()
    # 평일 08·12시 자동 반복은 scheduler()
    scheduler()

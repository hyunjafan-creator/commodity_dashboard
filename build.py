# -*- coding: utf-8 -*-
"""대시보드 HTML 생성기.

data/*.csv 를 읽어 카테고리별 차트(최근 200영업일)를 가진 dashboard.html 생성.
- OHLC: 캔들차트
- snapshot(line): 라인차트
- dram: 제품별 멀티라인
각 차트에 출처(source)를 명시한다. 표준 라이브러리만 사용.
"""
import csv
import json
import os
import re
import sys
from datetime import datetime, date, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
sys.path.insert(0, HERE)
from config import ITEMS, CATEGORIES, WINDOW  # noqa: E402


def read_rows(item_id):
    p = os.path.join(DATA, item_id + ".csv")
    if not os.path.exists(p):
        return []
    with open(p, "r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def fnum(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def build_payload():
    out = []
    for it in ITEMS:
        rows = read_rows(it["id"])
        p = dict(id=it["id"], name=it["name"], cat=it["cat"], unit=it["unit"],
                 source=it["source"], note=it.get("note", ""))

        if it["id"] == "topcon":
            # date,high,low,avg → High/Low/Average 3선
            rows = rows[-WINDOW:]
            dates = [r["date"] for r in rows]
            if not rows:
                p.update(type="empty")
                out.append(p)
                continue
            series = [
                dict(name="High", data=[fnum(r.get("high")) for r in rows]),
                dict(name="Low", data=[fnum(r.get("low")) for r in rows]),
                dict(name="Average", data=[fnum(r.get("avg")) for r in rows]),
            ]
            last = rows[-1]
            p.update(type="multiline", dates=dates, series=series,
                     last_date=dates[-1],
                     summary=f"평균 {last.get('avg')} (H {last.get('high')} / L {last.get('low')})")
            out.append(p)
            continue

        if it["src"] == "dram":
            # 공통 dram.csv(long format)에서 타입(match) 제품만 멀티라인.
            # X축 기간: 최근 2년(약 730일)으로 제한.
            mt = it.get("match", ".")
            rows = [r for r in read_rows("dram") if re.search(mt, r["product"])]
            cutoff = (date.today() - timedelta(days=730)).isoformat()
            dates = sorted(d for d in {r["date"] for r in rows} if d >= cutoff)
            dset = set(dates)
            prods = {}
            for r in rows:
                if r["date"] in dset:
                    prods.setdefault(r["product"], {})[r["date"]] = fnum(r["value"])
            series = []
            for name in sorted(prods):
                series.append(dict(name=name,
                                   data=[prods[name].get(d) for d in dates]))
            p.update(type="multiline", dates=dates, series=series,
                     last_date=dates[-1] if dates else "",
                     summary=f"{len(series)}개 제품")
            out.append(p)
            continue

        if it["src"] == "komis":
            # 일별 라인 (date= 'YYYY-MM-DD', value). 최근 3년 전체 표시.
            if not rows:
                p.update(type="empty")
                out.append(p)
                continue
            dates = [r["date"] for r in rows]
            vals = [fnum(r["value"]) for r in rows]
            last = vals[-1] if vals else None
            prev = vals[-2] if len(vals) > 1 else None
            p.update(type="line", dates=dates, values=vals,
                     last=last, last_date=dates[-1] if dates else "",
                     change=_chg(last, prev))
            out.append(p)
            continue

        if it["src"] == "snap" and not rows:
            p.update(type="empty")
            out.append(p)
            continue

        if it["src"] == "snap":
            rows = rows[-WINDOW:]
            dates = [r["date"] for r in rows]
            vals = [fnum(r["value"]) for r in rows]
            last = vals[-1] if vals else None
            prev = vals[-2] if len(vals) > 1 else None
            p.update(type="line", dates=dates, values=vals,
                     last=last, last_date=dates[-1] if dates else "",
                     change=_chg(last, prev))
            out.append(p)
            continue

        # OHLC (sina/yahoo)
        rows = rows[-WINDOW:]
        dates = [r["date"] for r in rows]
        ohlc = [[fnum(r["open"]), fnum(r["close"]), fnum(r["low"]), fnum(r["high"])]
                for r in rows]
        closes = [fnum(r["close"]) for r in rows]
        last = closes[-1] if closes else None
        prev = closes[-2] if len(closes) > 1 else None
        p.update(type="ohlc", dates=dates, ohlc=ohlc,
                 last=last, last_date=dates[-1] if dates else "",
                 change=_chg(last, prev))
        out.append(p)
    return out


def _chg(last, prev):
    if last is None or prev in (None, 0):
        return None
    return dict(abs=round(last - prev, 4), pct=round((last - prev) / prev * 100, 2))


HTML = """<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="refresh" content="1800">
<title>원자재 대시보드</title>
<script src="https://cdn.jsdelivr.net/npm/echarts@5/dist/echarts.min.js"></script>
<style>
  :root{--bg:#0f1419;--card:#1a212b;--bd:#2a333f;--tx:#e6edf3;--mut:#8b97a7;
        --up:#e5534b;--dn:#3fb950;--ac:#4493f8;}
  *{box-sizing:border-box;}
  body{margin:0;background:var(--bg);color:var(--tx);
       font-family:'Segoe UI','Malgun Gothic',sans-serif;}
  header{padding:20px 28px;border-bottom:1px solid var(--bd);
         position:sticky;top:0;background:var(--bg);z-index:10;}
  header h1{margin:0 0 4px;font-size:20px;}
  header .meta{color:var(--mut);font-size:13px;}
  nav{display:flex;gap:8px;flex-wrap:wrap;margin-top:12px;}
  nav a{color:var(--ac);text-decoration:none;font-size:13px;padding:4px 10px;
        border:1px solid var(--bd);border-radius:14px;}
  nav a:hover{background:var(--card);}
  .cat{padding:8px 28px 0;}
  .cat h2{font-size:16px;border-left:3px solid var(--ac);padding-left:10px;margin:22px 0 12px;}
  .grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(420px,1fr));gap:16px;}
  .card{background:var(--card);border:1px solid var(--bd);border-radius:10px;padding:14px 16px;}
  .card .top{display:flex;justify-content:space-between;align-items:baseline;gap:8px;}
  .card .nm{font-size:15px;font-weight:600;}
  .card .val{font-size:18px;font-weight:700;text-align:right;white-space:nowrap;}
  .card .unit{color:var(--mut);font-size:11px;font-weight:400;}
  .chg-up{color:var(--up);} .chg-dn{color:var(--dn);}
  .chip{font-size:11px;padding:1px 6px;border-radius:4px;margin-left:6px;}
  .chart{width:100%;height:240px;margin-top:6px;}
  .src{color:var(--mut);font-size:11px;margin-top:8px;line-height:1.5;}
  .src b{color:#aeb8c4;font-weight:600;}
  .note{color:#c9a44a;font-size:11px;margin-top:3px;}
  .updated{display:inline-block;margin:6px 0 2px;font-size:15px;font-weight:700;
           color:#e6edf3;background:rgba(68,147,248,0.15);border:1px solid var(--ac);
           border-radius:6px;padding:5px 12px;}
  .empty{height:200px;display:flex;align-items:center;justify-content:center;
         color:var(--mut);font-size:13px;text-align:center;border:1px dashed var(--bd);
         border-radius:8px;margin-top:8px;}
</style>
</head>
<body>
<header>
  <h1>📊 원자재 대시보드</h1>
  <div class="updated">🕒 마지막 업데이트 : __UPDATED__</div>
  <div class="meta">차트 기간: 선물 최근 __WINDOW__영업일 · 반도체/희소금속 전체기간 · 매일 08·14·17시 자동 새로고침</div>
  <nav>__NAV__</nav>
</header>
__BODY__
<script>
const PAYLOAD = __PAYLOAD__;
const charts = [];
function fmt(n){ if(n===null||n===undefined) return '-';
  return n.toLocaleString('en-US',{maximumFractionDigits: Math.abs(n)<10?4:2}); }
function mkChart(el, p){
  const c = echarts.init(el, 'dark');
  let opt;
  const grid = {left:58,right:14,top:14,bottom:24};
  const base = {backgroundColor:'transparent', grid,
    tooltip:{trigger:'axis'}, xAxis:{type:'category', data:p.dates,
      axisLabel:{color:'#8b97a7',fontSize:10}, axisLine:{lineStyle:{color:'#2a333f'}}},
    yAxis:{scale:true, axisLabel:{color:'#8b97a7',fontSize:10},
      splitLine:{lineStyle:{color:'#222b36'}}}};
  if(p.type==='ohlc'){
    opt=Object.assign({}, base, {series:[{type:'candlestick', data:p.ohlc,
      itemStyle:{color:'#e5534b',color0:'#3fb950',borderColor:'#e5534b',borderColor0:'#3fb950'}}]});
  } else if(p.type==='line'){
    opt=Object.assign({}, base, {series:[{type:'line', data:p.values, smooth:true,
      showSymbol:p.values.length<3, lineStyle:{color:'#4493f8'},
      areaStyle:{color:'rgba(68,147,248,0.12)'}}]});
  } else if(p.type==='multiline'){
    opt=Object.assign({}, base, {tooltip:{trigger:'axis'},
      legend:{type:'scroll',top:0,textStyle:{color:'#8b97a7',fontSize:9},
        pageTextStyle:{color:'#8b97a7'}},
      grid:{left:58,right:14,top:30,bottom:24},
      series:p.series.map(s=>({name:s.name,type:'line',data:s.data,
        showSymbol:p.dates.length<3,connectNulls:true}))});
  }
  c.setOption(opt); charts.push(c);
}
window.addEventListener('resize',()=>charts.forEach(c=>c.resize()));
document.querySelectorAll('.chart').forEach(el=>{
  const p = PAYLOAD.find(x=>x.id===el.dataset.id);
  if(p && p.type!=='empty') mkChart(el, p);
});
</script>
</body>
</html>"""


def card_html(p):
    # 값/변동 헤더
    if p["type"] in ("ohlc", "line"):
        val = fmt_py(p.get("last"))
        chg = p.get("change")
        chip = ""
        if chg:
            up = chg["pct"] >= 0
            cls = "chg-up" if up else "chg-dn"
            sign = "▲" if up else "▼"
            chip = (f'<span class="chip {cls}">{sign} {abs(chg["pct"]):.2f}% '
                    f'({"+" if up else ""}{fmt_py(chg["abs"])})</span>')
        head = (f'<div class="val">{val}<span class="unit"> {p["unit"]}</span>{chip}</div>')
        sub = f'기준일 {p.get("last_date","")}'
    elif p["type"] == "multiline":
        head = f'<div class="val" style="font-size:13px;color:#8b97a7">{p.get("summary","")}</div>'
        sub = f'기준일 {p.get("last_date","") or "수집 시작 전"}'
    else:  # empty
        head = '<div class="val" style="font-size:13px;color:#8b97a7">수집 대기</div>'
        sub = ""

    body = (f'<div class="empty">데이터 수집 대기 중<br>(로그인/별도 수집 연동 필요)</div>'
            if p["type"] == "empty"
            else f'<div class="chart" data-id="{p["id"]}"></div>')

    note = f'<div class="note">⚠ {p["note"]}</div>' if p["note"] else ""
    return (f'<div class="card"><div class="top">'
            f'<div class="nm">{p["name"]}</div>{head}</div>'
            f'{body}'
            f'<div class="src"><b>출처</b> {p["source"]} · {sub}</div>{note}</div>')


def fmt_py(n):
    if n is None:
        return "-"
    if abs(n) < 10:
        return f"{n:,.4f}".rstrip("0").rstrip(".")
    return f"{n:,.2f}"


def build():
    payload = build_payload()
    by_cat = {c: [] for c in CATEGORIES}
    for p in payload:
        by_cat.setdefault(p["cat"], []).append(p)

    nav = " ".join(f'<a href="#cat-{i}">{c}</a>' for i, c in enumerate(CATEGORIES))
    body = []
    for i, c in enumerate(CATEGORIES):
        cards = "".join(card_html(p) for p in by_cat.get(c, []))
        body.append(f'<section class="cat" id="cat-{i}"><h2>{c}</h2>'
                    f'<div class="grid">{cards}</div></section>')

    _now = datetime.now()
    _wd = ["월", "화", "수", "목", "금", "토", "일"][_now.weekday()]
    updated = _now.strftime(f"%Y년 %m월 %d일 ({_wd}) %H:%M:%S")
    html = (HTML
            .replace("__UPDATED__", updated)
            .replace("__WINDOW__", str(WINDOW))
            .replace("__NAV__", nav)
            .replace("__BODY__", "\n".join(body))
            .replace("__PAYLOAD__", json.dumps(payload, ensure_ascii=False)))

    out = os.path.join(HERE, "★Commodity_dashboard.html")
    # ★Commodity_dashboard.html = 사용자가 여는 파일, index.html = 미리보기 서버용
    for name in ("★Commodity_dashboard.html", "dashboard.html", "index.html"):
        with open(os.path.join(HERE, name), "w", encoding="utf-8") as f:
            f.write(html)
    print(f"대시보드 생성: {out}  ({len(payload)} 아이템)")
    return out


if __name__ == "__main__":
    build()

# -*- coding: utf-8 -*-
"""semiconductor_data.db (반도체 가격 DB) → data/dram.csv 백필.

DB의 일별 spot 관측(2022~)을 대시보드 제품명에 매핑해 long format(date,product,value)으로
채운다. 기존 스냅샷 값은 보존(setdefault)하고 과거 빈 날짜만 채운다. value = average(USD).
매 실행 시 호출해도 안전(idempotent).
"""
import csv
import os
import sqlite3

HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(HERE, "semiconductor_data.db")
DATA = os.path.join(HERE, "data")
DRAM_CSV = os.path.join(DATA, "dram.csv")

# DB product_name → 대시보드(DRAMeXchange 스냅샷) 제품명 (연속 시계열로 잇기 위해 정확히 매핑)
NAME_MAP = {
    "DDR3_4Gb_512Mx8_1600_1866": "DDR3 4Gb 512Mx8 1600/1866",
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


def import_spot():
    """DB 일별 spot 히스토리를 dram.csv 에 병합. 반영 행 수 반환."""
    if not os.path.exists(DB):
        return 0
    os.makedirs(DATA, exist_ok=True)
    con = sqlite3.connect(DB)
    rows = con.execute(
        """SELECT p.product_name, o.observed_date, o.average
           FROM price_observations o JOIN products p ON p.product_id = o.product_id
           WHERE p.market_type='spot' AND p.frequency='daily' AND o.average IS NOT NULL"""
    ).fetchall()
    con.close()

    # 기존 dram.csv 로드
    keyed = {}
    if os.path.exists(DRAM_CSV):
        with open(DRAM_CSV, encoding="utf-8", newline="") as f:
            for r in csv.DictReader(f):
                keyed[(r["date"], r["product"])] = r["value"]

    added = 0
    for name, d, avg in rows:
        disp = NAME_MAP.get(name)
        if not disp:
            continue
        key = (d, disp)
        if key not in keyed:                  # 기존(스냅샷) 값은 보존, 빈 과거만 채움
            keyed[key] = f"{avg:g}"
            added += 1

    with open(DRAM_CSV, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["date", "product", "value"])
        for d, prod in sorted(keyed):
            w.writerow([d, prod, keyed[(d, prod)]])
    return added


if __name__ == "__main__":
    print("DB 백필 추가 행:", import_spot())

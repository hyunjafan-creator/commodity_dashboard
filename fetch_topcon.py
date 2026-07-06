# -*- coding: utf-8 -*-
"""미국 TOPCon 모듈 (US assembled, DDP) 수집 - InfoLink PV Spot Price.

해당 항목은 로그인 없이 공개돼 있어 헤드리스로 표를 읽어 High/Low/Average 를 추출한다.
매일 당일값을 누적(date,high,low,avg)한다.
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DEBUG = os.path.join(HERE, "topcon_debug.txt")
URL = "https://www.infolink-group.com/spot-price/"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
TARGET = "TOPCon Module - US assembled (USD, DDP)"


def _parse(body):
    """본문에서 US assembled 행의 High/Low/Average 추출. dict 또는 None."""
    i = body.find(TARGET)
    if i < 0:
        i = body.find("US assembled")
        if i < 0:
            return None
    seg = body[i:i + 200]
    nums = re.findall(r"\d+\.\d{1,3}", seg)
    if len(nums) >= 3:
        return dict(high=nums[0], low=nums[1], avg=nums[2])
    return None


def fetch():
    """헤드리스로 페이지를 열어 US assembled High/Low/Avg 추출. dict 또는 None."""
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True,
                              args=["--disable-blink-features=AutomationControlled"])
        ctx = b.new_context(user_agent=UA, viewport={"width": 1500, "height": 1200})
        page = ctx.new_page()
        try:
            page.goto(URL, wait_until="networkidle", timeout=70000)
            d = None
            for _ in range(8):
                body = page.inner_text("body")
                d = _parse(body)
                if d:
                    try:
                        with open(DEBUG, "w", encoding="utf-8") as f:
                            f.write(body)
                    except Exception:
                        pass
                    break
                page.wait_for_timeout(1500)
        finally:
            b.close()
        return d


def _persist_and_build(d):
    if not d:
        return
    import update
    import build
    update.append_snapshot3("topcon", d["high"], d["low"], d["avg"])
    build.build()
    print("CSV 누적 + 대시보드 갱신 완료:", d)


if __name__ == "__main__":
    d = fetch()
    _persist_and_build(d)
    print("FETCH:", d)

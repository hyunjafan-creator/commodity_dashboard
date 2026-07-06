# -*- coding: utf-8 -*-
"""LiPF6 (육불화인산리튬) 수집 - metal.com (SMM).

[로그인 방식: 영속 브라우저 프로필]
metal.com 세션이 storage_state(JSON 스냅샷)로는 자주 만료되어, 실제 브라우저처럼
모든 상태(쿠키·localStorage·IndexedDB)를 폴더(.pw_profile_lipf6)에 보존하는
영속 프로필 방식으로 재사용한다. 매 수집 시 같은 프로필로 접속하므로 서버가 갱신해주는
쿠키가 그때그때 디스크에 저장되어(슬라이딩 세션) 매일 돌리는 한 세션이 오래 유지된다.

- login(): 헤드풀 창을 띄워 사용자가 직접 로그인. (비밀번호는 코드에 저장/입력하지 않음)
  로그인 시 '로그인 상태 유지 / Remember me' 가 있으면 체크하면 더 오래 간다.
  graceful close 로 프로필을 디스크에 저장한다.
- fetch(): 같은 프로필로 헤드리스 접속해 당일 High/Low/Avg 추출 + 갱신 쿠키 보존.

세션이 끊기면 login() 을 다시 실행하면 된다.
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROFILE = os.path.join(HERE, ".pw_profile_lipf6")  # 영속 프로필(쿠키/세션 보존)
DEBUG = os.path.join(HERE, "lipf6_debug.txt")
URL = "https://www.metal.com/Lithium/202110220001"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
MARK = "LIPF6_LOGIN_WINDOW"

_NUM = re.compile(r"^[\d,]+(?:\.\d+)?$")
_DATE = re.compile(r"^(\d{2})/(\d{2})/(\d{4})$")  # DD/MM/YYYY
# 가격 잠금 플레이스홀더 (영/한 모두) — 이게 있으면 미로그인
PLACEHOLDERS = ("Sign in to view", "로그인하여 보기")


def _iso(dmy):
    m = _DATE.match(dmy)
    return f"{m.group(3)}-{m.group(2)}-{m.group(1)}" if m else dmy


def _logged_in(page):
    """로그인됨 = 가격 잠금 플레이스홀더(영/한)가 사라짐. 단, 페이지가 로드된 상태에서만 판단."""
    try:
        body = page.inner_text("body")
        if "USD/tonne" not in body:   # 가격 섹션 미로드 → 판단 보류
            return False
        return not any(ph in body for ph in PLACEHOLDERS)
    except Exception:
        return False


def _dump_debug(page):
    try:
        body = page.inner_text("body")
        with open(DEBUG, "w", encoding="utf-8") as f:
            f.write(body)
    except Exception:
        pass


def _extract(page, tries=10, interval=1500):
    """로그인된 페이지에서 당일 High/Low/Avg/Date 추출.
    (1) 하단 일별 표의 최신 데이터행이 채워졌으면 거기서,
    (2) 아니면 상단 요약 블록(High/Low/Date)에서.
    값이 없으면 None."""
    for _ in range(tries):
        # (1) 일별 표
        rows = page.evaluate(
            """() => {
                const out = [];
                document.querySelectorAll('table tr').forEach(tr => {
                    const c = Array.from(tr.querySelectorAll('td,th')).map(x => x.innerText.trim());
                    if (c.length) out.push(c);
                });
                return out;
            }"""
        )
        for c in rows:
            if len(c) >= 5 and _DATE.match(c[0]):
                high, low, avg = c[2].replace(",", ""), c[3].replace(",", ""), c[4].replace(",", "")
                if _NUM.match(avg) and _NUM.match(high):
                    return dict(date=_iso(c[0]), high=high, low=low, avg=avg, src="table")
        # (2) 상단 요약 블록 — 라벨(고가/낮음/날짜, High/Low/Date) 기준 파싱.
        #     레이아웃: 수집 \n <현재가> \n <변동> \n 고가 \n <High> \n 낮음 \n <Low> \n 날짜 \n <date>
        body = page.inner_text("body")
        cut = len(body)
        for marker in ("가격 세부 정보", "Price Details"):
            j = body.find(marker)
            if j > 0:
                cut = min(cut, j)
        top = body[:cut]
        if not any(ph in top for ph in PLACEHOLDERS):
            n = r"([\d,]+(?:\.\d+)?)"
            m_price = re.search(r"(?:수집|Collect)\s+" + n, top)
            m_high = re.search(r"(?:고가|High)\s+" + n, top)
            m_low = re.search(r"(?:낮음|Low)\s+" + n, top)
            m_date = re.search(r"(?:날짜|Date)\s+([A-Z][a-z]{2}\s+\d{1,2},\s+\d{4})", top)
            if m_high and m_low:
                high = m_high.group(1).replace(",", "")
                low = m_low.group(1).replace(",", "")
                avg = (m_price.group(1).replace(",", "") if m_price
                       else str(round((float(high) + float(low)) / 2, 2)))
                return dict(date=_disp_iso(m_date.group(1)) if m_date else "",
                            high=high, low=low, avg=avg, src="top")
        page.wait_for_timeout(interval)
    return None


def _disp_iso(s):
    """'Jun 17, 2026' -> '2026-06-17'. 실패 시 원문."""
    try:
        from datetime import datetime
        return datetime.strptime(s, "%b %d, %Y").date().isoformat()
    except Exception:
        return s


def _force_foreground(keywords=(MARK,)):
    try:
        import ctypes
        from ctypes import wintypes
        u = ctypes.windll.user32
        found = []

        @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
        def cb(hwnd, _):
            if not u.IsWindowVisible(hwnd):
                return True
            n = u.GetWindowTextLengthW(hwnd)
            if n <= 0:
                return True
            buf = ctypes.create_unicode_buffer(n + 1)
            u.GetWindowTextW(hwnd, buf, n + 1)
            if any(k.lower() in buf.value.lower() for k in keywords):
                found.append((hwnd, buf.value))
            return True

        u.EnumWindows(cb, 0)
        if not found:
            return False
        hwnd = found[0][0]
        u.ShowWindow(hwnd, 9)
        u.ShowWindow(hwnd, 3)
        u.keybd_event(0x12, 0, 0, 0)
        u.keybd_event(0x12, 0, 2, 0)
        u.BringWindowToTop(hwnd)
        u.SetForegroundWindow(hwnd)
        return found[0][1]
    except Exception:
        return False


def login(timeout_sec=900):
    """헤드풀 영속 프로필 창에서 사용자가 직접 로그인. graceful close 로 프로필 저장."""
    from playwright.sync_api import sync_playwright
    os.makedirs(PROFILE, exist_ok=True)
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            PROFILE, headless=False, no_viewport=True, user_agent=UA,
            args=["--start-maximized", "--disable-blink-features=AutomationControlled"])
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto(URL, wait_until="domcontentloaded", timeout=60000)
        try:
            page.bring_to_front()
            page.evaluate(f"document.title='{MARK}'")
        except Exception:
            pass
        print("창 포그라운드:", _force_foreground())
        print("브라우저 창에서 직접 로그인하세요 (Sign In). '로그인 상태 유지'가 있으면 체크하세요.")
        waited = 0
        result = None
        while waited < timeout_sec:
            page.wait_for_timeout(5000)
            waited += 5
            if waited <= 30:
                try:
                    page.evaluate(f"document.title='{MARK}'")
                except Exception:
                    pass
                _force_foreground()
            try:
                if _logged_in(page):
                    print("로그인 감지! 프로필 저장 + DOM 덤프")
                    try:
                        page.reload(wait_until="networkidle", timeout=40000)
                    except Exception:
                        pass
                    _dump_debug(page)
                    result = _extract(page, tries=12, interval=1500)
                    print("추출 결과:", result)
                    break
                if waited % 30 < 5:
                    print("  ...로그인 대기", waited, "s")
            except Exception as e:
                print("  ...대기", waited, "s", type(e).__name__)
        ctx.close()   # graceful close → 영속 프로필(쿠키/세션) 디스크에 보존
        return result


def fetch():
    """영속 프로필로 헤드리스 접속해 당일값 추출. dict 또는 None.
    접속 시 서버가 갱신한 쿠키가 프로필에 자동 저장되어 세션이 오래 유지된다."""
    if not os.path.isdir(PROFILE):
        return None
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            PROFILE, headless=True, user_agent=UA,
            viewport={"width": 1280, "height": 900},
            args=["--disable-blink-features=AutomationControlled"])
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        try:
            page.goto(URL, wait_until="networkidle", timeout=60000)
            d = _extract(page, tries=10, interval=1500)
        finally:
            ctx.close()   # graceful close → 갱신된 쿠키 보존
        return d


def _persist_and_build(d):
    if not d:
        return
    import update
    import build
    update.append_snapshot("lipf6", d["avg"])
    build.build()
    print("CSV 누적 + 대시보드 갱신 완료:", d)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "login":
        secs = int(sys.argv[2]) if len(sys.argv) > 2 else 900
        d = login(timeout_sec=secs)
        _persist_and_build(d)
        print("LOGIN_RESULT:", "OK" if d else "FAIL")
    elif len(sys.argv) > 1 and sys.argv[1] == "dump":
        # 영속 프로필로 현재 페이지 본문 덤프(로그인/파서 점검용)
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            ctx = p.chromium.launch_persistent_context(
                PROFILE, headless=True, user_agent=UA,
                args=["--disable-blink-features=AutomationControlled"])
            pg = ctx.pages[0] if ctx.pages else ctx.new_page()
            pg.goto(URL, wait_until="networkidle", timeout=60000)
            pg.wait_for_timeout(6000)
            _dump_debug(pg)
            print("LOGGED_IN:", _logged_in(pg))
            ctx.close()
        print("dumped ->", DEBUG)
    else:
        d = fetch()
        _persist_and_build(d)
        print("FETCH:", d)

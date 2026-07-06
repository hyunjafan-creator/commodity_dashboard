# 원자재 대시보드

평일 **08:00 · 12:00 · 14:00** 자동 갱신되는 원자재 가격 대시보드.
차트는 **최근 200영업일**, 각 차트에 **출처**를 명시한다.

## 보기
- `dashboard.html` (또는 `index.html`) 더블클릭 → 브라우저에서 열림.
- 열어두면 30분마다 자동 새로고침되어 최신 데이터 반영.

## 구조
| 파일 | 역할 |
|------|------|
| `config.py` | 전체 아이템 정의(카테고리·심볼·단위·출처) |
| `update.py` | 데이터 수집 → `data/*.csv` 누적 저장 |
| `build.py`  | CSV → `dashboard.html` 생성 (ECharts) |
| `run.py`    | 수집+생성 묶음 (스케줄러가 실행) |
| `run_dashboard.bat` | 작업 스케줄러용 래퍼 |
| `data/*.csv` | 아이템별 누적 데이터 |

수동 실행: `py run.py`

## 데이터 소스
- **Sina Finance K데이(일봉) 16종** — 전체 히스토리 자동: 탄산리튬·코크스·폴리실리콘·가성소다·PX·PVC·PP·부타디엔고무·철광석·철근·스테인리스·열연·알루미늄합금·주석·니켈(SHFE)·팜유
- **Yahoo Finance 8종** — WTI·천연가스·가솔린RBOB·구리(COMEX)·소맥·옥수수·대두·알루미늄(COMEX)
- **DRAMeXchange** — 홈페이지 파싱, 매일 당일 스냅샷 누적. 반도체 타입별 6개 차트로 분리: **DDR4 · DDR5 · MLC · SLC · TLC · GDDR** (각 카드는 해당 타입 제품들의 멀티라인). `config.py` 의 `match` 정규식으로 `data/dram.csv`(공통)에서 타입별 필터링.
- **희소금속 5종** (KOMIS 한국자원정보서비스) — 월별·최근 3년. 텅스텐(Ferro-tungsten)·네오디뮴(Neodymium Oxide)·디스프로슘(Dysprosium Oxide)·티타늄(Ferro-titanium)·몰리브덴(Ferro-molybdenum). `fetch_komis.py` 가 getChartData(월별) 호출 → `data/komis_*.csv`

### 프록시로 대체한 소스 (무료 LME 미제공)
요청은 런던선물거래소(LME) 기준이나 무료 데이터가 없어 차트에 거래소를 명시하고 대체:
- 구리/알루미늄 → COMEX (Yahoo)
- 니켈 → SHFE (Sina)

### LiPF6 — 로그인 세션으로 자동 수집 (구축 완료)
metal.com 은 세션 쿠키 기반이라 **저장된 로그인 세션**(`.pw_state.json`)을 재사용한다.
- 수집: `fetch_lipf6.py` 가 헤드리스 Chromium 으로 상단 요약(고가/낮음/평균)을 읽어 `data/lipf6.csv` 에 당일 평균가를 누적. 스케줄 실행(`run.py`)에 연동됨.
- **세션 만료 시 재로그인:** `py fetch_lipf6.py login` 실행 → 뜨는 창에서 직접 로그인(비밀번호는 코드에 저장 안 함) → 세션 자동 저장.
- 참고: 과거 이력 표는 SMM 유료 구독 전용이라 비어 있어, 당일 요약값만 누적한다.

### TOPCon 모듈 (InfoLink) — 로그인 없이 자동 수집 (구축 완료)
`fetch_topcon.py` 가 InfoLink Spot Price 페이지를 헤드리스로 읽어
'TOPCon Module - US assembled (USD, DDP)' 행의 **High/Low/Average** 를
`data/topcon.csv` (date,high,low,avg)에 누적. 대시보드는 3선(High/Low/Average) 차트.

### 아직 수집 대기인 소스
- **런던 가스오일** (ICE) — 무료 소스 없음 (수동 입력 가능)

> 수동 입력도 가능: `data/<id>.csv` (헤더 `date,value`) 에 `2026-06-17,72500` 처럼 한 줄 추가하면 차트에 반영된다.

## 스케줄 변경/해제
```
schtasks /query  /tn CommodityDashboard_08
schtasks /change /tn CommodityDashboard_08 /st 09:00
schtasks /delete /tn CommodityDashboard_08 /f
```
작업명: `CommodityDashboard_08`, `_12`, `_14` (PC가 켜져 있을 때만 실행됨)

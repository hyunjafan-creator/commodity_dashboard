# -*- coding: utf-8 -*-
"""원자재 대시보드 설정 - 전체 아이템 정의.

src 종류:
  - sina   : Sina Finance 선물 일봉(K데이) API. 전체 OHLC 히스토리 자동 수집.
  - yahoo  : Yahoo Finance chart API. 전체 OHLC 히스토리 자동 수집.
  - dram   : DRAMeXchange 홈페이지 파싱. 매일 당일 스냅샷 누적.
  - snap   : 로그인/봇차단 소스(LiPF6, InfoLink). 스캐폴드만. 수동/브라우저 수집 누적.
"""

WINDOW = 200  # 차트에 표시할 최근 영업일 수

# (id, category, name, src, symbol, unit, source_label, note)
ITEMS = [
    # ── 1. 반도체 ───────────────────────────────────────────────
    dict(id="dram_ddr3", cat="반도체", name="DDR3 칩 현물가", src="dram", sym="", match=r"^DDR3",
         unit="USD", source="DRAMeXchange · DRAM Spot (DDR3 4Gb 512Mx8 1600/1866)", note="매일 당일 스냅샷 누적."),
    dict(id="dram_ddr4", cat="반도체", name="DDR4 칩 현물가", src="dram", sym="", match=r"^DDR4(?!.*DIMM)",
         unit="USD", source="DRAMeXchange · DRAM Spot (칩, 모듈 제외)", note="매일 당일 스냅샷 누적(제품별 라인)."),
    dict(id="dram_ddr5", cat="반도체", name="DDR5 칩 현물가", src="dram", sym="", match=r"^DDR5(?!.*DIMM)",
         unit="USD", source="DRAMeXchange · DRAM Spot (칩, 모듈 제외)", note="매일 당일 스냅샷 누적(제품별 라인)."),
    dict(id="dram_ddr4_mod", cat="반도체", name="DDR4 모듈 (DIMM)", src="dram", sym="", match=r"^DDR4.*DIMM",
         unit="USD", source="DRAMeXchange · DRAM Spot (모듈)", note="매일 당일 스냅샷 누적(제품별 라인)."),
    dict(id="dram_ddr5_mod", cat="반도체", name="DDR5 모듈 (DIMM)", src="dram", sym="", match=r"^DDR5.*DIMM",
         unit="USD", source="DRAMeXchange · DRAM Spot (모듈)", note="매일 당일 스냅샷 누적(제품별 라인)."),
    dict(id="dram_mlc", cat="반도체", name="MLC NAND 현물가", src="dram", sym="", match=r"^MLC",
         unit="USD", source="DRAMeXchange · NAND Flash Spot", note="매일 당일 스냅샷 누적(제품별 라인)."),
    dict(id="dram_slc", cat="반도체", name="SLC NAND 현물가", src="dram", sym="", match=r"^SLC",
         unit="USD", source="DRAMeXchange · NAND Flash Spot", note="매일 당일 스냅샷 누적(제품별 라인)."),
    dict(id="dram_tlc", cat="반도체", name="TLC NAND 현물가", src="dram", sym="", match=r"TLC",
         unit="USD", source="DRAMeXchange · NAND Flash Spot", note="매일 당일 스냅샷 누적(제품별 라인)."),
    dict(id="dram_gddr", cat="반도체", name="GDDR 현물가", src="dram", sym="", match=r"^GDDR",
         unit="USD", source="DRAMeXchange · GDDR Spot", note="매일 당일 스냅샷 누적(제품별 라인)."),

    # ── 2. 배터리 ───────────────────────────────────────────────
    dict(id="lc0", cat="배터리", name="탄산리튬 (Lithium Carbonate)", src="sina", sym="LC0",
         unit="CNY/톤", source="Sina Finance · GFEX 탄산리튬 LC0", note=""),
    dict(id="lipf6", cat="배터리", name="육불화인산리튬 LiPF6", src="snap", sym="lipf6",
         unit="USD/톤", source="Shanghai Metals Market (metal.com) · 로그인 세션",
         note="저장된 세션으로 매일 당일 평균가 자동 누적. 세션 만료 시 `py fetch_lipf6.py login` 재실행."),
    dict(id="copper", cat="배터리", name="구리 (Copper)", src="yahoo", sym="HG=F",
         unit="USD/lb", source="Yahoo Finance · COMEX HG=F",
         note="요청 기준은 LME이나 무료 LME 미제공 → COMEX 대체."),
    dict(id="alu", cat="배터리", name="알루미늄 (Aluminum)", src="yahoo", sym="ALI=F",
         unit="USD/톤", source="Yahoo Finance · COMEX ALI=F",
         note="요청 기준은 LME이나 무료 LME 미제공 → COMEX 대체."),
    dict(id="ni_bat", cat="배터리", name="니켈 (Nickel)", src="sina", sym="NI0",
         unit="CNY/톤", source="Sina Finance · SHFE 니켈 NI0",
         note="요청 기준은 LME이나 무료 LME 미제공 → SHFE 대체."),

    # ── 3. 에너지 ───────────────────────────────────────────────
    dict(id="wti", cat="에너지", name="WTI 원유", src="yahoo", sym="CL=F",
         unit="USD/배럴", source="Yahoo Finance · NYMEX CL=F (미국)", note=""),
    dict(id="natgas", cat="에너지", name="천연가스 (Natural Gas)", src="yahoo", sym="NG=F",
         unit="USD/MMBtu", source="Yahoo Finance · NYMEX NG=F (미국)", note=""),
    dict(id="rbob", cat="에너지", name="가솔린 RBOB", src="yahoo", sym="RB=F",
         unit="USD/갤런", source="Yahoo Finance · NYMEX RB=F (미국)", note=""),
    dict(id="gasoil", cat="에너지", name="런던 가스오일", src="snap", sym="gasoil",
         unit="USD/톤", source="ICE Gas Oil (영국)",
         note="무료 데이터 소스 없음 — 별도 수집 연동 필요."),
    dict(id="jm0", cat="에너지", name="코크스(코킹콜)", src="sina", sym="JM0",
         unit="CNY/톤", source="Sina Finance · DCE 코킹콜 JM0", note=""),

    # ── 4. 태양광 ───────────────────────────────────────────────
    dict(id="ps0", cat="태양광", name="폴리실리콘 (Polysilicon)", src="sina", sym="PS0",
         unit="CNY/톤", source="Sina Finance · GFEX 폴리실리콘 PS0", note=""),
    dict(id="topcon", cat="태양광", name="미국 TOPCon 모듈 (US assembled, DDP)", src="snap", sym="topcon",
         unit="USD/W", source="InfoLink PV Spot Price (infolink-group.com)",
         note="로그인 불필요. 매일 당일 High/Low/Average 자동 누적."),

    # ── 5. 화학제품 / 철강 ──────────────────────────────────────
    dict(id="sh0", cat="화학/철강", name="가성소다 (Caustic Soda)", src="sina", sym="SH0",
         unit="CNY/톤", source="Sina Finance · 가성소다 SH0", note=""),
    dict(id="px0", cat="화학/철강", name="파라자일렌 PX", src="sina", sym="PX0",
         unit="CNY/톤", source="Sina Finance · 파라자일렌 PX0",
         note="원 요청 라벨은 '프로필렌'이나 링크 종목은 PX(파라자일렌) PX0."),
    dict(id="v0", cat="화학/철강", name="PVC", src="sina", sym="V0",
         unit="CNY/톤", source="Sina Finance · DCE PVC V0", note=""),
    dict(id="pp0", cat="화학/철강", name="PP (폴리프로필렌)", src="sina", sym="PP0",
         unit="CNY/톤", source="Sina Finance · DCE PP0", note=""),
    dict(id="br0", cat="화학/철강", name="부타디엔 고무 (BR)", src="sina", sym="BR0",
         unit="CNY/톤", source="Sina Finance · 부타디엔고무 BR0", note=""),
    dict(id="i0", cat="화학/철강", name="철광석 (Iron Ore)", src="sina", sym="I0",
         unit="CNY/톤", source="Sina Finance · DCE 철광석 I0", note=""),
    dict(id="rb0", cat="화학/철강", name="철근 (Rebar)", src="sina", sym="RB0",
         unit="CNY/톤", source="Sina Finance · SHFE 철근 RB0", note=""),
    dict(id="ss0", cat="화학/철강", name="스테인리스 스틸", src="sina", sym="SS0",
         unit="CNY/톤", source="Sina Finance · SHFE 스테인리스 SS0", note=""),
    dict(id="hc0", cat="화학/철강", name="열연강판 (HRC)", src="sina", sym="HC0",
         unit="CNY/톤", source="Sina Finance · SHFE 열연 HC0", note=""),
    dict(id="ad0", cat="화학/철강", name="주조 알루미늄 합금", src="sina", sym="AD0",
         unit="CNY/톤", source="Sina Finance · SHFE 알루미늄합금 AD0", note=""),
    dict(id="sn0", cat="화학/철강", name="주석 (Tin)", src="sina", sym="SN0",
         unit="CNY/톤", source="Sina Finance · SHFE 주석 SN0", note=""),
    dict(id="ni0", cat="화학/철강", name="니켈 (Nickel, SHFE)", src="sina", sym="NI0",
         unit="CNY/톤", source="Sina Finance · SHFE 니켈 NI0", note=""),

    # ── 6. 식료품 ───────────────────────────────────────────────
    dict(id="p0", cat="식료품", name="팜유 (Palm Oil)", src="sina", sym="P0",
         unit="CNY/톤", source="Sina Finance · DCE 팜유 P0", note=""),
    dict(id="wheat", cat="식료품", name="미국 소맥 (Wheat)", src="yahoo", sym="ZW=F",
         unit="USc/부셸", source="Yahoo Finance · CBOT ZW=F (미국)", note=""),
    dict(id="corn", cat="식료품", name="미국 옥수수 (Corn)", src="yahoo", sym="ZC=F",
         unit="USc/부셸", source="Yahoo Finance · CBOT ZC=F (미국)", note=""),
    dict(id="soybean", cat="식료품", name="미국 대두 (Soybeans)", src="yahoo", sym="ZS=F",
         unit="USc/부셸", source="Yahoo Finance · CBOT ZS=F (미국)", note=""),

    # ── 7. 희소금속 (KOMIS · 월별 · 최근 3년) ───────────────────
    dict(id="komis_w", cat="희소금속", name="텅스텐 (Ferro-tungsten 75%)", src="komis",
         sym="MNRL0018", crtr="796", spec="75", unit="USD/kg",
         source="KOMIS 한국자원정보서비스 · Ferro-tungsten 75%min FOB China", note="일별·최근 3년"),
    dict(id="komis_nd", cat="희소금속", name="네오디뮴 (Neodymium Oxide)", src="komis",
         sym="MNRL1001", crtr="757", spec="99.5", unit="USD/kg",
         source="KOMIS 한국자원정보서비스 · Neodymium Oxide 99.5%min FOB China", note="일별·최근 3년"),
    dict(id="komis_dy", cat="희소금속", name="디스프로슘 (Dysprosium Oxide)", src="komis",
         sym="MNRL1004", crtr="803", spec="99.5", unit="USD/kg",
         source="KOMIS 한국자원정보서비스 · Dysprosium Oxide 99.5%min FOB China", note="일별·최근 3년"),
    dict(id="komis_ti", cat="희소금속", name="티타늄 (Ferro-titanium 70%)", src="komis",
         sym="MNRL0017", crtr="761", spec="70", unit="USD/kg",
         source="KOMIS 한국자원정보서비스 · Ferro-titanium 70%min In warehouse Rotterdam", note="일별·최근 3년"),
    dict(id="komis_mo", cat="희소금속", name="몰리브덴 (Ferro-molybdenum 60%)", src="komis",
         sym="MNRL0012", crtr="763", spec="60", unit="USD/mt",
         source="KOMIS 한국자원정보서비스 · Ferro-molybdenum 60%min EXW China", note="일별·최근 3년"),
]

CATEGORIES = ["반도체", "배터리", "에너지", "태양광", "화학/철강", "식료품", "희소금속"]

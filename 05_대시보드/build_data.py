# -*- coding: utf-8 -*-
"""
build_data.py — 대시보드 데이터 빌더

저장소의 원자료(02_수집자료)를 읽어 대시보드가 쓰는 단일 JSON을 만든다.
`--live` 옵션을 주면 NAVER 데이터랩 API를 호출해 최신 월까지 시계열을 연장한 뒤 빌드한다.

사용법
    python build_data.py           # 저장소 CSV만으로 빌드 (오프라인, 기본)
    python build_data.py --live    # API 재조회 후 빌드 (.env 필요)

지표 정의는 2026-08-19 팀 확정 기준을 따른다.
  - '제주' 연상 비중 = `이니스프리 제주` 단독 ÷ 브랜드   (합산 금지)
  - 경쟁 검색 점유율 = 3사·2사 병기, 게이트 판정은 2사
  - 지수 계열 = 일간 정밀(과거 확정) + 월간 API(라이브) 병기
자세한 근거: 02_수집자료/검색지수_표준수치표_2021-2026.md
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
SRC = REPO / "02_수집자료"
OUT = HERE / "data" / "dashboard_data.json"

KST = timezone(timedelta(hours=9))

# 라이브 조회에 쓰는 API 클라이언트 위치 (팀 공용 키 보관처)
API_APP = Path(r"C:\Users\EZ\Downloads\naver_api_streamlit_dashboard")


# ── 원자료 로더 ────────────────────────────────────────────────
def load_monthly_api() -> dict[str, dict[str, float]]:
    """naver_datalab_2021-2026_월간.csv → {그룹: {기간: 값}}  (월간 API 계열)"""
    out: dict[str, dict[str, float]] = {}
    with open(SRC / "naver_datalab_2021-2026_월간.csv", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            key = f'{row["호출"].split("_")[0]}:{row["그룹"]}'
            out.setdefault(key, {})[row["기간"]] = float(row["상대검색량"])
    return out


def load_daily_summary() -> dict[str, dict[str, float]]:
    """naver_datalab_일간원자료_월간요약.csv → {계열: {기간: 값}}  (일간 계열)"""
    out: dict[str, dict[str, float]] = {}
    with open(SRC / "naver_datalab_일간원자료_월간요약.csv", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            period = row["기간"][:7]
            for k, v in row.items():
                if k == "기간" or not v:
                    continue
                out.setdefault(k, {})[period] = float(v)
    return out


# ── 집계 헬퍼 ─────────────────────────────────────────────────
def months_of(series: dict[str, float], year: int, upto: str | None = None) -> list[str]:
    ms = [m for m in series if m.startswith(str(year))]
    if upto:
        ms = [m for m in ms if m <= upto]
    return sorted(ms)


def mean(vals: list[float]) -> float | None:
    return sum(vals) / len(vals) if vals else None


def annual(series: dict[str, float], year: int) -> float | None:
    ms = months_of(series, year)
    return mean([series[m] for m in ms]) if len(ms) == 12 else None


def ytd(series: dict[str, float], year: int, upto_month: int) -> float | None:
    ms = [f"{year}-{m:02d}" for m in range(1, upto_month + 1)]
    vals = [series[m] for m in ms if m in series]
    return mean(vals) if len(vals) == upto_month else None


def pct(a: float | None, b: float | None) -> float | None:
    if a in (None, 0) or b is None:
        return None
    return round((b - a) / a * 100, 1)


# ── 라이브 갱신 ────────────────────────────────────────────────
def refresh_live() -> str:
    """NAVER 데이터랩 재조회 → 02_수집자료 CSV 갱신. 성공 시 마지막 월 반환."""
    sys.path.insert(0, str(API_APP))
    try:
        from naver_api import NaverClient  # type: ignore
    except ImportError as e:
        raise SystemExit(f"[live] API 클라이언트를 찾을 수 없습니다: {API_APP}\n  {e}")

    env: dict[str, str] = {}
    env_file = API_APP / ".env"
    if not env_file.exists():
        raise SystemExit(f"[live] .env가 없습니다: {env_file}")
    for line in env_file.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.strip().startswith("#"):
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip().strip('"').strip("'")

    cli = NaverClient(client_id=env["NAVER_CLIENT_ID"], client_secret=env["NAVER_CLIENT_SECRET"])
    today = datetime.now(KST).date()
    start, end = "2021-01-01", today.isoformat()

    calls = {
        "1_내부_그룹합산": [
            {"groupName": "브랜드", "keywords": ["이니스프리"]},
            {"groupName": "제주_그린티계", "keywords": ["이니스프리 제주", "이니스프리 그린티"]},
            {"groupName": "제주_화산송이계", "keywords": ["이니스프리 제주", "이니스프리 화산송이"]},
            {"groupName": "제품군", "keywords": ["이니스프리 레티놀", "이니스프리 앰플"]},
            {"groupName": "리브랜딩", "keywords": ["이니스프리 리뉴얼", "이니스프리 로고"]},
        ],
        "2_경쟁사비교": [
            {"groupName": "이니스프리", "keywords": ["이니스프리"]},
            {"groupName": "토니모리", "keywords": ["토니모리"]},
            {"groupName": "미샤", "keywords": ["미샤"]},
        ],
        "3_키워드분해": [
            {"groupName": "브랜드", "keywords": ["이니스프리"]},
            {"groupName": "제주", "keywords": ["이니스프리 제주"]},
            {"groupName": "그린티", "keywords": ["이니스프리 그린티"]},
            {"groupName": "화산송이", "keywords": ["이니스프리 화산송이"]},
            {"groupName": "레티놀", "keywords": ["이니스프리 레티놀"]},
        ],
    }

    rows, raw, last = [], {}, ""
    for call, groups in calls.items():
        res = cli.datalab_search(start_date=start, end_date=end, time_unit="month", keyword_groups=groups)
        raw[call] = res
        for r in res["results"]:
            kw = ", ".join(r["keywords"])
            for d in r["data"]:
                p = d["period"][:7]
                last = max(last, p)
                rows.append([call, r["title"], kw, p, d["ratio"]])
        print(f"  [live] {call} · {len(res['results'])}개 그룹")

    with open(SRC / "naver_datalab_2021-2026_월간.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["호출", "그룹", "키워드", "기간", "상대검색량"])
        w.writerows(rows)
    (SRC / "naver_datalab_2021-2026_원자료.json").write_text(
        json.dumps({"_메모": f"라이브 갱신 {datetime.now(KST):%Y-%m-%d %H:%M} KST", **raw},
                   ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"  [live] CSV·JSON 갱신 완료 (최종 {last})")
    return last


# ── 빌드 ──────────────────────────────────────────────────────
def build(live: bool = False) -> dict:
    if live:
        print("[1/3] NAVER 데이터랩 라이브 재조회")
        refresh_live()
    else:
        print("[1/3] 저장소 CSV 사용 (오프라인)")

    print("[2/3] 집계")
    api = load_monthly_api()
    daily = load_daily_summary()

    brand = api["3:브랜드"]
    jeju = api["3:제주"]
    greentea = api["3:그린티"]
    volcanic = api["3:화산송이"]
    product = api["1:제품군"]
    inn = api["2:이니스프리"]
    tony = api["2:토니모리"]
    misha = api["2:미샤"]

    all_months = sorted(brand)
    last_full = max(m for m in all_months if len(months_of(brand, int(m[:4]))) >= int(m[5:7]))
    # 미완월 판정: 마지막 월은 조회일 기준 진행 중일 수 있음 → 집계에서 제외
    latest = all_months[-1]
    complete = all_months[:-1] if len(all_months) > 1 else all_months
    ytd_month = int(complete[-1][5:7]) if complete[-1].startswith(complete[-1][:4]) else 7
    cur_year = int(complete[-1][:4])
    prev_year = cur_year - 1
    if ytd_month == 12:
        ytd_month = 12

    # 연도별 시계열 (월간 API 계열)
    years = sorted({int(m[:4]) for m in all_months})
    full_years = [y for y in years if annual(brand, y) is not None]

    def annual_series(s):
        return {str(y): round(annual(s, y), 4) for y in full_years if annual(s, y) is not None}

    # 제주 단독 비중
    jeju_ratio = {str(y): round(annual(jeju, y) / annual(brand, y) * 100, 2)
                  for y in full_years}
    product_ratio = {str(y): round(annual(product, y) / annual(brand, y) * 100, 2)
                     for y in full_years}

    # 점유율 3사 / 2사
    share3, share2 = {}, {}
    for y in full_years:
        i, t, m = annual(inn, y), annual(tony, y), annual(misha, y)
        share3[str(y)] = round(i / (i + t + m) * 100, 1)
        share2[str(y)] = round(i / (i + m) * 100, 1)

    # YTD 동일구간 비교 (계절성 통제)
    ytd_cur = {k: ytd(s, cur_year, ytd_month) for k, s in
               dict(brand=brand, jeju=jeju, product=product, inn=inn, tony=tony, misha=misha).items()}
    ytd_prev = {k: ytd(s, prev_year, ytd_month) for k, s in
                dict(brand=brand, jeju=jeju, product=product, inn=inn, tony=tony, misha=misha).items()}

    def ytd_share(d):
        return round(d["inn"] / (d["inn"] + d["misha"]) * 100, 1), \
               round(d["inn"] / (d["inn"] + d["tony"] + d["misha"]) * 100, 1)

    s2_cur, s3_cur = ytd_share(ytd_cur)
    s2_prev, s3_prev = ytd_share(ytd_prev)

    brand_yoy = pct(ytd_prev["brand"], ytd_cur["brand"])
    product_yoy = pct(ytd_prev["product"], ytd_cur["product"])
    jeju_ratio_cur = round(ytd_cur["jeju"] / ytd_cur["brand"] * 100, 2)
    jeju_ratio_prev = round(ytd_prev["jeju"] / ytd_prev["brand"] * 100, 2)
    # Gap은 반올림값끼리 빼면 오차가 누적되므로 원값으로 계산한 뒤 반올림한다
    gap = None
    if None not in (ytd_prev["product"], ytd_cur["product"], ytd_prev["brand"], ytd_cur["brand"]):
        gap = round((ytd_cur["product"] - ytd_prev["product"]) / ytd_prev["product"] * 100
                    - (ytd_cur["brand"] - ytd_prev["brand"]) / ytd_prev["brand"] * 100, 1)

    # 월별 2사 점유율 (KPI 카드 스파크라인용)
    share2_monthly = [
        round(inn[m] / (inn[m] + misha[m]) * 100, 2) if inn.get(m) and misha.get(m) else None
        for m in all_months
    ]

    # ── 일간 정밀 계열 (표준수치표 기준) ──────────────────────────
    # 월간요약 CSV의 값은 '월평균'이므로, 그냥 12개를 평균하면 월 길이가 무시된
    # 단순평균 계열(8.515·YoY -38.6%)이 나온다. 이는 2026-08-19에 폐기된 계열이다.
    # 각 월평균에 그 달의 일수를 가중해야 1,826일 참평균(8.503·YoY -38.5%)이 재현된다.
    import calendar

    def daily_annual(col: str, year: int) -> float | None:
        num = den = 0.0
        for mth in range(1, 13):
            key = f"{year}-{mth:02d}"
            if key not in daily.get(col, {}):
                return None
            days = calendar.monthrange(year, mth)[1]
            num += daily[col][key] * days
            den += days
        return num / den if den else None

    DAILY_YEARS = range(2021, 2026)
    daily_brand = {str(y): round(daily_annual("이니스프리", y), 3)
                   for y in DAILY_YEARS if daily_annual("이니스프리", y) is not None}
    daily_yoy = {}
    ys = sorted(daily_brand)
    for a, b in zip(ys, ys[1:]):
        daily_yoy[b] = round((daily_brand[b] - daily_brand[a]) / daily_brand[a] * 100, 1)

    # 제품군 비중도 같은 계열로 산출해 표준수치표(1.07% → 11.67%)와 일치시킨다
    daily_product_ratio = {}
    for y in DAILY_YEARS:
        b, p = daily_annual("이니스프리", y), daily_annual("기능성", y)
        if b and p:
            daily_product_ratio[str(y)] = round(p / b * 100, 2)

    print("[3/3] JSON 출력")
    data = {
        "meta": {
            "generated_at": datetime.now(KST).strftime("%Y-%m-%d %H:%M KST"),
            "source_mode": "live" if live else "repo",
            "coverage": f"{all_months[0]} ~ {all_months[-1]}",
            "latest_partial_month": latest,
            "ytd_window": f"{cur_year} 1~{ytd_month}월 vs {prev_year} 동기",
            "definitions": {
                "jeju": "'이니스프리 제주' 단독 ÷ 브랜드 (2026-08-19 확정 · 합산 금지)",
                "share": "3사·2사 병기, 게이트 판정은 2사(이니스프리+미샤)",
                "index": "월간 API 계열(라이브) · 과거 확정치는 일간 정밀 계열 병기",
                "standard_doc": "02_수집자료/검색지수_표준수치표_2021-2026.md",
            },
            "sources": ["NAVER 데이터랩 검색어트렌드", "DART 감사보고서", "공정거래위원회 정보공개서",
                        "한국기업평판연구소", "Meta 광고 라이브러리"],
        },
        "kpi": {
            "brand_search": {"yoy": brand_yoy, "cum5y": pct(annual(brand, full_years[0]),
                                                            annual(brand, full_years[-1]))},
            "jeju_ratio": {"current": jeju_ratio_cur, "prev": jeju_ratio_prev,
                           "peak_year": max(jeju_ratio, key=lambda k: jeju_ratio[k]),
                           "peak": max(jeju_ratio.values()),
                           "abs_yoy": pct(ytd_prev["jeju"], ytd_cur["jeju"])},
            "gap": {"ytd": gap, "brand_yoy": brand_yoy, "product_yoy": product_yoy},
            "share": {"two": s2_cur, "two_prev": s2_prev, "three": s3_cur, "three_prev": s3_prev},
            "aeo": {"score": 1, "total": 4, "checked": "2026-08-19",
                    "items": [
                        {"k": "llms.txt", "ok": True, "note": "200 OK · 2026-08-19 신규 생성(8/18에는 404)"},
                        {"k": "robots.txt AI 크롤러 규칙", "ok": False, "note": "범용 규칙만 존재"},
                        {"k": "FAQPage 스키마(JSON-LD)", "ok": None, "note": "정적 조회 한계 · 판정 보류"},
                        {"k": "FAQ형 콘텐츠 비중", "ok": False, "note": "제품나열형 구조"},
                    ]},
        },
        "series": {
            "monthly": {"months": all_months,
                        "brand": [brand[m] for m in all_months],
                        "jeju": [jeju.get(m) for m in all_months],
                        "greentea": [greentea.get(m) for m in all_months],
                        "volcanic": [volcanic.get(m) for m in all_months],
                        "product": [product.get(m) for m in all_months],
                        "tony": [tony.get(m) for m in all_months],
                        "misha": [misha.get(m) for m in all_months],
                        "share2": share2_monthly},
            "annual": {"years": [str(y) for y in full_years],
                       "brand_api": annual_series(brand),
                       "brand_daily": daily_brand,
                       "brand_daily_yoy": daily_yoy,
                       "jeju_ratio": jeju_ratio,
                       "product_ratio": daily_product_ratio,
                       "product_ratio_api": product_ratio,
                       "share3": share3, "share2": share2},
        },
        # 저장소 문서에서 확정된 비검색 지표 (출처 주석 포함)
        "fixed": {
            "stores": {"2021": 400, "2022": 324, "2023": 234, "2024": 190,
                       "_note": "공정위 정보공개서 · 2024년말 190개가 인용 가능한 최신 공식치. 147개는 2025 가맹점협의회 주장치(비공식)"},
            "ad_spend": {"2021": 261.3, "2022": 243.6, "2023": 344.9, "2024": 273.9, "2025": 247.6,
                         "_note": "DART 감사보고서 주석21 · 억원. 광고선전비는 전체 마케팅비가 아님"},
            "correlation": {"store_brand": 0.98, "ad_brand": -0.03, "ad_product": 0.69,
                            "_note": "n=4~5로 표본이 작다. 상관이지 인과가 아니며 역인과 배제 안 됨"},
            "reputation": [{"p": "2021~2022", "rank": 2}, {"p": "2023-02", "rank": 3},
                           {"p": "2023 하반기", "rank": 2}, {"p": "2024H2~2025", "rank": 3},
                           {"_note": "버즈량 지표이지 선호도 아님 · 결측월 많아 분기 경향으로만 인용"}],
            "meta_ads": {"이니스프리": 220, "토니모리": 64, "미샤": 4, "3CE": 10,
                         "_note": "브랜드 스토리텔링 광고는 네 브랜드 모두 0건. 3CE는 참고군(로레알·색조 전문)"},
        },
        "events": [
            {"date": "2023-02", "label": "리브랜딩 발표", "kind": "major",
             "desc": "제주 → THE NEW ISLE 세계관 전환, 로고·컬러·용기·매장 전면 교체"},
            {"date": "2023-04", "label": "그린티 캠페인 피크", "kind": "minor",
             "desc": "2022 연평균 대비 2.73배"},
            {"date": "2024-01", "label": "광고선전비 -20.6%", "kind": "major",
             "desc": "증액 1년 만에 철회 · 같은 해 브랜드 검색 최대 낙폭"},
            {"date": "2024-07", "label": "PDRN 앰플 출시", "kind": "minor",
             "desc": "출시 당일 올리브영 판매 1위(회사 발표 기준)"},
            {"date": "2026-02", "label": "토니모리 레벨 시프트", "kind": "warn",
             "desc": "대조군 붕괴 · 검색량 대조군을 미샤로 대체(2026-08-19 확정)"},
        ],
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"완료 → {OUT.relative_to(REPO)}  ({OUT.stat().st_size/1024:.0f} KB)")
    print(f"  기간 {data['meta']['coverage']} · 모드 {data['meta']['source_mode']}")
    print(f"  브랜드 YoY {brand_yoy}% · 제주 {jeju_ratio_cur}% · 점유율(2사) {s2_cur}%")
    return data


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="대시보드 데이터 빌드")
    ap.add_argument("--live", action="store_true", help="NAVER API 재조회 후 빌드")
    build(live=ap.parse_args().live)

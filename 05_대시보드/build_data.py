# -*- coding: utf-8 -*-
"""
build_data.py — 대시보드 데이터 빌더

저장소의 원자료(02_수집자료)를 읽어 대시보드가 쓰는 단일 JSON을 만든다.
`--live` 옵션을 주면 NAVER 데이터랩 API를 호출해 최신 월까지 시계열을 연장한 뒤 빌드한다.

사용법
    python build_data.py             # 저장소 CSV만으로 빌드 (오프라인, 기본)
    python build_data.py --live      # API 재조회 후 빌드 (.env 필요)
    python build_data.py --standalone  # 공유용 단일 HTML(artifact) 함께 생성

지표 정의 (2026-08-19 팀 확정 + 2026-08-19 3CE 편입)
  - '제주' 연상 비중 = `이니스프리 제주` 단독 ÷ 브랜드   (합산 금지)
  - 경쟁 검색 점유율 = 직접경쟁 3사(이니스프리·미샤·3CE) 기준으로 판정.
      토니모리는 2026-02 레벨 시프트로 제외. 2사·4사는 참고 병기.
  - 지수 계열 = 일간 정밀(과거 확정) + 월간 API(라이브) 병기
자세한 근거: 02_수집자료/검색지수_표준수치표_2021-2026.md
"""
from __future__ import annotations

import argparse
import calendar
import csv
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
SRC = REPO / "02_수집자료"
OUT = HERE / "data" / "dashboard_data.json"
SNAPDIR = HERE / "data" / "snapshots"

KST = timezone(timedelta(hours=9))
API_APP = Path(r"C:\Users\EZ\Downloads\naver_api_streamlit_dashboard")

# 경쟁 검색 점유율 구성 (2026-08-19 확정)
DIRECT = ["이니스프리", "미샤", "3CE"]          # 직접경쟁 — 게이트 판정 기준
PAIR = ["이니스프리", "미샤"]                    # 참고: 최소 구성
ALL4 = ["이니스프리", "미샤", "3CE", "토니모리"]  # 참고: 토니모리 포함(붕괴 착시 주의)


# ── 원자료 로더 ────────────────────────────────────────────────
def load_monthly_api() -> dict[str, dict[str, float]]:
    out: dict[str, dict[str, float]] = {}
    with open(SRC / "naver_datalab_2021-2026_월간.csv", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            key = f'{row["호출"].split("_")[0]}:{row["그룹"]}'
            out.setdefault(key, {})[row["기간"]] = float(row["상대검색량"])
    return out


def load_daily_summary() -> dict[str, dict[str, float]]:
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
def mean(v: list[float]) -> float | None:
    return sum(v) / len(v) if v else None


def annual(s: dict[str, float], y: int) -> float | None:
    ms = [m for m in s if m.startswith(str(y))]
    return mean([s[m] for m in ms]) if len(ms) == 12 else None


def ytd(s: dict[str, float], y: int, upto: int) -> float | None:
    ms = [f"{y}-{m:02d}" for m in range(1, upto + 1)]
    v = [s[m] for m in ms if m in s]
    return mean(v) if len(v) == upto else None


def pct(a, b):
    return None if a in (None, 0) or b is None else round((b - a) / a * 100, 1)


LONGTAIL_FILE = SRC / "롱테일_실측.json"


def load_longtail() -> dict | None:
    """02_수집자료/롱테일_2차_자산축.py 산출물을 읽는다.

    조회 구간(2025-08~2026-08)이 본 시계열과 달라 별도 파일로 둔다.
    없으면 대시보드에서 해당 섹션을 그리지 않는다.
    """
    if not LONGTAIL_FILE.exists():
        print("  [메모] 롱테일_실측.json 없음 — 롱테일 섹션 생략")
        return None
    try:
        return json.loads(LONGTAIL_FILE.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"  [경고] 롱테일_실측.json 읽기 실패: {e}")
        return None


# ── 라이브 갱신 ────────────────────────────────────────────────
CALLS = {
    "1_내부_그룹합산": [
        {"groupName": "브랜드", "keywords": ["이니스프리"]},
        {"groupName": "제주_그린티계", "keywords": ["이니스프리 제주", "이니스프리 그린티"]},
        {"groupName": "제주_화산송이계", "keywords": ["이니스프리 제주", "이니스프리 화산송이"]},
        {"groupName": "제품군", "keywords": ["이니스프리 레티놀", "이니스프리 앰플"]},
        {"groupName": "리브랜딩", "keywords": ["이니스프리 리뉴얼", "이니스프리 로고"]},
    ],
    "2_경쟁사비교": [
        {"groupName": "이니스프리", "keywords": ["이니스프리"]},
        {"groupName": "미샤", "keywords": ["미샤"]},
        {"groupName": "3CE", "keywords": ["3CE"]},
        {"groupName": "토니모리", "keywords": ["토니모리"]},
        {"groupName": "에뛰드", "keywords": ["에뛰드"]},
    ],
    "3_키워드분해": [
        {"groupName": "브랜드", "keywords": ["이니스프리"]},
        {"groupName": "제주", "keywords": ["이니스프리 제주"]},
        {"groupName": "그린티", "keywords": ["이니스프리 그린티"]},
        {"groupName": "화산송이", "keywords": ["이니스프리 화산송이"]},
        {"groupName": "레티놀", "keywords": ["이니스프리 레티놀"]},
    ],
}


def refresh_live() -> str:
    sys.path.insert(0, str(API_APP))
    try:
        from naver_api import NaverClient  # type: ignore
    except ImportError as e:
        raise SystemExit(f"[live] API 클라이언트를 찾을 수 없습니다: {API_APP}\n  {e}")

    env_file = API_APP / ".env"
    if not env_file.exists():
        raise SystemExit(f"[live] .env가 없습니다: {env_file}")
    env = {}
    for line in env_file.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.strip().startswith("#"):
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip().strip('"').strip("'")

    cli = NaverClient(client_id=env["NAVER_CLIENT_ID"], client_secret=env["NAVER_CLIENT_SECRET"])
    start, end = "2021-01-01", datetime.now(KST).date().isoformat()

    rows, raw, last = [], {}, ""
    for call, groups in CALLS.items():
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


# ── 경보 규칙 ─────────────────────────────────────────────────
def make_alerts(k: dict, prev: dict | None) -> list[dict]:
    """KPI가 게이트를 벗어나면 경보.

    경보는 '화면의 다른 곳에 없는 정보'만 띄운다. 카드·차트 캡션에 이미 쓰여 있는
    내용을 경보로 중복 표시하면 배너가 KPI를 가려서 대시보드가 못 쓰게 된다.
    (2026-08-20 정리 — 6건 → 3건)

    의도적으로 뺀 것
      · 제주 '정점 이후 정체'  → KPI 카드에 정점 연도·값이 이미 표시됨
      · 4사 기준 상승(착시)    → 카드 sub와 점유율 차트 캡션에 이미 있음
      · 직전 갱신 대비 변화    → '변화 이력' 화면이 따로 있음
    """
    a: list[dict] = []

    if (k["brand_search"]["yoy"] or 0) < -25:
        a.append({"level": "high", "kpi": "브랜드 검색지수",
                  "msg": f'YoY {k["brand_search"]["yoy"]}% — 90일 게이트(낙폭 축소) 미달, 하락 지속',
                  "action": "KR1 게이트 재판정 · 개입 시점 대비 초과분 확인 필요"})

    jr = k["jeju_ratio"]
    if (jr["abs_yoy"] or 0) <= (k["brand_search"]["yoy"] or 0):
        a.append({"level": "high", "kpi": "‘제주’ 연상",
                  "msg": f'제주 절대 지수 {jr["abs_yoy"]}%가 브랜드 {k["brand_search"]["yoy"]}%보다 빠르게 하락',
                  "action": "‘브랜드보다 오래 버틴다’는 우위가 소멸 — 헤리티지 캠페인 우선순위 상향"})
    s = k["share"]
    if s["direct"] < s["direct_prev"]:
        a.append({"level": "high", "kpi": "경쟁 검색 점유율",
                  "msg": f'직접경쟁 3사 기준 {s["direct_prev"]}% → {s["direct"]}% 하락',
                  "action": "KR4 게이트 미달 — 3CE·미샤 대비 상대 위치 점검"})
    return a


# ── 스냅샷 ────────────────────────────────────────────────────
def load_prev_snapshot() -> dict | None:
    if not SNAPDIR.exists():
        return None
    files = sorted(SNAPDIR.glob("*.json"))
    if not files:
        return None
    try:
        return json.loads(files[-1].read_text(encoding="utf-8"))
    except Exception:
        return None


def diff_vs(prev: dict | None, cur: dict) -> dict:
    if not prev:
        return {"base": None, "rows": []}
    fields = [
        ("브랜드 검색 YoY", ["kpi", "brand_search", "yoy"], "%"),
        ("‘제주’ 연상 비중", ["kpi", "jeju_ratio", "current"], "%"),
        ("제품↔브랜드 Gap", ["kpi", "gap", "ytd"], "%p"),
        ("점유율(직접 3사)", ["kpi", "share", "direct"], "%"),
    ]
    rows = []
    for label, path, unit in fields:
        def dig(d):
            for p in path:
                d = (d or {}).get(p) if isinstance(d, dict) else None
            return d
        a, b = dig(prev), dig(cur)
        if a is None or b is None:
            continue
        rows.append({"label": label, "prev": a, "cur": b,
                     "delta": round(b - a, 2), "unit": unit})
    return {"base": prev.get("meta", {}).get("generated_at"), "rows": rows}


# ── 빌드 ──────────────────────────────────────────────────────
def build(live=False, standalone=False) -> dict:
    print("[1/4] " + ("NAVER 데이터랩 라이브 재조회" if live else "저장소 CSV 사용 (오프라인)"))
    if live:
        refresh_live()

    print("[2/4] 집계")
    api = load_monthly_api()
    daily = load_daily_summary()

    brand, jeju = api["3:브랜드"], api["3:제주"]
    greentea, volcanic = api["3:그린티"], api["3:화산송이"]
    product = api["1:제품군"]
    comp = {n: api.get(f"2:{n}") for n in ["이니스프리", "미샤", "3CE", "토니모리", "에뛰드"]}
    comp = {k: v for k, v in comp.items() if v}
    has3ce = "3CE" in comp

    all_months = sorted(brand)
    complete = all_months[:-1]
    cur_year, ytd_month = int(complete[-1][:4]), int(complete[-1][5:7])
    prev_year = cur_year - 1
    full_years = [y for y in sorted({int(m[:4]) for m in all_months}) if annual(brand, y) is not None]

    jeju_ratio = {str(y): round(annual(jeju, y) / annual(brand, y) * 100, 2) for y in full_years}

    # ── 헤리티지 자산 감가 ────────────────────────────────────
    # 비중(제주÷브랜드)만 보면 분모가 무너져도 올라 보인다. 절대 지수의 YoY를
    # 브랜드와 나란히 놓아야 "제주가 더 버티는가, 더 빨리 빠지는가"가 보인다.
    # 2025년에 역전됐다 — 제주 -30.2% vs 브랜드 -28.9%.
    def yoy_series(s):
        out, ys = {}, [y for y in full_years if annual(s, y)]
        for a, b in zip(ys, ys[1:]):
            out[str(b)] = round((annual(s, b) - annual(s, a)) / annual(s, a) * 100, 1)
        return out

    decay = {
        "years": [str(y) for y in full_years],
        "abs": {k: {str(y): round(annual(v, y), 3) for y in full_years if annual(v, y)}
                for k, v in {"브랜드": brand, "제주": jeju,
                             "그린티": api.get("3:그린티", {}),
                             "화산송이": api.get("3:화산송이", {}),
                             "제품군(레티놀)": api.get("3:레티놀", {})}.items()},
        "yoy": {k: yoy_series(v)
                for k, v in {"브랜드": brand, "제주": jeju,
                             "제품군(레티놀)": api.get("3:레티놀", {})}.items()},
        "_note": "월간 API 계열. 제주 우위 역전 시점과 제품군 피크 이후 하락을 함께 본다",
    }
    # 우위 역전 판정 — 제주 낙폭이 브랜드보다 커진 첫 해
    flip = None
    for y in decay["yoy"].get("제주", {}):
        j, b = decay["yoy"]["제주"].get(y), decay["yoy"]["브랜드"].get(y)
        if j is not None and b is not None and j < b and flip is None:
            flip = {"year": y, "jeju": j, "brand": b}
    decay["flip"] = flip
    # 제품군 피크 연도와 그 이후 낙폭
    pr = decay["abs"].get("제품군(레티놀)", {})
    if pr:
        pk = max(pr, key=lambda k: pr[k])
        last = sorted(pr)[-1]
        decay["product_peak"] = {"year": pk, "value": pr[pk], "last_year": last,
                                 "last": pr[last],
                                 "drop": round((pr[last] - pr[pk]) / pr[pk] * 100, 1)}

    def share_of(names, y, use_ytd=False):
        f = (lambda s: ytd(s, y, ytd_month)) if use_ytd else (lambda s: annual(s, y))
        vs = {n: f(comp[n]) for n in names if n in comp}
        if len(vs) != len(names) or any(v is None for v in vs.values()):
            return None
        return round(vs["이니스프리"] / sum(vs.values()) * 100, 1)

    share_direct = {str(y): share_of(DIRECT, y) for y in full_years}
    share_pair = {str(y): share_of(PAIR, y) for y in full_years}
    share_all4 = {str(y): share_of(ALL4, y) for y in full_years}

    ytd_cur = {k: ytd(s, cur_year, ytd_month) for k, s in
               dict(brand=brand, jeju=jeju, product=product).items()}
    ytd_prev = {k: ytd(s, prev_year, ytd_month) for k, s in
                dict(brand=brand, jeju=jeju, product=product).items()}

    brand_yoy = pct(ytd_prev["brand"], ytd_cur["brand"])
    product_yoy = pct(ytd_prev["product"], ytd_cur["product"])
    gap = None
    if None not in (ytd_prev["product"], ytd_cur["product"], ytd_prev["brand"], ytd_cur["brand"]):
        gap = round((ytd_cur["product"] - ytd_prev["product"]) / ytd_prev["product"] * 100
                    - (ytd_cur["brand"] - ytd_prev["brand"]) / ytd_prev["brand"] * 100, 1)

    # 월별 점유율 (스파크라인)
    def monthly_share(names):
        out = []
        for m in all_months:
            vs = [comp[n].get(m) for n in names if n in comp]
            out.append(round(vs[0] / sum(vs) * 100, 2) if len(vs) == len(names) and all(vs) else None)
        return out

    # 일간 정밀 계열 (월평균에 일수 가중 → 1,826일 참평균 재현)
    def daily_annual(col, year):
        num = den = 0.0
        for mth in range(1, 13):
            key = f"{year}-{mth:02d}"
            if key not in daily.get(col, {}):
                return None
            d = calendar.monthrange(year, mth)[1]
            num += daily[col][key] * d
            den += d
        return num / den if den else None

    DY = range(2021, 2026)
    daily_brand = {str(y): round(daily_annual("이니스프리", y), 3)
                   for y in DY if daily_annual("이니스프리", y) is not None}
    daily_yoy = {}
    ys = sorted(daily_brand)
    for a, b in zip(ys, ys[1:]):
        daily_yoy[b] = round((daily_brand[b] - daily_brand[a]) / daily_brand[a] * 100, 1)
    daily_product_ratio = {}
    for y in DY:
        b, p = daily_annual("이니스프리", y), daily_annual("기능성", y)
        if b and p:
            daily_product_ratio[str(y)] = round(p / b * 100, 2)

    kpi = {
        "brand_search": {"yoy": brand_yoy,
                         "cum5y": pct(annual(brand, full_years[0]), annual(brand, full_years[-1]))},
        "jeju_ratio": {"current": round(ytd_cur["jeju"] / ytd_cur["brand"] * 100, 2),
                       "prev": round(ytd_prev["jeju"] / ytd_prev["brand"] * 100, 2),
                       "peak_year": max(jeju_ratio, key=lambda k: jeju_ratio[k]),
                       "peak": max(jeju_ratio.values()),
                       "abs_yoy": pct(ytd_prev["jeju"], ytd_cur["jeju"])},
        "gap": {"ytd": gap, "brand_yoy": brand_yoy, "product_yoy": product_yoy},
        "share": {
            "direct": share_of(DIRECT, cur_year, True), "direct_prev": share_of(DIRECT, prev_year, True),
            "pair": share_of(PAIR, cur_year, True), "pair_prev": share_of(PAIR, prev_year, True),
            "all4": share_of(ALL4, cur_year, True), "all4_prev": share_of(ALL4, prev_year, True),
            "members": DIRECT,
        },
    }

    prev_snap = load_prev_snapshot()
    data = {
        "meta": {
            "generated_at": datetime.now(KST).strftime("%Y-%m-%d %H:%M KST"),
            "source_mode": "live" if live else "repo",
            "coverage": f"{all_months[0]} ~ {all_months[-1]}",
            "latest_partial_month": all_months[-1],
            "ytd_window": f"{cur_year} 1~{ytd_month}월 vs {prev_year} 동기",
            "definitions": {
                "jeju": "'이니스프리 제주' 단독 ÷ 브랜드 (2026-08-19 확정 · 합산 금지)",
                "share": "직접경쟁 3사(이니스프리·미샤·3CE) 기준 판정 · 2사·4사 참고 병기",
                "index": "월간 API 계열(라이브) · 과거 확정치는 일간 정밀 계열 병기",
                "standard_doc": "02_수집자료/검색지수_표준수치표_2021-2026.md",
            },
            "sources": ["NAVER 데이터랩 검색어트렌드", "DART 감사보고서", "공정거래위원회 정보공개서",
                        "한국기업평판연구소", "Meta 광고 라이브러리"],
        },
        "kpi": kpi,
        "alerts": make_alerts(kpi, prev_snap),
        "diff": diff_vs(prev_snap, {"kpi": kpi}),
        "series": {
            "monthly": {"months": all_months,
                        "brand": [brand[m] for m in all_months],
                        "jeju": [jeju.get(m) for m in all_months],
                        "greentea": [greentea.get(m) for m in all_months],
                        "volcanic": [volcanic.get(m) for m in all_months],
                        "product": [product.get(m) for m in all_months],
                        **{f"c_{n}": [comp[n].get(m) for m in all_months] for n in comp},
                        "share_direct": monthly_share(DIRECT),
                        "share_pair": monthly_share(PAIR)},
            "annual": {"years": [str(y) for y in full_years],
                       "brand_api": {str(y): round(annual(brand, y), 4) for y in full_years},
                       "brand_daily": daily_brand, "brand_daily_yoy": daily_yoy,
                       "jeju_ratio": jeju_ratio, "product_ratio": daily_product_ratio,
                       "decay": decay, "longtail": load_longtail(),
                       "share_direct": share_direct, "share_pair": share_pair, "share_all4": share_all4,
                       "competitors": {n: {str(y): round(annual(comp[n], y), 3)
                                           for y in full_years if annual(comp[n], y)} for n in comp}},
        },
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
                         "_note": "브랜드 스토리텔링 광고는 네 브랜드 모두 0건"},
        },
        "events": [
            {"date": "2023-02", "label": "리브랜딩 발표", "kind": "major",
             "desc": "제주 → THE NEW ISLE 세계관 전환, 로고·컬러·용기·매장 전면 교체"},
            {"date": "2023-04", "label": "그린티 캠페인 피크", "kind": "minor",
             "desc": "2022 연평균 대비 2.73배"},
            {"date": "2024-01", "label": "광고선전비 −20.6%", "kind": "major",
             "desc": "증액 1년 만에 철회 · 같은 해 브랜드 검색 최대 낙폭"},
            {"date": "2024-07", "label": "PDRN 앰플 출시", "kind": "minor",
             "desc": "출시 당일 올리브영 판매 1위(회사 발표 기준)"},
            {"date": "2026-02", "label": "토니모리 레벨 시프트", "kind": "warn",
             "desc": "대조군 붕괴 · 검색량 대조군을 미샤·3CE로 대체(2026-08-19 확정)"},
        ],
    }

    print("[3/4] JSON·스냅샷 출력")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    SNAPDIR.mkdir(parents=True, exist_ok=True)
    (SNAPDIR / f"{datetime.now(KST):%Y-%m-%d}.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")

    print("[4/4] " + ("공유용 단일 HTML 생성" if standalone else "완료"))
    if standalone:
        make_standalone(data)

    print(f"→ {OUT.relative_to(REPO)}  ({OUT.stat().st_size/1024:.0f} KB)")
    print(f"  기간 {data['meta']['coverage']} · 모드 {data['meta']['source_mode']}")
    print(f"  브랜드 YoY {brand_yoy}% · 제주 {kpi['jeju_ratio']['current']}% · "
          f"점유율(직접3사) {kpi['share']['direct']}% · 경보 {len(data['alerts'])}건")
    if has3ce:
        print(f"  3CE 편입됨 — 직접경쟁 {DIRECT}")
    return data


def make_standalone(data: dict):
    """공유용 단일 HTML — 데이터·CSS·JS를 한 파일에 인라인(외부 요청 0)."""
    html = (HERE / "index.html").read_text(encoding="utf-8")
    css = (HERE / "assets" / "style.css").read_text(encoding="utf-8")
    js = (HERE / "assets" / "app.js").read_text(encoding="utf-8")
    import re
    # 치환 문자열에 JS/CSS의 백슬래시(정규식 \s 등)가 그대로 들어가므로 람다로 넘긴다
    html = re.sub(r'<link rel="stylesheet" href="assets/style\.css[^"]*">',
                  lambda _: f"<style>\n{css}\n</style>", html)
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    html = re.sub(r'<script src="assets/app\.js[^"]*"></script>',
                  lambda _: (f'<script>window.__DATA__={payload};</script>\n'
                             f'<script>\n{js}\n</script>'), html)
    # 외부 폰트 제거 (공유 환경의 CSP 차단 대비) — 시스템 한글 폰트로 대체
    html = html.replace(
        '<link href="https://fonts.googleapis.com/css2?family=Gowun+Batang:wght@400;700&family=Noto+Sans+KR:wght@300;400;500;700;900&display=swap" rel="stylesheet">',
        '<!-- 공유본: 외부 폰트 대신 시스템 한글 폰트 사용 -->')
    out = HERE / "share" / "dashboard_share.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    print(f"  공유본 → {out.relative_to(REPO)}  ({out.stat().st_size/1024:.0f} KB)")

    # 웹 게시(Artifact)용 조각 — 문서 골격은 게시 측이 감싸므로 body 내용만 남긴다
    body = re.search(r"<body[^>]*>(.*)</body>", html, re.S)
    style = re.search(r"<style>.*?</style>", html, re.S)
    frag = (style.group(0) if style else "") + "\n" + (body.group(1) if body else html)
    frag_out = HERE / "share" / "artifact.html"
    frag_out.write_text(frag, encoding="utf-8")
    print(f"  게시용 조각 → {frag_out.relative_to(REPO)}  ({frag_out.stat().st_size/1024:.0f} KB)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="대시보드 데이터 빌드")
    ap.add_argument("--live", action="store_true", help="NAVER API 재조회 후 빌드")
    ap.add_argument("--standalone", action="store_true", help="공유용 단일 HTML 생성")
    a = ap.parse_args()
    build(live=a.live, standalone=a.standalone)

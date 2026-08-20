# -*- coding: utf-8 -*-
"""세 가지를 확실하게 판정한다. 앞선 조회의 오류 두 개를 고치는 것이 목적이다.

오류 1 — 그린티 점유율을 카테고리로 나눴는데, 카테고리가 곧 이니스프리면 순환논리다.
        → 월별 상관계수로 "카테고리 = 이니스프리인가"를 직접 판정한다.
           레티놀(다브랜드 시장)을 대조군으로 두어 상관 수준을 비교한다.

오류 2 — 점유율만 보고 절대량을 안 봤다. 시장에 올라타 절대량이 늘었으면
        점유율 하락만으로 "지고 있다"고 할 수 없다.
        → 절대량 궤적과 상승기/하락기 탄력도를 따로 본다.

그리고 처치 변수(광고선전비)를 붙인다. DART 감사보고서 기준이므로
검색량 추정이 아니라 확정 수치다. 출처: 광고선전비_2019-2025_원자료.md
"""
import sys
from collections import defaultdict
from pathlib import Path

BASE = Path(r"C:\Users\EZ\Downloads\naver_api_streamlit_dashboard")
sys.path.insert(0, str(BASE))
sys.stdout.reconfigure(encoding="utf-8")
from naver_api import NaverClient  # noqa: E402

env = {}
for line in (BASE / ".env").read_text(encoding="utf-8").splitlines():
    if "=" in line and not line.strip().startswith("#"):
        k, v = line.split("=", 1)
        env[k.strip()] = v.strip().strip('"').strip("'")
cli = NaverClient(client_id=env["NAVER_CLIENT_ID"], client_secret=env["NAVER_CLIENT_SECRET"])

# DART 감사보고서 (주)이니스프리 국내법인 별도기준 · 단위 억원
AD = {2021: 261.3, 2022: 243.6, 2023: 344.9, 2024: 273.9, 2025: 247.6}
REV = {2021: 3071.7, 2022: 2997.4, 2023: 2738.0, 2024: 2246.1, 2025: 2098.5}
OP = {2021: -9.6, 2022: 324.0, 2023: 103.2, 2024: 16.4, 2025: 133.5}

GROUPS = [
    {"groupName": "녹차·그린티 카테고리", "keywords": ["녹차 화장품", "그린티 화장품", "녹차 크림"]},
    {"groupName": "이니스프리 그린티", "keywords": ["이니스프리 그린티", "이니스프리 녹차"]},
    {"groupName": "레티놀 카테고리", "keywords": ["레티놀", "레티놀 크림", "레티놀 앰플"]},
    {"groupName": "이니스프리 레티놀", "keywords": ["이니스프리 레티놀", "이니스프리 비타c"]},
    {"groupName": "이니스프리(브랜드)", "keywords": ["이니스프리"]},
]

res = cli.datalab_search(start_date="2021-01-01", end_date="2026-08-18",
                        time_unit="month", keyword_groups=GROUPS)

monthly, yearly = {}, {}
for r in res["results"]:
    pts = [(d["period"][:7], d["ratio"]) for d in r["data"]]
    monthly[r["title"]] = dict(pts)
    by_y = defaultdict(list)
    for p, v in pts:
        by_y[int(p[:4])].append(v)
    yearly[r["title"]] = {y: sum(v) / len(v) for y, v in by_y.items()}


def pearson(a, b):
    keys = sorted(set(a) & set(b))
    n = len(keys)
    if n < 3:
        return None, n
    xs = [a[k] for k in keys]
    ys = [b[k] for k in keys]
    mx, my = sum(xs) / n, sum(ys) / n
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    dx = sum((x - mx) ** 2 for x in xs) ** 0.5
    dy = sum((y - my) ** 2 for y in ys) ** 0.5
    return (num / (dx * dy) if dx and dy else None), n


print("=" * 94)
print("[1] 카테고리 = 이니스프리인가 — 월별 상관계수")
print("    상관이 1에 가까우면 그 카테고리 검색은 사실상 이니스프리 검색이다.")
print("    → 그 경우 '카테고리 대비 점유율'은 자기를 자기로 나눈 값이라 의미가 없다.")
print("=" * 94)
for cat, brand in [("녹차·그린티 카테고리", "이니스프리 그린티"),
                   ("레티놀 카테고리", "이니스프리 레티놀")]:
    r, n = pearson(monthly[cat], monthly[brand])
    verdict = "사실상 같은 것" if r and r >= 0.85 else ("연동됨" if r and r >= 0.6 else "독립적")
    print(f"  {brand:<18} ↔ {cat:<18}  r = {r:6.3f}  (n={n}개월)  → {verdict}")

print()
print("=" * 94)
print("[2] 절대량 궤적 — 점유율이 아니라 실제 검색량")
print("=" * 94)
YS = [2021, 2022, 2023, 2024, 2025, 2026]
print(f"  {'계열':<22}" + "".join(f"{y:>9}" for y in YS))
for g in GROUPS:
    n = g["groupName"]
    print(f"  {n:<22}" + "".join(f"{yearly[n].get(y,0):9.3f}" for y in YS))

print()
print("  상승기(2021→2023)와 하락기(2023→2025) 탄력도 — 카테고리 1%p당 브랜드 몇 %p")
for cat, brand in [("레티놀 카테고리", "이니스프리 레티놀"),
                   ("녹차·그린티 카테고리", "이니스프리 그린티")]:
    for lo, hi, tag in [(2021, 2023, "상승기"), (2023, 2025, "하락기")]:
        c0, c1 = yearly[cat][lo], yearly[cat][hi]
        b0, b1 = yearly[brand][lo], yearly[brand][hi]
        if not c0 or not b0:
            continue
        cg, bg = (c1 / c0 - 1) * 100, (b1 / b0 - 1) * 100
        el = bg / cg if cg else float("nan")
        print(f"    {brand:<18} {tag} 카테고리 {cg:+7.1f}%  브랜드 {bg:+7.1f}%   탄력도 {el:5.2f}")

print()
print("=" * 94)
print("[3] 처치 변수 — 광고선전비(DART 감사보고서, 확정 수치)와 결과")
print("=" * 94)
print(f"  {'연도':<6}{'광고선전비':>11}{'전년비':>9}{'브랜드검색':>11}{'전년비':>9}{'매출':>10}{'전년비':>9}{'영업이익':>10}")
prev = None
for y in [2021, 2022, 2023, 2024, 2025]:
    ad, rev, op = AD[y], REV[y], OP[y]
    br = yearly["이니스프리(브랜드)"].get(y, 0)
    if prev:
        pad, pbr, prev_rev = prev
        s = (f"{(ad/pad-1)*100:+8.1f}%", f"{(br/pbr-1)*100:+8.1f}%", f"{(rev/prev_rev-1)*100:+8.1f}%")
    else:
        s = ("        —", "        —", "        —")
    print(f"  {y:<6}{ad:>10.1f}억{s[0]:>9}{br:>11.2f}{s[1]:>9}{rev:>9.1f}억{s[2]:>9}{op:>9.1f}억")
    prev = (ad, br, rev)

print()
a22, a23 = AD[2022], AD[2023]
b22 = yearly["이니스프리(브랜드)"][2022]
b23 = yearly["이니스프리(브랜드)"][2023]
print("  ★ 2023년 단일 연도 자연실험 — 광고비만 유일하게 급증한 해")
print(f"     광고선전비  {a22:.1f}억 → {a23:.1f}억   {(a23/a22-1)*100:+.1f}%")
print(f"     브랜드 검색 {b22:.2f} → {b23:.2f}   {(b23/b22-1)*100:+.1f}%")
print(f"     매출        {REV[2022]:.1f}억 → {REV[2023]:.1f}억   {(REV[2023]/REV[2022]-1)*100:+.1f}%")
print(f"     광고효율    {REV[2022]/a22:.1f}배 → {REV[2023]/a23:.1f}배   "
      f"{((REV[2023]/a23)/(REV[2022]/a22)-1)*100:+.1f}%")

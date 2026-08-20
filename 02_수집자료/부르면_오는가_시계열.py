# -*- coding: utf-8 -*-
"""'회사가 부르면 사람이 온다'를 상관에서 인과로 올린다.

E표(브랜드 결합형 순위)는 상관관계일 뿐이다. 회사가 부른 것이 크다는 것과
'불러서 커졌다'는 다르다. 시계열로 갈라지는 지점을 보면 인과에 가까워진다.

  · 회사가 민 것(레티놀)   → 올랐는가
  · 회사가 놓은 것(제주)   → 내렸는가
  · 브랜드 전체            → 통제군. 다 같이 내렸다면 의미 없다
  · THE NEW ISLE          → 회사가 밀었는데 안 온 반례. 정직하게 같이 본다

같은 요청 안이므로 5계열의 상대 크기와 궤적을 함께 볼 수 있다.
"""
import sys, time
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

GROUPS = [
    {"groupName": "이니스프리 레티놀(밀었음)", "keywords": ["이니스프리 레티놀", "이니스프리 비타c"]},
    {"groupName": "이니스프리 그린티(제품명만)", "keywords": ["이니스프리 그린티", "그린티 세럼"]},
    {"groupName": "이니스프리 제주(놓았음)", "keywords": ["이니스프리 제주", "제주 이니스프리"]},
    {"groupName": "더뉴아일(리브랜딩 슬로건)", "keywords": ["더뉴아일", "the new isle", "뉴아일"]},
    {"groupName": "이니스프리(브랜드 통제군)", "keywords": ["이니스프리"]},
]

res = cli.datalab_search(start_date="2021-01-01", end_date="2026-08-18",
                         time_unit="month", keyword_groups=GROUPS)

series = {}
for r in res["results"]:
    by_year = defaultdict(list)
    for d in r["data"]:
        by_year[d["period"][:4]].append(d["ratio"])
    series[r["title"]] = {y: sum(v) / len(v) for y, v in by_year.items()}

YEARS = ["2021", "2022", "2023", "2024", "2025", "2026"]
print("=" * 96)
print("연도별 평균 지수 (2021-01 ~ 2026-08, 같은 요청 = 서로 비교 가능)")
print("  2023 = 리브랜딩 시행 / 2026은 1~8월만")
print("=" * 96)
print(f"  {'계열':<28}" + "".join(f"{y:>10}" for y in YEARS) + f"{'21→25':>10}")
for name in [g["groupName"] for g in GROUPS]:
    s = series.get(name, {})
    row = "".join(f"{s.get(y, 0):10.2f}" for y in YEARS)
    base, last = s.get("2021", 0), s.get("2025", 0)
    chg = f"{(last/base-1)*100:+9.1f}%" if base else "        —"
    print(f"  {name:<28}{row}{chg}")

print()
print("=" * 96)
print("통제군 대비 — 브랜드 전체 하락을 빼고도 살아남는가")
print("=" * 96)
brand = series.get("이니스프리(브랜드 통제군)", {})
b21, b25 = brand.get("2021", 1), brand.get("2025", 1)
brand_chg = (b25 / b21 - 1) * 100 if b21 else 0
print(f"  브랜드 전체 2021→2025 : {brand_chg:+.1f}%   ← 이만큼은 시장·브랜드 요인")
print()
for name in [g["groupName"] for g in GROUPS]:
    if "통제군" in name:
        continue
    s = series.get(name, {})
    base, last = s.get("2021", 0), s.get("2025", 0)
    if not base:
        print(f"  {name:<28}  2021년 값 없음 → 증감 계산 불가")
        continue
    chg = (last / base - 1) * 100
    rel = chg - brand_chg
    mark = "▲ 브랜드보다 잘 버텼다" if rel > 0 else "▼ 브랜드보다 더 빠졌다"
    print(f"  {name:<28}{chg:+8.1f}%   통제군 대비 {rel:+7.1f}%p   {mark}")

print()
print("=" * 96)
print("더뉴아일 — 회사가 밀었는데 왔는가")
print("=" * 96)
n = series.get("더뉴아일(리브랜딩 슬로건)", {})
for y in YEARS:
    print(f"  {y}: {n.get(y, 0):8.3f}")
print("  → 2023 리브랜딩 시행 연도에 튀지 않으면, '회사가 불러도 안 오는 경우'가 존재한다.")
print("    그 차이가 무엇인지 해석에 반드시 적을 것.")

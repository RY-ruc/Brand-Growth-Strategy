# -*- coding: utf-8 -*-
"""'회사가 밀어서 올랐다'는 주장을 반증 시도한다.

앞선 시계열에서 '이니스프리 레티놀'이 브랜드 전체 하락 중에도 올랐다고 했으나,
그것이 회사의 푸시 때문인지 '레티놀 카테고리 자체의 유행' 때문인지 구분하지 않았다.
구분 방법 — 카테고리 대비 점유율을 본다.

  · 점유율이 올랐다  → 이니스프리 몫이 커졌다 = 회사 효과 쪽
  · 점유율이 평평하다 → 그냥 시장 파도를 탄 것 = 회사 효과 아님

같은 요청 안이므로 브랜드/카테고리 비율이 의미를 갖는다.
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

GROUPS = [
    {"groupName": "레티놀 카테고리", "keywords": ["레티놀", "레티놀 크림", "레티놀 앰플"]},
    {"groupName": "이니스프리 레티놀", "keywords": ["이니스프리 레티놀", "이니스프리 비타c"]},
    {"groupName": "녹차·그린티 카테고리", "keywords": ["그린티", "녹차 화장품", "그린티 화장품"]},
    {"groupName": "이니스프리 그린티", "keywords": ["이니스프리 그린티", "그린티 세럼"]},
    {"groupName": "이니스프리(통제군)", "keywords": ["이니스프리"]},
]

res = cli.datalab_search(start_date="2021-01-01", end_date="2026-08-18",
                        time_unit="month", keyword_groups=GROUPS)

s = {}
for r in res["results"]:
    by_year = defaultdict(list)
    for d in r["data"]:
        by_year[d["period"][:4]].append(d["ratio"])
    s[r["title"]] = {y: sum(v) / len(v) for y, v in by_year.items()}

YEARS = ["2021", "2022", "2023", "2024", "2025", "2026"]
print("=" * 92)
print("연평균 지수 (한 요청 = 서로 비교 가능) · 2026은 1~8월만")
print("=" * 92)
print(f"  {'계열':<24}" + "".join(f"{y:>11}" for y in YEARS))
for g in GROUPS:
    n = g["groupName"]
    print(f"  {n:<24}" + "".join(f"{s[n].get(y,0):11.3f}" for y in YEARS))

for brand, cat in [("이니스프리 레티놀", "레티놀 카테고리"),
                   ("이니스프리 그린티", "녹차·그린티 카테고리")]:
    print()
    print("=" * 92)
    print(f"점유율 — {brand} ÷ {cat}")
    print("=" * 92)
    base = None
    for y in YEARS:
        c, b = s[cat].get(y, 0), s[brand].get(y, 0)
        if not c:
            print(f"  {y}: 카테고리 0 → 계산 불가")
            continue
        sh = b / c * 100
        if base is None:
            base = sh
        print(f"  {y}: {sh:6.2f}%   (2021 대비 {sh-base:+6.2f}%p)  {'█'*max(0,round(sh*2))}")
    print("  → 점유율이 평평하면 '회사가 밀어서'가 아니라 '카테고리 파도'다.")

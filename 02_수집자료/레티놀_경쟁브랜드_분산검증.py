# -*- coding: utf-8 -*-
"""4막 반론 검증 — "이니스프리 레티놀이 준 건 경쟁자가 늘어 파이가 분산된 탓 아닌가?"

이 반론이 맞다면 '고를 이유가 없어서 진다'는 서술은 과장이다.
경쟁 브랜드들도 같이 줄었으면 = 시장 분산(이니스프리 고유 문제 아님)
경쟁 브랜드는 늘었는데 이니스프리만 줄었으면 = 뺏긴 것

같은 요청 안이므로 브랜드 간 상대 크기와 궤적을 함께 볼 수 있다.
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


def yearly(groups, start="2021-01-01"):
    res = cli.datalab_search(start_date=start, end_date="2026-08-18",
                            time_unit="month", keyword_groups=groups)
    out = {}
    for r in res["results"]:
        by_y = defaultdict(list)
        for d in r["data"]:
            by_y[int(d["period"][:4])].append(d["ratio"])
        out[r["title"]] = {y: sum(v) / len(v) for y, v in by_y.items()}
    return out


A = yearly([
    {"groupName": "이니스프리 레티놀", "keywords": ["이니스프리 레티놀", "이니스프리 비타c"]},
    {"groupName": "닥터지 레티놀", "keywords": ["닥터지 레티놀"]},
    {"groupName": "아이오페 레티놀", "keywords": ["아이오페 레티놀"]},
    {"groupName": "에스트라 레티놀", "keywords": ["에스트라 레티놀"]},
    {"groupName": "마녀공장 레티놀", "keywords": ["마녀공장 레티놀", "넘버즈인 레티놀"]},
])

YS = [2021, 2022, 2023, 2024, 2025, 2026]
print("=" * 92)
print("레티놀 시장 브랜드별 — 이니스프리만 빠지는가, 다 같이 빠지는가")
print("=" * 92)
print(f"  {'브랜드':<20}" + "".join(f"{y:>9}" for y in YS) + f"{'23→25':>10}")
for n, s in sorted(A.items(), key=lambda x: -x[1].get(2023, 0)):
    row = "".join(f"{s.get(y,0):9.3f}" for y in YS)
    b, l = s.get(2023, 0), s.get(2025, 0)
    chg = f"{(l/b-1)*100:+9.1f}%" if b else "        —"
    print(f"  {n:<20}{row}{chg}")

print()
print("  판정 — 이니스프리만 큰 폭으로 빠졌으면 '뺏긴 것', 다 같이 빠졌으면 '시장 분산'")
inn = A["이니스프리 레티놀"]
i_chg = (inn.get(2025, 0) / inn.get(2023, 1) - 1) * 100
others = []
for n, s in A.items():
    if n == "이니스프리 레티놀":
        continue
    b, l = s.get(2023, 0), s.get(2025, 0)
    if b:
        others.append((n, (l / b - 1) * 100))
if others:
    avg = sum(c for _, c in others) / len(others)
    print(f"    이니스프리        {i_chg:+7.1f}%")
    print(f"    경쟁 브랜드 평균  {avg:+7.1f}%   (n={len(others)})")
    print(f"    차이              {i_chg - avg:+7.1f}%p")

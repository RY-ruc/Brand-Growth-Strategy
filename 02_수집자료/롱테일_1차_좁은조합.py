# -*- coding: utf-8 -*-
"""롱테일 가설 검증 — '제주 그린티 수분크림'처럼 늘리면 실제로 검색되는가

데이터랩은 같은 요청 안에서만 척도가 같다. 그래서 비교군을 한 번에 조회한다.
"""
import json, sys, time
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

START, END = "2025-08-01", "2026-08-18"

CALLS = {
    "A. 일반명사 vs 브랜드결합 vs 헤리티지결합": [
        {"groupName": "수분크림(일반)", "keywords": ["수분크림"]},
        {"groupName": "이니스프리 수분크림", "keywords": ["이니스프리 수분크림"]},
        {"groupName": "그린티 수분크림", "keywords": ["그린티 수분크림", "이니스프리 그린티 수분크림"]},
        {"groupName": "제주 화장품", "keywords": ["제주 화장품", "제주 스킨케어"]},
        {"groupName": "녹차 화장품", "keywords": ["녹차 화장품", "녹차 스킨케어"]},
    ],
    "B. 회사가 실제로 건 롱테일 (피부고민 축)": [
        {"groupName": "끈적이지 않는 크림", "keywords": ["끈적이지 않는 크림"]},
        {"groupName": "수부지 크림", "keywords": ["수부지 크림", "수부지피부 크림"]},
        {"groupName": "속건조 크림", "keywords": ["속건조 크림", "속건조 보습크림"]},
        {"groupName": "비건 수분크림", "keywords": ["비건 수분크림", "비건 크림"]},
        {"groupName": "지성피부 크림", "keywords": ["지성피부 크림"]},
    ],
}

out = {}
for name, groups in CALLS.items():
    out[name] = cli.datalab_search(start_date=START, end_date=END,
                                   time_unit="month", keyword_groups=groups)
    time.sleep(0.4)

for name, res in out.items():
    print("=" * 78)
    print(name)
    print("=" * 78)
    rows = []
    for r in res["results"]:
        vals = [d["ratio"] for d in r["data"]]
        avg = sum(vals) / len(vals) if vals else 0
        rows.append((r["title"], avg, len(vals), ", ".join(r["keywords"])))
    mx = max((a for _, a, _, _ in rows), default=1) or 1
    for title, avg, n, kws in sorted(rows, key=lambda x: -x[1]):
        bar = "█" * max(0, round(avg / mx * 40))
        print(f"  {title:<22} {avg:8.3f}  {bar}")
        print(f"  {'':<22} {'':8}  └ {kws}  (n={n}개월)")
    print()

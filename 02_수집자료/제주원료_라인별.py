# -*- coding: utf-8 -*-
"""제주 원료 라인별 실제 크기 — 브랜드 결합형으로만 조회한다.

앞선 조회에서 '동백 오일'을 넣었다가 헤어·바디 등 무관 검색이 섞여
36.682라는 오염된 값이 나왔다. 여기서는 반드시 '이니스프리'를 붙여
브랜드 수요만 분리한다. 그린티를 기준선으로 같은 요청에 넣는다.
"""
import sys, time
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


def run(title, groups, note=""):
    res = cli.datalab_search(start_date=START, end_date=END, time_unit="month", keyword_groups=groups)
    rows = []
    for r in res["results"]:
        v = [d["ratio"] for d in r["data"]]
        rows.append((r["title"], sum(v) / len(v) if v else 0, len(v), ", ".join(r["keywords"])))
    mx = max((a for _, a, _, _ in rows), default=1) or 1
    print("=" * 84); print(title)
    if note: print(f"  ({note})")
    print("=" * 84)
    for t, avg, n, kw in sorted(rows, key=lambda x: -x[1]):
        miss = "" if n >= 13 else f"  ⚠{13-n}개월 결측"
        print(f"  {t:<24}{avg:8.3f}  {'█'*max(0,round(avg/mx*32))}{miss}")
        print(f"  {'':<24}{'':8}  └ {kw}")
    print()
    time.sleep(0.4)
    return {t: a for t, a, _, _ in rows}


F = run("F. 제주 원료 라인별 — 브랜드 결합형(오염 제거)",
        [{"groupName": "그린티(기준선)", "keywords": ["이니스프리 그린티", "그린티 세럼"]},
         {"groupName": "동백", "keywords": ["이니스프리 동백", "이니스프리 카멜리아"]},
         {"groupName": "비자(트러블)", "keywords": ["이니스프리 비자", "비자 트러블"]},
         {"groupName": "한란", "keywords": ["이니스프리 한란"]},
         {"groupName": "블랙티", "keywords": ["이니스프리 블랙티", "블랙티 유스"]}],
        "그린티를 같은 요청에 넣어 상대 크기를 본다")

print("=" * 84); print("판정 — 그린티 대비"); print("=" * 84)
g = F.get("그린티(기준선)", 0) or 1
for k, v in sorted(F.items(), key=lambda x: -x[1]):
    print(f"  {k:<24}{v:8.3f}   그린티의 {v/g*100:5.1f}%")

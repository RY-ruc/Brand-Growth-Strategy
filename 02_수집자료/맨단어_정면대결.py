# -*- coding: utf-8 -*-
"""두 가지 반박을 정면으로 시험한다.

반박 1 "화산송이는 그냥 재료라 검색 안 한다"
  → 맨단어로 고민어와 정면 대결시킨다. 앞선 조회의 고민어(`피지 조절`)가
    어색한 표현이라 작게 나왔을 가능성을 배제하기 위함.

반박 2 "회사가 불러도 사람이 안 부르면 죽는다"
  → 회사가 부른 정도에 따라 사람이 부르는 정도가 달라지는지 본다.
    같은 구성(브랜드 결합형)으로 통일해 한 요청에 넣는다.
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
        print(f"  {t:<26}{avg:8.3f}  {'█'*max(0,round(avg/mx*32))}{miss}")
        print(f"  {'':<26}{'':8}  └ {kw}")
    print()
    time.sleep(0.4)
    return {t: a for t, a, _, _ in rows}


# ── 반박 1 ── 맨단어 정면 대결. 재료어가 고민어에 진짜로 밀리는가?
D = run("D. 맨단어 정면 대결 — 재료어 vs 고민어 vs 카테고리어",
        [{"groupName": "모공(고민어)", "keywords": ["모공"]},
         {"groupName": "여드름(고민어)", "keywords": ["여드름"]},
         {"groupName": "화산송이(재료어)", "keywords": ["화산송이"]},
         {"groupName": "수분크림(카테고리)", "keywords": ["수분크림"]},
         {"groupName": "선크림(카테고리)", "keywords": ["선크림"]}],
        "고민어가 재료어를 압도하면 반박이 맞다")

# ── 반박 2 ── 회사가 부른 정도 ↔ 사람이 부르는 정도. 구성을 통일한다.
E = run("E. 회사가 부른 만큼 사람이 부르는가 — 브랜드 결합형으로 통일",
        [{"groupName": "노세범(질의어○ 현재밀기)", "keywords": ["이니스프리 노세범", "노세범 선크림"]},
         {"groupName": "그린티(제품명만 남음)", "keywords": ["이니스프리 그린티", "그린티 세럼"]},
         {"groupName": "화산송이(제품명만 남음)", "keywords": ["이니스프리 화산송이", "화산송이 클렌징"]},
         {"groupName": "제주(회사가 놓음)", "keywords": ["이니스프리 제주", "제주 이니스프리"]},
         {"groupName": "레티놀(현재밀기 기능성)", "keywords": ["이니스프리 레티놀", "이니스프리 비타c"]}],
        "회사가 부르는 것일수록 크면, 부르는 것이 검색을 만든다는 뜻")

print("=" * 84); print("판정"); print("=" * 84)
vol = D.get("화산송이(재료어)", 0)
for k in ("모공(고민어)", "여드름(고민어)", "수분크림(카테고리)"):
    d = D.get(k, 0)
    rel = f"{d/vol:.1f}배 크다" if vol and d > vol else (f"화산송이가 {vol/d:.1f}배 크다" if d else "—")
    print(f"  화산송이 {vol:.3f}  vs  {k} {d:.3f}   → {rel}")
print()
print("  회사가 부른 정도 순:")
for k, v in sorted(E.items(), key=lambda x: -x[1]):
    print(f"    {k:<26}{v:8.3f}")

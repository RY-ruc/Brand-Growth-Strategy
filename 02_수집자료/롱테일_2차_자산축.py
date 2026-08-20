# -*- coding: utf-8 -*-
"""롱테일 재검증 — 이니스프리가 '독점'하는 고유명사 롱테일이 실재하는가

1차 검증에서 '헤리티지 롱테일은 검색량이 작다'로 끝냈는데, 그건 롱테일 이론을
잘못 적용한 것이다. 롱테일의 핵심은 개별 볼륨이 아니라
  ① 경쟁 강도(내가 이길 수 있는가)  ② 합계  ③ 전환/의도 선명도
그래서 '이니스프리 고유 자산 키워드'가 일반명사 대비 어느 정도 규모인지,
그리고 회사가 이미 쓰고 있는 고유명사가 있는지 확인한다.
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
    res = cli.datalab_search(start_date=START, end_date=END, time_unit="month",
                             keyword_groups=groups)
    rows = []
    for r in res["results"]:
        v = [d["ratio"] for d in r["data"]]
        rows.append((r["title"], sum(v) / len(v) if v else 0, len(v), ", ".join(r["keywords"])))
    mx = max((a for _, a, _, _ in rows), default=1) or 1
    print("=" * 82)
    print(title)
    if note:
        print(f"  ({note})")
    print("=" * 82)
    for t, avg, n, kw in sorted(rows, key=lambda x: -x[1]):
        bar = "█" * max(0, round(avg / mx * 38))
        miss = "" if n >= 13 else f"  ⚠ {13-n}개월 결측"
        print(f"  {t:<20} {avg:8.3f}  {bar}{miss}")
        print(f"  {'':<20} {'':8}  └ {kw}")
    print()
    time.sleep(0.4)
    return {t: a for t, a, _, _ in rows}


A = run("A. 이니스프리 고유 자산 키워드 — 남이 쓸 수 없는 말",
        [{"groupName": "노세범", "keywords": ["노세범", "이니스프리 노세범"]},
         {"groupName": "화산송이", "keywords": ["화산송이", "이니스프리 화산송이"]},
         {"groupName": "그린티(이니스프리)", "keywords": ["이니스프리 그린티", "그린티 세럼", "그린티 수분크림"]},
         {"groupName": "제주 뷰티", "keywords": ["제주 화장품", "제주 스킨케어", "제주 여행 선물"]},
         {"groupName": "공병·그린사이클", "keywords": ["이니스프리 공병", "화장품 공병"]}],
        "각 키워드가 이니스프리를 얼마나 고유하게 가리키는지가 핵심")

B = run("B. 같은 카테고리에서 일반명사 vs 고유명사",
        [{"groupName": "선크림(일반)", "keywords": ["선크림"]},
         {"groupName": "노세범 선크림", "keywords": ["노세범 선크림", "이니스프리 선크림"]},
         {"groupName": "폼클렌징(일반)", "keywords": ["폼클렌징"]},
         {"groupName": "화산송이 클렌징", "keywords": ["화산송이 클렌징", "화산송이 폼클렌징", "이니스프리 폼클렌징"]},
         {"groupName": "모공 클렌징", "keywords": ["모공 클렌징", "딥클렌징"]}],
        "일반명사는 크지만 이니스프리 몫이 아니다")

print("=" * 82)
print("판정 — 회사가 이미 쓰는 고유명사가 있는가")
print("=" * 82)
print("  llms.txt 타겟 질의어에 실제로 들어있는 고유명사: '노세범 선크림' (제품 라인명)")
print(f"  노세범 검색 규모        : {A.get('노세범', 0):.3f}")
print(f"  화산송이 검색 규모      : {A.get('화산송이', 0):.3f}")
print(f"  그린티(이니스프리) 규모 : {A.get('그린티(이니스프리)', 0):.3f}")
print(f"  제주 뷰티 규모          : {A.get('제주 뷰티', 0):.3f}")
tot = sum(A.get(k, 0) for k in ["노세범", "화산송이", "그린티(이니스프리)", "제주 뷰티", "공병·그린사이클"])
print(f"\n  고유 자산 키워드 합계   : {tot:.3f}")
print(f"  (비교) 선크림 일반      : {B.get('선크림(일반)', 0):.3f}")
print(f"  (비교) 폼클렌징 일반    : {B.get('폼클렌징(일반)', 0):.3f}")

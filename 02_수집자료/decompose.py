# -*- coding: utf-8 -*-
"""키워드 단위 분해 — 어느 키워드가 2026 반전을 만들었나"""
import json, sys, time
from pathlib import Path

BASE = Path(r"C:\Users\EZ\Downloads\naver_api_streamlit_dashboard")
sys.path.insert(0, str(BASE))
from naver_api import NaverClient  # noqa: E402

env = {}
for line in (BASE / ".env").read_text(encoding="utf-8").splitlines():
    if "=" in line and not line.strip().startswith("#"):
        k, v = line.split("=", 1)
        env[k.strip()] = v.strip().strip('"').strip("'")
cli = NaverClient(client_id=env["NAVER_CLIENT_ID"], client_secret=env["NAVER_CLIENT_SECRET"])

OUT = Path(__file__).parent
CACHE = OUT / "raw_decomp.json"
GROUPS = [
    {"groupName": "브랜드",   "keywords": ["이니스프리"]},
    {"groupName": "제주",     "keywords": ["이니스프리 제주"]},
    {"groupName": "그린티",   "keywords": ["이니스프리 그린티"]},
    {"groupName": "화산송이", "keywords": ["이니스프리 화산송이"]},
    {"groupName": "레티놀",   "keywords": ["이니스프리 레티놀"]},
]

if CACHE.exists():
    raw = json.loads(CACHE.read_text(encoding="utf-8"))
else:
    raw = cli.datalab_search(start_date="2021-01-01", end_date="2026-08-18",
                             time_unit="month", keyword_groups=GROUPS)
    CACHE.write_text(json.dumps(raw, ensure_ascii=False, indent=1), encoding="utf-8")

S = {r["title"]: {d["period"][:7]: d["ratio"] for d in r["data"]} for r in raw["results"]}
L, w = [], None
L = []
w = L.append


def jj(g, y):
    # 데이터랩은 임계치 미만 구간을 응답에서 생략한다 → 0으로 간주(하한값)
    return sum(S[g].get(f"{y}-{m:02d}", 0.0) for m in range(1, 8))


def g(k, m):
    return S[k].get(m, 0.0)


w("# 키워드 단위 분해 — 2026 반전의 출처")
w("")
w("각 키워드를 개별 그룹으로 분리 조회(동일 요청 = 동일 척도). 1~7월 동일구간.")
w("")
w("## 1. 키워드별 1~7월 지수와 브랜드 대비 비중")
w("")
w("| 연도 | 브랜드 | 제주 | 그린티 | 화산송이 | 레티놀 | 제주/브랜드 | 그린티/브랜드 |")
w("|---|---|---|---|---|---|---|---|")
for y in range(2021, 2027):
    b = jj("브랜드", y)
    w(f"| {y} | {b:.2f} | {jj('제주',y):.3f} | {jj('그린티',y):.3f} | {jj('화산송이',y):.3f} | "
      f"{jj('레티놀',y):.3f} | {jj('제주',y)/b*100:.2f}% | {jj('그린티',y)/b*100:.2f}% |")
w("")
w("## 2. 월별 원자료 — 2025 vs 2026")
w("")
w("| 월 | 브랜드25 | 브랜드26 | 제주25 | 제주26 | 그린티25 | 그린티26 | 제주비중25 | 제주비중26 |")
w("|---|---|---|---|---|---|---|---|---|")
for m in range(1, 8):
    a, b = f"2025-{m:02d}", f"2026-{m:02d}"
    w(f"| {m}월 | {g('브랜드',a):.2f} | {g('브랜드',b):.2f} | {g('제주',a):.3f} | {g('제주',b):.3f} | "
      f"{g('그린티',a):.3f} | {g('그린티',b):.3f} | "
      f"{g('제주',a)/g('브랜드',a)*100:.2f}% | {g('제주',b)/g('브랜드',b)*100:.2f}% |")
w("")
w("## 3. 제주 단독 비중 — 연도별 1~7월 (계절성 통제)")
w("")
w("| 연도 | 제주/브랜드 | 전년 대비 |")
w("|---|---|---|")
prev = None
for y in range(2021, 2027):
    r = jj("제주", y) / jj("브랜드", y) * 100
    w(f"| {y} | {r:.2f}% | {'—' if prev is None else f'{r-prev:+.2f}%p'} |")
    prev = r
w("")
w("## 4. 그린티 월별 전량 (2025-01~2026-07) — 스파이크 확인")
w("")
w("| 월 | 그린티 지수 |")
w("|---|---|")
for y in (2025, 2026):
    for m in range(1, 13):
        k = f"{y}-{m:02d}"
        if k in S["그린티"] and k <= "2026-07":
            w(f"| {k} | {g('그린티',k):.3f} |")
w("")
(OUT / "결과_분해.md").write_text("\n".join(L), encoding="utf-8")
print("완료")


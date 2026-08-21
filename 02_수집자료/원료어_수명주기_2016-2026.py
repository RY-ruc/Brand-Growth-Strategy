# -*- coding: utf-8 -*-
"""원료어는 키울 수 있는가, 그리고 얼마나 오래 사는가 — 2016~2026 전 구간.

앞선 조회에서 라운드랩 '자작나무'가 2021→2023에 6.7배(5.114→34.203) 자랐다.
그런데 '자작나무'는 산지어가 아니라 원료어다. 이니스프리의 '화산송이'·'그린티'와
같은 종류다. 같은 형태의 이름인데 한쪽은 자라고 한쪽은 줄었다.

가능한 설명이 둘이다.
  (가) 이니스프리는 원료어를 못 키웠다        → 우리 제안이 새로운 시도가 된다
  (나) 이미 키웠고, 정점을 지나 감가 중이다   → "다시 부르면 되는가"가 쟁점이 된다

2021년부터만 보면 구분이 안 된다. 화산송이 전성기가 2016~2019이면 그 구간이 잘려 있다.
데이터랩 최댓값(2016-01)까지 늘려 수명주기 전체를 본다.

주의 — 요청 단위 재정규화다. 이 파일의 값을 2021~2026만 조회한 다른 문서와 섞지 말 것.
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

START, END = "2016-01-01", "2026-08-18"
YEARS = list(range(2016, 2027))


def run(title, groups, note=""):
    res = cli.datalab_search(start_date=START, end_date=END,
                            time_unit="month", keyword_groups=groups)
    y = {}
    for r in res["results"]:
        by = defaultdict(list)
        for d in r["data"]:
            by[int(d["period"][:4])].append(d["ratio"])
        y[r["title"]] = {k: sum(v) / len(v) for k, v in by.items()}
    print("=" * 104); print(title)
    if note: print(f"  ({note})")
    print("=" * 104)
    print(f"  {'계열':<20}" + "".join(f"{x:>7}" for x in YEARS) + f"{'정점':>8}{'정점比':>9}")
    for g in groups:
        n = g["groupName"]
        s = y.get(n, {})
        peak_y = max(s, key=lambda k: s[k]) if s else None
        peak_v = s.get(peak_y, 0)
        now = s.get(2026, 0)
        row = "".join(f"{s.get(x,0):7.2f}" for x in YEARS)
        drop = f"{(now/peak_v-1)*100:+8.1f}%" if peak_v else "        —"
        print(f"  {n:<20}{row}{str(peak_y):>8}{drop:>9}")
    print()
    time.sleep(0.4)
    return y


A = run("A. 원료어 수명주기 — 이니스프리 vs 라운드랩",
        [{"groupName": "화산송이", "keywords": ["화산송이", "이니스프리 화산송이"]},
         {"groupName": "그린티(이니스프리)", "keywords": ["이니스프리 그린티", "그린티 세럼"]},
         {"groupName": "자작나무(라운드랩)", "keywords": ["자작나무 크림", "라운드랩 자작나무", "자작나무 선크림"]},
         {"groupName": "노세범(이니스프리)", "keywords": ["노세범", "이니스프리 노세범"]},
         {"groupName": "이니스프리(브랜드)", "keywords": ["이니스프리"]}],
        "정점 연도가 언제인지가 핵심")

print("=" * 104); print("판정"); print("=" * 104)
for k in ("화산송이", "그린티(이니스프리)", "자작나무(라운드랩)", "노세범(이니스프리)"):
    s = A.get(k, {})
    if not s:
        continue
    peak_y = max(s, key=lambda x: s[x]); peak_v = s[peak_y]
    v16, now = s.get(2016, 0), s.get(2026, 0)
    growth = f"{(peak_v/v16):.1f}배" if v16 else "—"
    print(f"  {k:<20} 정점 {peak_y}년 {peak_v:6.2f}   2016 대비 정점 {growth:>7}   "
          f"현재 {now:5.2f} (정점의 {now/peak_v*100:4.1f}%)")
print()
print("  → 화산송이 정점이 2016~2019면 '이미 키웠다가 감가된 것'이다.")
print("    2021 이후만 보면 '원래 작았다'로 잘못 읽힌다.")

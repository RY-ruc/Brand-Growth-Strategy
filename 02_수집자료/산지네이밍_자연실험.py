# -*- coding: utf-8 -*-
"""산지를 제품 이름에 넣으면 검색이 생기는가 — 라운드랩이라는 자연실험.

배경
  자사몰 크롤링 결과, 산지 서사 분량은 라운드랩 23회 vs 이니스프리 20회로 비슷하다.
  그런데 '어디에' 있는지가 다르다.
    · 라운드랩 — 제품명 23개 중 9개(39.1%)에 산지어 (1025 독도 토너, 자작나무 수분 크림)
    · 이니스프리 — 제품명 30개 중 0개. 제주는 about 페이지에만 있다

  앞선 조회에서 '화산송이' 맨단어는 1.885로, 원료어로는 진입이 안 된다고 판정했다.
  라운드랩은 산지를 제품명에 넣는 전략을 이미 수년간 실행했다.
  그 결과를 보면 '산지를 제품에 실으면 작동하는가'를 남의 돈으로 검증할 수 있다.

판정
  · 독도/자작나무 결합어가 화산송이·그린티보다 크면 → 산지 네이밍이 작동한다
  · 비슷하거나 작으면 → 이름에 넣어도 안 된다. 우리 제안의 근거가 약해진다
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


def run(title, groups, note="", start="2021-01-01"):
    res = cli.datalab_search(start_date=start, end_date="2026-08-18",
                            time_unit="month", keyword_groups=groups)
    print("=" * 90); print(title)
    if note: print(f"  ({note})")
    print("=" * 90)
    out, yearly = {}, {}
    for r in res["results"]:
        v = [d["ratio"] for d in r["data"]]
        out[r["title"]] = sum(v) / len(v) if v else 0
        by = defaultdict(list)
        for d in r["data"]:
            by[int(d["period"][:4])].append(d["ratio"])
        yearly[r["title"]] = {y: sum(x) / len(x) for y, x in by.items()}
    mx = max(out.values()) or 1
    for t, a in sorted(out.items(), key=lambda x: -x[1]):
        kw = ", ".join(next(g["keywords"] for g in groups if g["groupName"] == t))
        print(f"  {t:<22}{a:8.3f}  {'█' * max(0, round(a / mx * 30))}")
        print(f"  {'':<22}{'':8}  └ {kw}")
    print()
    time.sleep(0.4)
    return out, yearly


# 산지가 이름에 박힌 것 vs 성분이 이름에 박힌 것. 같은 요청이라 비교 가능하다.
A, AY = run(
    "A. 산지 네이밍(라운드랩) vs 성분 네이밍(이니스프리)",
    [{"groupName": "독도(라운드랩)", "keywords": ["독도 토너", "1025 독도", "라운드랩 독도"]},
     {"groupName": "자작나무(라운드랩)", "keywords": ["자작나무 크림", "라운드랩 자작나무", "자작나무 선크림"]},
     {"groupName": "화산송이(이니스프리)", "keywords": ["화산송이", "이니스프리 화산송이"]},
     {"groupName": "그린티(이니스프리)", "keywords": ["이니스프리 그린티", "그린티 세럼"]},
     {"groupName": "노세범(이니스프리)", "keywords": ["노세범", "이니스프리 노세범"]}],
    "산지어가 성분어보다 크면 산지 네이밍이 작동한 것이다")

# 브랜드 자체 체급도 함께 봐야 한다. 라운드랩이 작은 브랜드면 위 비교가 불공정하다.
B, BY = run(
    "B. 브랜드 체급 — 공정한 비교인지 확인",
    [{"groupName": "이니스프리", "keywords": ["이니스프리"]},
     {"groupName": "라운드랩", "keywords": ["라운드랩"]},
     {"groupName": "토리든", "keywords": ["토리든"]},
     {"groupName": "메디힐", "keywords": ["메디힐"]},
     {"groupName": "에스네이처", "keywords": ["에스네이처"]}],
    "브랜드 크기 대비로 봐야 한다")

print("=" * 90); print("판정"); print("=" * 90)
dokdo = A.get("독도(라운드랩)", 0) + A.get("자작나무(라운드랩)", 0)
inni = A.get("화산송이(이니스프리)", 0) + A.get("그린티(이니스프리)", 0)
print(f"  라운드랩 산지 결합어 합계   : {dokdo:7.3f}")
print(f"  이니스프리 원료 결합어 합계 : {inni:7.3f}")
print(f"  이니스프리 노세범(고민형)   : {A.get('노세범(이니스프리)',0):7.3f}")
print()
b_i, b_r = B.get("이니스프리", 1), B.get("라운드랩", 1)
print(f"  브랜드 검색   이니스프리 {b_i:7.3f}  vs  라운드랩 {b_r:7.3f}   "
      f"(이니스프리가 {b_i/b_r:.1f}배)")
print(f"  브랜드 대비 산지어 비율")
print(f"    라운드랩   {dokdo/b_r*100:6.1f}%")
print(f"    이니스프리 {inni/b_i*100:6.1f}%")
print()
print("  ※ 브랜드 체급이 다르므로 절대값이 아니라 '브랜드 대비 비율'로 판단할 것")

print()
print("  라운드랩 산지어 연도별 추이 (제품 출시 후 실제로 자랐는가)")
for k in ("독도(라운드랩)", "자작나무(라운드랩)"):
    ys = AY.get(k, {})
    print(f"    {k:<20}" + "  ".join(f"{y}:{ys.get(y,0):6.3f}" for y in range(2021, 2027)))
print(f"    {'라운드랩(브랜드)':<20}" + "  ".join(f"{y}:{BY['라운드랩'].get(y,0):6.3f}" for y in range(2021, 2027)))

# -*- coding: utf-8 -*-
"""제품어는 브랜드를 끌 수 있는가 — 14개 브랜드 통합 조사 (2016~2026)

풀려는 문제
  데이터랩 지수는 요청 단위로 재정규화된다. 그래서 지금까지 나온 값들을
  서로 비교할 수 없었고("자작나무 21.215" vs "화산송이 6.709" 같은 혼동),
  브랜드 체급이 달라 절대값 비교도 무의미했다.

해결
  1) 모든 요청에 `이니스프리`를 기준점으로 넣는다
  2) 기준점 값의 비로 전 요청을 같은 척도로 환산한다
  3) 그 위에서 '제품어 ÷ 자기 브랜드' 비율을 본다
     → 1보다 크면 제품 이름이 브랜드를 끌고 있는 것
     → 1보다 작으면 브랜드가 제품을 끌고 있는 것

이 비율은 체급과 무관하므로 작은 브랜드와 큰 브랜드를 공정하게 비교할 수 있다.
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
ANCHOR = "이니스프리"
A = {"groupName": ANCHOR, "keywords": ["이니스프리"]}

# 각 요청은 [기준점 + 브랜드/제품어 4개]. 기준점으로 나중에 같은 척도로 환산한다.
REQUESTS = [
    ("이니스프리 제품어", [A,
        {"groupName": "화산송이", "keywords": ["화산송이", "이니스프리 화산송이"]},
        {"groupName": "그린티", "keywords": ["이니스프리 그린티", "그린티 세럼"]},
        {"groupName": "노세범", "keywords": ["노세범", "이니스프리 노세범"]},
        {"groupName": "블랙티", "keywords": ["이니스프리 블랙티", "블랙티 유스"]}]),
    ("라운드랩", [A,
        {"groupName": "*라운드랩", "keywords": ["라운드랩"]},
        {"groupName": "자작나무", "keywords": ["자작나무 크림", "라운드랩 자작나무", "자작나무 선크림"]},
        {"groupName": "독도(참고)", "keywords": ["독도 토너", "1025 독도"]},
        {"groupName": "약콩", "keywords": ["라운드랩 약콩", "약콩 크림"]}]),
    ("토리든·에스네이처", [A,
        {"groupName": "*토리든", "keywords": ["토리든"]},
        {"groupName": "다이브인", "keywords": ["다이브인 세럼", "토리든 다이브인"]},
        {"groupName": "*에스네이처", "keywords": ["에스네이처"]},
        {"groupName": "스쿠알란", "keywords": ["스쿠알란 수분크림", "에스네이처 스쿠알란"]}]),
    ("비플레인·닥터지", [A,
        {"groupName": "*비플레인", "keywords": ["비플레인"]},
        {"groupName": "녹두", "keywords": ["비플레인 녹두", "녹두 클렌징폼"]},
        {"groupName": "*닥터지", "keywords": ["닥터지"]},
        {"groupName": "레드블레미쉬", "keywords": ["레드블레미쉬", "닥터지 레드블레미쉬"]}]),
    ("라네즈·메디힐", [A,
        {"groupName": "*라네즈", "keywords": ["라네즈"]},
        {"groupName": "크림스킨", "keywords": ["라네즈 크림스킨", "크림스킨"]},
        {"groupName": "*메디힐", "keywords": ["메디힐"]},
        {"groupName": "마데카소사이드", "keywords": ["마데카소사이드", "메디힐 마데카"]}]),
]

YEARS = list(range(2016, 2027))
raw = {}
for label, groups in REQUESTS:
    res = cli.datalab_search(start_date=START, end_date=END,
                            time_unit="month", keyword_groups=groups)
    for r in res["results"]:
        by = defaultdict(list)
        for d in r["data"]:
            by[int(d["period"][:4])].append(d["ratio"])
        allv = [d["ratio"] for d in r["data"]]
        raw[(label, r["title"])] = {
            "yearly": {k: sum(v) / len(v) for k, v in by.items()},
            "mean": sum(allv) / len(allv) if allv else 0,
        }
    time.sleep(0.5)

# 기준점(이니스프리)의 전기간 평균을 맞춰 전 요청을 같은 척도로 환산한다
base = raw[(REQUESTS[0][0], ANCHOR)]["mean"]
scaled = {}
for (label, name), d in raw.items():
    a = raw[(label, ANCHOR)]["mean"]
    f = (base / a) if a else 1.0
    if name == ANCHOR and label != REQUESTS[0][0]:
        continue  # 기준점은 한 번만
    scaled[name] = {"yearly": {y: v * f for y, v in d["yearly"].items()},
                    "mean": d["mean"] * f, "req": label}

print("=" * 112)
print("공통 척도 환산 결과 — 모든 값이 서로 비교 가능하다 (기준점: 이니스프리 브랜드 검색)")
print("=" * 112)
print(f"  {'계열':<16}" + "".join(f"{y:>7}" for y in YEARS) + f"{'정점':>7}{'2026':>8}")
order = sorted(scaled, key=lambda k: -scaled[k]["yearly"].get(2026, 0))
for n in order:
    s = scaled[n]["yearly"]
    pk = max(s, key=lambda k: s[k]) if s else "-"
    print(f"  {n:<16}" + "".join(f"{s.get(y,0):7.2f}" for y in YEARS) + f"{pk:>7}{s.get(2026,0):8.2f}")

print()
print("=" * 112)
print("제품어 ÷ 자기 브랜드 — 1을 넘으면 제품 이름이 브랜드를 끌고 있는 것이다")
print("=" * 112)
PAIRS = [
    ("이니스프리", ["화산송이", "그린티", "노세범", "블랙티"]),
    ("*라운드랩", ["자작나무", "독도(참고)", "약콩"]),
    ("*토리든", ["다이브인"]),
    ("*에스네이처", ["스쿠알란"]),
    ("*비플레인", ["녹두"]),
    ("*닥터지", ["레드블레미쉬"]),
    ("*라네즈", ["크림스킨"]),
    ("*메디힐", ["마데카소사이드"]),
]
print(f"  {'브랜드':<12}{'브랜드26':>9}   {'제품어':<14}{'제품26':>8}{'비율':>8}   판정")
for b, prods in PAIRS:
    bv = scaled.get(b, {}).get("yearly", {}).get(2026, 0)
    for p in prods:
        pv = scaled.get(p, {}).get("yearly", {}).get(2026, 0)
        r = pv / bv if bv else 0
        verdict = "제품이 브랜드를 끈다" if r >= 1 else ("대등" if r >= 0.5 else "브랜드가 제품을 끈다")
        print(f"  {b:<12}{bv:9.2f}   {p:<14}{pv:8.2f}{r:8.2f}   {verdict}")

print()
print("=" * 112)
print("무에서 만들어졌는가 — 2016년 값이 0에 가까운데 지금 큰 것")
print("=" * 112)
for n in order:
    s = scaled[n]["yearly"]
    v16, v26 = s.get(2016, 0), s.get(2026, 0)
    if n.startswith("*") or n == ANCHOR:
        continue
    origin = "무에서 생성" if v16 < 0.02 else f"2016에 이미 {v16:.2f}"
    print(f"  {n:<16} 2016 {v16:6.3f} → 2026 {v26:6.3f}   {origin}")

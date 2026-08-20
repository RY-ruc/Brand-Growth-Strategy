# -*- coding: utf-8 -*-
"""반론 검증 — "제주는 이미 1등이니 다른 데 집중한 게 맞다"가 성립하는가.

핵심 질문: 안 부르는 동안 그 자산은 유지되는가, 줄어드는가?
"""
import csv, sys
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8")

SRC = Path(r"C:\Users\EZ\Desktop\이니스프리_리브랜딩분석\Brand-Growth-Strategy\02_수집자료")
S = {}
with open(SRC / "naver_datalab_2021-2026_월간.csv", encoding="utf-8-sig") as f:
    for row in csv.DictReader(f):
        if row["호출"].startswith("3"):          # 키워드분해
            S.setdefault(row["그룹"], {})[row["기간"]] = float(row["상대검색량"])

def ytd(g, y, n=7):
    v = [S[g].get(f"{y}-{m:02d}") for m in range(1, n + 1)]
    return sum(v) / len(v) if all(x is not None for x in v) else None

def yr(g, y):
    v = [S[g].get(f"{y}-{m:02d}") for m in range(1, 13)]
    return sum(v) / 12 if all(x is not None for x in v) else None

print("=" * 78)
print("① 헤리티지 키워드 절대 검색량 — 안 부르는 동안 유지됐는가")
print("=" * 78)
print(f"{'연도':<8}{'브랜드':>10}{'제주':>10}{'그린티':>10}{'화산송이':>10}{'레티놀':>10}")
for y in range(2021, 2026):
    row = [yr(g, y) for g in ["브랜드", "제주", "그린티", "화산송이", "레티놀"]]
    print(f"{y:<8}" + "".join(f"{(v if v else 0):>10.3f}" for v in row))

print(f"\n{'5년 변화':<8}", end="")
for g in ["브랜드", "제주", "그린티", "화산송이", "레티놀"]:
    a, b = yr(g, 2021), yr(g, 2025)
    print(f"{((b-a)/a*100 if a else 0):>9.1f}%", end="")
print()

print("\n" + "=" * 78)
print("② 2026년(1~7월) — 지금도 계속 빠지는가")
print("=" * 78)
for g in ["브랜드", "제주", "그린티", "화산송이", "레티놀"]:
    a, b = ytd(g, 2025), ytd(g, 2026)
    if a and b:
        print(f"  {g:<8} {a:>8.3f} → {b:>8.3f}   YoY {((b-a)/a*100):>7.1f}%")

print("\n" + "=" * 78)
print("③ 그린티 월별 — '이미 이기고 있다'는 자산의 현재 상태")
print("=" * 78)
for y in (2025, 2026):
    vals = [(m, S["그린티"].get(f"{y}-{m:02d}")) for m in range(1, 13)]
    line = "  ".join(f"{m}월 {v:.3f}" for m, v in vals if v is not None)
    print(f"  {y}: {line}")
a, b = S["그린티"].get("2025-07"), S["그린티"].get("2026-07")
if a and b:
    print(f"\n  2026-07은 2025-07의 {b/a*100:.0f}% 수준")

print("\n" + "=" * 78)
print("④ 판정")
print("=" * 78)
jp_a, jp_b = yr("제주", 2021), yr("제주", 2025)
br_a, br_b = yr("브랜드", 2021), yr("브랜드", 2025)
print(f"  제주 절대 검색량 5년 변화   : {(jp_b-jp_a)/jp_a*100:+.1f}%")
print(f"  브랜드 절대 검색량 5년 변화 : {(br_b-br_a)/br_a*100:+.1f}%")
print()
for y in (2024, 2025):
    p = yr("제주", y - 1); c = yr("제주", y)
    pb = yr("브랜드", y - 1); cb = yr("브랜드", y)
    dj, db = (c - p) / p * 100, (cb - pb) / pb * 100
    verdict = "제주가 더 빨리 빠짐 ⚠" if dj < db else "제주가 더 버팀"
    print(f"  {y}년 YoY  제주 {dj:>6.1f}%  vs  브랜드 {db:>6.1f}%   → {verdict}")

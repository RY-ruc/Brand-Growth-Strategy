# -*- coding: utf-8 -*-
"""
2026 재현 조회 + 계절성 판정
- 기존 원자료.json의 키워드 그룹 정의를 그대로 재현하고 기간만 2026-08까지 확장
- "제주 연상" 정의 2종(그린티계 / 화산송이계)을 동시 조회해 정의 의존성 확인
"""
import json, os, sys, time
from pathlib import Path

BASE = Path(r"C:\Users\EZ\Downloads\naver_api_streamlit_dashboard")
sys.path.insert(0, str(BASE))
from naver_api import NaverClient  # noqa: E402

# .env 로드 (값은 출력하지 않는다)
env = {}
for line in (BASE / ".env").read_text(encoding="utf-8").splitlines():
    if "=" in line and not line.strip().startswith("#"):
        k, v = line.split("=", 1)
        env[k.strip()] = v.strip().strip('"').strip("'")

cli = NaverClient(client_id=env["NAVER_CLIENT_ID"], client_secret=env["NAVER_CLIENT_SECRET"])

START, END = "2021-01-01", "2026-08-18"

CALL_A = [
    {"groupName": "브랜드",        "keywords": ["이니스프리"]},
    {"groupName": "제주_그린티계",  "keywords": ["이니스프리 제주", "이니스프리 그린티"]},
    {"groupName": "제주_화산송이계", "keywords": ["이니스프리 제주", "이니스프리 화산송이"]},
    {"groupName": "제품군",        "keywords": ["이니스프리 레티놀", "이니스프리 앰플"]},
    {"groupName": "리브랜딩",      "keywords": ["이니스프리 리뉴얼", "이니스프리 로고"]},
]
CALL_B = [
    {"groupName": "이니스프리", "keywords": ["이니스프리"]},
    {"groupName": "토니모리",   "keywords": ["토니모리"]},
    {"groupName": "미샤",       "keywords": ["미샤"]},
]

OUT = Path(__file__).parent
CACHE = OUT / "raw_2026.json"

if CACHE.exists():                      # 재실행 시 쿼터 낭비 방지
    out = json.loads(CACHE.read_text(encoding="utf-8"))
else:
    out = {}
    for name, groups in (("call1_내부", CALL_A), ("call2_경쟁사", CALL_B)):
        out[name] = cli.datalab_search(
            start_date=START, end_date=END, time_unit="month", keyword_groups=groups
        )
        time.sleep(0.5)
    CACHE.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")

# ── series[group][YYYY-MM] = value ───────────────────────────
S = {}
for call in out.values():
    for r in call["results"]:
        S[r["title"]] = {d["period"][:7]: d["ratio"] for d in r["data"]}

months = sorted(S["브랜드"].keys())
print("조회 성공 · 기간", months[0], "~", months[-1], f"({len(months)}개월)")
print("그룹:", ", ".join(S.keys()))

# 2026-08은 미완월 → 제외
FULL = [m for m in months if m < "2026-08"]
YEARS = list(range(2021, 2027))
H1 = [f"{{}}-{m:02d}".format for m in range(1, 8)]  # 1~7월


def jan_jul(g, y):
    """해당 연도 1~7월 합계 (없으면 None)"""
    vals = [S[g].get(f"{y}-{m:02d}") for m in range(1, 8)]
    return sum(vals) if all(v is not None for v in vals) else None


def full_year(g, y):
    vals = [S[g].get(f"{y}-{m:02d}") for m in range(1, 13)]
    return sum(vals) if all(v is not None for v in vals) else None


L = []
w = L.append

w("# 2026 재현 조회 · 계절성 판정")
w("")
w(f"- 조회일 2026-08-19 · NAVER 데이터랩 검색어트렌드 · 월간 · {START} ~ {END}")
w("- 2026-08은 미완월이라 모든 집계에서 제외했다")
w("- 데이터랩 지수는 요청 단위로 재정규화되므로 **이 표의 절대값은 기존 CSV와 다르다**. 비율·증감률만 비교 대상")
w("")

# ── 1. RY 표 재현 (1~7월 기준) ───────────────────────────────
w("## 1. RY 0-0장 표 재현 (1~7월 동일구간)")
w("")
w("| 지표 | 2025(1–7월) | 2026(1–7월) | YoY |")
w("|---|---|---|---|")


def yoy(a, b):
    return f"{(b - a) / a * 100:+.1f}%" if a else "—"


for g in ["브랜드", "제품군", "토니모리", "미샤"]:
    a, b = jan_jul(g, 2025), jan_jul(g, 2026)
    w(f"| {g} | {a:.2f} | {b:.2f} | {yoy(a, b)} |")

for jeju in ["제주_그린티계", "제주_화산송이계"]:
    a = jan_jul(jeju, 2025) / jan_jul("브랜드", 2025) * 100
    b = jan_jul(jeju, 2026) / jan_jul("브랜드", 2026) * 100
    w(f"| **{jeju} 비중** | {a:.2f}% | {b:.2f}% | {b - a:+.2f}%p |")

sh25 = jan_jul("이니스프리", 2025) / sum(jan_jul(g, 2025) for g in ["이니스프리", "토니모리", "미샤"]) * 100
sh26 = jan_jul("이니스프리", 2026) / sum(jan_jul(g, 2026) for g in ["이니스프리", "토니모리", "미샤"]) * 100
w(f"| 경쟁 검색 점유율 | {sh25:.1f}% | {sh26:.1f}% | {sh26 - sh25:+.1f}%p |")
w("")

# ── 2. 제주 비중 연도별 (1~7월 고정 = 계절성 통제) ──────────
w("## 2. 계절성 통제 — 매년 1~7월만 잘라 비교")
w("")
w("같은 달끼리 비교하므로 계절성은 구조적으로 제거된다. 2026 하락이 추세 전환이면 여기서도 꺾여야 한다.")
w("")
w("| 연도 | 브랜드 지수(1–7월) | 제주_그린티계 비중 | 제주_화산송이계 비중 | 제품군 비중 |")
w("|---|---|---|---|---|")
for y in YEARS:
    b = jan_jul("브랜드", y)
    if b is None:
        continue
    r1 = jan_jul("제주_그린티계", y) / b * 100
    r2 = jan_jul("제주_화산송이계", y) / b * 100
    r3 = jan_jul("제품군", y) / b * 100
    w(f"| {y} | {b:.2f} | {r1:.2f}% | {r2:.2f}% | {r3:.2f}% |")
w("")

w("### 참고 — 연간(1~12월) 기준")
w("")
w("| 연도 | 브랜드 | 제주_그린티계 비중 | 제주_화산송이계 비중 |")
w("|---|---|---|---|")
for y in YEARS:
    b = full_year("브랜드", y)
    if b is None:
        w(f"| {y} | (미완결) | — | — |")
        continue
    w(f"| {y} | {b:.2f} | {full_year('제주_그린티계', y)/b*100:.2f}% | {full_year('제주_화산송이계', y)/b*100:.2f}% |")
w("")

# ── 3. 월별 YoY — 하락이 균일한가, 특정 달에 몰렸나 ──────────
w("## 3. 2026 월별 YoY — 하락이 균일한가")
w("")
w("특정 달에만 몰려 있으면 일시적 이벤트, 전 구간 균일하면 추세 전환에 가깝다.")
w("")
w("| 월 | 브랜드 25 | 브랜드 26 | YoY | 제주(그린티계) 비중 25 | 26 | 차이 | 토니모리 YoY |")
w("|---|---|---|---|---|---|---|---|")
for m in range(1, 8):
    k25, k26 = f"2025-{m:02d}", f"2026-{m:02d}"
    b25, b26 = S["브랜드"][k25], S["브랜드"][k26]
    j25 = S["제주_그린티계"][k25] / b25 * 100
    j26 = S["제주_그린티계"][k26] / b26 * 100
    t25, t26 = S["토니모리"][k25], S["토니모리"][k26]
    w(f"| {m}월 | {b25:.2f} | {b26:.2f} | {yoy(b25,b26)} | {j25:.2f}% | {j26:.2f}% | {j26-j25:+.2f}%p | {yoy(t25,t26)} |")
w("")

# ── 4. 월별 계절 프로파일 (2021-2025 평균) ──────────────────
w("## 4. 제주 비중의 월별 계절 프로파일 (2021–2025 평균)")
w("")
w("1~7월 구간이 연평균보다 구조적으로 높거나 낮은지 확인 — 1~7월 절단 자체가 편향을 만드는지 판정.")
w("")
w("| 월 | 제주_그린티계 비중 평균 | 연평균 대비 |")
w("|---|---|---|")
prof = {}
for m in range(1, 13):
    vals = []
    for y in range(2021, 2026):
        k = f"{y}-{m:02d}"
        if k in S["브랜드"]:
            vals.append(S["제주_그린티계"][k] / S["브랜드"][k] * 100)
    prof[m] = sum(vals) / len(vals)
avg = sum(prof.values()) / 12
for m in range(1, 13):
    w(f"| {m}월 | {prof[m]:.2f}% | {prof[m]-avg:+.2f}%p |")
w("")
w(f"- 12개월 평균 {avg:.2f}% / 1~7월 평균 {sum(prof[m] for m in range(1,8))/7:.2f}% / 8~12월 평균 {sum(prof[m] for m in range(8,13))/5:.2f}%")
w("")

# ── 5. 원자료 월별 전량 ─────────────────────────────────────
w("## 5. 월별 원자료 (2026)")
w("")
w("| 월 | " + " | ".join(S.keys()) + " |")
w("|" + "---|" * (len(S) + 1))
for m in FULL:
    if m >= "2026-01":
        w(f"| {m} | " + " | ".join(f"{S[g][m]:.3f}" for g in S) + " |")
w("")

(OUT / "결과_2026재현.md").write_text("\n".join(L), encoding="utf-8")

# CSV
import csv
with open(OUT / "naver_datalab_2021-2026_월간.csv", "w", newline="", encoding="utf-8-sig") as f:
    wr = csv.writer(f)
    wr.writerow(["기간"] + list(S.keys()))
    for m in months:
        wr.writerow([m] + [S[g].get(m, "") for g in S])

print("완료:", OUT / "결과_2026재현.md")

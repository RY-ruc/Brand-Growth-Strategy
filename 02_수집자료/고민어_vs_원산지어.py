# -*- coding: utf-8 -*-
"""반론 검증 — "사람들은 피부고민으로 검색하지 원산지로 검색하지 않는다"

이 반론이 맞다면 제주 전략은 '진입 키워드'로는 무의미하다.
그런데 '노세범'은 이니스프리 고유명사인데 크다. 왜 노세범만 됐는가?
→ 노세범은 '피지 조절'이라는 피부고민을 브랜드 언어로 만든 이름이다.
   제주·그린티·화산송이는 원산지·원료라 고민과 직결되지 않는다.
가설: 고유명사가 크려면 '고민'과 붙어 있어야 한다.

결과 해석은 01_분석결과/고민어_vs_원산지어_검증.md 참조.

주의 — 데이터랩 지수는 요청 단위 재정규화다. A·B·C는 별도 요청이므로
      표를 가로질러 값을 비교하면 안 된다.
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
        print(f"  {t:<24}{avg:8.3f}  {'█'*max(0,round(avg/mx*34))}{miss}")
        print(f"  {'':<24}{'':8}  └ {kw}")
    print()
    time.sleep(0.4)
    return {t: a for t, a, _, _ in rows}


A = run("A. 피부고민 언어 — 사람들이 실제로 쓰는 말",
        [{"groupName": "저자극·순한", "keywords": ["저자극 스킨케어", "순한 화장품", "저자극 크림"]},
         {"groupName": "여드름·트러블", "keywords": ["여드름 화장품", "트러블 케어 화장품", "여드름 크림"]},
         {"groupName": "건성·수분", "keywords": ["건성 스킨케어", "속건조 크림", "수분크림 추천"]},
         {"groupName": "지성·수부지", "keywords": ["지성 스킨케어", "수부지 크림", "지성피부 크림"]},
         {"groupName": "예민·민감", "keywords": ["민감성 화장품", "예민피부 크림", "진정 크림"]}],
        "반론의 근거 — 이게 크면 반론이 맞다")

B = run("B. 노세범은 왜 컸나 — 고민을 브랜드 언어로 만든 이름",
        [{"groupName": "노세범(브랜드어)", "keywords": ["노세범", "이니스프리 노세범"]},
         {"groupName": "피지조절(일반 고민어)", "keywords": ["피지 조절", "피지 컨트롤"]},
         {"groupName": "기름종이(일반 카테고리)", "keywords": ["기름종이"]},
         {"groupName": "화산송이(원료어)", "keywords": ["화산송이", "이니스프리 화산송이"]},
         {"groupName": "그린티(원료어)", "keywords": ["이니스프리 그린티", "그린티 세럼"]}],
        "노세범은 고민어에 가깝고, 화산송이·그린티는 원료어다")

# ⚠ '비자림·동백' 축은 결과가 오염됐다. '동백 오일'이 일반 원료명이라
#   헤어·바디 등 이니스프리 무관 검색을 대량으로 끌어온다. 인용 금지.
#   비자림 자산을 재려면 '이니스프리 비자림'처럼 브랜드 결합어로 다시 조회할 것.
C = run("C. 원료 × 고민 결합어 — 지금 얼마나 검색되는가",
        [{"groupName": "화산송이 모공", "keywords": ["화산송이 모공", "화산송이 클렌징", "화산송이 팩"]},
         {"groupName": "그린티 수분·건조", "keywords": ["그린티 수분", "그린티 보습", "그린티 수분크림"]},
         {"groupName": "제주 원료·성분", "keywords": ["제주 원료 화장품", "제주 성분 화장품", "제주 화장품"]},
         {"groupName": "녹차 진정·수분", "keywords": ["녹차 진정", "녹차 수분", "녹차 화장품"]},
         {"groupName": "비자림·동백(오염-인용금지)", "keywords": ["비자림 화장품", "동백 오일", "제주 동백"]}],
        "결합어가 0에 가까우면 '지금은 아무도 안 찾는다'가 사실이다")

print("=" * 84); print("판정"); print("=" * 84)
print(f"  피부고민 언어 합계        : {sum(A.values()):.1f}")
print(f"  그중 저자극·순한          : {A.get('저자극·순한',0):.3f}  ← 추상 고민어는 거의 안 쓰인다")
print(f"  노세범(고민형 브랜드어)   : {B.get('노세범(브랜드어)',0):.3f}")
print(f"  기름종이(직접 대체 카테고리): {B.get('기름종이(일반 카테고리)',0):.3f}")
print(f"  피지조절(추상 고민어)     : {B.get('피지조절(일반 고민어)',0):.3f}")
print(f"\n  → 노세범 > 기름종이 이면 브랜드어가 카테고리어를 대체한 것이다(제네릭 브랜드화).")
print(f"  → 검색 서열: 브랜드어 > 구체적 물건 >> 추상 고민어")
print(f"  원료×고민 결합어(비자림 제외): "
      f"{sum(v for k, v in C.items() if '비자림' not in k):.3f}  ← 사실상 0")

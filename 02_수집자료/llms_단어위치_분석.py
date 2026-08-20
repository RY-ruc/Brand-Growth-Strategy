# -*- coding: utf-8 -*-
"""제주·그린티가 llms.txt의 '어느 자리'에 있는가 — 제품명인가, 이야기인가, 검색 진입점인가"""
import re, ssl, sys, urllib.request
sys.stdout.reconfigure(encoding="utf-8")

req = urllib.request.Request("https://www.innisfree.com/llms.txt",
                             headers={"User-Agent": "Mozilla/5.0 (compatible; capstone/1.0)"})
with urllib.request.urlopen(req, timeout=20, context=ssl.create_default_context()) as r:
    txt = r.read().decode("utf-8", "replace")

# 자리 분류
brand_intro = txt.split("## 💄")[0]                     # 브랜드 소개 구역
product_names = re.findall(r"\* \[([^\]]+)\]\(https://www\.innisfree\.com/kr/ko/dp/product/\d+\)", txt)
queries = []
for _, desc in re.findall(r"\* \[([^\]]+)\]\(https://www\.innisfree\.com/kr/ko/dp/product/\d+\):\s*(.+)", txt):
    q = desc.split("의도로")[0].strip().rstrip(",")
    queries += [x.strip() for x in re.split(r"[,·]", q) if x.strip()]

for word in ["제주", "그린티", "녹차", "화산송이", "자연주의", "헤리티지"]:
    n_intro = brand_intro.count(word)
    n_name = sum(word in p for p in product_names)
    n_query = sum(word in q for q in queries)
    n_total = txt.count(word)
    print(f"\n■ '{word}'  총 {n_total}회")
    print(f"    브랜드 소개문 : {n_intro}회   ← 회사가 스스로를 설명하는 자리")
    print(f"    제품 이름     : {n_name}개    ← 라벨에만 붙어 있는 자리")
    print(f"    타겟 질의어   : {n_query}개    ← 소비자를 데려오는 자리")
    if n_intro and not n_query:
        print(f"    → 말은 하는데 그 말로 찾게 하지는 않는다")
    if n_name and not n_query:
        print(f"    → 라벨에는 있는데 검색 진입점으로는 안 쓴다")

print("\n" + "=" * 78)
print("타겟 질의어 34개 전량 — 무엇으로 찾게 하는가")
print("=" * 78)
BUCKET = {
    "기능·효능": ["수분", "보습", "속건조", "지성", "수부지", "톤업", "미백", "잡티", "탄력",
                "안티에이징", "트러블", "흔적", "모공", "피지", "딥클렌징", "저자극", "차단",
                "끈적", "나이트", "건성", "케어"],
    "성분": ["레티놀", "PDRN", "비타민C", "바하", "판테놀", "히알루론산", "시카"],
    "제형·카테고리": ["크림", "세럼", "앰플", "에센스", "선크림", "선세럼", "폼클렌징", "스킨부스터", "밀크"],
    "가치": ["비건"],
    "시즌": ["여름"],
    "헤리티지": ["제주", "그린티", "녹차", "화산송이", "자연주의"],
}
cnt = {k: 0 for k in BUCKET}
for q in queries:
    for k, kws in BUCKET.items():
        if any(w in q for w in kws):
            cnt[k] += 1
            break
for k, v in sorted(cnt.items(), key=lambda x: -x[1]):
    bar = "█" * v
    print(f"  {k:<12} {v:>2}개  {bar}")
print(f"\n  전체 {len(queries)}개")

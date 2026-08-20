# -*- coding: utf-8 -*-
"""히어로 상품 11개의 '타겟 질의어' 분석 —
회사가 AI에게 '이 검색어로 물으면 우리를 추천하라'고 지정한 키워드에 제주·그린티가 있는가"""
import re, ssl, sys, urllib.request
sys.stdout.reconfigure(encoding="utf-8")

req = urllib.request.Request("https://www.innisfree.com/llms.txt",
                             headers={"User-Agent": "Mozilla/5.0 (compatible; capstone/1.0)"})
with urllib.request.urlopen(req, timeout=20, context=ssl.create_default_context()) as r:
    txt = r.read().decode("utf-8", "replace")

# "* [상품명](url): 질의어 ... 의도로 탐색할 때 ..." 패턴
rows = re.findall(r"\* \[([^\]]+)\]\(https://www\.innisfree\.com/kr/ko/dp/product/\d+\):\s*(.+)", txt)

print("=" * 96)
print(f"히어로 상품 {len(rows)}개 — 회사가 지정한 타겟 질의어")
print("=" * 96)

HERITAGE = ["제주", "그린티", "녹차", "화산송이", "비자림", "자연주의", "청정"]
tot_q, herit_q = 0, 0

for name, desc in rows:
    q = desc.split("의도로")[0].strip().rstrip(",")
    queries = [x.strip() for x in re.split(r"[,·]", q) if x.strip()]
    tot_q += len(queries)
    hits = [x for x in queries if any(h in x for h in HERITAGE)]
    herit_q += len(hits)
    mark = "◆" if any(h in name for h in HERITAGE) else " "
    print(f"\n{mark} {name}")
    print(f"   질의어({len(queries)}): {' / '.join(queries)}")
    print(f"   헤리티지 질의어: {hits if hits else '없음'}")

print("\n" + "=" * 96)
print("집계")
print("=" * 96)
herit_products = [n for n, _ in rows if any(h in n for h in HERITAGE)]
print(f"  상품명에 헤리티지 원료가 든 제품 : {len(herit_products)}/{len(rows)}개")
for n in herit_products:
    print(f"      · {n}")
print(f"\n  전체 타겟 질의어           : {tot_q}개")
print(f"  그중 헤리티지 단어를 쓴 질의어 : {herit_q}개")
print(f"\n  → 회사는 제주·그린티 제품을 팔면서, 그 제품을 찾게 할 검색어로는")
print(f"     헤리티지 단어를 {herit_q}개 지정했다.")

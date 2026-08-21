# -*- coding: utf-8 -*-
"""경쟁사 자사몰 크롤링 — 브랜드 서사와 기계 가독성을 같은 잣대로 잰다.

메타 광고에서는 14곳 전부 브랜드 서사가 0건이었다. 그런데 광고는 원래 서사를
싣는 자리가 아니다. **자사몰이 서사가 있어야 하는 자리다.**
여기서도 0이면 업계 전체가 서사를 안 쓰는 것이고,
이니스프리만 있으면 "가진 것을 안 쓰고 있다"가 성립한다.

재는 것
  1. 브랜드 스토리 페이지가 있는가, 몇 글자인가
  2. 산지·원료·창립 서사 단어가 몇 번 나오는가 (홈 + 스토리)
  3. AEO 3항목 — llms.txt / JSON-LD 스키마 / robots.txt AI 크롤러 차단 여부
     (이니스프리 4/4 실측과 같은 잣대. FAQ 페이지는 경로가 브랜드마다 달라 제외)

주의
  - robots.txt는 기본이 허용이다. 이름이 없는 것은 차단이 아니다
  - 글자수는 렌더링 전 HTML 기준이라 SPA(자바스크립트로 그리는 사이트)는 과소 측정된다.
    0에 가깝게 나오면 SPA 여부를 반드시 따로 확인할 것
"""
import sys, ssl, re, json, time, html, urllib.request, urllib.error
from urllib.parse import urljoin, urlparse

sys.stdout.reconfigure(encoding="utf-8")

SITES = {
    "이니스프리":  "https://www.innisfree.com/kr/ko",
    "토리든":     "https://torriden.com/",
    "더샘":       "https://thesaemcosmetic.com/",
    "라네즈":     "https://www.laneige.com/",
    "라운드랩":   "https://roundlab.co.kr/",
    "에뛰드":     "https://www.etude.com/",
    "토니모리":   "https://tonymoly.com/",
    "웰라쥬":     "https://wellage.co.kr/",
    # dr-g.co.kr은 SNI 불일치로 SSL 실패, gowoonsesang.com은 DNS 미해석.
    # 실제로 응답하는 글로벌 도메인으로 잡는다 (국내몰과 내용이 다를 수 있으므로 인용 시 표기할 것)
    "닥터지":     "https://www.dr-g.com/",
    "메디힐":     "https://www.mediheal.co.kr/",
    "에스네이처":  "https://snature.co.kr/",
    "에스트라":   "https://www.aestura.com/web/main.do",
    "비플레인":   "https://beplain.co.kr/",
    "스킨푸드":   "https://www.theskinfood.com/",
}

# 산지·유래·창립 서사를 나타내는 말. 브랜드 고유 산지어를 함께 넣는다.
STORY = [
    "제주", "서귀포", "녹차", "화산송이", "비자림", "동백",          # 이니스프리
    "울릉도", "독도", "자작나무",                                    # 라운드랩
    "산지", "원산지", "재배", "농장", "밭", "청정", "자생",
    "창립", "설립", "철학", "헤리티지", "유래", "since", "브랜드 스토리",
    "자연주의", "우리의 이야기", "시작되었", "탄생",
]
STORY_LINK = re.compile(
    r"(about|brand|story|philosophy|heritage|introduce|company|history)", re.I)
STORY_LINK_KR = re.compile(r"(브랜드|스토리|소개|이야기|철학|역사|about)")

AI_BOTS = ["GPTBot", "ClaudeBot", "anthropic-ai", "Google-Extended",
           "PerplexityBot", "CCBot", "Bytespider", "Applebot-Extended"]

ctx = ssl.create_default_context(); ctx.check_hostname = False; ctx.verify_mode = ssl.CERT_NONE
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/128.0 Safari/537.36")


def get(url, limit=400000):
    req = urllib.request.Request(url, headers={
        "User-Agent": UA, "Accept-Language": "ko-KR,ko;q=0.9",
        "Accept": "text/html,application/xhtml+xml,*/*;q=0.8"})
    try:
        with urllib.request.urlopen(req, timeout=15, context=ctx) as r:
            raw = r.read(limit)
            enc = r.headers.get_content_charset() or "utf-8"
            return r.status, raw.decode(enc, "replace"), r.geturl()
    except urllib.error.HTTPError as e:
        return e.code, "", url
    except Exception:
        return None, "", url


def text_of(h):
    h = re.sub(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>", " ", h)
    h = re.sub(r"(?s)<[^>]+>", " ", h)
    return re.sub(r"\s+", " ", html.unescape(h)).strip()


def jsonld_types(h):
    out = []
    for m in re.finditer(r'(?is)<script[^>]+application/ld\+json[^>]*>(.*?)</script>', h):
        try:
            d = json.loads(m.group(1).strip())
        except Exception:
            continue
        for node in (d if isinstance(d, list) else [d]):
            if isinstance(node, dict):
                t = node.get("@type")
                if t:
                    out += t if isinstance(t, list) else [t]
                for g in node.get("@graph", []) or []:
                    if isinstance(g, dict) and g.get("@type"):
                        gt = g["@type"]
                        out += gt if isinstance(gt, list) else [gt]
    return sorted(set(out))


def story_page(base, home_html):
    cands = []
    for m in re.finditer(r'(?is)<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', home_html):
        href, label = m.group(1), text_of(m.group(2))[:40]
        if href.startswith(("#", "javascript:", "mailto:", "tel:")):
            continue
        if STORY_LINK.search(href) or STORY_LINK_KR.search(label):
            u = urljoin(base, href)
            if urlparse(u).netloc == urlparse(base).netloc:
                cands.append((u, label))
    seen, out = set(), []
    for u, l in cands:
        if u not in seen:
            seen.add(u); out.append((u, l))
    return out[:4]


print(f"{'브랜드':<9}{'llms':<7}{'스키마':<26}{'AI차단':<8}{'홈글자':>7}{'스토리글자':>9}{'서사어':>6}")
print("=" * 96)
rows = {}
for brand, url in SITES.items():
    st, home, final = get(url)
    if st != 200:
        print(f"  {brand:<9}접속 실패 ({st})")
        rows[brand] = {"error": st}
        continue
    root = f"{urlparse(final).scheme}://{urlparse(final).netloc}"

    ls, ltxt, _ = get(root + "/llms.txt", 200000)
    has_llms = (ls == 200 and "<html" not in ltxt[:400].lower())

    rs, rtxt, _ = get(root + "/robots.txt", 100000)
    blocked = []
    if rs == 200:
        for bot in AI_BOTS:
            m = re.search(rf"(?is)User-agent:\s*{re.escape(bot)}\s*(.*?)(?=\nUser-agent:|\Z)", rtxt)
            if m and re.search(r"(?im)^\s*Disallow:\s*/\s*$", m.group(1)):
                blocked.append(bot)

    schemas = jsonld_types(home)
    htxt = text_of(home)

    best_len, best_url, best_hits = 0, None, {}
    for u, _ in story_page(final, home):
        s2, h2, _ = get(u)
        if s2 == 200:
            t2 = text_of(h2)
            if len(t2) > best_len:
                best_len, best_url = len(t2), u
                best_hits = {w: t2.count(w) for w in STORY if t2.count(w)}
        time.sleep(0.4)

    home_hits = {w: htxt.count(w) for w in STORY if htxt.count(w)}
    merged = dict(home_hits)
    for k, v in best_hits.items():
        merged[k] = merged.get(k, 0) + v
    total_story = sum(merged.values())

    rows[brand] = {"root": root, "llms": has_llms, "llms_len": len(ltxt) if has_llms else 0,
                   "schemas": schemas, "blocked": blocked, "home_len": len(htxt),
                   "story_url": best_url, "story_len": best_len, "hits": merged}

    print(f"  {brand:<9}{'O' if has_llms else '-':<7}{','.join(schemas)[:24]:<26}"
          f"{(','.join(blocked)[:6] if blocked else '-'):<8}{len(htxt):>7}{best_len:>9}{total_story:>6}")
    time.sleep(0.6)

print("\n" + "=" * 96)
print("서사 단어 상세 (홈 + 스토리 페이지 합산)")
print("=" * 96)
for b, r in rows.items():
    if "hits" not in r:
        print(f"  {b:<9}  접속 실패 — 수동 확인 필요")
        continue
    hits = r["hits"]
    top = ", ".join(f"{k} {v}" for k, v in sorted(hits.items(), key=lambda x: -x[1])[:8])
    print(f"  {b:<9}{sum(hits.values()):>4}회  {top if top else '(없음)'}")
    if r["story_url"]:
        print(f"  {'':<9}      스토리: {r['story_url'][:76]}")

with open("경쟁사_자사몰_실측.json", "w", encoding="utf-8") as f:
    json.dump(rows, f, ensure_ascii=False, indent=1)
print("\n→ 경쟁사_자사몰_실측.json 저장")

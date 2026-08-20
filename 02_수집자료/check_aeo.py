# -*- coding: utf-8 -*-
"""
check_aeo.py — AEO/SEO 대응 상태 자동 점검

이니스프리 공식몰을 직접 조회해 4개 항목을 판정하고 결과를 JSON으로 남긴다.
`dashboard_data.json`이 있으면 그 안의 kpi.aeo 블록도 실측값으로 교체한다
조사 전용 도구다 — 대시보드에는 연결하지 않는다.
(랜딩·상세페이지를 제안하는 마당에 대시보드가 "이미 완비"라고 보여주면 제안과 충돌한다.)

사용법
    python check_aeo.py            # 점검 → data/aeo_status.json (+ 대시보드 반영)
    python check_aeo.py --no-apply # 점검만, 대시보드는 건드리지 않음

왜 자동화하는가
    llms.txt는 팀 08-18 점검 때 404였는데 재조회에서는 200 OK다. 이렇게 바뀌는
    유동 항목이라 수동 점검 결과를 문서에 박아두면 금방 낡는다.

점검 항목 (KPI 4위 · 실행 지표)
    1) robots.txt에 AI 크롤러 전용 규칙이 있는가
    2) llms.txt가 존재하는가 (200 응답)
    3) 메인 페이지에 FAQPage 스키마(JSON-LD)가 있는가
    4) FAQ형 콘텐츠 경로가 존재하는가

한계
    공식몰이 클라이언트 렌더링(SPA)이면 정적 조회로는 스키마를 못 본다.
    그 경우 3)은 '판정 보류'로 남기며, 이는 "없음"과 다르다.
"""
from __future__ import annotations

import argparse
import json
import re
import ssl
import urllib.error
import urllib.request
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "aeo_실사" / "aeo_status.json"

KST = timezone(timedelta(hours=9))

BASE = "https://www.innisfree.com"
UA = "Mozilla/5.0 (compatible; capstone-research/1.0; +brand-awareness-monitor)"
TIMEOUT = 12

# 확인할 AI 크롤러 (해당 UA를 명시적으로 다루는 규칙이 있는지)
AI_BOTS = ["GPTBot", "ClaudeBot", "anthropic-ai", "PerplexityBot",
           "CCBot", "Google-Extended", "Applebot-Extended", "Bytespider"]

# 실제 경로는 llms.txt가 직접 알려준다(2026-08-20 확인). 추측 경로만 보다가
# 존재하는 FAQ를 '없음'으로 잘못 판정했던 이력이 있어 공식 경로를 맨 앞에 둔다.
FAQ_PATHS = [
    "/kr/ko/cu/support/faq",   # llms.txt에 명시된 공식 FAQ
    "/faq", "/support/faq", "/cs/faq", "/help", "/customer/faq",
]

# FAQPage 스키마는 메인이 아니라 FAQ 페이지에 있을 가능성이 높다.
# llms.txt가 "모든 PDP에 JSON-LD가 구현돼 있다"고 밝히므로 상품 페이지도 함께 본다.
SCHEMA_PATHS = [
    "/kr/ko/cu/support/faq",            # FAQ 페이지
    "/",                                 # 메인
    "/kr/ko/dp/product/103436",          # 히어로 상품 PDP (그린티 히알루론산 수분 크림)
]


def fetch_h(url: str) -> tuple[int, str, dict | None]:
    """(status, body, headers) — 헤더까지 필요한 경우"""
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept": "text/html,application/xhtml+xml,text/plain,*/*",
        "Accept-Language": "ko-KR,ko;q=0.9",
    })
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT, context=ssl.create_default_context()) as r:
            raw = r.read(600_000)
            enc = r.headers.get_content_charset() or "utf-8"
            return r.status, raw.decode(enc, errors="replace"), dict(r.headers)
    except urllib.error.HTTPError as e:
        return e.code, "", (dict(e.headers) if e.headers else None)
    except Exception as e:
        return 0, f"{type(e).__name__}: {e}", None


def fetch(url: str) -> tuple[int, str]:
    """(status, body) — 실패 시 (0, 사유)"""
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept": "text/html,application/xhtml+xml,text/plain,*/*",
        "Accept-Language": "ko-KR,ko;q=0.9",
    })
    ctx = ssl.create_default_context()
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT, context=ctx) as r:
            raw = r.read(600_000)
            enc = r.headers.get_content_charset() or "utf-8"
            return r.status, raw.decode(enc, errors="replace")
    except urllib.error.HTTPError as e:
        return e.code, ""
    except Exception as e:  # 네트워크·타임아웃·SSL
        return 0, f"{type(e).__name__}: {e}"


def check_robots() -> dict:
    """robots.txt — 판정 기준을 '차단 여부'로 바로잡았다(2026-08-20).

    기존에는 'GPTBot 등 전용 규칙이 있는가'로 봤고 없으면 미충족 처리했다. 그런데
    robots.txt는 기본이 허용이라, 전용 규칙이 없다는 것은 '차단하지 않는다'는 뜻이다.
    AEO에서 중요한 것은 AI 크롤러가 실제로 접근할 수 있는가이지 이름이 적혀 있는가가 아니다.
    → 차단이 없으면 충족으로 본다. 명시적 차단이 있을 때만 미충족.
    """
    st, body = fetch(f"{BASE}/robots.txt")
    if st != 200:
        return {"k": "robots.txt — AI 크롤러 접근", "ok": None,
                "note": f"조회 실패(status {st}) — 판정 보류"}

    # AI 봇을 이름으로 차단하는 블록이 있는가
    blocked = []
    for bot in AI_BOTS:
        m = re.search(rf"(?ims)^user-agent:\s*{re.escape(bot)}\s*$(.*?)(?=^user-agent:|\Z)", body)
        if m and re.search(r"(?im)^disallow:\s*/\s*$", m.group(1)):
            blocked.append(bot)
    # 전체(*) 블록이 사이트를 통째로 막는가
    star = re.search(r"(?ims)^user-agent:\s*\*\s*$(.*?)(?=^user-agent:|\Z)", body)
    star_all = bool(star and re.search(r"(?im)^disallow:\s*/\s*$", star.group(1)))

    named = [b for b in AI_BOTS if re.search(rf"(?im)^user-agent:\s*{re.escape(b)}\s*$", body)]
    dis = len(re.findall(r"(?im)^disallow:", body))

    if star_all or blocked:
        who = ", ".join(blocked) if blocked else "전체(*)"
        return {"k": "robots.txt — AI 크롤러 접근", "ok": False,
                "note": f"차단됨 — {who}에 Disallow: / 적용. llms.txt가 있어도 크롤러가 못 읽는다"}

    detail = (f"AI 봇 명시 {', '.join(named)}" if named
              else "AI 봇 개별 명시는 없음(= 기본 허용)")
    return {"k": "robots.txt — AI 크롤러 접근", "ok": True,
            "note": f"접근 허용 · {detail} · 차단 경로는 중복·API {dis}건뿐 — 전체 차단 없음"}


def check_llms() -> dict:
    """llms.txt — Last-Modified로 '언제 만들어졌는지'까지 기록한다.

    서버 Last-Modified는 2026-08-18 14:16:45 KST다. 다만 이 헤더는 '그 시각에
    파일이 쓰였다'만 증명하고 신규 생성과 기존 파일 갱신을 구분하지 못한다.
    웨이백·archive.today 스냅샷이 0건이라 이전 존재 여부도 확인 불가.
    → '신설'로 단정하지 말고 '최종 갱신 시각'으로만 인용할 것.
    """
    st, body, hdr = fetch_h(f"{BASE}/llms.txt")
    if st == 200 and body.strip():
        lm = hdr.get("Last-Modified") if hdr else None
        when = ""
        if lm:
            try:
                dt = parsedate_to_datetime(lm).astimezone(KST)
                when = f" · 최종 갱신 {dt:%Y-%m-%d %H:%M} KST(서버 기준)"
            except Exception:
                when = f" · Last-Modified {lm}"
        head = " ".join(body.split())[:70]
        return {"k": "llms.txt", "ok": True,
                "note": f"200 OK · {len(body):,}자{when} · 첫머리 “{head}…”",
                "last_modified": lm}
    if st == 404:
        return {"k": "llms.txt", "ok": False, "note": "404 — 파일 없음"}
    return {"k": "llms.txt", "ok": None, "note": f"판정 보류 (status {st})"}


def _ld_types(body: str) -> tuple[list[str], int]:
    blocks = re.findall(r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
                        body, re.S | re.I)
    types: list[str] = []
    for b in blocks:
        try:
            data = json.loads(b.strip())
        except json.JSONDecodeError:
            continue
        stack = [data]
        while stack:                       # @graph 등 중첩 구조까지 훑는다
            cur = stack.pop()
            if isinstance(cur, list):
                stack.extend(cur)
            elif isinstance(cur, dict):
                t = cur.get("@type")
                if t:
                    types += t if isinstance(t, list) else [t]
                for v in cur.values():
                    if isinstance(v, (list, dict)):
                        stack.append(v)
    return types, len(blocks)


def check_faq_schema() -> dict:
    """FAQPage 스키마 — 메인만 보면 놓친다. FAQ 페이지·상품 PDP까지 확인한다."""
    seen: dict[str, list[str]] = {}
    any_ok = False
    for p in SCHEMA_PATHS:
        st, body = fetch(BASE + p if p != "/" else BASE)
        if st != 200:
            seen[p] = [f"status {st}"]
            continue
        types, n = _ld_types(body)
        seen[p] = sorted(set(types)) or [f"JSON-LD {n}개·타입 불명" if n else "JSON-LD 없음"]
        if "FAQPage" in types:
            any_ok = True

    detail = " / ".join(f"{p} → {', '.join(v)}" for p, v in seen.items())
    if any_ok:
        return {"k": "FAQPage 스키마(JSON-LD)", "ok": True, "note": f"확인 · {detail}"}
    found_any_ld = any(v and not v[0].startswith(("status", "JSON-LD 없음")) for v in seen.values())
    return {"k": "FAQPage 스키마(JSON-LD)", "ok": False if found_any_ld else None,
            "note": (f"FAQPage 없음 — {detail}" if found_any_ld
                     else f"판정 보류(JSON-LD 미검출) — {detail}")}


def check_faq_content() -> dict:
    hits = []
    for p in FAQ_PATHS:
        st, _ = fetch(BASE + p)
        if st == 200:
            hits.append(p)
    if hits:
        return {"k": "FAQ형 콘텐츠 경로", "ok": True, "note": f"존재: {', '.join(hits)}"}
    return {"k": "FAQ형 콘텐츠 경로", "ok": False,
            "note": f"확인한 경로 {len(FAQ_PATHS)}개 모두 미응답 — 제품나열형 구조"}


SNAPDIR = HERE / "aeo_실사" / "llms_snapshots"


def snapshot_llms() -> dict:
    """llms.txt 본문을 보관하고 직전 스냅샷과 비교한다.

    과거 버전은 구할 수 없다 — 웨이백·archive.today·Common Crawl 모두 이 URL 스냅샷이 0건이다
    (도메인 자체는 1996년부터 아카이브되지만 llms.txt는 크롤 대상이 아니었다).
    그래서 '8/18에 무엇이 바뀌었나'는 영구히 알 수 없다.
    대신 지금부터 매번 보관해두면 다음 변경은 무엇이 바뀌었는지 정확히 말할 수 있다.
    """
    import difflib
    import hashlib

    st, body, hdr = fetch_h(f"{BASE}/llms.txt")
    if st != 200 or not body.strip():
        return {"ok": False, "note": f"스냅샷 실패(status {st})"}

    SNAPDIR.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256(body.encode("utf-8")).hexdigest()[:12]
    lm = (hdr or {}).get("Last-Modified", "")
    stamp = datetime.now(KST).strftime("%Y%m%d-%H%M")

    prev = sorted(SNAPDIR.glob("llms_*.txt"))
    changed, diff_lines = None, []
    if prev:
        old = prev[-1].read_text(encoding="utf-8")
        changed = (old != body)
        if changed:
            diff_lines = [l for l in difflib.unified_diff(
                old.splitlines(), body.splitlines(),
                fromfile=prev[-1].name, tofile=f"llms_{stamp}.txt", lineterm="", n=1)]

    if not prev or changed:
        (SNAPDIR / f"llms_{stamp}_{digest}.txt").write_text(body, encoding="utf-8")

    if not prev:
        print(f"  [스냅샷] 최초 보관 — 이후 변경분부터 diff 가능 ({len(body):,}자)")
        return {"ok": True, "first": True, "digest": digest, "last_modified": lm}
    if changed:
        print(f"  [스냅샷] ⚠ llms.txt 변경 감지 — {len(diff_lines)}줄 차이")
        for l in diff_lines[:40]:
            print(f"      {l}")
        (SNAPDIR / f"diff_{stamp}.txt").write_text("\n".join(diff_lines), encoding="utf-8")
        return {"ok": True, "changed": True, "digest": digest,
                "diff_lines": len(diff_lines), "last_modified": lm}
    print(f"  [스냅샷] 직전과 동일 (sha {digest})")
    return {"ok": True, "changed": False, "digest": digest, "last_modified": lm}


def main(apply_to_dashboard: bool = False) -> dict:  # 대시보드 연동 없음
    print(f"[AEO] {BASE} 점검 시작")
    snap = snapshot_llms()
    items = [check_robots(), check_llms(), check_faq_schema(), check_faq_content()]
    score = sum(1 for i in items if i["ok"] is True)
    pending = sum(1 for i in items if i["ok"] is None)

    result = {
        "checked": datetime.now(KST).strftime("%Y-%m-%d %H:%M KST"),
        "base_url": BASE,
        "score": score,
        "total": len(items),
        "pending": pending,
        "items": items,
        "llms_snapshot": snap,
        "_note": "실행 지표(회사가 숙제를 했는가)이지 소비자 인지 지표가 아니다. KR 목록 밖. "
                 "항목이 유동적이므로 인용 시점을 반드시 함께 표기할 것.",
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding="utf-8")

    for i in items:
        mark = "●" if i["ok"] is True else ("○" if i["ok"] is False else "◐")
        print(f"  {mark} {i['k']} — {i['note']}")
    print(f"[AEO] {score}/{len(items)} 충족" + (f" (판정 보류 {pending}건)" if pending else ""))
    print(f"  → {OUT.relative_to(HERE)}")

    return result


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="AEO/SEO 대응 상태 자동 점검")
    ap.add_argument("--no-apply", action="store_true", help="대시보드 데이터는 갱신하지 않음")
    main(apply_to_dashboard=not ap.parse_args().no_apply)

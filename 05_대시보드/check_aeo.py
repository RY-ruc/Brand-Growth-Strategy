# -*- coding: utf-8 -*-
"""
check_aeo.py — AEO/SEO 대응 상태 자동 점검

이니스프리 공식몰을 직접 조회해 4개 항목을 판정하고 결과를 JSON으로 남긴다.
`dashboard_data.json`이 있으면 그 안의 kpi.aeo 블록도 실측값으로 교체한다
(build_data.py를 건드리지 않고 후처리만 한다).

사용법
    python check_aeo.py            # 점검 → data/aeo_status.json (+ 대시보드 반영)
    python check_aeo.py --no-apply # 점검만, 대시보드는 건드리지 않음

왜 자동화하는가
    llms.txt는 2026-08-18에 404였다가 08-19에 200 OK로 생겼다. 하루 만에 바뀌는
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
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "data" / "aeo_status.json"
DASH = HERE / "data" / "dashboard_data.json"
KST = timezone(timedelta(hours=9))

BASE = "https://www.innisfree.com"
UA = "Mozilla/5.0 (compatible; capstone-research/1.0; +brand-awareness-monitor)"
TIMEOUT = 12

# 확인할 AI 크롤러 (해당 UA를 명시적으로 다루는 규칙이 있는지)
AI_BOTS = ["GPTBot", "ClaudeBot", "anthropic-ai", "PerplexityBot",
           "CCBot", "Google-Extended", "Applebot-Extended", "Bytespider"]

FAQ_PATHS = ["/faq", "/support/faq", "/cs/faq", "/help", "/customer/faq"]


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
    st, body = fetch(f"{BASE}/robots.txt")
    if st != 200:
        return {"k": "robots.txt AI 크롤러 규칙", "ok": None,
                "note": f"robots.txt 조회 실패(status {st}) — 판정 보류"}
    found = [b for b in AI_BOTS if re.search(rf"User-agent:\s*{re.escape(b)}", body, re.I)]
    if found:
        return {"k": "robots.txt AI 크롤러 규칙", "ok": True,
                "note": f"전용 규칙 확인: {', '.join(found)}"}
    ua_count = len(re.findall(r"^\s*User-agent:", body, re.I | re.M))
    return {"k": "robots.txt AI 크롤러 규칙", "ok": False,
            "note": f"AI 크롤러 전용 규칙 없음 (User-agent 블록 {ua_count}개 — 범용 규칙만)"}


def check_llms() -> dict:
    st, body = fetch(f"{BASE}/llms.txt")
    if st == 200 and body.strip():
        head = " ".join(body.split())[:90]
        return {"k": "llms.txt", "ok": True,
                "note": f"200 OK · {len(body)}자 · 첫머리 “{head}…”"}
    if st == 404:
        return {"k": "llms.txt", "ok": False, "note": "404 — 파일 없음"}
    return {"k": "llms.txt", "ok": None, "note": f"판정 보류 (status {st})"}


def check_faq_schema() -> dict:
    st, body = fetch(BASE)
    if st != 200:
        return {"k": "FAQPage 스키마(JSON-LD)", "ok": None,
                "note": f"메인 페이지 조회 실패(status {st}) — 판정 보류"}
    blocks = re.findall(r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
                        body, re.S | re.I)
    types: list[str] = []
    for b in blocks:
        try:
            data = json.loads(b.strip())
        except json.JSONDecodeError:
            continue
        for item in (data if isinstance(data, list) else [data]):
            if isinstance(item, dict) and item.get("@type"):
                t = item["@type"]
                types += t if isinstance(t, list) else [t]
    if "FAQPage" in types:
        return {"k": "FAQPage 스키마(JSON-LD)", "ok": True, "note": f"확인 · 스키마 {', '.join(sorted(set(types)))}"}
    if blocks:
        return {"k": "FAQPage 스키마(JSON-LD)", "ok": False,
                "note": f"JSON-LD {len(blocks)}개 있으나 FAQPage 아님 ({', '.join(sorted(set(types))) or '타입 불명'})"}
    # SPA면 정적 HTML에 스키마가 없는 게 정상 — '없음'으로 단정하지 않는다
    spa = len(body) < 60_000 and body.count("<script") > 3
    return {"k": "FAQPage 스키마(JSON-LD)", "ok": None if spa else False,
            "note": "정적 HTML에 JSON-LD 없음 — 클라이언트 렌더링 추정, 판정 보류" if spa
                    else "JSON-LD 자체가 없음"}


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


def main(apply_to_dashboard: bool = True) -> dict:
    print(f"[AEO] {BASE} 점검 시작")
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

    if apply_to_dashboard and DASH.exists():
        d = json.loads(DASH.read_text(encoding="utf-8"))
        d.setdefault("kpi", {})["aeo"] = {
            "score": score, "total": len(items),
            "checked": result["checked"].split()[0],
            "items": items,
        }
        d.setdefault("meta", {})["aeo_checked_at"] = result["checked"]
        DASH.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"  → dashboard_data.json의 kpi.aeo 실측값으로 갱신")
    return result


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="AEO/SEO 대응 상태 자동 점검")
    ap.add_argument("--no-apply", action="store_true", help="대시보드 데이터는 갱신하지 않음")
    main(apply_to_dashboard=not ap.parse_args().no_apply)

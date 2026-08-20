# -*- coding: utf-8 -*-
"""
serve.py — 대시보드 로컬 서버

포트를 코드에 박지 않고 `PORT` 환경변수에서 받는다. 여러 세션이 동시에 띄워도
포트가 겹치지 않게 하기 위함이다(없으면 8765를 기본으로 쓴다).

    python 05_대시보드/serve.py          # http://localhost:8765
    PORT=9000 python 05_대시보드/serve.py # http://localhost:9000

저장소 루트를 서빙하므로 `/02_수집자료/...` 같은 다른 폴더의 파일도 함께 열린다.
루트(`/`)로 들어오면 대시보드로 보낸다.
"""
from __future__ import annotations

import functools
import http.server
import os
import sys
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent   # Brand-Growth-Strategy/
PORT = int(os.environ.get("PORT") or 8765)

# HTTP 헤더는 latin-1로 인코딩된다. 폴더명이 한글이라 그대로 넣으면
# UnicodeEncodeError로 서버가 매 요청마다 죽는다 → 반드시 퍼센트 인코딩할 것.
HOME_PATH = f"/{Path(__file__).resolve().parent.name}/index.html"
HOME = urllib.parse.quote(HOME_PATH)


class Handler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path in ("/", "/index.html"):
            self.send_response(302)
            self.send_header("Location", HOME)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        super().do_GET()

    def end_headers(self):
        # 자산을 고쳐도 옛 파일이 잡히지 않도록 캐시를 끈다
        self.send_header("Cache-Control", "no-store, must-revalidate")
        super().end_headers()

    def log_message(self, fmt, *args):        # 접근 로그는 조용히
        if "404" in (fmt % args):
            sys.stderr.write(f"  404 {args[0] if args else ''}\n")


class Server(http.server.ThreadingHTTPServer):
    """단일 스레드면 브라우저가 연결을 물고 있을 때 나머지 요청이 막힌다."""
    allow_reuse_address = True
    daemon_threads = True


if __name__ == "__main__":
    handler = functools.partial(Handler, directory=str(ROOT))
    with Server(("", PORT), handler) as httpd:
        print(f"대시보드 → http://localhost:{PORT}{HOME_PATH}")
        print(f"서빙 루트: {ROOT}")
        sys.stdout.flush()
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n종료")

/* 이니스프리 브랜드 인지도 대시보드 — 렌더러
   외부 차트 라이브러리 없이 인라인 SVG로 그린다(오프라인·파일 열기로도 동작).
   데이터는 data/dashboard_data.json (build_data.py 산출물). */

const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];
const fmt = (v, d = 1) => (v === null || v === undefined) ? '—' : Number(v).toFixed(d);
const sign = v => (v > 0 ? '+' : '') + fmt(v);

let D = null;
let DIRECT_SET = new Set(['이니스프리', '미샤', '3CE']);

/* ── 차트 헬퍼 ─────────────────────────────── */
/* viewBox 폭보다 과하게 확대되면 차트 안 글자가 커지므로 상한(1.25배)을 건다 */
function svg(vb, inner, cls = '') {
  const w = parseFloat(vb.split(/\s+/)[2]) || 0;
  const cap = w ? ` style="max-width:${Math.round(w * 1.25)}px"` : '';
  return `<svg viewBox="${vb}" class="${cls}"${cap} preserveAspectRatio="xMidYMid meet" role="img">${inner}</svg>`;
}
const esc = s => String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

function scale(vals, lo, hi, invert = true) {
  const mn = Math.min(...vals), mx = Math.max(...vals), sp = (mx - mn) || 1;
  return v => invert ? hi - ((v - mn) / sp) * (hi - lo) : lo + ((v - mn) / sp) * (hi - lo);
}

/* 라인 차트 (다계열) */
function lineChart({ labels, series, w = 540, h = 150, pad = { l: 34, r: 12, t: 16, b: 22 }, marks = [] }) {
  const xs = i => pad.l + i * (w - pad.l - pad.r) / Math.max(1, labels.length - 1);
  let out = `<line x1="${pad.l}" y1="${h - pad.b}" x2="${w - pad.r}" y2="${h - pad.b}" stroke="#E8E2D6"/>`;
  marks.forEach(m => {
    const x = xs(m.i);
    out += `<line x1="${x}" y1="${pad.t - 6}" x2="${x}" y2="${h - pad.b}" stroke="#C97C86" stroke-width="1" stroke-dasharray="2 3" opacity=".7"/>
            <text x="${x}" y="${pad.t - 9}" text-anchor="middle" font-size="8.5" fill="#8E4A52" font-weight="700">${esc(m.label)}</text>`;
  });
  series.forEach(s => {
    const y = scale(s.values.filter(v => v != null), pad.t, h - pad.b);
    const pts = s.values.map((v, i) => v == null ? null : `${xs(i).toFixed(1)},${y(v).toFixed(1)}`).filter(Boolean).join(' ');
    out += `<polyline points="${pts}" fill="none" stroke="${s.color}" stroke-width="${s.w || 2}"
             ${s.dash ? `stroke-dasharray="${s.dash}"` : ''} stroke-linejoin="round"/>`;
    if (s.label) out += `<text x="${pad.l + 2}" y="${s.labelY}" font-size="9" font-weight="500" fill="${s.color}">${esc(s.label)}</text>`;
  });
  labels.forEach((l, i) => {
    if (l) out += `<text x="${xs(i)}" y="${h - 6}" text-anchor="middle" font-size="8.5" opacity=".45">${esc(l)}</text>`;
  });
  return svg(`0 0 ${w} ${h}`, out);
}

/* 막대 차트 */
function barChart({ labels, values, color = '#3B5D48', hiIdx = -1, w = 230, h = 145, unit = '' }) {
  const pad = { l: 20, r: 12, t: 14, b: 26 };
  const mx = Math.max(...values), bw = (w - pad.l - pad.r) / values.length * .58;
  const step = (w - pad.l - pad.r) / values.length;
  let out = `<line x1="${pad.l - 4}" y1="${h - pad.b}" x2="${w - pad.r}" y2="${h - pad.b}" stroke="#E8E2D6"/>`;
  values.forEach((v, i) => {
    const bh = (v / mx) * (h - pad.t - pad.b);
    const x = pad.l + i * step + (step - bw) / 2, y = h - pad.b - bh;
    const isHi = i === hiIdx;
    out += `<rect x="${x.toFixed(1)}" y="${y.toFixed(1)}" width="${bw.toFixed(1)}" height="${bh.toFixed(1)}"
             fill="${isHi ? '#24382C' : color}" opacity="${isHi ? 1 : (.45 + i * .1).toFixed(2)}"/>
            <text x="${(x + bw / 2).toFixed(1)}" y="${(y - 4).toFixed(1)}" text-anchor="middle" font-size="${isHi ? 9.5 : 8.5}"
             font-weight="${isHi ? 700 : 400}" fill="#22241F" opacity="${isHi ? 1 : .62}">${v}${unit}</text>
            <text x="${(x + bw / 2).toFixed(1)}" y="${h - 8}" text-anchor="middle" font-size="8.5" opacity=".45">${esc(labels[i])}</text>`;
  });
  return svg(`0 0 ${w} ${h}`, out);
}

/* 산점도 + 추세선 */
function scatter({ pts, w = 250, h = 138, trend = true, color = '#24382C', trendColor = '#9FB89A', xlab, ylab }) {
  const pad = { l: 26, r: 14, t: 14, b: 26 };
  const xv = pts.map(p => p.x), yv = pts.map(p => p.y);
  const xmn = Math.min(...xv), xmx = Math.max(...xv), ymn = Math.min(...yv), ymx = Math.max(...yv);
  const X = v => pad.l + (v - xmn) / ((xmx - xmn) || 1) * (w - pad.l - pad.r);
  const Y = v => (h - pad.b) - (v - ymn) / ((ymx - ymn) || 1) * (h - pad.t - pad.b);
  let out = `<line x1="${pad.l - 4}" y1="${h - pad.b}" x2="${w - pad.r}" y2="${h - pad.b}" stroke="#E8E2D6"/>`;
  if (trend) {
    const n = pts.length, sx = xv.reduce((a, b) => a + b, 0), sy = yv.reduce((a, b) => a + b, 0);
    const sxy = pts.reduce((a, p) => a + p.x * p.y, 0), sxx = pts.reduce((a, p) => a + p.x * p.x, 0);
    const b = (n * sxy - sx * sy) / ((n * sxx - sx * sx) || 1), a = (sy - b * sx) / n;
    out += `<line x1="${X(xmn)}" y1="${Y(a + b * xmn)}" x2="${X(xmx)}" y2="${Y(a + b * xmx)}"
             stroke="${trendColor}" stroke-width="1.3" stroke-dasharray="4 3"/>`;
  }
  pts.forEach(p => {
    out += `<circle cx="${X(p.x).toFixed(1)}" cy="${Y(p.y).toFixed(1)}" r="4.2" fill="${color}"><title>${esc(p.t || '')}</title></circle>`;
    if (p.note) out += `<text x="${X(p.x).toFixed(1)}" y="${(Y(p.y) - 8).toFixed(1)}" text-anchor="middle" font-size="8" opacity=".5">${esc(p.note)}</text>`;
  });
  if (xlab) out += `<text x="${w - pad.r}" y="${h - 6}" text-anchor="end" font-size="8" opacity=".4">${esc(xlab)}</text>`;
  if (ylab) out += `<text x="${pad.l - 4}" y="${pad.t - 3}" font-size="8" opacity=".4">${esc(ylab)}</text>`;
  return svg(`0 0 ${w} ${h}`, out);
}

/* 스파크라인 — 기능①: 구간 안에 이벤트가 있으면 세로 마커를 함께 찍는다 */
function spark(values, color = '#3B5D48', w = 150, h = 26, months = null) {
  const idx = values.map((v, i) => v == null ? null : i).filter(i => i !== null);
  const v = idx.map(i => values[i]);
  if (!v.length) return svg(`0 0 ${w} ${h}`, '');
  const y = scale(v, 3, h - 3);
  const X = j => 2 + j * (w - 4) / Math.max(1, v.length - 1);
  const pts = v.map((val, j) => `${X(j).toFixed(1)},${y(val).toFixed(1)}`).join(' ');
  let marks = '';
  if (months && D && D.events) {
    D.events.forEach(e => {
      const pos = idx.indexOf(months.indexOf(e.date));
      if (pos >= 0) marks += `<line x1="${X(pos).toFixed(1)}" y1="0" x2="${X(pos).toFixed(1)}" y2="${h}"
        stroke="${e.kind === 'warn' ? '#C97C86' : '#B3A98F'}" stroke-width="1" stroke-dasharray="2 2" opacity=".8"><title>${esc(e.date)} ${esc(e.label)}</title></line>`;
    });
  }
  return svg(`0 0 ${w} ${h}`, marks + `<polyline points="${pts}" fill="none" stroke="${color}" stroke-width="1.6"/>`);
}

/* ── 렌더 ──────────────────────────────────── */
function renderMeta() {
  const m = D.meta;
  $('#stamp').innerHTML = `<b><span class="dot"></span>${esc(m.generated_at)}</b>
    ${m.source_mode === 'live' ? 'API 라이브 갱신' : '저장소 데이터'} · ${esc(m.coverage)}`;
  $('#defBox').innerHTML = `‘제주’ 연상 = <b>제주 단독</b><br>점유율 판정 = <b>2사 기준</b><br>지수 = 월간 API 계열`;
  $('#srcBox').innerHTML = m.sources.map(esc).join('<br>');
  $('#sideFoot').innerHTML = `${esc(m.coverage)}<br>갱신 ${esc(m.generated_at)}<br>공개 데이터 기반 학습용 분석`;
}

/* 기능③ — 임계값 경보 배너 */
function renderAlerts() {
  const a = D.alerts || [];
  const box = $('#alertBox');
  if (!a.length) { box.innerHTML = `<div class="alert ok">현재 게이트를 벗어난 지표가 없습니다.</div>`; return; }
  const order = { high: 0, mid: 1, info: 2 };
  box.innerHTML = [...a].sort((x, y) => order[x.level] - order[y.level]).map(x => `
    <div class="alert ${esc(x.level)}">
      <span class="tag">${x.level === 'high' ? '주의' : x.level === 'mid' ? '점검' : '참고'}</span>
      <div><b>${esc(x.kpi)}</b> — ${esc(x.msg)}
        <span class="act">→ ${esc(x.action)}</span></div>
    </div>`).join('');
}

/* 기능② — 직전 스냅샷 대비 변화 */
function renderDiff() {
  const d = D.diff || {};
  const box = $('#diffBox');
  if (!d.base || !d.rows?.length) {
    box.innerHTML = `<div class="src">직전 스냅샷이 없습니다. 다음 갱신부터 변화가 표시됩니다.</div>`;
    return;
  }
  box.innerHTML = `<div class="src">기준: ${esc(d.base)} 스냅샷 대비</div>
    <div class="tblwrap"><table><thead><tr><th>지표</th><th>이전</th><th>현재</th><th>변화</th></tr></thead>
    <tbody>${d.rows.map(r => {
      const same = Math.abs(r.delta) < 0.005;
      return `<tr><td class="hi" style="text-align:left">${esc(r.label)}</td>
        <td>${r.prev}${esc(r.unit)}</td><td>${r.cur}${esc(r.unit)}</td>
        <td class="${same ? '' : (r.delta > 0 ? 'up' : 'dn')}">${same ? '변화 없음' : (r.delta > 0 ? '+' : '') + r.delta + esc(r.unit)}</td></tr>`;
    }).join('')}</tbody></table></div>
    <div class="cap"><b>왜 필요한가</b> 이 프로젝트의 가장 큰 사고는 “정의가 바뀐 걸 모른 채 옛 수치를 인용한 것”이었다. 갱신 때마다 무엇이 어떻게 움직였는지 남겨 같은 사고를 막는다.</div>`;
}

function renderKPI() {
  const k = D.kpi, s = D.series.monthly;
  const M = s.months;
  const last24 = a => a.slice(-24), last24m = M.slice(-24);
  $('#kpiStrip').innerHTML = `
    <div>
      <div class="lab">브랜드 검색지수</div>
      <div class="num">${sign(k.brand_search.yoy)}%</div>
      <div class="sub">${esc(D.meta.ytd_window)} · <span class="neg">하락 지속</span><br>5년 누적 ${fmt(k.brand_search.cum5y)}%</div>
      ${spark(last24(s.brand), '#9C4A42', 150, 26, last24m)}
      <div class="gatestrip"><em>게이트 — 낙폭이 자연 감속을 초과해 축소</em></div>
    </div>
    <div>
      <div class="lab">‘제주’ 연상 비중 <i>(제주 단독)</i></div>
      <div class="num">${fmt(k.jeju_ratio.current, 2)}%</div>
      <div class="sub"><span class="hold">보합</span> · ${esc(k.jeju_ratio.peak_year)}년 ${fmt(k.jeju_ratio.peak, 2)}% 정점<br>절대 지수 ${fmt(k.jeju_ratio.abs_yoy)}% 동반 판정</div>
      ${spark(last24(s.jeju), '#3B5D48', 150, 26, last24m)}
      <div class="gatestrip"><em>게이트 — 비중 상승 + 절대 지수 낙폭 &lt; 브랜드</em></div>
    </div>
    <div>
      <div class="lab">제품 ↔ 브랜드 Gap</div>
      <div class="num">${sign(k.gap.ytd)}<span class="u">%p</span></div>
      <div class="sub">제품 ${fmt(k.gap.product_yoy)}% · 브랜드 ${fmt(k.gap.brand_yoy)}%<br>구간 따라 부호 반전 · KR1 종속</div>
      ${spark(last24(s.product), '#C97C86', 150, 26, last24m)}
      <div class="gatestrip"><em>게이트 — KR1 개선 시에만 Gap 축소를 성과로 인정</em></div>
    </div>
    <div>
      <div class="lab">경쟁 검색 점유율 <i>(직접경쟁 3사)</i></div>
      <div class="num">${fmt(k.share.direct)}%</div>
      <div class="sub">이니스프리·미샤·3CE · <span class="neg">하락 중</span>(전년 ${fmt(k.share.direct_prev)}%)<br>4사(+토니모리) ${fmt(k.share.all4)}%는 붕괴 착시</div>
      ${spark(last24(s.share_direct || s.brand), '#3B5D48', 150, 26, last24m)}
      <div class="gatestrip"><em>게이트 — 자연 둔화 대비 초과 회복분만 인정</em></div>
    </div>`;

  renderAeo();
}

/* AEO — Before(기존 이니스프리 공식몰) / After(우리 제안 페이지) 2열 */
function renderAeo() {
  const a = D.kpi.aeo;
  const auto = a.source === 'check_aeo.py';
  const fail = a.total - a.score;

  const row = i => {
    const st = i.ok === true ? 'y' : i.ok === false ? 'n' : 'q';
    const mark = i.ok === true ? '충족' : i.ok === false ? '미충족' : '보류';
    return `<li class="ck ${st}">
      <span class="badge">${mark}</span>
      <div><b>${esc(i.k)}</b><span class="d">${esc(i.note)}</span></div>
    </li>`;
  };

  $('#aeoBox').innerHTML = `
    <div class="aeo-col before">
      <div class="hd">
        <div>
          <span class="k">Before · 현재 이니스프리 공식몰</span>
          <a class="url" href="https://www.innisfree.com" target="_blank" rel="noopener">www.innisfree.com</a>
        </div>
        <div class="score">
          <b>${a.score}</b><span>/ ${a.total}</span>
          <em>${fail}개 항목 미충족</em>
        </div>
      </div>
      <ul class="cklist">${a.items.map(row).join('')}</ul>
      <div class="stampline">${auto ? '자동 점검' : '수동 확인값'} · ${esc(a.checked || '')} · <code>check_aeo.py</code></div>
    </div>

    <div class="aeo-col after pending">
      <div class="hd">
        <div><span class="k">After · 제안 랜딩·상세페이지</span>
          <span class="url">Part 4-3 · 4-4 (제작 예정)</span></div>
        <div class="score"><b>—</b><span>/ ${a.total}</span><em>페이지 완성 후 측정</em></div>
      </div>
      <ul class="cklist">${a.items.map(i => `<li class="ck todo">
        <span class="badge">설계 반영</span>
        <div><b>${esc(i.k)}</b><span class="d">제안 페이지에 포함할 항목</span></div></li>`).join('')}</ul>
      <div class="stampline">우리가 만드는 페이지는 <b>목업</b>이라 실제 공식몰 점수를 바꾸지 않는다 — 회사가 채택해 적용해야 왼쪽 숫자가 오른다</div>
    </div>`;
}

function renderScreen1() {
  const an = D.series.annual, f = D.fixed, ev = D.events;
  const years = an.years;

  /* 브랜드 vs 제품군 (월간, 이벤트 마킹) */
  const m = D.series.monthly, mi = m.months;
  const markIdx = ev.filter(e => e.kind !== 'minor').map(e => ({ i: mi.indexOf(e.date), label: e.label }))
    .filter(x => x.i >= 0);
  $('#chartTrend').innerHTML = lineChart({
    labels: mi.map((x, i) => (i % 12 === 0 ? x.slice(0, 4) : '')),
    marks: markIdx,
    series: [
      { values: m.brand, color: '#24382C', w: 2, label: '브랜드', labelY: 26 },
      { values: m.product, color: '#C97C86', w: 1.8, dash: '5 3', label: '제품군', labelY: 116 },
    ],
  });

  /* 제주 단독 비중 */
  const jr = years.map(y => an.jeju_ratio[y]);
  $('#chartJeju').innerHTML = barChart({
    labels: years, values: jr, hiIdx: jr.indexOf(Math.max(...jr)), unit: '',
  });

  /* 매장 ↔ 검색 */
  const st = f.stores;
  $('#chartStore').innerHTML = scatter({
    pts: Object.keys(st).filter(k => !k.startsWith('_')).map(y => ({
      x: st[y], y: an.brand_daily[y], t: `${y} · 매장 ${st[y]}개 · 지수 ${an.brand_daily[y]}`,
      note: y === '2021' ? '400개' : (y === '2024' ? '190개' : ''),
    })), xlab: '매장 수 →', ylab: '↑ 브랜드 검색',
  });

  /* 광고비 ↔ 검색 */
  const ad = f.ad_spend;
  $('#chartAd').innerHTML = scatter({
    pts: Object.keys(ad).filter(k => !k.startsWith('_')).map(y => ({
      x: ad[y], y: an.brand_daily[y], t: `${y} · 광고비 ${ad[y]}억 · 지수 ${an.brand_daily[y]}`,
      note: y === '2023' ? '2023 345억' : '',
    })), trendColor: '#C97C86', xlab: '광고선전비 →', ylab: '↑ 브랜드 검색',
  });

  /* 브랜드평판 순위 */
  const rep = f.reputation.filter(r => r.rank);
  let repSvg = `<text x="26" y="46" font-size="9" opacity=".45">2위</text><text x="26" y="92" font-size="9" opacity=".45">3위</text>
    <line x1="48" y1="42" x2="240" y2="42" stroke="#E8E2D6" stroke-dasharray="2 3"/>
    <line x1="48" y1="88" x2="240" y2="88" stroke="#E8E2D6" stroke-dasharray="2 3"/>`;
  const stepX = 190 / rep.length;
  let path = [];
  rep.forEach((r, i) => {
    const x0 = 50 + i * stepX, x1 = 50 + (i + 1) * stepX, y = r.rank === 2 ? 42 : 88;
    path.push(`${x0},${y} ${x1},${y}`);
  });
  repSvg += `<polyline points="${path.join(' ')}" fill="none" stroke="#24382C" stroke-width="2.2"/>`;
  const idx3 = rep.findIndex(r => r.rank === 3);
  if (idx3 >= 0) {
    const cx = 50 + idx3 * stepX + stepX / 2;
    repSvg += `<circle cx="${cx.toFixed(1)}" cy="88" r="4.2" fill="#C97C86"/>
      <text x="${cx.toFixed(1)}" y="106" text-anchor="middle" font-size="8.5" font-weight="700" fill="#8E4A52">${esc(rep[idx3].p)}</text>
      <text x="${cx.toFixed(1)}" y="117" text-anchor="middle" font-size="8" opacity=".5">첫 3위 이탈</text>`;
  }
  $('#chartRep').innerHTML = svg('0 0 250 138', repSvg);

  /* 점유율 — 직접경쟁 3사(판정) vs 2사·4사(참고) */
  $('#chartShare').innerHTML = lineChart({
    labels: years, w: 320, h: 150,
    series: [
      { values: years.map(y => an.share_direct[y]), color: '#24382C', w: 2.4, label: '직접 3사(판정)', labelY: 26 },
      { values: years.map(y => an.share_pair[y]), color: '#9FB89A', w: 1.6, dash: '4 3', label: '2사(참고)', labelY: 38 },
      { values: years.map(y => an.share_all4[y]), color: '#C97C86', w: 1.6, dash: '2 3', label: '4사(+토니모리)', labelY: 124 },
    ],
  });

  /* 기능⑤ — 경쟁 브랜드 검색량 추이 (3CE 직접경쟁 편입) */
  const comp = an.competitors || {};
  const palette = { '이니스프리': '#24382C', '미샤': '#C97C86', '3CE': '#3B5D48', '토니모리': '#B3A98F', '에뛰드': '#C6D4C2' };
  $('#chartComp').innerHTML = lineChart({
    labels: years, w: 320, h: 150,
    series: Object.keys(comp).map((n, i) => ({
      values: years.map(y => comp[n][y] ?? null),
      color: palette[n] || '#9FB89A',
      w: DIRECT_SET.has(n) ? 2.2 : 1.4,
      dash: DIRECT_SET.has(n) ? null : '3 3',
      label: n, labelY: 26 + i * 12,
    })),
  });
  $('#compTbl').innerHTML = `<table><thead><tr><th>브랜드</th><th>구분</th>
    ${years.map(y => `<th>${y}</th>`).join('')}<th>5년 변화</th></tr></thead><tbody>
    ${Object.keys(comp).map(n => {
      const v = years.map(y => comp[n][y]);
      const first = v.find(x => x != null), last = [...v].reverse().find(x => x != null);
      const chg = (first && last) ? ((last - first) / first * 100) : null;
      return `<tr><td class="hi" style="text-align:left">${esc(n)}</td>
        <td style="text-align:left">${DIRECT_SET.has(n) ? '<b>직접경쟁</b>' : (n === '토니모리' ? '제외(붕괴)' : '참고')}</td>
        ${v.map(x => `<td>${x ?? '—'}</td>`).join('')}
        <td class="${chg < 0 ? 'dn' : 'up'}">${chg == null ? '—' : fmt(chg) + '%'}</td></tr>`;
    }).join('')}</tbody></table>`;

  /* 연도별 표 */
  $('#tblAnnual').innerHTML = `
    <table><thead><tr><th>연도</th><th>브랜드 지수<br><small>일간 정밀</small></th><th>YoY</th>
      <th>제주 비중<br><small>단독</small></th><th>제품군 비중</th><th>점유율<br><small>직접 3사</small></th><th>매장 수</th><th>광고선전비</th></tr></thead>
    <tbody>${years.map(y => `<tr>
      <td class="hi">${y}</td>
      <td>${an.brand_daily[y] ?? '—'}</td>
      <td>${an.brand_daily_yoy[y] != null ? fmt(an.brand_daily_yoy[y]) + '%' : '—'}</td>
      <td>${fmt(an.jeju_ratio[y], 2)}%</td>
      <td>${an.product_ratio[y] != null ? fmt(an.product_ratio[y], 2) + '%' : '—'}</td>
      <td>${an.share_direct[y] != null ? fmt(an.share_direct[y]) + '%' : '—'}</td>
      <td>${D.fixed.stores[y] ?? '—'}</td>
      <td>${D.fixed.ad_spend[y] ? D.fixed.ad_spend[y] + '억' : '—'}</td></tr>`).join('')}</tbody></table>`;

  /* 이벤트 타임라인 (분석 재현 · 변화 이력 두 곳에 동일 목록) */
  const evHtml = ev.map(e => `<tr>
    <td class="hi">${esc(e.date)}</td><td style="text-align:left">${esc(e.label)}</td>
    <td style="text-align:left;font-weight:300;opacity:.75">${esc(e.desc)}</td></tr>`).join('');
  $('#eventList').innerHTML = evHtml;
  const ev2 = $('#eventList2'); if (ev2) ev2.innerHTML = evHtml;
}

/* ── 네비게이션 ────────────────────────────── */
function go(id, push = true) {
  const target = id || 'monitor';
  $$('section').forEach(s => { s.hidden = (s.dataset.view !== target); });
  $$('.nav a').forEach(a => a.classList.toggle('on', a.dataset.go === target));
  if (push && location.hash !== '#' + target) history.pushState(null, '', '#' + target);
  $('aside').classList.remove('open'); $('.scrim').classList.remove('on');
  window.scrollTo({ top: 0, behavior: 'instant' });
}

function toast(html, ms = 4200) {
  const t = $('#toast'); t.innerHTML = html; t.classList.add('on');
  clearTimeout(t._t); t._t = setTimeout(() => t.classList.remove('on'), ms);
}

/* ── 기능④: 내보내기 ───────────────────────── */
/* 차트 SVG를 PNG로 저장 — 발표 자료 만들 때 수동 캡처로 생기는 수치 어긋남을 막는다 */
function exportChart(box, name) {
  const src = box.querySelector('svg');
  if (!src) return;
  const clone = src.cloneNode(true);
  clone.setAttribute('xmlns', 'http://www.w3.org/2000/svg');
  const vb = (clone.getAttribute('viewBox') || '0 0 600 300').split(/\s+/).map(Number);
  const S = 3; // 3배 해상도
  clone.setAttribute('width', vb[2] * S); clone.setAttribute('height', vb[3] * S);
  // 인라인 스타일 주입(외부 CSS는 이미지로 안 따라온다)
  const st = document.createElementNS('http://www.w3.org/2000/svg', 'style');
  st.textContent = `text{font-family:'Noto Sans KR','Malgun Gothic',system-ui,sans-serif}`;
  clone.insertBefore(st, clone.firstChild);
  const blob = new Blob([new XMLSerializer().serializeToString(clone)], { type: 'image/svg+xml;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const img = new Image();
  img.onload = () => {
    const c = document.createElement('canvas');
    c.width = vb[2] * S; c.height = vb[3] * S;
    const ctx = c.getContext('2d');
    ctx.fillStyle = '#fff'; ctx.fillRect(0, 0, c.width, c.height);
    ctx.drawImage(img, 0, 0);
    URL.revokeObjectURL(url);
    c.toBlob(b => {
      const a = document.createElement('a');
      a.href = URL.createObjectURL(b);
      a.download = `${name}_${(D.meta.generated_at || '').slice(0, 10)}.png`;
      a.click(); setTimeout(() => URL.revokeObjectURL(a.href), 1000);
      toast(`<b>${esc(name)}.png</b> 저장했습니다. 발표 자료에 그대로 넣으세요 — 수동 캡처보다 수치가 어긋날 위험이 없습니다.`);
    });
  };
  img.onerror = () => { URL.revokeObjectURL(url); toast('이미지 변환에 실패했습니다. 인쇄(PDF)를 이용해 주세요.'); };
  img.src = url;
}

function attachExports() {
  $$('.p').forEach(p => {
    const box = p.querySelector('.chartbox');
    const h = p.querySelector('h3');
    if (!box || !h || h.querySelector('.exp')) return;
    const b = document.createElement('button');
    b.className = 'exp'; b.type = 'button'; b.textContent = 'PNG';
    b.title = '이 차트를 PNG로 저장';
    b.addEventListener('click', () => exportChart(box, h.textContent.trim().replace(/[\\/:*?"<>|]/g, '')));
    h.appendChild(b);
  });
}

/* ── 부팅 ──────────────────────────────────── */
async function boot() {
  try {
    if (window.__DATA__) {           // 공유용 단일 HTML — 데이터가 인라인돼 있다
      D = window.__DATA__;
    } else {
      const r = await fetch('data/dashboard_data.json', { cache: 'no-store' });
      if (!r.ok) throw new Error(r.status);
      D = await r.json();
    }
  } catch (e) {
    $('#kpiStrip').innerHTML = `<div style="padding:20px;grid-column:1/-1;font-size:12px;line-height:1.8">
      <b>데이터를 불러오지 못했습니다.</b><br>
      로컬 파일로 직접 열면 브라우저 보안정책(CORS)에 막힙니다. 아래처럼 로컬 서버로 여세요:<br>
      <code style="background:#E8E2D6;padding:3px 7px;display:inline-block;margin-top:8px">python -m http.server 8000</code>
      <span style="opacity:.6"> → http://localhost:8000</span></div>`;
    return;
  }
  if (D.kpi?.share?.members) DIRECT_SET = new Set(D.kpi.share.members);
  // 한 렌더러가 실패해도 나머지 화면은 살린다 (조용한 전체 중단 방지)
  [['meta', renderMeta], ['alerts', renderAlerts], ['diff', renderDiff],
   ['kpi', renderKPI], ['screens', renderScreen1], ['export', attachExports]]
    .forEach(([name, fn]) => {
      try { fn(); } catch (err) {
        console.error(`[render:${name}]`, err);
        toast(`<b>일부 화면을 그리지 못했습니다.</b><br>${esc(name)} — ${esc(err.message)}`, 9000);
      }
    });
  go(location.hash.slice(1) || 'monitor', false);

  $$('.nav a').forEach(a => a.addEventListener('click', ev => { ev.preventDefault(); go(a.dataset.go); }));
  window.addEventListener('popstate', () => go(location.hash.slice(1) || 'monitor', false));
  $('.burger').addEventListener('click', () => {
    $('aside').classList.toggle('open'); $('.scrim').classList.toggle('on');
  });
  $('.scrim').addEventListener('click', () => { $('aside').classList.remove('open'); $('.scrim').classList.remove('on'); });
  $('#liveBtn').addEventListener('click', () => {
    toast(`<b>API 갱신은 로컬에서 실행합니다.</b><br>
      <code style="display:block;margin-top:6px;font-size:10px">python build_data.py --live</code>
      실행 후 이 페이지를 새로고침하면 최신 월까지 반영됩니다. (브라우저에서 직접 호출하면 API 키가 노출됩니다)`, 7000);
  });
  const pb = $('#printBtn');
  if (pb) pb.addEventListener('click', () => {
    $$('section').forEach(s => s.hidden = false);   // 인쇄 시 전 화면 포함
    setTimeout(() => { window.print(); go(location.hash.slice(1) || 'monitor', false); }, 60);
  });
}
boot();

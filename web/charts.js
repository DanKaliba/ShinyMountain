'use strict';
/* Společné pomocné funkce pro grafy a mapy (převzato z ShinySpace – web Piráti Praha 5). */

const $ = (s) => document.querySelector(s);
const css = (v) => getComputedStyle(document.documentElement).getPropertyValue(v).trim();
const nf = (v, d = 1) => (v == null || isNaN(v) ? '–' : Number(v).toLocaleString('cs-CZ', { minimumFractionDigits: d, maximumFractionDigits: d }));
const pct = (v, d = 1) => (v == null ? '–' : nf(v, d) + ' %');
const pp = (v, d = 1) => (v == null ? '–' : (v > 0 ? '+' : v < 0 ? '−' : '±') + nf(Math.abs(v), d) + ' p. b.');
const pr = (v, d = 1) => (v == null ? '–' : (v > 0 ? '+' : v < 0 ? '−' : '±') + nf(Math.abs(v), d) + ' %');
const int = (v) => (v == null ? '–' : Math.round(v).toLocaleString('cs-CZ'));
const esc = (s) => String(s ?? '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const sgnCls = (v) => (v < 0 ? 'down' : v > 0 ? 'up' : '');

const BLUE = ['#cde2fb', '#9ec5f4', '#6da7ec', '#3987e5', '#256abf', '#104281'];
const ORANGE = ['#fbd9c8', '#f6b393', '#f08b5f', '#eb6834', '#c4501f', '#8f3814'];
const DIV = ['#b8322f', '#dc5f55', '#ec958b', '#f5c6c0', '#e1e0d9', '#6da7ec'];
const TYPES = ['Stánek / stan', 'Rozdávání letáků', 'SWAP', 'Debata', 'Roznos do schránek', 'Komunitní akce'];
const typeColor = (t) => css('--s' + (TYPES.indexOf(t) + 1));

/* ---------- tooltip ---------- */
const tip = $('#tip');
function showTip(html, ev) {
  tip.innerHTML = html; tip.hidden = false;
  const x = Math.min(ev.clientX + 14, window.innerWidth - tip.offsetWidth - 8);
  const y = Math.min(ev.clientY + 14, window.innerHeight - tip.offsetHeight - 8);
  tip.style.left = x + 'px'; tip.style.top = y + 'px';
}
const hideTip = () => { tip.hidden = true; };

/* ---------- SVG helpers ---------- */
const NS = 'http://www.w3.org/2000/svg';
function el(tag, attrs = {}, parent) {
  const e = document.createElementNS(NS, tag);
  for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, v);
  if (parent) parent.appendChild(e);
  return e;
}
function svgRoot(container, w, h) {
  container.innerHTML = '';
  const s = el('svg', { viewBox: `0 0 ${w} ${h}`, width: w, role: 'img' });
  container.appendChild(s);
  return s;
}
function hover(node, html) {
  node.addEventListener('mousemove', (e) => showTip(html, e));
  node.addEventListener('mouseleave', hideTip);
}

/* Tabulková alternativa ke grafu (přístupnost, kopírování čísel) */
function tableToggle(container, headers, rows) {
  const d = document.createElement('details');
  d.className = 'tbl';
  d.innerHTML = `<summary>Zobrazit jako tabulku</summary><div class="tablewrap"><table class="data"><thead><tr>${headers.map((h) => `<th>${esc(h)}</th>`).join('')}</tr></thead><tbody>${rows.map((r) => `<tr>${r.map((c) => `<td>${esc(c)}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`;
  container.appendChild(d);
}
const stripHtml = (s) => String(s ?? '').replace(/<br\s*\/?>/g, ' · ').replace(/<[^>]+>/g, '');

/* Dumbbell: rows [{label, a, b, hi, extra}] – a = dřívější, b = pozdější. */
function dumbbell(container, rows, opts = {}) {
  dumbbellSvg(container, rows, opts);
  const { la = '2022', lb = '2026', extraLabel } = opts;
  tableToggle(container, ['', la, lb, ...(extraLabel ? [extraLabel] : [])], rows.map((r) => [r.label, pct(r.a), pct(r.b), ...(extraLabel ? [r.extra ?? ''] : [])]));
}
function dumbbellSvg(container, rows, { la = '2022', lb = '2026', max, extraLabel } = {}) {
  const W = 560, rowH = 30, L = 170, R = extraLabel ? 70 : 24, T = 26;
  const H = T + rows.length * rowH + 22;
  const s = svgRoot(container, W, H);
  max = max || Math.ceil(Math.max(...rows.flatMap((r) => [r.a || 0, r.b || 0])) / 5) * 5;
  const x = (v) => L + (v / max) * (W - L - R);
  for (let t = 0; t <= max; t += max > 30 ? 10 : 5) {
    el('line', { x1: x(t), x2: x(t), y1: T - 6, y2: H - 20, class: 'grid' }, s);
    el('text', { x: x(t), y: H - 6, 'text-anchor': 'middle' }, s).textContent = t + ' %';
  }
  // legenda
  const lg = el('g', {}, s);
  el('circle', { cx: L, cy: 10, r: 5, fill: 'none', stroke: css('--ink-2'), 'stroke-width': 2 }, lg);
  el('text', { x: L + 10, y: 14 }, lg).textContent = la;
  el('circle', { cx: L + 60, cy: 10, r: 5, fill: css('--ink') }, lg);
  el('text', { x: L + 70, y: 14 }, lg).textContent = lb;
  if (extraLabel) el('text', { x: W - 4, y: 14, 'text-anchor': 'end' }, s).textContent = extraLabel;
  rows.forEach((r, i) => {
    const y = T + i * rowH + rowH / 2;
    const ink = r.hi ? css('--ink') : css('--muted');
    const g = el('g', {}, s);
    el('rect', { x: 0, y: y - rowH / 2, width: W, height: rowH, fill: 'transparent' }, g);
    const t = el('text', { x: L - 10, y: y + 4, 'text-anchor': 'end', class: r.hi ? 'lbl' : '' }, g);
    t.textContent = r.label; if (r.hi) t.setAttribute('font-weight', '650');
    if (r.a != null && r.b != null) el('line', { x1: x(r.a), x2: x(r.b), y1: y, y2: y, stroke: r.hi ? css('--ink') : css('--gray-mark'), 'stroke-width': 2 }, g);
    if (r.a != null) el('circle', { cx: x(r.a), cy: y, r: 5, fill: css('--surface'), stroke: ink, 'stroke-width': 2 }, g);
    if (r.b != null) el('circle', { cx: x(r.b), cy: y, r: 6, fill: r.hi ? css('--ink') : css('--muted'), stroke: css('--surface'), 'stroke-width': 2 }, g);
    if (r.hi || r.lab) {
      const v = r.b ?? r.a;
      const right = r.b != null && r.a != null && r.b < r.a;
      el('text', { x: x(v) + (right ? -10 : 10), y: y + 4, 'text-anchor': right ? 'end' : 'start', class: 'lbl' }, g).textContent = nf(v);
    }
    if (extraLabel) el('text', { x: W - 4, y: y + 4, 'text-anchor': 'end' }, g).textContent = r.extra ?? '';
    hover(g, `<b>${esc(r.label)}</b><br>${la}: ${pct(r.a, 2)}${r.ma != null ? ` (${r.ma} mand.)` : ''}<br>${lb}: ${pct(r.b, 2)}${r.mb != null ? ` (${r.mb} mand.)` : ''}` +
      (r.a != null && r.b != null ? `<br>změna: ${pp(r.b - r.a, 2)}` : '') + (r.tipx || ''));
  });
}

/* Horizontální sloupce: rows [{label, v, hi, note}] */
function bars(container, rows, opts = {}) {
  barsSvg(container, rows, opts);
  if (!opts.noTable) tableToggle(container, ['', 'hodnota'], rows.map((r) => [r.label, r.txt ?? nf(r.v, opts.d ?? 1) + (opts.unit ?? ' %')]));
}
function barsSvg(container, rows, { max, unit = ' %', d = 1 } = {}) {
  const W = Math.max(280, Math.min(560, container.clientWidth || 560)), rowH = W < 400 ? 22 : 30, L = Math.min(200, Math.round(W * 0.42)), R = 56, T = 6;
  const H = T + rows.length * rowH + 6;
  const s = svgRoot(container, W, H);
  max = max || Math.max(...rows.map((r) => r.v));
  const x = (v) => (v / max) * (W - L - R);
  rows.forEach((r, i) => {
    const y = T + i * rowH;
    const g = el('g', {}, s);
    el('rect', { x: 0, y, width: W, height: rowH, fill: 'transparent' }, g);
    const t = el('text', { x: L - 10, y: y + rowH / 2 + 4, 'text-anchor': 'end', class: r.hi ? 'lbl' : '' }, g);
    t.textContent = r.label; if (r.hi) t.setAttribute('font-weight', '650');
    const w = Math.max(2, x(r.v));
    el('path', { d: `M${L},${y + 5} h${w - 4} a4,4 0 0 1 4,4 v${rowH - 18} a4,4 0 0 1 -4,4 h${-(w - 4)} z`, fill: r.color || (r.hi ? css('--ink') : css('--gray-mark')) }, g);
    el('text', { x: L + w + 6, y: y + rowH / 2 + 4, class: 'lbl' }, g).textContent = r.txt ?? nf(r.v, d) + unit;
    hover(g, `<b>${esc(r.label)}</b><br>${nf(r.v, 2)}${unit}${r.note ? '<br>' + r.note : ''}`);
  });
}

/* Bodový graf: points [{x, y, label, series}] */
function scatter(container, pts, opts = {}) {
  scatterSvg(container, pts, opts);
  tableToggle(container, ['bod', opts.xl, opts.yl], pts.map((p) => [stripHtml(p.tip || p.label), nf(p.x, 2), nf(p.y, 2)]));
}
function scatterSvg(container, pts, { xl, yl, series, zeroY = false, zeroX = false, fit = false } = {}) {
  const W = 560, H = 380, L = 48, R = 16, T = 16, B = 44;
  const s = svgRoot(container, W, H);
  const xs = pts.map((p) => p.x), ys = pts.map((p) => p.y);
  const nice = (a, b) => { const r = b - a, st = r > 20 ? 5 : r > 8 ? 2 : r > 3 ? 1 : r > 1.2 ? 0.5 : 0.25; return [Math.floor(a / st) * st, Math.ceil(b / st) * st, st]; };
  const [x0, x1, xst] = nice(Math.min(zeroX ? 0 : Infinity, ...xs), Math.max(...xs));
  const [y0, y1, yst] = nice(Math.min(...ys, zeroY ? 0 : Infinity), Math.max(...ys, zeroY ? 0 : -Infinity));
  const X = (v) => L + ((v - x0) / (x1 - x0 || 1)) * (W - L - R);
  const Y = (v) => H - B - ((v - y0) / (y1 - y0 || 1)) * (H - T - B);
  for (let v = y0; v <= y1 + 1e-9; v += yst) {
    el('line', { x1: L, x2: W - R, y1: Y(v), y2: Y(v), class: Math.abs(v) < 1e-9 ? 'axis' : 'grid' }, s);
    el('text', { x: L - 6, y: Y(v) + 4, 'text-anchor': 'end' }, s).textContent = nf(v, yst < 1 ? 2 : 0);
  }
  for (let v = x0; v <= x1 + 1e-9; v += xst) {
    el('line', { x1: X(v), x2: X(v), y1: T, y2: H - B, class: 'grid' }, s);
    el('text', { x: X(v), y: H - B + 16, 'text-anchor': 'middle' }, s).textContent = nf(v, xst < 1 ? 2 : 0);
  }
  el('text', { x: (L + W - R) / 2, y: H - 6, 'text-anchor': 'middle' }, s).textContent = xl;
  const yt = el('text', { x: 12, y: (T + H - B) / 2, 'text-anchor': 'middle', transform: `rotate(-90 12 ${(T + H - B) / 2})` }, s);
  yt.textContent = yl;
  const ser = series || [{ key: undefined, color: css('--s1') }];
  if (fit) {
    ser.forEach((sr) => {
      const P = pts.filter((p) => p.series === sr.key);
      const n = P.length, mx = P.reduce((a, p) => a + p.x, 0) / n, my = P.reduce((a, p) => a + p.y, 0) / n;
      const b = P.reduce((a, p) => a + (p.x - mx) * (p.y - my), 0) / P.reduce((a, p) => a + (p.x - mx) ** 2, 0);
      const lo = Math.min(...P.map((p) => p.x)), hi = Math.max(...P.map((p) => p.x));
      el('line', { x1: X(lo), x2: X(hi), y1: Y(my + b * (lo - mx)), y2: Y(my + b * (hi - mx)), stroke: sr.color, 'stroke-width': 2, opacity: 0.8 }, s);
    });
  }
  pts.forEach((p) => {
    const sr = ser.find((q) => q.key === p.series) || ser[0];
    const c = el('circle', { cx: X(p.x), cy: Y(p.y), r: 5, fill: sr.color, stroke: css('--surface'), 'stroke-width': 2, 'fill-opacity': 0.85 }, s);
    const hit = el('circle', { cx: X(p.x), cy: Y(p.y), r: 10, fill: 'transparent' }, s);
    hover(hit, p.tip || esc(p.label));
    if (p.onclick) { hit.style.cursor = 'pointer'; hit.addEventListener('click', p.onclick); }
  });
}

/* Skládané sloupce po týdnech */
function weekBars(container, weeks) {
  const W = 560, H = 260, L = 30, R = 8, T = 10, B = 40;
  const s = svgRoot(container, W, H);
  const max = Math.max(...weeks.map((w) => w.total));
  const bw = (W - L - R) / weeks.length;
  const Y = (v) => H - B - (v / max) * (H - T - B);
  for (let v = 0; v <= max; v += 2) {
    el('line', { x1: L, x2: W - R, y1: Y(v), y2: Y(v), class: v ? 'grid' : 'axis' }, s);
    el('text', { x: L - 6, y: Y(v) + 4, 'text-anchor': 'end' }, s).textContent = v;
  }
  weeks.forEach((w, i) => {
    const x = L + i * bw + 1;
    let acc = 0;
    const g = el('g', {}, s);
    el('rect', { x, y: T, width: bw - 2, height: H - T - B, fill: 'transparent' }, g);
    TYPES.forEach((t) => {
      const n = w.byType[t] || 0;
      if (!n) return;
      const y1 = Y(acc + n), y0 = Y(acc);
      el('rect', { x, y: y1 + (acc ? 0 : 0), width: Math.max(1, bw - 2), height: Math.max(0, y0 - y1 - 1), fill: typeColor(t), rx: 1.5 }, g);
      acc += n;
    });
    if (w.label) el('text', { x: x + bw / 2, y: H - B + 16, 'text-anchor': 'middle' }, s).textContent = w.label;
    hover(g, `<b>Týden od ${w.from}</b><br>` + TYPES.filter((t) => w.byType[t]).map((t) => `${t}: ${w.byType[t]}`).join('<br>') + `<br><b>celkem ${w.total}</b>`);
  });
  el('line', { x1: L, x2: W - R, y1: H - B, y2: H - B, class: 'axis' }, s);
}

/* Sankey: cats (stejné kategorie vlevo i vpravo), size = velikost kategorií 2022 (osoby), M = matice přesunů (řádky 2022) */
const CAT_COLOR = [[/^Piráti|^LOL/, '--ink'], [/^SLK|^STAN/, '--s5'], [/^Lepší/, '--s3'], [/^ODS|^SPOLU/, '--s1'], [/^ANO/, '--s7'], [/^SPD|^Ostatní|^Motoristé/, '--s2'], [/^Nevoliči/, '--gray-mark']];
const catColor = (c) => css((CAT_COLOR.find(([rx]) => rx.test(c)) || [0, '--muted'])[1]);
function sankey(container, { cats, catsR, size, M, nonvoters = false }) {
  catsR = catsR || cats;
  const W = 760, H = 460, NW = 14, GAP = 10, LW = 170;
  // bez zaškrtnutí se skryje jen tok "nevolil ani jednou" (jinak by přebil celý diagram); příchody a odchody nevoličů zůstávají
  const idx = cats.map((c, i) => i), jdx = catsR.map((c, j) => j);
  const f = idx.map((i) => jdx.map((j) => (!nonvoters && cats[i] === 'Nevoliči' && catsR[j] === 'Nevoliči' ? 0 : size[cats[i]] * M[i][j])));
  const Lt = f.map((r) => r.reduce((a, b) => a + b, 0)), Rt = jdx.map((_, j) => f.reduce((a, r) => a + r[j], 0));
  const T = Lt.reduce((a, b) => a + b, 0), k = (H - 20 - GAP * (Math.max(idx.length, jdx.length) - 1)) / T;
  const s = svgRoot(container, W, H), x0 = LW, x1 = W - LW - NW;
  const ly = [], ry = [];
  let y = 10; Lt.forEach((v) => { ly.push(y); y += v * k + GAP; });
  y = 10; Rt.forEach((v) => { ry.push(y); y += v * k + GAP; });
  const lOff = [...ly], rOff = [...ry];
  const links = el('g', {}, s);
  idx.forEach((_, a) => jdx.forEach((__, b) => {
    const v = f[a][b], h = v * k;
    const ys = lOff[a], yt = rOff[b]; lOff[a] += h; rOff[b] += h;
    if (v < T * 0.002) return;
    const mx = (x0 + NW + x1) / 2, src = cats[idx[a]], tgt = catsR[jdx[b]];
    const pir = /^Piráti|^LOL/.test(src) || /^Piráti|^LOL/.test(tgt);
    const p = el('path', { d: `M${x0 + NW},${ys} C${mx},${ys} ${mx},${yt} ${x1},${yt} L${x1},${yt + h} C${mx},${yt + h} ${mx},${ys + h} ${x0 + NW},${ys + h} Z`,
      fill: catColor(src), 'fill-opacity': pir ? 0.55 : 0.22 }, links);
    hover(p, `<b>${esc(src)} → ${esc(tgt)}</b><br>≈ ${int(v)} voličů<br>${nf(v / Lt[a] * 100, 0)} % voličů ${esc(src)}${tgt === 'Nevoliči' || src === 'Nevoliči' ? '<br><i>toky z/do nevoličů jsou nejméně jistý odhad</i>' : ''}`);
  }));
  const node = (x, yy, h, c, n, left) => {
    if (n < 1) return; // prázdný uzel (např. nevoliči bez toků) nekreslit
    el('rect', { x, y: yy, width: NW, height: Math.max(1, h), rx: 2, fill: catColor(c) }, s);
    const t = el('text', { x: left ? x - 6 : x + NW + 6, y: yy + Math.max(h, 12) / 2 + 4, 'text-anchor': left ? 'end' : 'start', class: 'lbl' }, s);
    t.textContent = `${c === 'Nevoliči' ? (left ? 'Nevolili (dříve)' : 'Nevolili (nyní)') : c} · ${int(n)}`;
    if (/^Piráti|^LOL/.test(c)) t.setAttribute('font-weight', '650');
  };
  idx.forEach((i, a) => node(x0, ly[a], Lt[a] * k, cats[i], Lt[a], true));
  jdx.forEach((j, b) => node(x1, ry[b], Rt[b] * k, catsR[j], Rt[b], false));
  el('text', { x: x0 + NW / 2, y: H - 2, 'text-anchor': 'middle' }, s).textContent = '';
}

/* ---------- tabulky ---------- */
function table(elm, cols, rows, { sort, desc = true, onRow, rowClass } = {}) {
  let sk = sort, sd = desc;
  function render() {
    const R = [...rows];
    if (sk) R.sort((a, b) => {
      const c = cols.find((q) => q.k === sk), va = c.sv ? c.sv(a) : a[sk], vb = c.sv ? c.sv(b) : b[sk];
      if (va == null) return 1; if (vb == null) return -1;
      return (typeof va === 'string' ? va.localeCompare(vb, 'cs') : va - vb) * (sd ? -1 : 1);
    });
    elm.innerHTML = '<thead><tr>' + cols.map((c) => `<th class="${c.n ? 'n' : ''}" data-k="${c.k}" ${sk === c.k ? `aria-sort="${sd ? 'descending' : 'ascending'}"` : ''} title="${esc(c.title || '')}">${c.label}</th>`).join('') + '</tr></thead><tbody>' +
      R.map((r, i) => `<tr data-i="${rows.indexOf(r)}" class="${onRow ? 'click ' : ''}${rowClass ? rowClass(r) : ''}">` + cols.map((c) => `<td class="${c.n ? 'n' : ''} ${c.cls || ''}">${c.f ? c.f(r) : esc(r[c.k])}</td>`).join('') + '</tr>').join('') + '</tbody>';
    if (elm.classList.contains('sortable')) elm.querySelectorAll('th').forEach((th) => th.addEventListener('click', () => {
      const k = th.dataset.k; if (sk === k) sd = !sd; else { sk = k; sd = !!cols.find((c) => c.k === k).n; } render();
    }));
    if (onRow) elm.querySelectorAll('tbody tr').forEach((tr) => tr.addEventListener('click', () => onRow(rows[+tr.dataset.i])));
  }
  render();
  return { set(newRows) { rows = newRows; render(); } };
}

/* ---------- mapy ---------- */
function tiles(map) {
  const dark = matchMedia('(prefers-color-scheme: dark)').matches && document.documentElement.dataset.theme !== 'light';
  const base = dark ? 'World_Dark_Gray_Base' : 'World_Light_Gray_Base';
  const ref = dark ? 'World_Dark_Gray_Reference' : 'World_Light_Gray_Reference';
  L.tileLayer(`https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/${base}/MapServer/tile/{z}/{y}/{x}`, {
    attribution: 'Podklad © Esri, HERE, OpenStreetMap · okrsky © ČSÚ', maxZoom: 16,
  }).addTo(map);
  L.tileLayer(`https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/${ref}/MapServer/tile/{z}/{y}/{x}`, { maxZoom: 16, pane: 'shadowPane' }).addTo(map);
}
const binColor = (v, breaks, ramp) => { if (v == null) return '#999'; let i = 0; while (i < breaks.length && v >= breaks[i]) i++; return ramp[i]; };
function legend(elm, breaks, ramp, fmt) {
  const lab = (i) => i === 0 ? `pod ${fmt(breaks[0])}` : i === breaks.length ? `${fmt(breaks[i - 1])} a víc` : `${fmt(breaks[i - 1])} – ${fmt(breaks[i])}`;
  elm.innerHTML = ramp.map((c, i) => `<span><span class="sw" style="background:${c}"></span>${lab(i)}</span>`).join('');
}

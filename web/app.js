'use strict';
/* Piráti Liberec – komunální volby 2026. Data: data/liberec.json (generuje scripts/liberec.py). Grafy: charts.js. */

/* ---------- tlačítko „zpět“ u každé sekce ---------- */
document.querySelectorAll('main section[id]').forEach((sec) => {
  if (sec.id === 'tiles') return;
  const a = document.createElement('a');
  a.href = '#top'; a.className = 'back'; a.textContent = '‹ zpět na obsah';
  a.addEventListener('click', (e) => { e.preventDefault(); document.getElementById('top').scrollIntoView({ behavior: 'smooth' }); history.replaceState(null, '', location.pathname); });
  sec.insertBefore(a, sec.firstChild);
});

/* ---------- zjištění z Markdownu (složka zjisteni/) ---------- */
document.querySelectorAll('[data-md]').forEach((elm) => {
  fetch('../zjisteni/' + elm.dataset.md + '?v=20261020a').then((r) => (r.ok ? r.text() : Promise.reject(new Error(r.status)))).then((md) => {
    elm.innerHTML = window.marked ? marked.parse(md) : `<pre>${esc(md)}</pre>`;
  }).catch((e) => { elm.innerHTML = `<p class="muted">Soubor zjisteni/${esc(elm.dataset.md)} se nepodařilo načíst (${esc(e.message)}).</p>`; });
});

fetch('../data/liberec.json?v=20261020a').then((r) => r.json()).then(init).catch((e) => {
  document.querySelector('main').insertAdjacentHTML('afterbegin', `<p class="card">Data se nepodařilo načíst (${esc(e.message)}). Stránku je potřeba otevřít přes web server, ne jako soubor.</p>`);
});

const KOAL = 'LOL a Piráti';
const rf = (v) => (v < 0 ? '−' : '') + nf(Math.abs(v), 2); // korelace s typografickým minus

function init(D) {
  const O = D.okrsky, byO = Object.fromEntries(O.map((o) => [o.okrsek, o]));
  const blk = Object.fromEntries(D.bloky.map((b) => [b.blok, b]));
  const K = blk[KOAL];
  const l26 = D.listiny_2026.find((l) => l.pirati), pir22 = D.listiny_2022.find((l) => /pirátská/.test(l.nazev)), lol22 = D.listiny_2022.find((l) => /^Liberec otevřený/.test(l.nazev));
  const H26 = Object.values(D.hrany_2026)[0];
  const ps = Object.fromEntries(D.ps2025.map((p) => [p.nazev, p]));
  const N = D.nominace;
  const V = D.volici_bloku;

  /* dlaždice */
  const tile = (k, v, d) => `<div class="tile"><div class="k">${k}</div><div class="v">${v}</div><div class="d">${d}</div></div>`;
  $('#tiles').innerHTML =
    tile('LOL a Piráti 2026', pct(K.pct_2026, 2), `<b class="down">${pp(K.pct_2026 - K.pct_2022, 2)}</b> proti součtu obou kandidátek 2022 (${pct(K.pct_2022, 2)})`) +
    tile('Mandáty z 39', `${K.mand_2026}`, `2022: ${K.mand_2022} (Piráti ${pir22.mandaty} + LOL ${lol22.mandaty}) · zvolení Piráti: ${N['Piráti'].zvoleno}`) +
    tile('Voliči (odhad)', `≈ ${int(V.koalice_2026)}`, `2022: ≈ ${int(V.pirati_2022 + V.lol_2022)} · Piráti ve sněmovních 2025: ${int(V.pirati_ps2025)}`) +
    tile('Účast', pct(D.ucast_2026), `2022: ${pct(D.ucast_2022)} · sněmovní 2025: ${pct(D.ucast_ps2025)}`);

  /* strany */
  $('#strany-note').innerHTML = `Zastupitelstvo má 39 mandátů, kandidovalo 11 kandidátek (2022: 10). Nové hnutí Lepší Liberec získalo ${pct(blk['Lepší Liberec'].pct_2026, 2)} a ${blk['Lepší Liberec'].mand_2026} mandátů; ODS a SPD se do zastupitelstva nedostaly (pod 5 %).`;
  dumbbell($('#ch-bloky'), D.bloky.filter((b) => b.blok !== 'Ostatní').map((b) => ({ label: b.blok, a: b.pct_2022, b: b.pct_2026, ma: b.mand_2022, mb: b.mand_2026, hi: b.blok === KOAL, extra: `${b.mand_2022 ?? '–'} → ${b.mand_2026}` }))
    .sort((x, y) => y.b - x.b), { max: 35, extraLabel: 'mandáty' });
  bars($('#ch-trend'), [
    { label: 'KV 2022 – Piráti', v: pir22.pct, color: css('--gray-mark'), note: `${pir22.mandaty} mandáty` },
    { label: 'KV 2022 – LOL', v: lol22.pct, color: css('--gray-mark'), note: `${lol22.mandaty} mandátů` },
    { label: 'KV 2022 – Piráti + LOL', v: K.pct_2022, color: css('--gray-mark'), note: `${K.mand_2022} mandátů` },
    { label: 'PS 2025 – Piráti', v: ps['Piráti'].pct, color: css('--gray-mark'), note: `${int(ps['Piráti'].hlasy)} hlasů, účast ${pct(D.ucast_ps2025)}` },
    { label: 'KV 2026 – LOL a Piráti', v: l26.pct, hi: true, note: `${l26.mandaty} mandátů` },
  ], { max: 22 });
  const lcols = [
    { k: 'nazev', label: 'Kandidátka', f: (r) => (r.pirati ? `<b>${esc(r.nazev)}</b>` : esc(r.nazev)) },
    { k: 'pct', label: 'Hlasy', n: 1, f: (r) => pct(r.pct, 2) },
    { k: 'mandaty', label: 'Mandáty', n: 1 },
  ];
  table($('#tb-l26'), lcols, D.listiny_2026, { rowClass: (r) => (r.pirati ? 'hl' : '') });
  table($('#tb-l22'), lcols, D.listiny_2022, { rowClass: (r) => (r.pirati ? 'hl' : '') });

  /* mandáty */
  const H22p = D.hrany_2022['Česká pirátská strana'], H22l = D.hrany_2022['Liberec otevřený lidem'];
  $('#mand-text').innerHTML = `<p>Na <b>7. mandát</b> chybělo společné kandidátce <b>${int(H26.hlasu_na_dalsi)} hlasů</b>, tedy zhruba <b>${int(H26.volicu_na_dalsi)} voličů</b> s plnou podporou kandidátky.
    Šestý mandát byl naopak jistý: kandidátka mohla ztratit ještě ${int(H26.rezerva_hlasu)} hlasů (≈ ${int(H26.rezerva_volicu)} voličů). Poslední, 39. mandát připadl kandidátce ${esc(D.posledni_mandat_2026.listina)}.</p>
    <p>V roce 2022 kandidovali Piráti a LOL zvlášť: Pirátům chybělo na 3. mandát ${int(H22p.hlasu_na_dalsi)} hlasů (≈ ${int(H22p.volicu_na_dalsi)} voličů), LOL měl rezervu jen ${int(H22l.rezerva_hlasu)} hlasů (≈ ${int(H22l.rezerva_volicu)} voličů).
    Přepočet mandátů (5% klauzule, D'Hondt) sedí na oficiální výsledek v obou volbách.</p>`;
  const hr = [
    ...Object.entries(D.hrany_2022).map(([k, v]) => ({ rok: 2022, kand: k, ...v })),
    ...Object.entries(D.hrany_2026).map(([k, v]) => ({ rok: 2026, kand: k, ...v })),
  ];
  table($('#tb-hrany'), [
    { k: 'rok', label: 'Rok' }, { k: 'kand', label: 'Kandidátka' }, { k: 'mandaty', label: 'Mandáty', n: 1 },
    { k: 'hlasu_na_dalsi', label: 'Chybělo na další', n: 1, f: (r) => `${int(r.hlasu_na_dalsi)} hlasů · ≈ ${int(r.volicu_na_dalsi)} voličů` },
    { k: 'rezerva_hlasu', label: 'Rezerva', n: 1, f: (r) => `${int(r.rezerva_hlasu)} hlasů · ≈ ${int(r.rezerva_volicu)} voličů` },
  ], hr);

  /* okrsky – mapa */
  const DIVr = ['#b8322f', '#dc5f55', '#ec958b', '#f5c6c0', '#e1e0d9', '#6da7ec'];
  const LAYERS = [
    { k: 'blok_2026', label: 'LOL a Piráti 2026', br: [8, 10, 12, 14, 16], ramp: BLUE },
    { k: 'zmena', label: 'Změna proti 2022', br: [-10, -8, -6, -4, -2], ramp: DIVr, fmt: (v) => nf(v, 0), pp: true },
    { k: 'blok_2022', label: 'Piráti + LOL 2022', br: [14, 17, 20, 23, 26], ramp: BLUE },
    { k: 'pir_2022', label: 'Piráti 2022 (samostatně)', br: [4, 5, 6, 7, 8], ramp: BLUE },
    { k: 'ps_pir', label: 'Piráti sněmovna 2025', br: [8, 9.5, 11, 12.5, 14], ramp: BLUE },
    { k: 'pir_individualni', label: 'Pirátští kandidáti: podíl individuálních hlasů', br: [34, 36, 38, 40, 42], ramp: BLUE, unit: ' individuálních hlasů koalice (15 z 39 kandidátů = 38,5 %)' },
    { k: 'll_2026', label: 'Lepší Liberec 2026', br: [15, 18, 21, 24, 27], ramp: ORANGE },
    { k: 'slk_2026', label: 'SLK, TOP 09, KDU 2026', br: [25, 29, 33, 37, 41], ramp: ORANGE },
    { k: 'ano_2026', label: 'ANO 2026', br: [12, 15, 18, 21, 24], ramp: ORANGE },
    { k: 'ucast_2026', label: 'Účast 2026', br: [32, 37, 42, 47, 52], ramp: BLUE },
  ];
  let cur = LAYERS[0], sel = null, lyr;
  const fmtV = (L, v) => (L.pp ? pp(v) : pct(v));
  const map = L.map('map', { scrollWheelZoom: false, zoomSnap: 0.25 });
  tiles(map);
  const btns = $('#layer-btns');
  btns.innerHTML = LAYERS.map((Lr, i) => `<button role="radio" aria-checked="${i === 0}" data-i="${i}">${Lr.label}</button>`).join('');
  btns.querySelectorAll('button').forEach((b) => b.addEventListener('click', () => {
    btns.querySelectorAll('button').forEach((x) => x.setAttribute('aria-checked', 'false'));
    b.setAttribute('aria-checked', 'true'); cur = LAYERS[+b.dataset.i]; restyle();
  }));
  const styleF = (f) => {
    const o = byO[f.properties.o];
    return { fillColor: binColor(o[cur.k], cur.br, cur.ramp), fillOpacity: 0.82, color: sel === o.okrsek ? css('--ink') : css('--surface'), weight: sel === o.okrsek ? 3 : 1 };
  };
  function restyle() {
    lyr && lyr.setStyle(styleF);
    legend($('#lg'), cur.br, cur.ramp, cur.fmt || ((v) => v + ' %'));
    if (cur.pp) $('#lg').insertAdjacentHTML('beforeend', '<span class="muted">p. b.</span>');
    if (cur.unit) $('#lg').insertAdjacentHTML('beforeend', `<span class="muted">${esc(cur.unit)}</span>`);
  }
  const oname = (o) => `Okrsek ${o.okrsek}${o.vratislavice ? ' · Vratislavice' : ''}`;
  fetch('../data/okrsky_liberec.geojson').then((r) => r.json()).then((g) => {
    lyr = L.geoJSON(g, {
      style: styleF,
      onEachFeature: (f, l) => {
        const o = byO[f.properties.o];
        l.bindTooltip(() => `<b>${oname(o)}</b><br>${cur.label}: ${fmtV(cur, o[cur.k])}`, { sticky: true });
        l.on('click', () => select(o.okrsek));
      },
    }).addTo(map);
    map.fitBounds(lyr.getBounds(), { padding: [10, 10] });
    restyle();
  });
  function select(n, pan) {
    sel = n; const o = byO[n];
    lyr && lyr.setStyle(styleF);
    if (pan && lyr) lyr.eachLayer((l) => l.feature.properties.o === n && map.fitBounds(l.getBounds(), { maxZoom: 15 }));
    $('#okr-detail').innerHTML = `<h3>${oname(o)}</h3><p class="sub">${int(o.volici)} voličů v seznamu</p>
      <dl>
        <dt>Piráti + LOL 2022 → LOL a Piráti 2026</dt><dd>${pct(o.blok_2022)} → <b>${pct(o.blok_2026)}</b></dd>
        <dt>Změna</dt><dd class="${sgnCls(o.zmena)}">${pp(o.zmena)}</dd>
        <dt>2022 zvlášť: Piráti / LOL</dt><dd>${pct(o.pir_2022)} / ${pct(o.lol_2022)}</dd>
        <dt>Pořadí kandidátky v okrsku 2026</dt><dd>${o.poradi_2026}.</dd>
        <dt>Piráti sněmovna 2025</dt><dd>${pct(o.ps_pir)} (${int(o.volici_pir_ps)} hlasů)</dd>
        <dt>Voliči kandidátky (odhad) 2022 → 2026</dt><dd>≈ ${int(o.volici_blok_2022)} → ≈ ${int(o.volici_blok_2026)}</dd>
        <dt>Pirátští kandidáti v individuálních hlasech</dt><dd>${pct(o.pir_individualni)}</dd>
        <dt>Lepší Liberec / SLK+ / ANO 2026</dt><dd>${pct(o.ll_2026)} / ${pct(o.slk_2026)} / ${pct(o.ano_2026)}</dd>
        <dt>Účast 2022 → 2026 (sněmovní 2025)</dt><dd>${pct(o.ucast_2022)} → ${pct(o.ucast_2026)} (${pct(o.ucast_ps)})</dd>
      </dl>`;
  }
  table($('#tb-okr'), [
    { k: 'okrsek', label: 'Okrsek', n: 1, f: (r) => r.okrsek + (r.vratislavice ? ' V' : '') },
    { k: 'volici', label: 'Voliči', n: 1, f: (r) => int(r.volici) },
    { k: 'blok_2022', label: '2022', n: 1, f: (r) => pct(r.blok_2022), title: 'Piráti + LOL 2022' },
    { k: 'blok_2026', label: '2026', n: 1, f: (r) => pct(r.blok_2026), title: 'LOL a Piráti 2026' },
    { k: 'zmena', label: 'Změna', n: 1, f: (r) => `<span class="${sgnCls(r.zmena)}">${pp(r.zmena)}</span>` },
    { k: 'ps_pir', label: 'PS 2025', n: 1, f: (r) => pct(r.ps_pir), title: 'Piráti ve sněmovních volbách 2025' },
    { k: 'll_2026', label: 'Lepší Lib.', n: 1, f: (r) => pct(r.ll_2026) },
    { k: 'slk_2026', label: 'SLK+', n: 1, f: (r) => pct(r.slk_2026) },
    { k: 'ano_2026', label: 'ANO', n: 1, f: (r) => pct(r.ano_2026) },
    { k: 'ucast_2026', label: 'Účast', n: 1, f: (r) => pct(r.ucast_2026) },
  ], O, { sort: 'blok_2026', onRow: (r) => { select(r.okrsek, true); $('#map').scrollIntoView({ behavior: 'smooth', block: 'center' }); } });

  /* kde se ztrácelo */
  const S = D.swing, kor = Object.fromEntries(D.korelace_zmeny.map((k) => [k.promenna, k]));
  $('#zmena-text').innerHTML = `<p>Kandidátka si v průměrném okrsku udržela <b>${nf(S.pomer * 100, 0)} %</b> podílu, který měli Piráti a LOL v roce 2022 dohromady. Ztráty byly úměrné síle:
    model „každý okrsek ztratí stejný díl“ (poměrný) vysvětluje výsledek lépe než „každý okrsek ztratí stejný počet procentních bodů“ (plošný) – průměrná chyba ${nf(S.pomerny_rmse, 1)} vs. ${nf(S.plosny_rmse, 1)} p. b.
    Kde byl blok v roce 2022 silnější, ztratil víc (r = ${rf(kor['Síla bloku 2022'].r)}); část toho je ale i obyčejný návrat k průměru.</p>
    <p>Se silou Lepšího Liberce změna nesouvisí (r = ${rf(kor['Lepší Liberec 2026'].r)}), s růstem SLK, TOP 09 a KDU slabě ano (r = ${rf(kor['Změna SLK, TOP 09, KDU'].r)}). Změna účasti ani výsledek Pirátů ve sněmovních volbách se změnou nesouvisí.
    Podpora kandidátky je v prostoru shlukovaná (Moranovo I = ${nf(D.moran.blok_2026.I, 2)}), samotná změna téměř ne (I = ${nf(D.moran.zmena.I, 2)}).</p>`;
  scatter($('#ch-zmena'), O.map((o) => ({ x: o.blok_2022, y: o.zmena, label: oname(o), tip: `<b>${oname(o)}</b><br>2022: ${pct(o.blok_2022)}<br>2026: ${pct(o.blok_2026)}<br>změna: ${pp(o.zmena)}` })),
    { xl: 'Piráti + LOL 2022 (%)', yl: 'změna do 2026 (p. b.)', fit: true });
  table($('#tb-kor'), [
    { k: 'promenna', label: 'Proměnná v okrsku' },
    { k: 'r', label: 'r', n: 1, f: (r) => rf(r.r) },
    { k: 'p', label: 'p', n: 1, f: (r) => (r.p < 0.001 ? '< 0,001' : nf(r.p, 3)) },
    { k: 'fdr', label: 'FDR', f: (r) => (r.fdr ? 'ano' : '–') },
  ], D.korelace_zmeny);

  /* přesuny voličů */
  const EI = { kv: D.ei_kv, ps: D.ei_ps };
  const eiLab = { kv: 'Komunální 2022 → komunální 2026', ps: 'Sněmovní 2025 → komunální 2026' };
  const at = (E, z, d) => { const i = E.kategorie_z.indexOf(z), j = E.kategorie_do.indexOf(d); return [E.matice[i][j], E.p05[i][j], E.p95[i][j]].map((x) => x * 100); };
  const rng = (E, z, d) => { const [m, a, b] = at(E, z, d); return `${nf(m, 0)} % (${nf(a, 0)}–${nf(b, 0)})`; };
  $('#presuny-text').innerHTML = `<p>Odhad je ekologická inference (Goodmanova regrese s omezeními) z rozdílů mezi okrsky – kdo kam přešel, se z tajných voleb přímo zjistit nedá.
    Intervaly jsou široké a v komunálních volbách, kde lidé dělí hlasy mezi kandidátky, jsou „voliči“ jen přepočet hlasů. Ber to jako hrubý obraz, ne jako fakt.</p>
    <p><b>2022 → 2026:</b> společnou kandidátku podle odhadu znovu volilo ${rng(EI.kv, 'Piráti', KOAL)} pirátských a ${rng(EI.kv, 'LOL', KOAL)} LOL voličů z roku 2022.
    Většina zbytku podle modelu přešla ke kandidátkám SLK, TOP 09 a KDU: z pirátských voličů ${rng(EI.kv, 'Piráti', 'SLK, TOP 09, KDU')}, z voličů LOL ${rng(EI.kv, 'LOL', 'SLK, TOP 09, KDU')}.
    Tyto kandidátky přitom samy ztrácely k Lepšímu Liberci – odešlo k němu ${rng(EI.kv, 'SLK, TOP 09, KDU', 'Lepší Liberec')} jejich voličů z roku 2022.
    Okrsky silné pro LOL a Piráty jsou ale zároveň silné pro SLK, takže tyto dva toky model odděluje špatně.</p>
    <p><b>Sněmovní 2025 → 2026:</b> z pirátských voličů roku 2025 volilo společnou kandidátku asi ${rng(EI.ps, 'Piráti', KOAL)}, SLK a spol. ${rng(EI.ps, 'Piráti', 'SLK, TOP 09, KDU')} a doma zůstalo ${rng(EI.ps, 'Piráti', 'Nevoliči')}.</p>`;
  let eiCur = 'kv';
  const eb = $('#ei-btns');
  eb.innerHTML = Object.entries(eiLab).map(([k, l], i) => `<button role="radio" aria-checked="${i === 0}" data-k="${k}">${l}</button>`).join('');
  eb.querySelectorAll('button').forEach((b) => b.addEventListener('click', () => {
    eb.querySelectorAll('button').forEach((x) => x.setAttribute('aria-checked', 'false'));
    b.setAttribute('aria-checked', 'true'); eiCur = b.dataset.k; drawEI();
  }));
  $('#ei-nev').addEventListener('change', drawEI);
  function drawEI() {
    const E = EI[eiCur];
    $('#ei-cap').textContent = `${eiLab[eiCur]} – odhad přesunů voličů (${E.okrsku} okrsků)`;
    sankey($('#ch-sankey'), { cats: E.kategorie_z, catsR: E.kategorie_do, size: E.velikost, M: E.matice, nonvoters: $('#ei-nev').checked });
    const cols = [{ k: 'z', label: eiCur === 'kv' ? 'Voliči 2022' : 'Voliči 2025' }, { k: 'n', label: 'Počet', n: 1, f: (r) => int(r.n) },
      ...E.kategorie_do.map((d, j) => ({ k: 'c' + j, label: d === 'Nevoliči' ? 'Nevolili' : d, n: 1, f: (r) => r.cells[j] }))];
    const rows = E.kategorie_z.map((z, i) => ({ z: z === 'Nevoliči' ? 'Nevolili' : z, n: E.velikost[z],
      cells: E.kategorie_do.map((d, j) => { const m = E.matice[i][j] * 100; return m < 0.5 ? '<span class="muted">0</span>' : `${nf(m, 0)} <span class="muted">(${nf(E.p05[i][j] * 100, 0)}–${nf(E.p95[i][j] * 100, 0)})</span>`; }) }));
    table($('#tb-ei'), cols, rows, { rowClass: (r) => (/^Piráti|^LOL/.test(r.z) ? 'hl' : '') });
    $('#ei-note').textContent = `Součty vpravo v diagramu jsou modelové (matice × složení okrsků), proto se od skutečných počtů o něco liší. R² pro společnou kandidátku ${nf(E.r2_koalice, 2)}. Vyřazené okrsky: se změnou počtu voličů o víc než 20–25 % nebo s nízkou účastí („úřední“ trvalé pobyty). Intervaly: bootstrap okrsků, 200×.`;
  }
  drawEI();

  /* kandidáti */
  const LL = D.lepsi_liberec_puvod;
  $('#kand-text').innerHTML = `<p>Kandidátku vedl pirát Jan Hruška. Piráti nominovali ${N['Piráti'].kandidatu} z 39 kandidátů a získali <b>${N['Piráti'].zvoleno} mandáty</b> – stejně jako v roce 2022 samostatně.
    Zelení a LOL nominovali ${N['Zelení'].kandidatu} kandidátů a mají ${N['Zelení'].zvoleno} mandáty (2022: ${lol22.mandaty}). O oba ztracené mandáty tedy přišla „zelená“ část kandidátky.</p>
    <p>Voliči, kteří vybírali jednotlivé kandidáty, mezi oběma stranami nerozlišovali: pirátský kandidát dostal v průměru ${int(N['Piráti'].individualnich_na_kandidata)} individuálních hlasů, kandidát Zelených ${int(N['Zelení'].individualnich_na_kandidata)}.
    Na přednostní posun bylo potřeba ${int(D.pref_hranice.hranice_10pct)} hlasů (o 10 % víc, než je průměr na kandidáta) – díky tomu se z 9. místa dostal do zastupitelstva Jaromír Baxa.</p>
    <p class="small">Pro srovnání Lepší Liberec: z jeho 39 kandidátů ${LL.novych} v roce 2022 do zastupitelstva Liberce nekandidovali; zbylí ${LL.kandidatu - LL.novych} kandidovali za ${Object.keys(LL.z_kandidatek_2022).map(esc).join(', ')}.</p>`;
  table($('#tb-kand'), [
    { k: 'poradi', label: '#', n: 1 },
    { k: 'jmeno', label: 'Kandidát', f: (r) => (r.zvolen ? `<b>${esc(r.jmeno)}</b>` : esc(r.jmeno)) },
    { k: 'nominace', label: 'Nominace' },
    { k: 'clen', label: 'Členství' },
    { k: 'hlasy', label: 'Hlasy', n: 1, f: (r) => int(r.hlasy) },
    { k: 'individualnich', label: 'Individuální', n: 1, f: (r) => int(r.individualnich) },
    { k: 'zvolen', label: 'Mandát', sv: (r) => (r.zvolen ? 100 - r.poradi_mandat : 0), f: (r) => (r.zvolen ? `ano (${r.poradi_mandat}.)` : '–'), title: 'v závorce pořadí, v jakém mandát připadl' },
    { k: 'list_2022', label: 'Kandidatura 2022', f: (r) => (r.list_2022 ? esc(r.list_2022) + (r.zvolen_2022 ? ' · mandát' : '') : '–') },
  ], D.kandidati_koalice, { rowClass: (r) => (r.nominace === 'Piráti' ? 'hl' : '') });
}

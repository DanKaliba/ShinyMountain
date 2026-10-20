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
  fetch('../zjisteni/' + elm.dataset.md + '?v=20261020c').then((r) => (r.ok ? r.text() : Promise.reject(new Error(r.status)))).then((md) => {
    elm.innerHTML = window.marked ? marked.parse(md) : `<pre>${esc(md)}</pre>`;
  }).catch((e) => { elm.innerHTML = `<p class="muted">Soubor zjisteni/${esc(elm.dataset.md)} se nepodařilo načíst (${esc(e.message)}).</p>`; });
});

fetch('../data/liberec.json?v=20261020c').then((r) => r.json()).then(init).catch((e) => {
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
    { k: 'zs_uspesnost', label: 'Spádová ZŠ: úspěšnost zápisu', br: [80, 85, 90, 95, 99], ramp: BLUE },
    { k: 'zs_mista_na_spadove', label: 'Spádová ZŠ: místa na spádové dítě', br: [0.7, 0.8, 0.9, 1.1, 1.3], ramp: BLUE, fmt: (v) => nf(v, 1), num: true },
    { k: 'cen_65', label: 'Senioři 65+ (SLDB)', br: [15, 18, 21, 24, 27], ramp: BLUE },
    { k: 'cen_0_14', label: 'Děti 0–14 (SLDB)', br: [14, 15, 16, 17.5, 19], ramp: BLUE },
    { k: 'cen_byty_neobydl', label: 'Neobydlené byty (SLDB)', br: [5, 7, 9, 12, 14], ramp: BLUE },
    { k: 'cen_rust_11_21', label: 'Růst obyvatel 2011–21', br: [-5, 0, 5, 10, 20], ramp: BLUE },
    { k: 'rust_volicu', label: 'Přírůstek voličů 2022 → 2026', br: [-5, -2, 0, 2, 5], ramp: BLUE },
    { k: 'r_kz2024', label: 'Piráti krajské 2024', br: [3, 4, 5, 6, 7], ramp: BLUE, get: (o) => o.rada?.kz2024 },
    { k: 'r_ep2024', label: 'Piráti evropské 2024', br: [4, 5, 6.5, 8, 9.5], ramp: BLUE, get: (o) => o.rada?.ep2024 },
    { k: 'r_ps2021', label: 'PIRÁTI a STAROSTOVÉ 2021', br: [18, 21, 24, 27, 30], ramp: BLUE, get: (o) => o.rada?.ps2021 },
    { k: 'r_kv2018', label: 'LOL! + Změna pro Liberec 2018', br: [12, 15, 18, 21, 24], ramp: BLUE, get: (o) => o.rada?.kv2018 },
    { k: 'rada_rezidual', label: '2026 proti očekávání', br: [-3, -1.5, 0, 1.5, 3], ramp: DIVr, fmt: (v) => nf(v, 1), pp: true },
    { k: 'hodin_secteni', label: 'Čas sečtení', br: [3.5, 4, 4.5, 5.5, 6.5], ramp: ORANGE, fmt: (v) => nf(v, 1) + ' h', num: true, unit: ' hodin po uzavření místností (sobota 14:00)' },
  ];
  let cur = LAYERS[0], sel = null, lyr;
  const fmtV = (L, v) => (L.pp ? pp(v) : L.num ? L.fmt(v) : pct(v));
  const map = L.map('map', { scrollWheelZoom: false, zoomSnap: 0.25 });
  tiles(map);
  const btns = $('#layer-btns');
  btns.innerHTML = LAYERS.map((Lr, i) => `<button role="radio" aria-checked="${i === 0}" data-i="${i}">${Lr.label}</button>`).join('');
  btns.querySelectorAll('button').forEach((b) => b.addEventListener('click', () => {
    btns.querySelectorAll('button').forEach((x) => x.setAttribute('aria-checked', 'false'));
    b.setAttribute('aria-checked', 'true'); cur = LAYERS[+b.dataset.i]; restyle();
  }));
  const val = (o, Lr) => (Lr.get ? Lr.get(o) : o[Lr.k]);
  const styleF = (f) => {
    const o = byO[f.properties.o];
    return { fillColor: binColor(val(o, cur), cur.br, cur.ramp), fillOpacity: 0.82, color: sel === o.okrsek ? css('--ink') : css('--surface'), weight: sel === o.okrsek ? 3 : 1 };
  };
  function restyle() {
    lyr && lyr.setStyle(styleF);
    legend($('#lg'), cur.br, cur.ramp, cur.fmt || ((v) => v + ' %'));
    if (cur.pp) $('#lg').insertAdjacentHTML('beforeend', '<span class="muted">p. b.</span>');
    if (cur.unit) $('#lg').insertAdjacentHTML('beforeend', `<span class="muted">${esc(cur.unit)}</span>`);
  }
  const oname = (o) => `Okrsek ${o.okrsek} · ${o.ctvrt || ''}`;
  fetch('../data/okrsky_liberec.geojson').then((r) => r.json()).then((g) => {
    lyr = L.geoJSON(g, {
      style: styleF,
      onEachFeature: (f, l) => {
        const o = byO[f.properties.o];
        l.bindTooltip(() => `<b>${oname(o)}</b><br>${cur.label}: ${fmtV(cur, val(o, cur))}`, { sticky: true });
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
    $('#okr-detail').innerHTML = `<h3>${oname(o)}</h3><p class="sub">${int(o.volici)} voličů v seznamu · ${o.ctvrt_podil} % adres v části ${esc(o.ctvrt)}${o.ctvrt_dalsi.length ? ', dále ' + o.ctvrt_dalsi.map(esc).join(', ') : ''}<br>volební místnost: ${esc(o.mistnost || '–')}${o.domov_seniory ? ` · domov pro seniory (${int(o.domov_seniory)} lůžek)` : ''}</p>
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
        <dt>Spádová ZŠ (${o.zs_obvod_podil} % adres)</dt><dd>${esc(o.zs_spadova || '–')}${o.zs_uspesnost != null ? ` · úspěšnost zápisu ${pct(o.zs_uspesnost, 0)}` : ''}</dd>
        <dt>Senioři 65+ / děti 0–14 (SLDB 2021)</dt><dd>${pct(o.cen_65)} / ${pct(o.cen_0_14)}</dd>
        <dt>Voliči 2022 → 2026</dt><dd>${int(o.volici_2022)} → ${int(o.volici)} (${pr(o.rust_volicu)})</dd>
        <dt>Sečteno</dt><dd>${o.cas_secteni ? o.cas_secteni.slice(11, 16) : '–'}</dd>
      </dl>`;
  }
  table($('#tb-okr'), [
    { k: 'okrsek', label: 'Okrsek', n: 1 },
    { k: 'ctvrt', label: 'Část města' },
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

  if (D.doplnky) doplnky(D, byO, oname);
  if (D.casova_rada) casovaRada(D, byO, oname);
}

/* Spojnicový graf v čase: body [{datum, v, label, tip, hi}] */
function timeLine(container, pts, { max }) {
  const W = 560, H = 300, L = 56, R = 24, T = 16, B = 56;
  const s = svgRoot(container, W, H);
  const ts = pts.map((p) => +new Date(p.datum)), t0 = Math.min(...ts), t1 = Math.max(...ts);
  const X = (t) => L + (t - t0) / (t1 - t0) * (W - L - R), Y = (v) => H - B - v / max * (H - T - B);
  for (let v = 0; v <= max; v += 10) {
    el('line', { x1: L, x2: W - R, y1: Y(v), y2: Y(v), class: v ? 'grid' : 'axis' }, s);
    el('text', { x: L - 6, y: Y(v) + 4, 'text-anchor': 'end' }, s).textContent = v + ' %';
  }
  for (let y = 2018; y <= 2026; y += 2) el('text', { x: X(+new Date(`${y}-07-01`)), y: H - B + 18, 'text-anchor': 'middle' }, s).textContent = y;
  const P = pts.filter((p) => p.line);
  el('path', { d: P.map((p, i) => `${i ? 'L' : 'M'}${X(+new Date(p.datum))},${Y(p.v)}`).join(' '), fill: 'none', stroke: css('--ink'), 'stroke-width': 2, opacity: 0.5 }, s);
  pts.forEach((p) => {
    const x = X(+new Date(p.datum)), y = Y(p.v);
    const c = el('circle', { cx: x, cy: y, r: p.hi ? 7 : 5, fill: p.line ? css('--ink') : css('--surface'), stroke: p.line ? css('--surface') : css('--muted'), 'stroke-width': 2 }, s);
    el('text', { x, y: y - 12, 'text-anchor': 'middle', class: 'lbl' }, s).textContent = nf(p.v, 1);
    const hit = el('circle', { cx: x, cy: y, r: 14, fill: 'transparent' }, s);
    hover(hit, p.tip);
    void c;
  });
  tableToggle(container, ['Volby', 'Co se měří', 'Podíl', 'Účast'], pts.map((p) => [p.label, p.popis, pct(p.v, 2), pct(p.ucast)]));
}

/* ---------- časová řada 2018–2026 ---------- */
function casovaRada(D, byO, oname) {
  const C = D.casova_rada, R = C.rada, byK = Object.fromEntries(R.map((r) => [r.kod, r]));
  const PR = C.predikce_2026;
  $('#rada-text').innerHTML = `<p>V roce 2018 Piráti do zastupitelstva Liberce nekandidovali (kandidovali předchůdci LOL), v roce 2022 kandidovali samostatně. Mezi komunálními volbami pak prošli prudkým propadem:
    v evropských volbách 2024 měli ${pct(byK.ep2024.pct)} a v krajských ${pct(byK.kz2024.pct)} – v době, kdy byli ve vedení města. Ve sněmovních volbách 2025 se zvedli na ${pct(byK.ps2025.pct)}.
    Komunální výsledek 2026 (${pct(byK.kv2026.pct)}) je tak nad úrovní Pirátů z let 2024–2025, ale pod součtem obou kandidátek z roku 2022 (${pct(byK.kv2022.pct)}).</p>
    <p>Rozložení po okrscích je v čase stabilní: kde byla kandidátka silná v roce 2022, je silná i v roce 2026 (r = ${nf(C.index_zmeny.kv22_kv26.r, 2)}), a stejně podobné je rozložení Pirátů ve sněmovních volbách 2025 (r = ${nf(C.index_zmeny.ps25_kv26.r, 2)}).
    Obě volby dohromady vysvětlují ${nf(PR.r2 * 100, 0)} % rozdílů mezi okrsky v roce 2026; krajské volby 2024 už nic nepřidávají.</p>`;
  const pts = R.map((r) => ({ datum: r.datum, v: r.pct, label: r.volby, popis: r.popis, ucast: r.ucast, line: r.typ !== 'PREZ', hi: r.kod === 'kv2026',
    tip: `<b>${esc(r.volby)}</b><br>${esc(r.popis)}: ${pct(r.pct, 2)}<br>účast ${pct(r.ucast)}` + Object.entries(r.dalsi).map(([k, v]) => `<br>${{ ano: 'ANO', slk: 'Starostové (SLK)', stan: 'STAN', spolu: 'SPOLU', nerudova: 'Nerudová', babis: 'Babiš', pirati: 'Piráti samotní' }[k] || k}: ${pct(v, 1)}`).join('') }));
  timeLine($('#ch-rada'), pts, { max: 45 });
  const lab = Object.fromEntries(R.map((r) => [r.kod, r.volby.replace('Prezident 2023, 1. kolo', 'Pavel 23').replace('Komunální', 'KV').replace('Sněmovní', 'PS').replace('Evropské', 'EP').replace('Krajské', 'KZ').replace(/ 20(\d\d)$/, ' $1')]));
  const K = C.korelace, ord = R.map((r) => r.kod);
  $('#tb-rada-kor').innerHTML = `<thead><tr><th></th>${ord.map((k) => `<th class="n">${esc(lab[k])}</th>`).join('')}</tr></thead><tbody>` +
    ord.map((a) => `<tr><td>${esc(lab[a])}</td>${ord.map((b) => { const v = K.r[K.volby.indexOf(a)][K.volby.indexOf(b)]; return `<td class="n" style="background:${a === b ? 'transparent' : `color-mix(in srgb, ${css('--s1')} ${Math.round(Math.max(0, v) * 60)}%, transparent)`}">${a === b ? '' : nf(v, 2)}</td>`; }).join('')}</tr>`).join('') + '</tbody>';
  const rows = [...C.nejlepe.map((r) => ({ ...r, smer: 'lépe' })), ...C.nejhure.map((r) => ({ ...r, smer: 'hůř' }))];
  table($('#tb-rada-rez'), [
    { k: 'okrsek', label: 'Okrsek', n: 1 }, { k: 'ctvrt', label: 'Část' },
    { k: 'kv2026', label: '2026', n: 1, f: (r) => pct(r.kv2026) },
    { k: 'rezidual', label: 'Proti očekávání', n: 1, f: (r) => `<span class="${sgnCls(r.rezidual)}">${pp(r.rezidual)}</span>` },
  ], rows, { sort: 'rezidual' });
  $('#rada-rez-note').textContent = `Očekávání = lineární model z výsledků KV 2022, PS 2025 a KZ 2024 v okrsku (R² = ${nf(PR.r2, 2)}). Lépe: ${[...new Set(C.nejlepe.map((r) => r.ctvrt))].join(', ')}; hůř: ${[...new Set(C.nejhure.map((r) => r.ctvrt))].join(', ')}. Vrstva „2026 proti očekávání“ je i v mapě.`;
  const PZ = C.prukazy;
  table($('#tb-prukazy'), [
    { k: 'okrsek', label: 'Okrsek', n: 1 }, { k: 'ctvrt', label: 'Část' },
    { k: 'kv2026', label: 'Voliči KV 2026', n: 1, f: (r) => int(r.kv2026) },
    { k: 'ps2021', label: 'PS 2021', n: 1, f: (r) => pr(r.ps2021 / r.kv2026 * 100, 0), sv: (r) => r.ps2021 },
    { k: 'prez2023_1', label: 'Prezident 2023', n: 1, f: (r) => pr(r.prez2023_1 / r.kv2026 * 100, 0), sv: (r) => r.prez2023_1 },
    { k: 'ps2025', label: 'PS 2025', n: 1, f: (r) => pr(r.ps2025 / r.kv2026 * 100, 0), sv: (r) => r.ps2025 },
  ], PZ.okrsky, { sort: 'ps2025' });
  $('#prukazy-note').textContent = `V celostátních volbách se lze zapsat na voličský průkaz v libovolném okrsku (studenti TUL na kolejích, pacienti nemocnice), v komunálních ne. V celém Liberci to ve sněmovních volbách 2025 dělalo čistě jen asi ${int(PZ.celkem.ps2025)} voličů navíc proti komunálním (2021: ${int(PZ.celkem.ps2021)}) – na srovnání sněmovních a komunálních voleb to má jen malý vliv. Přebytek je čistý: cizinci z EU naopak mohou volit jen v komunálních.`;
}

/* ---------- doplňky: části města, statutární města, školy, senioři, demografie, kontrola dat, kuriozity ---------- */
function doplnky(D, byO, oname) {
  const X = D.doplnky;
  const sig = (r) => (r.fdr ? `<b>${rf(r.r)}</b>` : rf(r.r));

  /* části města */
  const CT = X.ctvrti.filter((c) => c.okrsku >= 2).sort((a, b) => b.blok_2026 - a.blok_2026);
  dumbbell($('#ch-ctvrti'), CT.map((c) => ({ label: `${c.ctvrt} (${c.okrsku})`, a: c.blok_2022, b: c.blok_2026, hi: true })), { la: '2022', lb: '2026', max: 25 });
  $('#ch-ctvrti').insertAdjacentHTML('beforeend', '<p class="small">Jen části se dvěma a více okrsky (v závorce počet okrsků).</p>');
  table($('#tb-ctvrti'), [
    { k: 'ctvrt', label: 'Část' }, { k: 'okrsku', label: 'Okrsků', n: 1 }, { k: 'volici', label: 'Voliči', n: 1, f: (r) => int(r.volici) },
    { k: 'blok_2026', label: '2026', n: 1, f: (r) => pct(r.blok_2026) },
    { k: 'zmena', label: 'Změna', n: 1, f: (r) => `<span class="${sgnCls(r.zmena)}">${pp(r.zmena)}</span>` },
    { k: 'ps_pir', label: 'PS 2025', n: 1, f: (r) => pct(r.ps_pir) },
    { k: 'll_2026', label: 'Lepší L.', n: 1, f: (r) => pct(r.ll_2026) },
    { k: 'slk_2026', label: 'SLK+', n: 1, f: (r) => pct(r.slk_2026) },
  ], X.ctvrti, { sort: 'blok_2026' });

  /* statutární města */
  const M = X.mesta, lib = M.mesta.find((m) => m.mesto === 'Liberec');
  $('#mesta-text').innerHTML = `<p>Piráti kandidovali v obou volbách ve ${M.srovnatelnych} z 26 statutárních měst. V polovině z nich si pirátský blok (Piráti + partneři) polepšil alespoň o ${nf((M.median_pomer - 1) * 100, 0)} % svého podílu.
    Liberec s poměrem ${nf(lib.pomer, 2)} (ztráta třetiny podílu) je ${M.poradi_liberec}. z ${M.srovnatelnych}.</p>
    <p>Rozhoduje ale, s kým Piráti kandidovali. Kde vstoupili do širších místních uskupení bez „Pirátů“ v názvu (Kladno, Ústí nad Labem, Karlovy Vary…), počítá se do bloku celé uskupení a podíl roste – medián ${nf(M.koalice.median_pomer, 2)}, rostlo ${M.koalice.rostlo} z ${M.koalice.mest}.
    Mezi ${M.znacka.mest} městy, kde měla kandidátka „Piráti“ v názvu, je medián ${nf(M.znacka.median_pomer, 2)} a Liberec je ${M.znacka.poradi_liberec}. Kde Piráti kandidovali samostatně (Plzeň, Frýdek-Místek, Ostrava, Jablonec, Prostějov), blok všude klesl.</p>`;
  const mt = table($('#tb-mesta'), [
    { k: 'mesto', label: 'Město' },
    { k: 'blok_2022', label: '2022', n: 1, f: (r) => (r.blok_2022 != null ? `${pct(r.blok_2022)} · ${r.mand_2022}` : '–'), title: 'podíl · mandáty' },
    { k: 'blok_2026', label: '2026', n: 1, f: (r) => (r.blok_2026 != null ? `${pct(r.blok_2026)} · ${r.mand_2026}` : '–'), title: 'podíl · mandáty' },
    { k: 'pomer', label: 'Poměr', n: 1, f: (r) => (r.pomer != null ? nf(r.pomer, 2) : '–'), title: '2026 ÷ 2022' },
    { k: 'ps2025', label: 'PS 2025', n: 1, f: (r) => pct(r.ps2025) },
    { k: 'pirlist_2026', label: 'Kandidátka s Piráty 2026', f: (r) => esc((r.pirlist_2026 || []).join(', ') || 'nekandidovali'), cls: 'wrap' },
    { k: 'pirlist_2022', label: '2022', f: (r) => esc((r.pirlist_2022 || []).join(', ') || 'nekandidovali'), cls: 'wrap' },
  ], M.mesta, { sort: 'pomer', rowClass: (r) => (r.mesto === 'Liberec' ? 'hl' : !r.srovnatelne ? 'muted' : '') });
  $('#mesta-znacka').addEventListener('change', (e) => mt.set(e.target.checked ? M.mesta.filter((m) => m.znacka_2026 && m.srovnatelne) : M.mesta));

  /* školy */
  const S = X.skoly, P = S.portal;
  $('#skoly-text').innerHTML = `<p>Liberec zveřejňuje průběh zápisů v portálech <a href="https://zapisyms.liberec.cz/materske-skoly">zapisyms.liberec.cz</a> a <a href="https://zapisyzs.liberec.cz/zakladni-skoly">zapisyzs.liberec.cz</a>.
    Do mateřských škol se pro rok 2026/27 hlásilo ${int(P.ms.zadosti)} dětí na ${int(P.ms.mista)} míst (přijato ${int(P.ms.prijato)}), do prvních tříd ${int(P.zs.zadosti)} dětí na ${int(P.zs.mista)} míst (přijato ${int(P.zs.prijato)}).
    Součty žádostí za jednotlivé školy jsou vyšší, protože rodiče se hlásí na víc škol najednou.</p>
    <p>Spádové obvody ZŠ jsou ve vyhlášce jako seznam ulic. ${int(S.kontrola.jednoznacnych)} adres šlo přiřadit jednoznačně, ${int(S.kontrola.dopocitanych)} (úseky ulic „od – po“) podle nejbližších sousedních adres. Vratislavická ZŠ v portálu není.
    Se změnou výsledku ani se silou kandidátky žádný ukazatel zápisů nesouvisí.</p>`;
  table($('#tb-zs'), [
    { k: 'kratky', label: 'Škola', cls: 'wrap', f: (r) => esc(r.adresa_kratka && /\d/.test(r.adresa_kratka) ? r.adresa_kratka : r.kratky.replace(/, Liberec.*$/, '')) },
    { k: 'mista', label: 'Místa', n: 1 }, { k: 'spadove', label: 'Spádové děti', n: 1 },
    { k: 'zadosti', label: 'Žádosti', n: 1 }, { k: 'prijato', label: 'Přijato', n: 1 }, { k: 'neprijato', label: 'Nepřijato', n: 1 },
    { k: 'uspesnost', label: 'Úspěšnost', n: 1, f: (r) => pct(r.uspesnost, 0) },
    { k: 'mista_na_spadove', label: 'Místa / spád.', n: 1, f: (r) => nf(r.mista_na_spadove, 2) },
  ], S.zs, { sort: 'uspesnost', desc: false });
  table($('#tb-ms'), [
    { k: 'ctvrt', label: 'Část' }, { k: 'skol', label: 'Škol', n: 1 }, { k: 'mista', label: 'Místa', n: 1 }, { k: 'zadosti', label: 'Žádosti', n: 1 },
    { k: 'prijato', label: 'Přijato', n: 1 }, { k: 'neprijato', label: 'Nepřijato', n: 1 },
    { k: 'uspesnost', label: 'Úspěšnost', n: 1, f: (r) => pct(r.uspesnost, 0) },
    { k: 'zadosti_na_misto', label: 'Žádostí / místo', n: 1, f: (r) => nf(r.zadosti_na_misto, 2) },
  ], S.ms_ctvrti, { sort: 'uspesnost', desc: false });
  const skL = [...new Set(S.korelace.map((k) => k.skola_label))], vyL = [...new Set(S.korelace.map((k) => k.vysledek_label))];
  $('#tb-skoly-kor').innerHTML = `<thead><tr><th></th>${vyL.map((v) => `<th class="n">${esc(v)}</th>`).join('')}</tr></thead><tbody>` +
    skL.map((s) => `<tr><td>${esc(s)}</td>${vyL.map((v) => { const k = S.korelace.find((q) => q.skola_label === s && q.vysledek_label === v); return `<td class="n">${sig(k)}</td>`; }).join('')}</tr>`).join('') + '</tbody>';

  /* senioři */
  const SN = X.seniori;
  $('#seniori-note').textContent = `V Liberci je ${SN.domovy.length} pobytových zařízení pro seniory s ${int(SN.domovy.reduce((a, d) => a + d.kapacita, 0))} lůžky. Největší je Dům seniorů Františkov (okrsek 36) a dva domovy ve Vratislavicích (okrsek 1001).`;
  table($('#tb-seniori'), [
    { k: 'nazev', label: 'Zařízení', cls: 'wrap', f: (r) => `${esc(r.nazev)}<br><span class="muted">${esc(r.adresa)}</span>` },
    { k: 'okrsek', label: 'Okrsek', n: 1, f: (r) => `${r.okrsek}<br><span class="muted">${esc(r.ctvrt)}</span>` },
    { k: 'kapacita', label: 'Lůžek', n: 1, f: (r) => int(r.kapacita) },
    { k: 'podil_kapacity', label: '% voličů', n: 1, f: (r) => pct(r.podil_kapacity), title: 'lůžka jako podíl voličů okrsku' },
    ...['blok_2026', 'ano_2026', 'ucast_2026'].map((k) => ({ k, label: { blok_2026: 'LOL a Piráti', ano_2026: 'ANO', ucast_2026: 'Účast' }[k] + ' okrsek / okolí', n: 1,
      sv: (r) => r.okrsek_hodnoty[k] - r.sousede_hodnoty[k], f: (r) => `${pct(r.okrsek_hodnoty[k])} / ${pct(r.sousede_hodnoty[k])}` })),
  ], SN.domovy, { sort: 'kapacita' });

  /* demografie */
  const DM = X.demografie;
  $('#demo-note').innerHTML = `Rozpočet z ${DM.bunek} buněk 1 km. Součet za okrsky (${int(DM.odhad.obyv)} obyvatel, 65+ ${pct(DM.odhad.v65)}, děti ${pct(DM.odhad.v0_14)}) je o několik procent vyšší než skutečný počet obyvatel, protože okrajové buňky zasahují do sousedních obcí; podíly to neovlivňuje.
    Kandidátka LOL a Pirátů je silnější v okrscích s víc neobydlenými byty (r = ${rf(DM.korelace.find((k) => k.demo === 'cen_byty_neobydl' && k.vysledek === 'blok_2026').r)}) a stejně tak Piráti ve sněmovních volbách (r = ${rf(DM.korelace.find((k) => k.demo === 'cen_byty_neobydl' && k.vysledek === 'ps_pir').r)}). S věkovou skladbou ani s růstem okrsku výsledek nesouvisí.`;
  const dL = [...new Set(DM.korelace.map((k) => k.demo_label))], vL = [...new Set(DM.korelace.map((k) => k.vysledek_label))];
  $('#tb-demo').innerHTML = `<thead><tr><th></th>${vL.map((v) => `<th class="n">${esc(v)}</th>`).join('')}</tr></thead><tbody>` +
    dL.map((d) => `<tr><td>${esc(d)}</td>${vL.map((v) => { const k = DM.korelace.find((q) => q.demo_label === d && q.vysledek_label === v); return `<td class="n">${sig(k)}</td>`; }).join('')}</tr>`).join('') + '</tbody>';
  const VY = X.vystavba;
  table($('#tb-vystavba'), [
    { k: 'okrsek', label: 'Okrsek', n: 1 }, { k: 'ctvrt', label: 'Část' },
    { k: 'volici_2022', label: 'Voliči 2022', n: 1, f: (r) => int(r.volici_2022) }, { k: 'volici_2026', label: '2026', n: 1, f: (r) => int(r.volici_2026) },
    { k: 'rust', label: 'Přírůstek', n: 1, f: (r) => pr(r.rust) },
    { k: 'blok_2026', label: 'LOL a Piráti', n: 1, f: (r) => pct(r.blok_2026) }, { k: 'zmena', label: 'Změna', n: 1, f: (r) => pp(r.zmena) },
  ], VY.top);
  $('#vystavba-note').textContent = `Liberec jako celek má o ${nf(Math.abs(VY.mesto_rust), 1)} % voličů ${VY.mesto_rust < 0 ? 'méně' : 'více'} než v roce 2022; o víc než 10 % vyrostly jen ${VY.rostoucich_10} okrsky. S přírůstkem voličů výsledek kandidátky nesouvisí (r = ${rf(VY.r_blok)}, změna r = ${rf(VY.r_zmena)}).`;

  /* kontrola dat */
  const KD = X.kontrola;
  $('#kontrola-text').innerHTML = `<p>Přepočet mandátů sedí na oficiální výsledek 2022 i 2026. Poslední číslice počtu hlasů kandidátek v okrscích (${int(KD.cislice.n)} čísel ≥ 100) jsou rozložené rovnoměrně (χ² = ${nf(KD.cislice.chi2, 1)}, p = ${nf(KD.cislice.p, 2)}) – nic nenasvědčuje „vymýšleným“ číslům.</p>
    <p>Výrazně odlišné jsou dvě skupiny okrsků. Okrsek 1 má účast ${pct(KD.nalezy.find((n) => n.okrsek === 1).hodnota)}, protože na adrese magistrátu jsou hlášené osoby bez skutečného bydliště. <b>V šesti ze sedmi vratislavických okrsků</b> je 4,5–12 % neplatných lístků do zastupitelstva města (medián města ${pct(KD.median.neplatne)}). Ve Vratislavicích se zároveň volí zastupitelstvo městského obvodu, voliči tedy dostávají dva lístky. Podobně nízké využití hlasů tam bylo už v roce 2022 (80–88 % možných hlasů na obálku proti 93 % ve zbytku města), jde tedy o dlouhodobý jev, ne o chybu sčítání. Na mandáty to vliv nemá.</p>`;
  table($('#tb-kontrola'), [
    { k: 'test', label: 'Ukazatel' }, { k: 'okrsek', label: 'Okrsek', n: 1, f: (r) => `${r.okrsek} <span class="muted">${esc(byO[r.okrsek]?.ctvrt || '')}</span>` },
    { k: 'hodnota', label: 'Hodnota', n: 1, f: (r) => (r.jednotka === '%' ? pct(r.hodnota, 2) : `${nf(r.hodnota, 0)} ${esc(r.jednotka)}`) },
    { k: 'median', label: 'Medián', n: 1, f: (r) => (r.jednotka === '%' ? pct(r.median, 2) : nf(r.median, 0)) },
    { k: 'vysvetleni', label: 'Poznámka', cls: 'wrap', f: (r) => esc(r.vysvetleni) },
  ], KD.nalezy);

  /* kuriozity */
  const KU = X.kuriozity;
  table($('#tb-kur-povolani'), [
    { k: 'listina', label: 'Kandidátka', cls: 'wrap' }, { k: 'it', label: 'IT', n: 1, f: (r) => pct(r.it, 0) }, { k: 'ucitele', label: 'Učitelé', n: 1, f: (r) => pct(r.ucitele, 0) },
    { k: 'podnikatele', label: 'Podnikatelé', n: 1, f: (r) => pct(r.podnikatele, 0) }, { k: 'duchodci', label: 'Důchodci', n: 1, f: (r) => pct(r.duchodci, 0) },
    { k: 'vek', label: 'Medián věku', n: 1, f: (r) => nf(r.vek, 0) },
  ], KU.povolani.filter((p) => p.kandidatu >= 10), { rowClass: (r) => (/Piráti/.test(r.listina) ? 'hl' : '') });
  const PA = KU.parita;
  bars($('#ch-kur-parita'), [{ label: `Sudé okrsky (${PA.sudych})`, v: PA.sude, hi: true }, { label: `Liché okrsky (${PA.lichych})`, v: PA.liche, color: css('--gray-mark') }], { max: 15, d: 2 });
  $('#kur-parita-note').textContent = `Rozdíl ${pp(PA.rozdil, 2)}, permutační p = ${nf(PA.p, 2)}. Parita čísla okrsku na výsledek nemá vliv – na rozdíl od Prahy 5, kde sudé okrsky „vyhrály“ o půl bodu (také náhodou).`;
  bars($('#ch-kur-mistnost'), KU.mistnost.map((m) => ({ label: `${m.typ} (${m.okrsku})`, v: m.blok, hi: m.typ === 'základní škola', color: m.typ === 'základní škola' ? undefined : css('--gray-mark'), note: `změna proti 2022 ${pp(m.zmena)}` })), { max: 15 });
  $('#kur-mistnost-note').textContent = `Typ budovy podle adresy místnosti v seznamu volebních místností (shoda s adresou školy). Rozdíl ve výsledku je zanedbatelný; ve školách se ale ztrácelo o ${nf(Math.abs(KU.mistnost.find((m) => m.typ === 'základní škola').zmena - KU.mistnost.find((m) => m.typ !== 'základní škola').zmena), 1)} bodu víc.`;
  const C = KU.cas;
  scatter($('#ch-kur-cas'), C.body.map((b) => ({ x: b.hodin, y: b.blok, label: oname(byO[b.okrsek]), tip: `<b>${esc(oname(byO[b.okrsek]))}</b><br>sečteno ${byO[b.okrsek].cas_secteni.slice(11, 16)}<br>LOL a Piráti ${pct(b.blok)}<br>${int(b.obalky)} obálek` })),
    { xl: 'hodin po uzavření místností', yl: 'LOL a Piráti 2026 (%)', fit: true });
  $('#kur-cas-note').textContent = `První byl sečtený okrsek ${C.prvni.okrsek} (${C.prvni.cas.slice(11, 16)}), poslední okrsek ${C.posledni.okrsek} (${C.posledni.cas.slice(11, 16)}). Výsledek kandidátky s časem nesouvisí (r = ${rf(C.r_blok)}); déle se počítalo tam, kde bylo víc obálek (r = ${rf(C.r_obalky)}) – v komunálních volbách se sčítá každý křížek.`;
  const T = KU.titul;
  bars($('#ch-kur-titul'), [{ label: `S titulem (${T.s_titulem_n})`, v: T.s_titulem * 100, hi: true }, { label: `Bez titulu (${T.kandidatu - T.s_titulem_n})`, v: T.bez_titulu * 100, color: css('--gray-mark') }], { max: 110, unit: '', d: 1 });
  $('#kur-titul-note').textContent = `Kandidát s titulem dostane v průměru o ${nf(T.rozdil_pct, 1)} % víc preferenčních hlasů než průměr své kandidátky (90% interval ${nf(T.p05, 1)}–${nf(T.p95, 1)} %); po zohlednění pořadí na kandidátce o ${nf(T.rozdil_po_poradi, 1)} %. ${T.kandidatu} kandidátů všech kandidátek do zastupitelstva Liberce.`;
}

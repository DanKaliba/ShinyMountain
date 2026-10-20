"""Liberec – Piráti v komunálních volbách 2026 (společná kandidátka „Liberec otevřený lidem a Piráti“).

python -P scripts/liberec.py <dl_dir> data

Zastupitelstvo statutárního města Liberec (KODZASTUP 563889, 39 mandátů, 87 okrsků: 1–80 Liberec, 1001–1007 Vratislavice).
2022 kandidovali Piráti samostatně a Zelení s nezávislými jako „Liberec otevřený lidem“ (LOL); 2026 společně.
Výstup: data/liberec.json (web) a data/okrsky_liberec.geojson (hranice okrsků z ČSÚ, kv2022 – okrsky se do 2026 nezměnily).
"""
import sys, os, json, math, re
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from jsonio import save  # noqa: E402
from ei import fit, bootstrap  # noqa: E402
from mandaty import allocate, margins  # noqa: E402

DL, OUT = sys.argv[1:3]
KOD, SEATS = 563889, 39
rng = np.random.default_rng(2026)


def rd(p):
    return pd.read_csv(os.path.join(DL, p), low_memory=False)


# ---------------------------------------------------------------- načtení KV 2022 a 2026
def kv(y):
    if y == 2026:
        t3, hl = (rd(f'KV2026_data_20261011_csv/csv_od/{f}.csv') for f in ('kvt3', 'kvhl'))
        ros, rk, z = (rd(f'KV2026reg20261011_csv/csv_od/{f}.csv') for f in ('kvros', 'kvrk', 'kvrzcoco'))
    else:
        t3, hl = (rd(f'KV2022_data_20260328_csv/csv_od/{f}.csv') for f in ('kvt3', 'kvhl'))
        ros, rk, z = (rd(f'KV2022reg20260328_csv/csv_od/{f}.csv') for f in ('kvros', 'kvrk', 'kvrzcoco'))
        t3, hl, ros, rk, z = (d[d.DATUMVOLEB == 20220923] if 'DATUMVOLEB' in d else d for d in (t3, hl, ros, rk, z))
    t3 = t3[t3.KODZASTUP == KOD].set_index('OKRSEK')
    hl = hl[hl.ID_OKRSKY.isin(set(t3.ID_OKRSKY))]
    ros, rk = ros[ros.KODZASTUP == KOD].set_index('POR_STR_HL'), rk[rk.KODZASTUP == KOD]
    assert int(z[z.KODZASTUP == KOD].MANDATY.iloc[0]) == SEATS
    return t3, hl, ros, rk


K = {y: kv(y) for y in (2022, 2026)}

# bloky pro srovnání 2022 → 2026 (koalice se mezi volbami změnily)
B22 = [('Piráti', r'^Česká pirátská'), ('LOL', r'^Liberec otevřený'), ('SLK, TOP 09, KDU', r'^SLK'), ('ANO', r'^ANO'),
       ('ODS a Sportovci', r'^ODS'), ('SPD a Trikolora', r'SPD|^Trikolora'), ('Ostatní', r'.')]
B26 = [('LOL a Piráti', r'^Liberec otevřený'), ('SLK, TOP 09, KDU', r'^Starostové pro|^LIBERECKÁ 9'), ('Lepší Liberec', r'^Lepší Liberec'),
       ('ANO', r'^ANO'), ('ODS a Sportovci', r'^ODS'), ('SPD a Trikolora', r'SPD|^Svoboda'), ('Ostatní', r'.')]
PSB = [('Piráti', r'pirátská'), ('ANO', r'^ANO'), ('SPOLU', r'^SPOLU'), ('STAN', r'^STAROSTOVÉ'), ('SPD', r'SPD'), ('Motoristé', r'^Motoristé'), ('Ostatní', r'.')]


def blok(name, blocs):
    return next(b for b, rx in blocs if re.search(rx, name))


def bloc_votes(y, blocs):
    t3, hl, ros, _ = K[y]
    h = hl.merge(t3.reset_index()[['ID_OKRSKY', 'OKRSEK']], on='ID_OKRSKY', suffixes=('_x', ''))
    h['blok'] = h.POR_STR_HL.map(lambda p: blok(ros.loc[p, 'ZKRATKAO30'], blocs))
    return h.pivot_table(index='OKRSEK', columns='blok', values='POC_HLASU', aggfunc='sum', fill_value=0).reindex(columns=[b for b, _ in blocs], fill_value=0)


def ps_votes(blocs):
    t, p = rd('PS2025data20251005_csv/csv_od/pst4.csv'), rd('PS2025data20251005_csv/csv_od/pst4p.csv')
    k = rd('PS2025reg20251005_csv/csv_od/psrkl.csv').set_index('KSTRANA').ZKRATKAK30
    ob = set(K[2026][0].OBEC)
    t, p = t[t.OBEC.isin(ob)], p[p.OBEC.isin(ob)]
    p = p.assign(blok=p.KSTRANA.map(lambda s: blok(str(k.get(s, '')), blocs)))
    v = p.pivot_table(index='OKRSEK', columns='blok', values='POC_HLASU', aggfunc='sum', fill_value=0).reindex(columns=[b for b, _ in blocs], fill_value=0)
    return v, t.groupby('OKRSEK')[['VOL_SEZNAM', 'ODEVZ_OBAL']].sum()


v22, v26 = bloc_votes(2022, B22), bloc_votes(2026, B26)
vps, tps = ps_votes(PSB)
t22, t26 = K[2022][0], K[2026][0]
okr = sorted(set(t26.index) & set(t22.index) & set(tps.index))
assert len(okr) == 87, len(okr)


def sh(v):
    return v.div(v.sum(axis=1), axis=0) * 100


s22, s26, sps = sh(v22).loc[okr], sh(v26).loc[okr], sh(vps).loc[okr]
s22['LOL a Piráti'] = s22['Piráti'] + s22['LOL']

# ---------------------------------------------------------------- listiny a mandáty
out = dict(mandaty=SEATS, okrsku=len(okr))
for y in (2022, 2026):
    t3, hl, ros, rk = K[y]
    votes = hl.groupby('POR_STR_HL').POC_HLASU.sum()
    nc = rk.groupby('POR_STR_HL').size()
    alloc = allocate(votes.to_dict(), nc.to_dict(), SEATS)
    lst = []
    for p, r in ros.iterrows():
        assert alloc[p] == int(r.MAND_STR), (y, r.ZKRATKAO30, alloc[p], r.MAND_STR)
        lst.append(dict(nazev=r.ZKRATKAO30, slozeni=str(r.SLOZENI), pct=float(r.PROCHLSTR), hlasy=int(votes.get(p, 0)), mandaty=int(r.MAND_STR),
                        kandidatu=int(nc.get(p, 0)), pirati=bool(re.search(r'^Česká pirátská|^Liberec otevřený', r.ZKRATKAO30)),
                        blok=blok(r.ZKRATKAO30, B22 if y == 2022 else B26)))
    out[f'listiny_{y}'] = sorted(lst, key=lambda d: -d['pct'])
    out[f'ucast_{y}'] = round(float(t3.ODEVZ_OBAL.sum() / t3.VOL_SEZNAM.sum() * 100), 2)
    out[f'volici_{y}'] = int(t3.VOL_SEZNAM.sum())
    # poslední přidělený mandát (nejmenší vítězný podíl) a hrany koalice
    ok = [p for p in votes.index if alloc[p] > 0]
    q = sorted([(votes[p] / alloc[p], p) for p in ok])
    out[f'posledni_mandat_{y}'] = dict(listina=ros.loc[q[0][1], 'ZKRATKAO30'], podil=round(float(q[0][0]), 1))
    hr = {}
    for p in [p for p in ros.index if re.search(r'^Česká pirátská|^Liberec otevřený', ros.loc[p, 'ZKRATKAO30'])]:
        base, plus, minus = margins(votes.to_dict(), nc.to_dict(), SEATS, p)
        hr[ros.loc[p, 'ZKRATKAO30']] = dict(mandaty=base, hlasu_na_dalsi=int(plus), volicu_na_dalsi=round(plus / SEATS), rezerva_hlasu=int(minus),
                                            rezerva_volicu=round(minus / SEATS))
    out[f'hrany_{y}'] = hr
out['ucast_ps2025'] = round(float(tps.ODEVZ_OBAL.sum() / tps.VOL_SEZNAM.sum() * 100), 2)
out['ps2025'] = [dict(nazev=b, pct=round(float(vps[b].sum() / vps.values.sum() * 100), 2), hlasy=int(vps[b].sum())) for b in vps.columns]

# bloky 2022 → 2026 (podíl hlasů, mandáty)
b22 = v22.sum() / v22.values.sum() * 100
b26 = v26.sum() / v26.values.sum() * 100
m22 = pd.Series({d['blok']: 0 for d in out['listiny_2022']}); m26 = pd.Series({d['blok']: 0 for d in out['listiny_2026']})
for d in out['listiny_2022']:
    m22[d['blok']] += d['mandaty']
for d in out['listiny_2026']:
    m26[d['blok']] += d['mandaty']
bl = []
for b, _ in B26:
    a = float(b22['Piráti'] + b22['LOL']) if b == 'LOL a Piráti' else (float(b22[b]) if b in b22 else None)
    ma = int(m22.get('Piráti', 0) + m22.get('LOL', 0)) if b == 'LOL a Piráti' else (int(m22[b]) if b in m22 else None)
    bl.append(dict(blok=b, pct_2022=None if a is None or b == 'Lepší Liberec' else round(a, 2), pct_2026=round(float(b26[b]), 2),
                   mand_2022=None if b == 'Lepší Liberec' else ma, mand_2026=int(m26.get(b, 0))))
out['bloky'] = bl
# „voliči“ ≈ hlasy ÷ 39 (volič má 39 hlasů; orientačně)
out['volici_bloku'] = dict(pirati_2022=round(v22['Piráti'].sum() / SEATS), lol_2022=round(v22['LOL'].sum() / SEATS),
                           koalice_2026=round(v26['LOL a Piráti'].sum() / SEATS), pirati_ps2025=int(vps['Piráti'].sum()))

# ---------------------------------------------------------------- kandidáti společné kandidátky: kdo je nominoval, preferenční hlasy
t3, hl, ros, rk = K[2026]
pk = [p for p in ros.index if re.search(r'^Liberec otevřený', ros.loc[p, 'ZKRATKAO30'])][0]
k22 = K[2022][3].assign(list22=lambda d: d.POR_STR_HL.map(K[2022][2].ZKRATKAO30))
kc = rk[rk.POR_STR_HL == pk].merge(k22[['JMENO', 'PRIJMENI', 'VEK', 'list22', 'MANDAT', 'POCHLASU']], on=['JMENO', 'PRIJMENI'], how='left', suffixes=('', '_22'))
kc = kc[kc.VEK_22.isna() | (kc.VEK - kc.VEK_22).between(3, 5)].sort_values('PORCISLO')
NOM = {720: 'Piráti', 5: 'Zelení'}
hk = hl[hl.POR_STR_HL == pk]
cols = [f'HLASY_{i:02d}' for i in kc.PORCISLO]
# individuální hlasy: nad „podlahou“ okrsku (nejmenší počet hlasů kandidáta ≈ hlasy pro celou kandidátku)
H = hk.merge(t3.reset_index()[['ID_OKRSKY', 'OKRSEK']], on='ID_OKRSKY', suffixes=('_x', '')).set_index('OKRSEK')[cols]
floor = H.min(axis=1)
ind = H.sub(floor, axis=0)
nom = kc.NSTRANA.map(lambda s: NOM.get(int(s), 'jiná')).values
kand = []
for (_, r), c, n in zip(kc.iterrows(), cols, nom):
    kand.append(dict(poradi=int(r.PORCISLO), jmeno=f'{r.JMENO} {r.PRIJMENI}', vek=int(r.VEK), nominace=n,
                     clen='Piráti' if r.PSTRANA == 720 else 'Zelení' if r.PSTRANA == 5 else 'bez příslušnosti',
                     hlasy=int(r.POCHLASU), pct=float(r.POCPROCVSE), zvolen=r.MANDAT == 'A', poradi_mandat=int(r.PORADIMAND) if r.MANDAT == 'A' else None,
                     individualnich=int(ind[c].sum()), list_2022=r.list22 if isinstance(r.list22, str) else None, zvolen_2022=r.MANDAT_22 == 'A'))
out['kandidati_koalice'] = kand
nomS = pd.Series(nom, index=cols)
ind_by = {n: int(ind[nomS[nomS == n].index].values.sum()) for n in ('Piráti', 'Zelení')}
out['nominace'] = {n: dict(kandidatu=int((nom == n).sum()), zvoleno=int(sum(k['zvolen'] for k in kand if k['nominace'] == n)),
                           individualnich=ind_by[n], individualnich_na_kandidata=round(ind_by[n] / int((nom == n).sum())))
                   for n in ('Piráti', 'Zelení')}
out['pref_hranice'] = dict(prumer_na_kandidata=round(hk.POC_HLASU.sum() / len(kc)), hranice_10pct=round(hk.POC_HLASU.sum() / len(kc) * 1.1))
pir_ind_okr = (ind[nomS[nomS == 'Piráti'].index].sum(axis=1) / ind.sum(axis=1).replace(0, np.nan) * 100)

# kandidáti Lepšího Liberce: odkud přišli (kandidátky 2022)
pl = [p for p in ros.index if re.search(r'^Lepší Liberec', ros.loc[p, 'ZKRATKAO30'])][0]
ll = rk[rk.POR_STR_HL == pl].merge(k22[['JMENO', 'PRIJMENI', 'VEK', 'list22', 'MANDAT']], on=['JMENO', 'PRIJMENI'], how='left', suffixes=('', '_22'))
ll = ll[ll.VEK_22.isna() | (ll.VEK - ll.VEK_22).between(3, 5)]
out['lepsi_liberec_puvod'] = dict(kandidatu=int(len(ll)), novych=int(ll.list22.isna().sum()),
                                  z_kandidatek_2022=ll.list22.dropna().value_counts().to_dict(),
                                  zvoleni_2022=int((ll.MANDAT_22 == 'A').sum()), zvolenych_2026=int((ll.MANDAT == 'A').sum()))

# ---------------------------------------------------------------- okrsky: hranice, těžiště
g = json.load(open(os.path.join(DL, 'geo/kv2022_geo_vol_okrsky_2022g100.geojson'), encoding='utf8'))
feats = [f for f in g['features'] if f['properties'].get('OBEC') == str(KOD)]
assert len(feats) == 87


def ring_centroid(c):
    c = np.asarray(c, float); x, y = c[:, 0], c[:, 1]
    a = x[:-1] * y[1:] - x[1:] * y[:-1]
    A = a.sum() / 2
    return A, ((x[:-1] + x[1:]) * a).sum() / (6 * A), ((y[:-1] + y[1:]) * a).sum() / (6 * A)


cent, gout = {}, []
for f in feats:
    polys = f['geometry']['coordinates'] if f['geometry']['type'] == 'MultiPolygon' else [f['geometry']['coordinates']]
    parts = [ring_centroid(p[0]) for p in polys]
    A = sum(abs(a) for a, _, _ in parts)
    o = int(f['properties']['CISLO'])
    cent[o] = (sum(abs(a) * cy for a, _, cy in parts) / A, sum(abs(a) * cx for a, cx, _ in parts) / A)
    rnd = lambda c: [[round(x, 5), round(y, 5)] for x, y in c]  # noqa: E731
    geom = dict(type=f['geometry']['type'], coordinates=[[rnd(r) for r in p] for p in polys] if f['geometry']['type'] == 'MultiPolygon' else [rnd(r) for r in polys[0]])
    gout.append(dict(type='Feature', properties=dict(o=o), geometry=geom))
with open(os.path.join(OUT, 'okrsky_liberec.geojson'), 'w', encoding='utf8') as fh:
    json.dump(dict(type='FeatureCollection', features=gout), fh, separators=(',', ':'))

# ---------------------------------------------------------------- okrsková tabulka
u22 = t22.ODEVZ_OBAL / t22.VOL_SEZNAM * 100
u26 = t26.ODEVZ_OBAL / t26.VOL_SEZNAM * 100
ups = tps.ODEVZ_OBAL / tps.VOL_SEZNAM * 100
R = pd.DataFrame(dict(volici=t26.VOL_SEZNAM.loc[okr], ucast_2022=u22.loc[okr], ucast_2026=u26.loc[okr], ucast_ps=ups.loc[okr],
                      pir_2022=s22['Piráti'], lol_2022=s22['LOL'], blok_2022=s22['LOL a Piráti'], blok_2026=s26['LOL a Piráti'],
                      ps_pir=sps['Piráti'], ll_2026=s26['Lepší Liberec'], slk_2026=s26['SLK, TOP 09, KDU'], slk_2022=s22['SLK, TOP 09, KDU'],
                      ano_2026=s26['ANO'], ano_2022=s22['ANO'], ods_2026=s26['ODS a Sportovci'], ods_2022=s22['ODS a Sportovci'],
                      spd_2026=s26['SPD a Trikolora'], spd_2022=s22['SPD a Trikolora'],
                      volici_blok_2026=v26['LOL a Piráti'].loc[okr] / SEATS, volici_blok_2022=(v22['Piráti'] + v22['LOL']).loc[okr] / SEATS,
                      volici_pir_ps=vps['Piráti'].loc[okr], pir_individualni=pir_ind_okr.reindex(okr)), index=okr)
R['zmena'] = R.blok_2026 - R.blok_2022
R['vratislavice'] = R.index >= 1000
sts = R.copy()
# poradí koalice v okrsku
rank26 = sh(v26).loc[okr].rank(axis=1, ascending=False, method='min')['LOL a Piráti']
okrsky = []
for o, r in R.iterrows():
    d = {k: (round(float(v), 2) if isinstance(v, (float, np.floating)) and not pd.isna(v) else (None if isinstance(v, float) and pd.isna(v) else v)) for k, v in r.items()}
    d.update(okrsek=int(o), lat=round(cent[o][0], 5), lon=round(cent[o][1], 5), volici=int(r.volici), poradi_2026=int(rank26[o]),
             vratislavice=bool(r.vratislavice), volici_blok_2026=int(round(r.volici_blok_2026)), volici_blok_2022=int(round(r.volici_blok_2022)),
             volici_pir_ps=int(r.volici_pir_ps))
    okrsky.append(d)
out['okrsky'] = okrsky

# ---------------------------------------------------------------- swing: plošný × poměrný
w = R.volici.values.astype(float)
uni = R.blok_2022 + (np.average(R.blok_2026, weights=w) - np.average(R.blok_2022, weights=w))
prop = R.blok_2022 * (np.average(R.blok_2026, weights=w) / np.average(R.blok_2022, weights=w))
rm = lambda e: round(float(np.sqrt(np.average(e ** 2, weights=w))), 2)  # noqa: E731
out['swing'] = dict(plosny_rmse=rm(uni - R.blok_2026), pomerny_rmse=rm(prop - R.blok_2026), pomer=round(float(np.average(R.blok_2026, weights=w) / np.average(R.blok_2022, weights=w)), 3),
                    r_2022_2026=round(float(R.blok_2022.corr(R.blok_2026)), 3))


# ---------------------------------------------------------------- korelace změny (permutační p, n = 87)
def kor(x, y, n=9999):
    x, y = np.asarray(x, float), np.asarray(y, float)
    ok = ~(np.isnan(x) | np.isnan(y)); x, y = x[ok], y[ok]
    r = np.corrcoef(x, y)[0, 1]
    sims = np.array([np.corrcoef(x, rng.permutation(y))[0, 1] for _ in range(n)])
    return dict(r=round(float(r), 3), p=round(float((np.sum(np.abs(sims) >= abs(r)) + 1) / (n + 1)), 4), n=int(ok.sum()))


KOR = [('Síla bloku 2022', R.blok_2022), ('Podíl Pirátů 2022 (bez LOL)', R.pir_2022), ('Lepší Liberec 2026', R.ll_2026),
       ('Změna účasti 2022 → 2026', R.ucast_2026 - R.ucast_2022), ('Piráti PS 2025', R.ps_pir), ('Změna ANO', R.ano_2026 - R.ano_2022),
       ('Změna SLK, TOP 09, KDU', R.slk_2026 - R.slk_2022), ('Účast 2026', R.ucast_2026)]
kk = [dict(promenna=n, **kor(x, R.zmena)) for n, x in KOR]
# Benjamini–Hochberg
pv = np.array([d['p'] for d in kk]); order = np.argsort(pv); m = len(pv)
passed = pv[order] <= 0.05 * np.arange(1, m + 1) / m
kb = int(np.max(np.nonzero(passed)[0]) + 1) if passed.any() else 0
for d in kk:
    d['fdr'] = bool(kb and d['p'] <= pv[order][kb - 1])
out['korelace_zmeny'] = kk

# ---------------------------------------------------------------- Moranovo I (k = 6 nejbližších těžišť)
xy = np.array([[cent[o][1] * math.cos(math.radians(50.77)), cent[o][0]] for o in okr])
Dm = np.sqrt(((xy[:, None] - xy[None]) ** 2).sum(-1))
Wm = np.zeros_like(Dm)
for a in range(len(okr)):
    Wm[a, np.argsort(Dm[a])[1:7]] = 1
Wm /= Wm.sum(1, keepdims=True)


def moran(z, perms=999):
    z = np.asarray(z, float); z = z - z.mean()
    f = lambda p: (len(p) / Wm.sum()) * (p @ Wm @ p) / (p @ p)  # noqa: E731
    I = f(z); sims = np.array([f(rng.permutation(z)) for _ in range(perms)])
    return dict(I=round(float(I), 3), p=round(float((np.sum(sims >= I) + 1) / (perms + 1)), 3))


out['moran'] = dict(blok_2026=moran(R.blok_2026), zmena=moran(R.zmena), ll_2026=moran(R.ll_2026), k=6)


# ---------------------------------------------------------------- ekologická inference
def comp(v, t, keys):
    s = v.loc[keys].div(v.loc[keys].sum(axis=1), axis=0).mul(t.ODEVZ_OBAL.loc[keys], axis=0)
    s['Nevoliči'] = t.VOL_SEZNAM.loc[keys] - t.ODEVZ_OBAL.loc[keys]
    return s.div(t.VOL_SEZNAM.loc[keys], axis=0)


def stable(ta, tb, keys):
    r = tb.VOL_SEZNAM.loc[keys] / ta.VOL_SEZNAM.loc[keys]
    ua, ub = ta.ODEVZ_OBAL.loc[keys] / ta.VOL_SEZNAM.loc[keys], tb.ODEVZ_OBAL.loc[keys] / tb.VOL_SEZNAM.loc[keys]
    return [k for k in keys if 0.8 < r[k] < 1.25 and ta.VOL_SEZNAM[k] >= 150 and ua[k] > 0.15 and ub[k] > 0.10]


def ei_out(Xd, Yd, wts):
    Bm = fit(Xd.values, Yd.values, wts)
    bo = bootstrap(Xd.values, Yd.values, wts, rng, n=200)
    pred = Xd.values @ Bm
    j = list(Yd.columns).index('LOL a Piráti')
    r2 = 1 - np.average((Yd.values[:, j] - pred[:, j]) ** 2, weights=wts) / np.average((Yd.values[:, j] - np.average(Yd.values[:, j], weights=wts)) ** 2, weights=wts)
    size = (Xd.mul(wts, axis=0)).sum()
    return dict(kategorie_z=list(Xd.columns), kategorie_do=list(Yd.columns), velikost={k: int(v) for k, v in size.items()}, okrsku=len(Xd),
                matice=[[round(float(x), 4) for x in r] for r in Bm],
                p05=[[round(float(x), 4) for x in r] for r in np.percentile(bo, 5, axis=0)],
                p95=[[round(float(x), 4) for x in r] for r in np.percentile(bo, 95, axis=0)], r2_koalice=round(float(r2), 3))


keys = stable(t22, t26, okr)
X = comp(v22, t22, keys); Y = comp(v26, t26, keys)
out['ei_kv'] = ei_out(X, Y, t22.VOL_SEZNAM.loc[keys].values.astype(float))
keys2 = stable(tps, t26, okr)
X2 = comp(vps, tps, keys2); Y2 = comp(v26, t26, keys2)
out['ei_ps'] = ei_out(X2, Y2, tps.VOL_SEZNAM.loc[keys2].values.astype(float))

save(out, os.path.join(OUT, 'liberec.json'))

# ---------------------------------------------------------------- kontrolní výpis
print('ucast', out['ucast_2022'], out['ucast_2026'], out['ucast_ps2025'])
print('bloky', json.dumps(out['bloky'], ensure_ascii=False))
print('hrany', out['hrany_2022'], out['hrany_2026'], out['posledni_mandat_2026'])
print('volici', out['volici_bloku'], 'nominace', out['nominace'], out['pref_hranice'])
print('LL', out['lepsi_liberec_puvod'])
print('swing', out['swing'])
print('moran', out['moran'])
for d in kk:
    print('  kor', d)
for nm in ('ei_kv', 'ei_ps'):
    E = out[nm]
    print(nm, E['okrsku'], 'R2', E['r2_koalice'], E['kategorie_do'])
    for k, r, a, b in zip(E['kategorie_z'], E['matice'], E['p05'], E['p95']):
        print(f'  {k:20s} {E["velikost"][k]:7d}', ' '.join(f'{x * 100:4.0f}({lo * 100:.0f}-{hi * 100:.0f})' for x, lo, hi in zip(r, a, b)))

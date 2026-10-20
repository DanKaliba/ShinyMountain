"""Časová řada voleb v Liberci po okrscích 2018–2026: kde stáli Piráti (a předchůdci společné kandidátky) v každých volbách.

python -P scripts/casova_rada.py <dl_dir> data        (spouštět po liberec.py a doplnky.py)

Volby: KV 2018, PS 2021, prezident 2023 (1. a 2. kolo), EP 2024, KZ 2024, KV 2022, PS 2025, KV 2026 – otevřená data ČSÚ (csv_od).
Okrsky 1–80 a 1001–1007 mají ve všech volbách stejná čísla (hranice platí od 2014).
Voličský průkaz: v celostátních volbách se lze zapsat do seznamu v libovolném okrsku (studenti TUL na kolejích), v komunálních ne.
Přebytek voličů v seznamu proti komunálním volbám proto ukazuje okrsky, kde volili lidé bez trvalého pobytu v Liberci.
"""
import sys, os, json, re
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from jsonio import save  # noqa: E402

DL, OUT = sys.argv[1:3]
KOD, OB = 563889, {556904, 556891, 563889}
rng = np.random.default_rng(2026)
data = json.load(open(os.path.join(OUT, 'liberec.json'), encoding='utf8'))
O = {o['okrsek']: o for o in data['okrsky']}
ids = sorted(O)


def rd(folder, f):
    return pd.read_csv(os.path.join(DL, folder, 'csv_od', f), low_memory=False)


def per_okrsek(t, p, key, groups, names):
    """t = okrsky (VOL_SEZNAM, ODEVZ_OBAL), p = hlasy stran (key, POC_HLASU); groups = {skupina: regex na název}."""
    t = t[t.OBEC.isin(OB)].groupby('OKRSEK')[['VOL_SEZNAM', 'ODEVZ_OBAL']].sum()
    p = p[p.OBEC.isin(OB)].copy()
    p['nazev'] = p[key].map(names).fillna('')
    tot = p.groupby('OKRSEK').POC_HLASU.sum()
    res = {'volici': t.VOL_SEZNAM, 'ucast': t.ODEVZ_OBAL / t.VOL_SEZNAM * 100, 'platne': tot}
    city = {}
    for g, rx in groups.items():
        v = p[p.nazev.str.contains(rx, regex=True)].groupby('OKRSEK').POC_HLASU.sum().reindex(tot.index, fill_value=0)
        res[g] = v / tot * 100
        city[g] = round(float(v.sum() / tot.sum() * 100), 2)
        city[g + '_hlasy'] = int(v.sum())
    return pd.DataFrame(res), dict(city, ucast=round(float(t.ODEVZ_OBAL.sum() / t.VOL_SEZNAM.sum() * 100), 2), volici=int(t.VOL_SEZNAM.sum()))


V, MESTO = {}, {}

# ---- KV 2018 (Piráti nekandidovali; předchůdci: LOL! a Změna pro Liberec se Zelenými)
t3, hl, ros = rd('KV2018_data_20230224_csv', 'kvt3.csv'), rd('KV2018_data_20230224_csv', 'kvhl.csv'), rd('KV2018_reg_20230224_csv', 'kvros.csv')
t3 = t3[(t3.DATUMVOLEB == 20181005) & (t3.KODZASTUP == KOD)]
hl = hl[hl.ID_OKRSKY.isin(set(t3.ID_OKRSKY))].merge(t3[['ID_OKRSKY', 'OBEC', 'OKRSEK']], on='ID_OKRSKY', suffixes=('_x', ''))
ros = ros[(ros.KODZASTUP == KOD) & (ros.DATUMVOLEB == 20181005)].set_index('POR_STR_HL') if 'DATUMVOLEB' in ros else ros[ros.KODZASTUP == KOD].set_index('POR_STR_HL')
V['kv2018'], MESTO['kv2018'] = per_okrsek(t3, hl, 'POR_STR_HL', {'predchudci': r'^Liberec otevřený|^Změna pro Liberec', 'slk': r'^Starostové', 'ano': r'^ANO'},
                                          ros.ZKRATKAO30)

# ---- PS 2021 (koalice PIRÁTI a STAROSTOVÉ – podíl samotných Pirátů z okrsků nejde oddělit)
t, p = rd('PS2021_data_20211010_csv', 'pst4.csv'), rd('PS2021_data_20211010_csv', 'pst4p.csv')
k = rd('PS2021reg20211010_csv', 'psrkl.csv').drop_duplicates('KSTRANA').set_index('KSTRANA').ZKRATKAK30
V['ps2021'], MESTO['ps2021'] = per_okrsek(t, p, 'KSTRANA', {'pirati': r'PIRÁTI a STAROSTOVÉ', 'spolu': r'^SPOLU', 'ano': r'^ANO'}, k)

# ---- Prezident 2023 (kandidáti po okrscích jako sloupce HLASY_<CKAND>)
pe = rd('PREZ2023_data_20230222_csv_NSS', 'pet1.csv')
rk = rd('PREZ2023reg20230222_csv_NSS', 'perk.csv').set_index('CKAND').PRIJMENI
for kolo in (1, 2):
    x = pe[(pe.KOLO == kolo) & pe.OBEC.isin(OB)].groupby('OKRSEK').sum(numeric_only=True)
    df = pd.DataFrame({'volici': x.VOL_SEZNAM, 'ucast': x.ODEVZ_OBAL / x.VOL_SEZNAM * 100, 'platne': x.PL_HL_CELK})
    cand = {'pavel': 'Pavel', 'nerudova': 'Nerudová', 'babis': 'Babiš'} if kolo == 1 else {'pavel': 'Pavel', 'babis': 'Babiš'}
    city = {}
    for g, n in cand.items():
        c = f'HLASY_{int(rk[rk == n].index[0]):02d}'
        df[g] = x[c] / x.PL_HL_CELK * 100
        city[g] = round(float(x[c].sum() / x.PL_HL_CELK.sum() * 100), 2)
    V[f'prez2023_{kolo}'] = df
    MESTO[f'prez2023_{kolo}'] = dict(city, ucast=round(float(x.ODEVZ_OBAL.sum() / x.VOL_SEZNAM.sum() * 100), 2), volici=int(x.VOL_SEZNAM.sum()))

# ---- EP 2024
t, p = rd('EP2024data20240609_csv', 'ept2.csv'), rd('EP2024data20240609_csv', 'ept2p.csv')
k = rd('EP2024reg20240609_csv', 'eprkl.csv').drop_duplicates('ESTRANA').set_index('ESTRANA').ZKRATKAE30
V['ep2024'], MESTO['ep2024'] = per_okrsek(t, p, 'ESTRANA', {'pirati': r'pirátská', 'stan': r'^Starostové', 'spolu': r'^SPOLU', 'ano': r'^ANO'}, k)

# ---- KZ 2024 (kandidátky jsou po krajích – vybrat kraj, kde kandidovali Starostové pro Liberecký kraj)
t, p = rd('KZ2024data20240922_csv', 'kzt6.csv'), rd('KZ2024data20240922_csv', 'kzt6p.csv')
kl = rd('KZ2024reg20240922_csv', 'kzrkl.csv')
kr = int(kl[kl.ZKRATKAK30.astype(str).str.contains('Starostové pro Liberecký')].KRZAST.iloc[0])
k = kl[kl.KRZAST == kr].set_index('KSTRANA').ZKRATKAK30
V['kz2024'], MESTO['kz2024'] = per_okrsek(t, p, 'KSTRANA', {'pirati': r'pirátská', 'slk': r'^Starostové pro Liberecký', 'ano': r'^ANO'}, k)

# ---- KV 2022, PS 2025, KV 2026 – z liberec.json (stejné výpočty jako na webu)
R = pd.DataFrame(data['okrsky']).set_index('okrsek')
V['kv2022'] = pd.DataFrame({'volici': R.volici_2022, 'ucast': R.ucast_2022, 'pirati': R.pir_2022, 'blok': R.blok_2022, 'ano': R.ano_2022, 'slk': R.slk_2022})
V['ps2025'] = pd.DataFrame({'ucast': R.ucast_ps, 'pirati': R.ps_pir})
t = rd('PS2025data20251005_csv', 'pst4.csv')
V['ps2025']['volici'] = t[t.OBEC.isin(OB)].groupby('OKRSEK').VOL_SEZNAM.sum()
V['kv2026'] = pd.DataFrame({'volici': R.volici, 'ucast': R.ucast_2026, 'blok': R.blok_2026, 'ano': R.ano_2026, 'slk': R.slk_2026, 'll': R.ll_2026})
L22 = {l['blok']: l for l in data['listiny_2022']}
MESTO['kv2022'] = dict(pirati=next(l['pct'] for l in data['listiny_2022'] if 'pirátská' in l['nazev']), blok=next(b['pct_2022'] for b in data['bloky'] if b['blok'] == 'LOL a Piráti'),
                       ucast=data['ucast_2022'], volici=data['volici_2022'])
MESTO['ps2025'] = dict(pirati=next(p['pct'] for p in data['ps2025'] if p['nazev'] == 'Piráti'), ucast=data['ucast_ps2025'])
MESTO['kv2026'] = dict(blok=next(b['pct_2026'] for b in data['bloky'] if b['blok'] == 'LOL a Piráti'), ucast=data['ucast_2026'], volici=data['volici_2026'])

VOLBY = [  # (klíč, popis, datum, typ, sloupec „pirátské“ řady, popis řady)
    ('kv2018', 'Komunální 2018', '2018-10-06', 'KV', 'predchudci', 'LOL! + Změna pro Liberec (se Zelenými); Piráti nekandidovali'),
    ('ps2021', 'Sněmovní 2021', '2021-10-09', 'PS', 'pirati', 'PIRÁTI a STAROSTOVÉ (koalice)'),
    ('prez2023_1', 'Prezident 2023, 1. kolo', '2023-01-14', 'PREZ', 'pavel', 'Petr Pavel'),
    ('ep2024', 'Evropské 2024', '2024-06-08', 'EP', 'pirati', 'Piráti'),
    ('kz2024', 'Krajské 2024', '2024-09-21', 'KZ', 'pirati', 'Piráti'),
    ('kv2022', 'Komunální 2022', '2022-09-24', 'KV', 'blok', 'Piráti + LOL (dvě kandidátky)'),
    ('ps2025', 'Sněmovní 2025', '2025-10-04', 'PS', 'pirati', 'Piráti'),
    ('kv2026', 'Komunální 2026', '2026-10-10', 'KV', 'blok', 'Liberec otevřený lidem a Piráti'),
]
VOLBY.sort(key=lambda v: v[2])
for kk, *_ in VOLBY:
    assert set(ids) <= set(V[kk].index), (kk, set(ids) - set(V[kk].index))

# ---------------------------------------------------------------- přebytek voličů v seznamu (voličské průkazy) proti nejbližším komunálním volbám
kv_ref = {'ps2021': 'kv2022', 'prez2023_1': 'kv2022', 'ep2024': 'kv2022', 'kz2024': 'kv2022', 'ps2025': 'kv2026'}
prukazy = {}
for kk, ref in kv_ref.items():
    ex = V[kk].volici.reindex(ids) - V[ref].volici.reindex(ids)
    prukazy[kk] = ex
P = pd.DataFrame(prukazy)
P['median'] = P.median(axis=1)
koleje = P[(P.ps2025 >= 40) | (P.ps2021 >= 40)].sort_values('ps2025', ascending=False)
for o in ids:
    O[o]['ps2025_volici_navic'] = int(P.ps2025[o])
out = dict(prukazy=dict(
    okrsky=[dict(okrsek=int(o), ctvrt=O[o].get('ctvrt'), kv2026=int(V['kv2026'].volici[o]), **{k_: int(r[k_]) for k_ in kv_ref}) for o, r in koleje.iterrows()],
    celkem={k_: int(P[k_].clip(lower=0).sum()) for k_ in kv_ref}))
print('voliči navíc (průkazy):', out['prukazy']['celkem'])
print(koleje.head(10))

# ---------------------------------------------------------------- řada za město a po okrscích
rada = []
for kk, label, datum, typ, col, popis in VOLBY:
    m = MESTO[kk]
    rada.append(dict(kod=kk, volby=label, datum=datum, typ=typ, popis=popis, pct=m.get(col), ucast=m.get('ucast'),
                     dalsi={g: m[g] for g in ('ano', 'slk', 'stan', 'spolu', 'nerudova', 'babis', 'pirati') if g in m and g != col}))
okr = {}
for o in ids:
    okr[o] = {kk: (round(float(V[kk][col][o]), 2) if pd.notna(V[kk][col].get(o)) else None) for kk, _, _, _, col, _ in VOLBY}
    O[o]['rada'] = okr[o]
    # relativní síla okrsku (podíl ÷ podíl za město) – stabilita „pirátských“ okrsků v čase
    O[o]['rada_index'] = {kk: round(okr[o][kk] / MESTO[kk][col], 2) if okr[o][kk] is not None and MESTO[kk][col] else None for kk, _, _, _, col, _ in VOLBY}
M = pd.DataFrame(okr).T.astype(float)
w = V['kv2026'].volici.reindex(ids).values.astype(float)
uredni = [o for o in ids if V['kv2026'].ucast[o] < 15]
Mk = M.drop(index=uredni)
kor = Mk.corr().round(2)
out['rada'] = rada
out['korelace'] = dict(volby=list(kor.columns), r=kor.values.tolist())

# ---------------------------------------------------------------- kdy se okrsky rozešly: změna relativní síly KV 2022 → PS 2025 → KV 2026
I = pd.DataFrame({o: O[o]['rada_index'] for o in ids}).T.astype(float).drop(index=uredni)
out['index_zmeny'] = dict(
    kv22_kv26=dict(r=round(float(I.kv2022.corr(I.kv2026)), 2)),
    ps25_kv26=dict(r=round(float(I.ps2025.corr(I.kv2026)), 2)),
    kz24_kv26=dict(r=round(float(I.kz2024.corr(I.kv2026)), 2)),
    ep24_kv26=dict(r=round(float(I.ep2024.corr(I.kv2026)), 2)))
# regrese: KV 2026 (blok) ~ KV 2022 (blok) + PS 2025 (Piráti) + KZ 2024 (Piráti) – co nejlépe předpovídá rozložení 2026
X = np.c_[np.ones(len(Mk)), Mk.kv2022, Mk.ps2025, Mk.kz2024]
y = Mk.kv2026.values
b, *_ = np.linalg.lstsq(X, y, rcond=None)
pred = X @ b
r2 = 1 - ((y - pred) ** 2).sum() / ((y - y.mean()) ** 2).sum()
r2s = {}
for nm, cols in (('jen KV 2022', ['kv2022']), ('jen PS 2025', ['ps2025']), ('jen KZ 2024', ['kz2024']), ('jen EP 2024', ['ep2024']), ('jen Pavel 2023', ['prez2023_1'])):
    Xs = np.c_[np.ones(len(Mk)), Mk[cols]]
    bs, *_ = np.linalg.lstsq(Xs, y, rcond=None)
    r2s[nm] = round(float(1 - ((y - Xs @ bs) ** 2).sum() / ((y - y.mean()) ** 2).sum()), 3)
out['predikce_2026'] = dict(koef=dict(abs=round(float(b[0]), 2), kv2022=round(float(b[1]), 3), ps2025=round(float(b[2]), 3), kz2024=round(float(b[3]), 3)),
                            r2=round(float(r2), 3), r2_jednotlive=r2s, okrsku=len(Mk))
# okrsky, které si 2026 proti očekávání (z KV 2022 + PS 2025 + KZ 2024) vedly nejlépe / nejhůř
res = pd.Series(y - pred, index=Mk.index)
for o in ids:
    O[o]['rada_rezidual'] = round(float(res[o]), 2) if o in res.index else None
out['nejlepe'] = [dict(okrsek=int(o), ctvrt=O[o]['ctvrt'], rezidual=round(float(v), 2), kv2026=O[o]['blok_2026']) for o, v in res.sort_values(ascending=False).head(6).items()]
out['nejhure'] = [dict(okrsek=int(o), ctvrt=O[o]['ctvrt'], rezidual=round(float(v), 2), kv2026=O[o]['blok_2026']) for o, v in res.sort_values().head(6).items()]

data['casova_rada'] = out
data['okrsky'] = [O[o] for o in ids]
save(data, os.path.join(OUT, 'liberec.json'))
for r in rada:
    print(f"{r['datum']} {r['volby']:26s} {r['pct']:6.2f}  účast {r['ucast']}  {r['popis']}  {r['dalsi']}")
print(kor.to_string())
print('index r', out['index_zmeny'])
print('predikce', out['predikce_2026'])
print('nejlépe', out['nejlepe'])
print('nejhůř', out['nejhure'])

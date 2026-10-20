"""Doplňky k liberecké analýze: části města, školy, domovy pro seniory, demografie (SLDB 2021), nová výstavba,
kontrola dat okrsků, kuriozity a srovnání statutárních měst.

python -P scripts/doplnky.py <dl_dir> <dl_liberec> data       (spouštět po liberec.py)

<dl_dir>     otevřená data ČSÚ (KV 2022/2026, PS 2025), rpss/rpss.json (MPSV), davky/*.xml (dávky KV 2026 s časem zpracování)
<dl_liberec> ruian/<datum>_OB_563889_ADR.csv (ČÚZK), skoly/ms.html, skoly/zs.html (zapisyms/zapisyzs.liberec.cz),
             skoly/vyhlaska.txt (OZV č. 1/2025 o školských obvodech, text z .docx ze Sbírky právních předpisů),
             census/*.geojson (Statistický atlas ČSÚ, 1km grid), telefony_vo.txt (seznam volebních místností, liberec.cz)
"""
import sys, os, json, re, glob, math, html
import xml.etree.ElementTree as ET
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from jsonio import save  # noqa: E402
import adresy  # noqa: E402

DL, DLL, OUT = sys.argv[1:4]
KOD, SEATS = 563889, 39
rng = np.random.default_rng(2026)
data = json.load(open(os.path.join(OUT, 'liberec.json'), encoding='utf8'))
O = {o['okrsek']: o for o in data['okrsky']}
ids = sorted(O)
DF = pd.DataFrame(data['okrsky']).set_index('okrsek')
rd = lambda p: pd.read_csv(os.path.join(DL, p), low_memory=False)  # noqa: E731
out = {}


def perm_r(x, y, n=4999):
    x, y = np.asarray(x, float), np.asarray(y, float)
    ok = ~(np.isnan(x) | np.isnan(y)); x, y = x[ok], y[ok]
    r = np.corrcoef(x, y)[0, 1]
    sims = np.array([np.corrcoef(x, rng.permutation(y))[0, 1] for _ in range(n)])
    return round(float(r), 3), round(float((np.sum(np.abs(sims) >= abs(r)) + 1) / (n + 1)), 4), int(ok.sum())


def bh(rows):
    """Benjamini–Hochberg (FDR 5 %) – doplní rows[i]['fdr']."""
    pv = np.array([r['p'] for r in rows]); order = np.argsort(pv); m = len(pv)
    ok = pv[order] <= 0.05 * np.arange(1, m + 1) / m
    k = int(np.max(np.nonzero(ok)[0]) + 1) if ok.any() else 0
    for r in rows:
        r['fdr'] = bool(k and r['p'] <= pv[order][k - 1])
    return rows


# ---------------------------------------------------------------- adresní místa → okrsky
A = adresy.load(glob.glob(os.path.join(DLL, 'ruian', '*_ADR.csv'))[0])
POLY = adresy.polygons(os.path.join(OUT, 'okrsky_liberec.geojson'))
A['okrsek'] = adresy.assign(A.lon.values, A.lat.values, POLY)
mimo = A.okrsek.isna()
KX = math.cos(math.radians(50.77))


def nearest_fill(mask, col):
    """Doplní hodnotu sloupce u bodů `mask` podle nejbližšího bodu, který ji má."""
    src = A[~mask & A[col].notna()]
    S = np.c_[src.lon.values * KX, src.lat.values]
    for i in np.nonzero(mask.values)[0]:
        d = (S[:, 0] - A.lon.iat[i] * KX) ** 2 + (S[:, 1] - A.lat.iat[i]) ** 2
        A.at[A.index[i], col] = src[col].iat[int(d.argmin())]


nearest_fill(mimo, 'okrsek')
A['okrsek'] = A.okrsek.astype(int)
out['adresy'] = dict(adres=int(len(A)), mimo_polygony=int(mimo.sum()), okrsku_s_adresami=int(A.okrsek.nunique()))
print('adresy', out['adresy'])

# ---------------------------------------------------------------- 1) části města (převažující část obce v okrsku)
A['cast'] = A.cast_obce.str.replace(r'^Liberec [IVXL]+-', '', regex=True)
cnt = A.groupby(['okrsek', 'cast']).size()
for o in ids:
    c = cnt.loc[o].sort_values(ascending=False)
    O[o]['ctvrt'] = c.index[0]
    O[o]['ctvrt_podil'] = round(float(c.iloc[0] / c.sum() * 100))
    O[o]['ctvrt_dalsi'] = [k for k, v in c.iloc[1:3].items() if v / c.sum() >= 0.15]
DF['ctvrt'] = [O[o]['ctvrt'] for o in DF.index]
DF['odevzdano'] = DF.volici * DF.ucast_2026 / 100
ct = []
for c, g in DF.groupby('ctvrt'):
    w26 = g.volici * g.ucast_2026; w22 = g.volici * g.ucast_2022
    ct.append(dict(ctvrt=c, okrsku=int(len(g)), volici=int(g.volici.sum()), okrsky=[int(o) for o in g.index],
                   blok_2022=round(float(np.average(g.blok_2022, weights=w22)), 2), blok_2026=round(float(np.average(g.blok_2026, weights=w26)), 2),
                   ps_pir=round(float(np.average(g.ps_pir, weights=g.volici * g.ucast_ps)), 2), ll_2026=round(float(np.average(g.ll_2026, weights=w26)), 2),
                   slk_2026=round(float(np.average(g.slk_2026, weights=w26)), 2), ano_2026=round(float(np.average(g.ano_2026, weights=w26)), 2),
                   ucast_2026=round(float(np.average(g.ucast_2026, weights=g.volici)), 2)))
for c in ct:
    c['zmena'] = round(c['blok_2026'] - c['blok_2022'], 2)
out['ctvrti'] = sorted(ct, key=lambda d: -d['volici'])

# ---------------------------------------------------------------- 2) školy: zápisy 2026/27 a spádové obvody ZŠ
STREET_ABBR = [(r'^ul\.\s*', ''), (r'^náměstí\s+', 'nám. '), (r'\s+', ' ')]


def norm_street(s):
    s = str(s).strip()
    for a, b in STREET_ABBR:
        s = re.sub(a, b, s)
    return s


A['ul_n'] = A.ulice.map(norm_street)
addr_ix = {(r.ul_n, r.cd): i for i, r in A.iterrows()}


def geocode(text):
    """'Na Pískovně 761/3' → index adresy (ulice + č. p.), jinak těžiště ulice."""
    m = re.match(r'\s*(?:ul\.\s*)?(.+?)\s+(\d+)(?:/(\w+))?\s*$', text.strip().rstrip(','))
    if m:
        ul, cd = norm_street(m.group(1)), int(m.group(2))
        if (ul, cd) in addr_ix:
            i = addr_ix[(ul, cd)]
            return dict(lat=float(A.lat[i]), lon=float(A.lon[i]), okrsek=int(A.okrsek[i]), presne=True)
        s = A[A.ul_n == ul]
    else:
        s = A.iloc[0:0]
    if not len(s):
        # bez adresy v názvu (např. „ZŠ a MŠ Barvířská“, „MŠ Lísteček, Vratislavice nad Nisou“): ulice nebo část obce z názvu
        for w in re.findall(r'[A-ZÁČĎÉĚÍŇÓŘŠŤÚŮÝŽ][\wáčďéěíňóřšťúůýž]+(?: nad Nisou)?', text):
            s = A[(A.ul_n == w) | (A.cast == w)]
            if len(s):
                break
    if len(s):
        o = int(s.okrsek.mode().iloc[0])
        return dict(lat=float(s.lat.mean()), lon=float(s.lon.mean()), okrsek=o, presne=False)
    return None


def parse_zapisy(path):
    t = open(path, encoding='utf8').read()
    txt = html.unescape(re.sub(r'<[^>]+>', '\n', re.sub(r'<(script|style)[\s\S]*?</\1>', '', t)))
    L = [l.strip() for l in txt.split('\n') if l.strip()]
    L = L[L.index('Průběžné výsledky') + 1:]
    KEYS = {'Děti ze spádové oblasti:': 'spadove', 'Podaných žádostí:': 'zadosti', 'Přijatých dětí:': 'prijato', 'Přijatých žáků:': 'prijato',
            'Přijatých spádových:': 'prijato_spad', 'Nepřijatých dětí:': 'neprijato', 'Nepřijatých žáků:': 'neprijato', 'Přerušených řízení:': 'preruseno',
            'Zastavených řízení:': 'zastaveno'}
    rows, cur = [], None
    for k, l in enumerate(L):
        if re.fullmatch(r'\d+', l) and k + 1 < len(L) and re.search(r'[Šš]kol', L[k + 1]):
            cur = dict(nazev=L[k + 1], mista=0, mista_cisla=[]); rows.append(cur)
            continue
        if cur is None:
            continue
        if l in KEYS and k + 1 < len(L) and re.fullmatch(r'\d+', L[k + 1]):
            cur[KEYS[l]] = int(L[k + 1])
        elif 'zadosti' not in cur and re.fullmatch(r'\d+\s*/?', l) and L[k - 1] != cur['nazev'] and L[k - 1] not in KEYS:
            cur['mista_cisla'].append(int(l.rstrip(' /')))
        elif 'zadosti' not in cur and k > 0 and L[k - 1] == cur['nazev'] and not re.fullmatch(r'\d+\s*/?', l):
            cur['adresa_kratka'] = l
    for r in rows:
        r['mista'] = sum(r.pop('mista_cisla'))
        d = r.get('prijato', 0) + r.get('neprijato', 0)
        r['uspesnost'] = round(r.get('prijato', 0) / d * 100, 1) if d else None
        r['zadosti_na_misto'] = round(r['zadosti'] / r['mista'], 2) if r.get('mista') else None
        r['mista_na_spadove'] = round(r['mista'] / r['spadove'], 2) if r.get('spadove') else None
        adr = re.search(r'Liberec[^,]*,\s*(?:ul\.\s*)?([^,]+\d[^,]*),', r['nazev'])
        g = geocode(adr.group(1)) if adr else None
        if g is None and r.get('adresa_kratka') and re.search(r'\d', r['adresa_kratka']):
            g = geocode(r['adresa_kratka'])
        if g is None:
            g = geocode(re.sub(r'(Mateřská|Základní|Umělecká) škola|příspěvková organizace|Liberec', '', r['nazev']))
        r.update(g or {})
        r['kratky'] = re.sub(r',?\s*příspěvková organizace', '', r['nazev']).replace('Mateřská škola', 'MŠ').replace('Základní škola', 'ZŠ').strip(' ,')
    head = re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', t)))
    portal = {}
    for lab, key in (('Počet vypsaných volných míst', 'mista'), ('Počet podaných žádostí', 'zadosti'), ('Počet přijatých dětí', 'prijato'), ('Počet přijatých žáků', 'prijato')):
        m = re.search(lab + r':\s*(\d+)', head)
        if m:
            portal[key] = int(m.group(1))
    return rows, portal


(MS, MS_P), (ZS, ZS_P) = parse_zapisy(os.path.join(DLL, 'skoly', 'ms.html')), parse_zapisy(os.path.join(DLL, 'skoly', 'zs.html'))
print('portál MŠ', MS_P, 'součet škol', sum(r['mista'] for r in MS), sum(r.get('zadosti', 0) for r in MS), sum(r.get('prijato', 0) for r in MS))
print('portál ZŠ', ZS_P, 'součet škol', sum(r['mista'] for r in ZS), sum(r.get('zadosti', 0) for r in ZS), sum(r.get('prijato', 0) for r in ZS))
print('MŠ', len(MS), 'bez polohy', sum('okrsek' not in r for r in MS), '| ZŠ', len(ZS), 'bez polohy', sum('okrsek' not in r for r in ZS))

# vyhláška: školské obvody → ulice
V = [l.strip() for l in open(os.path.join(DLL, 'skoly', 'vyhlaska.txt'), encoding='utf8').read().split('\n')]
obv, curo = {}, None
for l in V:
    m = re.match(r'Školský obvod (\d+)$', l)
    if m:
        curo = int(m.group(1)); obv[curo] = dict(skola='', text='')
        continue
    if l.startswith('Čl. 2'):
        break
    if curo is None or not l:
        continue
    if not obv[curo]['text'] and (l.startswith('Základní') or l.startswith('příspěvková') or (obv[curo]['skola'] and len(l) < 60 and ',' not in l[:-2])):
        obv[curo]['skola'] += ' ' + l
    else:
        obv[curo]['text'] += ' ' + l


def split_items(s):
    items, depth, cur = [], 0, ''
    for ch in s:
        depth += ch == '('; depth -= ch == ')'
        if ch == ',' and depth == 0:
            items.append(cur.strip()); cur = ''
        else:
            cur += ch
    if cur.strip():
        items.append(cur.strip().rstrip('.'))
    return items


RULES = {}  # ulice → [(obvod, druh, čísla)]
for n, d in obv.items():
    t = d['text'].strip()
    if 'se stanovuje' in t:
        t = t.split(':', 1)[1]
    if n == 21:
        continue  # celé Vratislavice
    for it in split_items(t):
        m = re.match(r'(.+?)\s*\((.*)\)$', it)
        name, q = (m.group(1), m.group(2)) if m else (it, '')
        if ' – ' in name:  # „Zhořelecká – část od Sokolské k Pavlovické“
            name, q = name.split(' – ', 1)
        name = norm_street(name.replace('\xa0', ' '))
        if q.startswith('č') and 'p.' in q[:6]:
            nums = {int(x) for x in re.findall(r'\d+', q.split('vše v')[0])}
            RULES.setdefault(name, []).append((n, 'cp', nums))
        elif q.startswith('bez č'):
            RULES.setdefault(name, []).append((n, 'except', set()))
        elif q == '' or 'na území' in q:
            RULES.setdefault(name, []).append((n, 'all', set()))
        else:
            RULES.setdefault(name, []).append((n, 'partial', set()))
ul_set = set(A.ul_n)
out_skoly_kontrola = dict(ulic_ve_vyhlasce=len(RULES), nenalezenych=sorted(set(RULES) - ul_set))
A['obvod'] = None
A['obvod_kand'] = None
for i, r in A.iterrows():
    if r.momc == '556891':
        A.at[i, 'obvod'] = 21; continue
    rules = RULES.get(r.ul_n)
    if not rules:
        continue
    hit = [n for n, k, nums in rules if k == 'cp' and r.cd in nums]
    if hit:
        A.at[i, 'obvod'] = hit[0]; continue
    rest = [n for n, k, _ in rules if k != 'cp']
    if len(rest) == 1:
        A.at[i, 'obvod'] = rest[0]
    else:
        A.at[i, 'obvod_kand'] = tuple(sorted(set(rest or [n for n, _, _ in rules])))
# nejasné adresy (úseky ulic, adresy bez ulice v vyhlášce) → většina z 7 nejbližších jednoznačných adres (mezi kandidáty)
src = A[A.obvod.notna()]
S = np.c_[src.lon.values * KX, src.lat.values]
SO = src.obvod.values.astype(int)
nejasnych = 0
for i in np.nonzero(A.obvod.isna().values)[0]:
    d = (S[:, 0] - A.lon.iat[i] * KX) ** 2 + (S[:, 1] - A.lat.iat[i]) ** 2
    nn = SO[np.argsort(d)[:15]]
    kand = A.obvod_kand.iat[i]
    pool = [x for x in nn if kand is None or x in kand] or list(nn)
    A.at[A.index[i], 'obvod'] = int(pd.Series(pool[:7]).mode().iloc[0])
    nejasnych += 1
A['obvod'] = A.obvod.astype(int)
out_skoly_kontrola.update(jednoznacnych=int(len(src)), dopocitanych=nejasnych)
print('vyhláška', out_skoly_kontrola)

# obvod → škola v portálu zápisů (podle adresy v názvu školy)
for n, d in obv.items():
    sk = re.sub(r'\s+', ' ', d['skola']).strip()
    d['skola'] = sk
    best = None

    def akey(s):  # (ulice, č. p.) z názvu školy „…, Liberec, ul. 5. května 64/49, příspěvková organizace“
        m = re.search(r'Liberec\s*,\s*(?:ul\.\s*)?(.+?)\s+(\d+)(?:/\w+)?\s*(?:,|příspěvková|$)', s)
        return (norm_street(m.group(1)), int(m.group(2))) if m else None
    for z in ZS:
        if (akey(sk) and akey(sk) == akey(z['nazev'])) or (n == 21 and 'Vratislavice' in z['nazev']) \
                or ('Barvířská' in sk and 'Barvířská' in z['nazev']) or ('Ostašov' in sk and 'Ostašov' in z['nazev']):
            best = z
            break
    d['zapis'] = best
    if best:
        best['obvod'] = n
print('obvody bez školy v portálu:', [n for n, d in obv.items() if not d['zapis']])

# okrsek → podíly adres v obvodech → vážené ukazatele spádových škol
share = A.groupby(['okrsek', 'obvod']).size().unstack(fill_value=0)
share = share.div(share.sum(axis=1), axis=0)
for o in ids:
    s = share.loc[o]
    s = s[s > 0]
    vals = {}
    for k in ('uspesnost', 'mista_na_spadove', 'zadosti_na_misto'):
        pr = [(obv[n]['zapis'][k], w) for n, w in s.items() if obv[n]['zapis'] and obv[n]['zapis'].get(k) is not None]
        sw = sum(w for _, w in pr)
        vals[k] = round(sum(v * w for v, w in pr) / sw, 2) if sw else None
    top = int(s.idxmax())
    O[o].update(zs_uspesnost=vals['uspesnost'], zs_mista_na_spadove=vals['mista_na_spadove'], zs_zadosti_na_misto=vals['zadosti_na_misto'],
                zs_spadova=(obv[top]['zapis'] or {}).get('kratky') or obv[top]['skola'], zs_obvod=top, zs_obvod_podil=round(float(s.max() * 100)))
for r in MS + ZS:
    r['ctvrt'] = O[r['okrsek']]['ctvrt'] if r.get('okrsek') else None
ms_ct = []
for c, g in pd.DataFrame(MS).groupby('ctvrt'):
    d = g.prijato.sum() + g.neprijato.sum()
    ms_ct.append(dict(ctvrt=c, skol=int(len(g)), mista=int(g.mista.sum()), zadosti=int(g.zadosti.sum()), prijato=int(g.prijato.sum()), neprijato=int(g.neprijato.sum()),
                      uspesnost=round(float(g.prijato.sum() / d * 100), 1) if d else None, zadosti_na_misto=round(float(g.zadosti.sum() / g.mista.sum()), 2) if g.mista.sum() else None))
DF = DF.join(pd.DataFrame({o: {k: O[o][k] for k in ('zs_uspesnost', 'zs_mista_na_spadove', 'zs_zadosti_na_misto')} for o in ids}).T)
sk_kor = []
for a, al in (('zs_uspesnost', 'úspěšnost zápisu do spádové ZŠ'), ('zs_mista_na_spadove', 'místa na spádové dítě'), ('zs_zadosti_na_misto', 'žádosti na místo')):
    for b, bl in (('blok_2026', 'LOL a Piráti 2026'), ('zmena', 'změna 2022 → 2026'), ('ps_pir', 'Piráti PS 2025'), ('ll_2026', 'Lepší Liberec')):
        r, p, n = perm_r(DF[a], DF[b])
        sk_kor.append(dict(skola=a, skola_label=al, vysledek=b, vysledek_label=bl, r=r, p=p, n=n))
out['skoly'] = dict(rok='2026/27', ms=[{k: v for k, v in r.items() if k != 'nazev'} | dict(nazev=r['nazev']) for r in MS],
                    zs=[{k: v for k, v in r.items()} for r in ZS], ms_ctvrti=sorted(ms_ct, key=lambda d: d['uspesnost'] or 0),
                    portal=dict(ms=MS_P, zs=ZS_P),
                    souhrn=dict(ms=dict(mista=sum(r['mista'] for r in MS), zadosti=sum(r.get('zadosti', 0) for r in MS), prijato=sum(r.get('prijato', 0) for r in MS),
                                        neprijato=sum(r.get('neprijato', 0) for r in MS)),
                                zs=dict(mista=sum(r['mista'] for r in ZS), zadosti=sum(r.get('zadosti', 0) for r in ZS), prijato=sum(r.get('prijato', 0) for r in ZS),
                                        neprijato=sum(r.get('neprijato', 0) for r in ZS), spadove=sum(r.get('spadove', 0) for r in ZS))),
                    obvody=[dict(obvod=n, skola=d['skola'], zapis=(d['zapis'] or {}).get('kratky'), adres=int((A.obvod == n).sum())) for n, d in obv.items()],
                    kontrola=out_skoly_kontrola, korelace=bh(sk_kor))

# ---------------------------------------------------------------- 3) domovy pro seniory (registr poskytovatelů sociálních služeb MPSV)
rp = json.load(open(os.path.join(DL, 'rpss', 'rpss.json'), encoding='utf8'))['polozky']
DRUH = {'8': 'odlehčovací pobytová služba', '13': 'domov pro seniory', '14': 'domov se zvláštním režimem'}
adm_ix = {int(a): i for i, a in A.adm.items()}
zar = {}
for it in rp:
    if it.get('datumPoskytovaniDo'):
        continue
    druh = it['druhSocialniSluzby']['id'].split('/')[-1]
    cs = {c['cilovaSkupina']['id'].split('/')[-1] for c in it.get('ciloveSkupiny') or []}
    pob = [f for f in it.get('formy') or [] if f['forma']['id'].endswith('/pob')]
    if not pob or not (druh in ('13', '14') or (druh == '8' and '24' in cs)):
        continue
    cap = sum(k['pocet'] for f in pob for k in (f.get('kapacity') or []) if k.get('pocet') and k['typ']['id'].endswith(('luzka', 'klient')) and k['typ']['id'].endswith('luzka')) or \
        max([k['pocet'] for f in pob for k in (f.get('kapacity') or []) if k.get('pocet')] or [0])
    zz = [z for z in it.get('zarizeni') or [] if (((z or {}).get('adresa') or {}).get('obec') or {}).get('id') == f'Obec/{KOD}']
    cap = cap / max(1, len(zz))  # kapacita služby je za všechna zařízení dohromady – rozdělit mezi budovy
    for z in zz:
        a = (z or {}).get('adresa') or {}
        i = adm_ix.get(a.get('kodAdresnihoMista'))
        if i is None:
            continue
        key = ((z.get('nazev') or '').strip() or int(A.adm[i]), int(A.okrsek[i]))  # více budov jednoho domova v okrsku = jedno zařízení
        rec = zar.setdefault(key, dict(nazev=(z.get('nazev') or '').strip(), adresa=f"{A.ulice[i] or A.cast[i]} {A.cd[i]}" + (f"/{A.co[i]}" if A.co[i] else ''),
                                       poskytovatel=(it.get('poskytovatel') or {}).get('nazev'), lat=float(A.lat[i]), lon=float(A.lon[i]), okrsek=int(A.okrsek[i]), sluzby={}))
        rec['sluzby'][DRUH[druh]] = rec['sluzby'].get(DRUH[druh], 0) + cap
xy = np.array([[O[o]['lon'] * KX, O[o]['lat']] for o in ids])
Dm = np.sqrt(((xy[:, None] - xy[None]) ** 2).sum(-1))
METR = [('blok_2026', 'LOL a Piráti 2026'), ('zmena', 'změna proti 2022'), ('ano_2026', 'ANO'), ('ll_2026', 'Lepší Liberec'), ('slk_2026', 'SLK, TOP 09, KDU'),
        ('ucast_2026', 'Účast'), ('ps_pir', 'Piráti PS 2025')]
dom = []
for rec in zar.values():
    o = rec['okrsek']; i = ids.index(o)
    nn = [ids[j] for j in np.argsort(Dm[i])[1:7]]
    kap = sum(rec['sluzby'].values())
    dom.append(dict(**{k: v for k, v in rec.items()}, kapacita=kap, ctvrt=O[o]['ctvrt'], volici=O[o]['volici'], podil_kapacity=round(kap / O[o]['volici'] * 100, 1),
                    okrsek_hodnoty={k: O[o][k] for k, _ in METR}, sousede=nn, sousede_hodnoty={k: round(float(np.mean([O[n][k] for n in nn])), 2) for k, _ in METR}))
for o in ids:
    O[o]['domov_seniory'] = None
for d in dom:
    O[d['okrsek']]['domov_seniory'] = (O[d['okrsek']]['domov_seniory'] or 0) + d['kapacita']
mesto = {k: round(float(np.average(DF[k], weights=DF.volici if k == 'ucast_2026' else DF.odevzdano)), 2) for k, _ in METR}
out['seniori'] = dict(domovy=sorted(dom, key=lambda d: -d['kapacita']), mesto=mesto, metriky=[dict(k=k, label=l) for k, l in METR])
print('domovy', [(d['nazev'][:30], d['okrsek'], d['kapacita']) for d in dom])

# ---------------------------------------------------------------- 4) demografie: 1km grid SLDB 2021 → okrsky (dasymetricky podle adres)
LAYERS = {
    'sldb2021_obyvatelstvo': {'gis131620000': 'obyv', 'gis131620011': 'v0_14', 'gis131620012': 'v15_64', 'gis131620013': 'v65'},
    'byty': {'gis326070001': 'byty', 'gis326070002': 'byty_obydl', 'gis326070003': 'byty_neobydl'},
    'srovnani_sldb': {'gis243162002': 'zmena_obyv_11_21', 'gis242607002': 'zmena_byty_11_21'},
    'vyjizdka': {'gis174119001': 'vyjizdka', 'gis174119006': 'vyjizdka_prace', 'gis174119011': 'vyjizdka_skola'},
}
cells, cpoly = {}, []
for lay, fields in LAYERS.items():
    for f in json.load(open(os.path.join(DLL, 'census', f'{lay}.geojson'), encoding='utf8'))['features']:
        p = f['properties']
        rec = cells.setdefault(p['kod'], {})
        for k, v in fields.items():
            rec[v] = float(p.get(k) or 0)
        if lay == 'sldb2021_obyvatelstvo':
            cpoly.append((p['kod'], [np.array(f['geometry']['coordinates'][0])]))
A['bunka'] = adresy.assign(A.lon.values, A.lat.values, cpoly)
B = A[A.bunka.notna()]
n_cell = B.groupby('bunka').size()
n_co = B.groupby(['bunka', 'okrsek']).size()
VARS = ['obyv', 'v0_14', 'v15_64', 'v65', 'byty', 'byty_obydl', 'byty_neobydl', 'zmena_obyv_11_21', 'vyjizdka']
alloc = {o: dict.fromkeys(VARS, 0.0) for o in ids}
for (k, o), n in n_co.items():
    w = n / n_cell[k]
    for v in VARS:
        alloc[o][v] += cells[k].get(v, 0) * w
for o, a in alloc.items():
    ob = a['obyv']
    O[o].update(cen_obyv=round(ob), cen_65=round(a['v65'] / ob * 100, 1) if ob else None, cen_0_14=round(a['v0_14'] / ob * 100, 1) if ob else None,
                cen_rust_11_21=round(a['zmena_obyv_11_21'] / (ob - a['zmena_obyv_11_21']) * 100, 1) if ob - a['zmena_obyv_11_21'] > 0 else None,
                cen_byty_neobydl=round(a['byty_neobydl'] / a['byty'] * 100, 1) if a['byty'] else None,
                cen_obyv_na_byt=round(ob / a['byty_obydl'], 2) if a['byty_obydl'] else None,
                cen_vyjizdka=round(a['vyjizdka'] / ob * 100, 1) if ob else None)
tot = {v: sum(a[v] for a in alloc.values()) for v in VARS}
DEMO = [('cen_65', 'podíl 65+'), ('cen_0_14', 'podíl dětí 0–14'), ('cen_rust_11_21', 'růst obyvatel 2011–21'), ('cen_obyv_na_byt', 'obyvatel na obydlený byt'),
        ('cen_byty_neobydl', 'neobydlené byty'), ('cen_vyjizdka', 'vyjíždějící za prací a do škol')]
VYS = [('blok_2026', 'LOL a Piráti 2026'), ('zmena', 'změna 2022 → 2026'), ('ps_pir', 'Piráti PS 2025'), ('ucast_2026', 'účast 2026'),
       ('ll_2026', 'Lepší Liberec'), ('slk_2026', 'SLK, TOP 09, KDU'), ('ano_2026', 'ANO')]
D2 = DF.join(pd.DataFrame({o: {k: O[o][k] for k, _ in DEMO} for o in ids}).T)
D2 = D2[D2.ucast_2026 >= 15]  # bez „úředního“ okrsku
dk = []
for a, al in DEMO:
    for b, bl in VYS:
        r, p, n = perm_r(D2[a], D2[b], n=1999)
        dk.append(dict(demo=a, demo_label=al, vysledek=b, vysledek_label=bl, r=r, p=p, n=n))
out['demografie'] = dict(korelace=bh(dk), bunek=int(B.bunka.nunique()), adres=int(len(B)),
                         odhad=dict(obyv=round(tot['obyv']), v65=round(tot['v65'] / tot['obyv'] * 100, 1), v0_14=round(tot['v0_14'] / tot['obyv'] * 100, 1)))
print('demografie', out['demografie']['odhad'], out['demografie']['bunek'])

# ---------------------------------------------------------------- 5) nová výstavba: přírůstek voličů 2022 → 2026
t3 = {}
for y, f in ((2026, 'KV2026_data_20261011_csv/csv_od/kvt3.csv'), (2022, 'KV2022_data_20260328_csv/csv_od/kvt3.csv')):
    t = rd(f)
    if 'DATUMVOLEB' in t:
        t = t[t.DATUMVOLEB == 20220923]
    t3[y] = t[t.KODZASTUP == KOD].set_index('OKRSEK')
rust = (t3[2026].VOL_SEZNAM / t3[2022].VOL_SEZNAM - 1) * 100
for o in ids:
    O[o]['rust_volicu'] = round(float(rust[o]), 1)
    O[o]['volici_2022'] = int(t3[2022].VOL_SEZNAM[o])
DF['rust_volicu'] = rust
top = DF.sort_values('rust_volicu', ascending=False).head(8)
r1, p1, _ = perm_r(DF.rust_volicu, DF.zmena)
r2, p2, _ = perm_r(DF.rust_volicu, DF.blok_2026)
out['vystavba'] = dict(top=[dict(okrsek=int(o), ctvrt=O[o]['ctvrt'], volici_2022=O[o]['volici_2022'], volici_2026=int(r.volici), rust=round(float(r.rust_volicu), 1),
                                 blok_2026=r.blok_2026, zmena=r.zmena, ll_2026=r.ll_2026) for o, r in top.iterrows()],
                       mesto_rust=round(float((t3[2026].VOL_SEZNAM.sum() / t3[2022].VOL_SEZNAM.sum() - 1) * 100), 1),
                       r_zmena=r1, p_zmena=p1, r_blok=r2, p_blok=p2, rostoucich_10=int((rust >= 10).sum()))

# ---------------------------------------------------------------- 6) kontrola dat okrsků
t = t3[2026]
hl = rd('KV2026_data_20261011_csv/csv_od/kvhl.csv')
hl = hl[hl.ID_OKRSKY.isin(set(t.ID_OKRSKY))].merge(t.reset_index()[['ID_OKRSKY', 'OKRSEK']], on='ID_OKRSKY', suffixes=('_x', ''))
ros = rd('KV2026reg20261011_csv/csv_od/kvros.csv'); ros = ros[ros.KODZASTUP == KOD].set_index('POR_STR_HL')


nf2 = lambda v: f'{v:.2f}'.replace('.', ',')  # noqa: E731


def rz(s):
    med = s.median(); mad = (s - med).abs().median()
    return 0.6745 * (s - med) / mad if mad else s * 0


ucast = t.ODEVZ_OBAL / t.VOL_SEZNAM * 100
neplatne = (1 - t.PLAT_LISTKY / t.ODEVZ_OBAL) * 100
# 2022 nemá počet platných lístků – srovnatelné je jen využití hlasů na odevzdanou obálku (neplatný lístek = 0 hlasů)
obal26 = t.PL_HL_CELK / (t.ODEVZ_OBAL * SEATS) * 100
obal22 = t3[2022].PL_HL_CELK / (t3[2022].ODEVZ_OBAL * SEATS) * 100
vyuziti = t.PL_HL_CELK / (t.PLAT_LISTKY * SEATS) * 100
nevratene = t.VYD_OBALKY - t.ODEVZ_OBAL
nal = []
for nazev, s, popis in (('účast', ucast, '%'), ('neplatné hlasovací lístky', neplatne, '%'), ('využití hlasů (39 na lístek)', vyuziti, '%')):
    z = rz(s)
    for o in z[z.abs() > 3.5].index:
        vys = ''
        if o == 1 and nazev == 'účast':
            vys = 'úřední adresa magistrátu (trvalé pobyty bez skutečného bydliště)'
        elif nazev.startswith('neplatné'):
            vys = f'hlasy na obálku {nf2(obal26[o])} % (2022: {nf2(obal22[o])} %; město {nf2(obal26.median())} / {nf2(obal22.median())} %)'
        nal.append(dict(test=nazev, okrsek=int(o), hodnota=round(float(s[o]), 2), median=round(float(s.median()), 2), z=round(float(z[o]), 1), jednotka=popis, vysvetleni=vys))
for o in nevratene[nevratene > 2].index:
    nal.append(dict(test='vydané a neodevzdané obálky', okrsek=int(o), hodnota=int(nevratene[o]), median=float(nevratene.median()), z=None, jednotka='obálek', vysvetleni=''))
tot_l = hl.groupby('POR_STR_HL').POC_HLASU.sum()
big = tot_l[tot_l / tot_l.sum() > 0.05].index
pv = hl.pivot_table(index='OKRSEK', columns='POR_STR_HL', values='POC_HLASU', aggfunc='sum', fill_value=0)
for p in big:
    for o in pv.index[pv[p] == 0]:
        nal.append(dict(test='nula hlasů pro kandidátku nad 5 %', okrsek=int(o), hodnota=0, median=float(pv[p].median()), z=None, jednotka=ros.loc[p, 'ZKRATKAO30'], vysvetleni=''))
# poslední číslice hlasů kandidátek (≥ 100 hlasů) – rovnoměrnost, simulované p
v = hl.POC_HLASU[hl.POC_HLASU >= 100].astype(int).values
obs = np.bincount(v % 10, minlength=10)
chi = float(((obs - len(v) / 10) ** 2 / (len(v) / 10)).sum())
sims = np.array([(lambda c: ((c - len(v) / 10) ** 2 / (len(v) / 10)).sum())(rng.multinomial(len(v), [0.1] * 10)) for _ in range(20000)])
out['kontrola'] = dict(nalezy=nal, okrsku=int(len(t)), opravenych=int((t.OPRAVA > 0).sum()) if 'OPRAVA' in t else None,
                       cislice=dict(n=int(len(v)), chi2=round(chi, 2), p=round(float((sims >= chi).mean()), 3), cetnosti=obs.tolist()),
                       median=dict(ucast=round(float(ucast.median()), 2), neplatne=round(float(neplatne.median()), 2), vyuziti=round(float(vyuziti.median()), 2)),
                       mandaty_sedi=True)
print('kontrola', len(nal), out['kontrola']['cislice'])

# ---------------------------------------------------------------- 7) kuriozity
K = {}
rk = rd('KV2026reg20261011_csv/csv_od/kvrk.csv'); rk = rk[rk.KODZASTUP == KOD].copy()
rk['listina'] = rk.POR_STR_HL.map(ros.ZKRATKAO30)
P = rk.POVOLANI.astype(str).str.lower()
rk['it'] = P.str.contains(r'program|vývojář|developer|\bit\b|softwar|datov|data |analytik dat|digitaliz|informatik', regex=True)
rk['duchodce'] = P.str.contains('důchod')
rk['ucitel'] = P.str.contains(r'učitel|pedagog', regex=True)
rk['podnikatel'] = P.str.contains(r'podnikatel|osvč|živnost', regex=True)
g = rk.groupby('listina').agg(kandidatu=('it', 'size'), it=('it', 'mean'), duchodci=('duchodce', 'mean'), ucitele=('ucitel', 'mean'), podnikatele=('podnikatel', 'mean'),
                              vek=('VEK', 'median'), procent=('POR_STR_HL', lambda s: float(ros.loc[s.iloc[0], 'PROCHLSTR'])))
K['povolani'] = [dict(listina=s, kandidatu=int(r.kandidatu), it=round(float(r.it) * 100, 1), duchodci=round(float(r.duchodci) * 100, 1), ucitele=round(float(r.ucitele) * 100, 1),
                      podnikatele=round(float(r.podnikatele) * 100, 1), vek=float(r.vek), procent=r.procent) for s, r in g.sort_values('procent', ascending=False).iterrows()]
# sudé × liché okrsky
lich = np.array([o % 2 == 1 for o in DF.index]); y = DF.blok_2026.values
d_obs = y[~lich].mean() - y[lich].mean()
perm = np.array([(lambda s: y[~s].mean() - y[s].mean())(rng.permutation(lich)) for _ in range(20000)])
K['parita'] = dict(sude=round(float(y[~lich].mean()), 2), liche=round(float(y[lich].mean()), 2), rozdil=round(float(d_obs), 2), p=round(float((np.abs(perm) >= abs(d_obs)).mean()), 2),
                   sudych=int((~lich).sum()), lichych=int(lich.sum()))
# volební místnosti (seznam telefonů do místností na liberec.cz: okrsek, adresa) → typ budovy podle adres škol
TL = [l.strip() for l in open(os.path.join(DLL, 'telefony_vo.txt'), encoding='utf8').read().split('\n') if l.strip()]
mist = {}
i0 = next(i for i, l in enumerate(TL) if l == 'Liberec' and i > 2)
k = i0 + 1
while k < len(TL) - 1:
    if re.fullmatch(r'\d+', TL[k]) and re.search(r'\d', TL[k + 1]) and 'Liberec' in TL[k + 1]:
        mist[int(TL[k])] = TL[k + 1]
        k += 2
        continue
    if re.fullmatch(r'\d+', TL[k]) and k + 1 < len(TL) and not re.search(r'\d', TL[k + 1]) and len(mist) > 20:
        break
    k += 1
skol_adr = {}
for r in MS + ZS:
    m = re.search(r'Liberec[^,]*,\s*(?:ul\.\s*)?([^,]+?)\s+(\d+)', r['nazev'])
    if m:
        skol_adr[(norm_street(m.group(1)), int(m.group(2)))] = 'základní škola' if r in ZS else 'mateřská škola'
    if r.get('adresa_kratka'):
        m = re.search(r'(.+?)\s+(\d+)', r['adresa_kratka'])
        if m:
            skol_adr.setdefault((norm_street(m.group(1)), int(m.group(2))), 'základní škola')


def typ_mist(a):
    m = re.match(r'(.+?)\s+(\d+)', a)
    return skol_adr.get((norm_street(m.group(1)), int(m.group(2))), 'jiná budova') if m else 'jiná budova'


for o, a in mist.items():
    if o in O:
        O[o]['mistnost'] = a.split(',')[0]
        O[o]['mistnost_typ'] = typ_mist(a)
mt = DF.assign(typ=[O[o].get('mistnost_typ') for o in DF.index]).dropna(subset=['typ'])
K['mistnost'] = [dict(typ=t_, okrsku=int(len(g_)), blok=round(float(g_.blok_2026.mean()), 1), zmena=round(float(g_.zmena.mean()), 1),
                      sdilene=int(g_.assign(m=[O[o]['mistnost'] for o in g_.index]).m.duplicated(keep=False).sum()))
                 for t_, g_ in mt.groupby('typ')]
K['mistnosti_nalezeno'] = len(mist)
# čas sečtení okrsku (dávky KV 2026) × výsledek
NS = '{http://www.volby.cz/kv/}'
cas = {}
for f in sorted(glob.glob(os.path.join(DL, 'davky', '*.xml'))):
    for ok in ET.parse(f).getroot().iter(NS + 'OKRSEK'):
        if ok.get('KODZASTUP') == str(KOD):
            o = int(ok.get('CIS_OKRSEK'))
            cas.setdefault(o, ok.get('DATUM_CAS_ZPRAC'))
start = pd.Timestamp('2026-10-10 14:00:00')
for o, c in cas.items():
    if o in O:
        O[o]['cas_secteni'] = c
        O[o]['hodin_secteni'] = round((pd.Timestamp(c) - start).total_seconds() / 3600, 2)
X = DF.assign(h=[O[o].get('hodin_secteni') for o in DF.index]).dropna(subset=['h'])
r_c, p_c, n_c = perm_r(X.h, X.blok_2026)
r_o, p_o, _ = perm_r(X.h, X.odevzdano)
K['cas'] = dict(r_blok=r_c, p_blok=p_c, r_obalky=r_o, p_obalky=p_o, n=n_c, prvni=dict(okrsek=int(X.h.idxmin()), cas=O[int(X.h.idxmin())]['cas_secteni']),
                posledni=dict(okrsek=int(X.h.idxmax()), cas=O[int(X.h.idxmax())]['cas_secteni']),
                body=[dict(okrsek=int(o), hodin=float(r.h), blok=float(r.blok_2026), obalky=int(r.odevzdano), ctvrt=O[o]['ctvrt']) for o, r in X.iterrows()])
# titul × preferenční hlasy (relativně k průměru vlastní kandidátky)
rk['rel'] = rk.POCHLASU / rk.groupby('POR_STR_HL').POCHLASU.transform('mean')
rk['titul'] = rk.TITULPRED.fillna('').astype(str).str.strip().str.len() > 0
a_, b_ = rk[rk.titul].rel.values, rk[~rk.titul].rel.values
boot = [rng.choice(a_, len(a_)).mean() / rng.choice(b_, len(b_)).mean() - 1 for _ in range(4000)]
rk['por_bin'] = pd.qcut(rk.PORCISLO, 5, labels=False, duplicates='drop')
po = rk.groupby('por_bin').apply(lambda g_: g_[g_.titul].rel.mean() / g_[~g_.titul].rel.mean() - 1).mean()
K['titul'] = dict(s_titulem=round(float(a_.mean()), 3), bez_titulu=round(float(b_.mean()), 3), rozdil_pct=round(float(a_.mean() / b_.mean() - 1) * 100, 1),
                  p05=round(float(np.percentile(boot, 5)) * 100, 1), p95=round(float(np.percentile(boot, 95)) * 100, 1), kandidatu=int(len(rk)), s_titulem_n=int(len(a_)),
                  rozdil_po_poradi=round(float(po) * 100, 1))
out['kuriozity'] = K
print('kuriozity', K['parita'], K['mistnost'], 'místností', len(mist), 'časů', len(cas), {k: v for k, v in K['cas'].items() if k != 'body'}, K['titul'])

# ---------------------------------------------------------------- 8) statutární města: pirátský blok 2022 → 2026
z = rd('KV2026reg20261011_csv/csv_od/kvrzcoco.csv')
mesta = z[(z.TYPZASTUP == 1) & (z.DRUHZASTUP == 3)].drop_duplicates('KODZASTUP')[['KODZASTUP', 'NAZEVZAST', 'MANDATY']]
R = {}
for y, f in ((2022, 'KV2022reg20260328_csv/csv_od/kvros.csv'), (2026, 'KV2026reg20261011_csv/csv_od/kvros.csv')):
    r_ = rd(f)
    if 'DATUMVOLEB' in r_:
        r_ = r_[r_.DATUMVOLEB == 20220923]
    R[y] = r_[r_.KODZASTUP.isin(mesta.KODZASTUP)].copy()
    R[y]['kody'] = R[y].SLOZENI.astype(str).map(lambda s: {c.strip().zfill(3) for c in s.split(',')})
ps_t = rd('PS2025data20251005_csv/csv_od/pst4p.csv')
ps_k = rd('PS2025reg20251005_csv/csv_od/psrkl.csv').set_index('KSTRANA').ZKRATKAK30
pir_ks = [k for k, n in ps_k.items() if 'pirát' in str(n).lower()]
t26 = rd('KV2026_data_20261011_csv/csv_od/kvt3.csv')
obce = t26[t26.KODZASTUP.isin(mesta.KODZASTUP)].groupby('KODZASTUP').OBEC.unique()
ps_t = ps_t[ps_t.OBEC.isin(set(np.concatenate(obce.values)))]
rows = []
for _, mr in mesta.iterrows():
    kz = mr.KODZASTUP
    part = set()
    for y in (2022, 2026):
        for s in R[y][R[y].KODZASTUP == kz].kody:
            if '720' in s:
                part |= s
    if not part:
        continue
    part -= {'720', '080'}
    rec = dict(mesto=mr.NAZEVZAST, kod=int(kz), mandatu=int(mr.MANDATY), partneri=sorted(part))
    for y in (2022, 2026):
        L_ = R[y][R[y].KODZASTUP == kz]
        blk = L_[L_.kody.map(lambda s: s <= part | {'720', '080'} and bool(s & (part | {'720'})))]
        tot_h = L_.HLASY_STR.sum()
        rec[f'blok_{y}'] = round(float(blk.HLASY_STR.sum() / tot_h * 100), 2) if tot_h else None
        rec[f'mand_{y}'] = int(blk.MAND_STR.sum())
        rec[f'listiny_{y}'] = blk.ZKRATKAO30.tolist()
        rec[f'pirati_{y}'] = bool(L_.kody.map(lambda s: '720' in s).any())
        pl = L_[L_.kody.map(lambda s: '720' in s)]
        rec[f'typ_{y}'] = None if pl.empty else ('samostatně' if all(s <= {'720', '080'} for s in pl.kody) else 'koalice')
        rec[f'pirlist_{y}'] = pl.ZKRATKAO30.tolist()
    # vlastní značka = kandidátka s Piráty má v názvu „Piráti“ (samostatně nebo „X a Piráti“); jinak širší místní uskupení
    rec['znacka_2026'] = bool(rec['pirlist_2026']) and any(re.search(r'pirát', n, re.I) for n in rec['pirlist_2026'])
    pt = ps_t[ps_t.OBEC.isin(obce[kz])]
    rec['ps2025'] = round(float(pt[pt.KSTRANA.isin(pir_ks)].POC_HLASU.sum() / pt.POC_HLASU.sum() * 100), 2) if len(pt) else None
    if rec['blok_2022'] and rec['blok_2026'] is not None:
        rec['zmena'] = round(rec['blok_2026'] - rec['blok_2022'], 2)
        rec['pomer'] = round(rec['blok_2026'] / rec['blok_2022'], 3) if rec['blok_2022'] else None
    rec['srovnatelne'] = rec['pirati_2022'] and rec['pirati_2026']
    rows.append(rec)
S_ = [r for r in rows if r['srovnatelne'] and r.get('pomer')]
SZ = [r for r in S_ if r['znacka_2026']]
SK = [r for r in S_ if not r['znacka_2026']]
lib = next(r for r in S_ if r['kod'] == KOD)
out['mesta'] = dict(mesta=sorted(rows, key=lambda r: -(r.get('pomer') or 0)), srovnatelnych=len(S_),
                    poradi_liberec=1 + sorted([r['pomer'] for r in S_], reverse=True).index(lib['pomer']),
                    median_pomer=round(float(np.median([r['pomer'] for r in S_])), 3),
                    znacka=dict(mest=len(SZ), median_pomer=round(float(np.median([r['pomer'] for r in SZ])), 3), rostlo=sum(r['pomer'] > 1 for r in SZ),
                                poradi_liberec=1 + sorted([r['pomer'] for r in SZ], reverse=True).index(lib['pomer'])),
                    koalice=dict(mest=len(SK), median_pomer=round(float(np.median([r['pomer'] for r in SK])), 3) if SK else None, rostlo=sum(r['pomer'] > 1 for r in SK)))
print('města', len(rows), 'srovnatelných', len(S_), 'Liberec pořadí', out['mesta']['poradi_liberec'], 'medián poměru', out['mesta']['median_pomer'],
      'značka', out['mesta']['znacka'], 'koalice', out['mesta']['koalice'])
for r in out['mesta']['mesta']:
    print(f"  {r['mesto']:20s} {r.get('blok_2022')} → {r.get('blok_2026')} ({r.get('pomer')}) {r['typ_2022']}/{r['typ_2026']} PS {r['ps2025']} {r['listiny_2026']}")

data['okrsky'] = [O[o] for o in ids]
data['doplnky'] = out
save(data, os.path.join(OUT, 'liberec.json'))
print('ctvrti', [(c['ctvrt'], c['okrsku'], c['blok_2026']) for c in out['ctvrti'][:12]])
print('školy souhrn', out['skoly']['souhrn'])
for k_ in out['skoly']['korelace']:
    print('  škola×', k_['skola'], k_['vysledek'], k_['r'], k_['p'], k_['fdr'])
for k_ in out['demografie']['korelace']:
    if k_['fdr']:
        print('  demo×', k_['demo'], k_['vysledek'], k_['r'], k_['p'])
print('výstavba', {k: v for k, v in out['vystavba'].items() if k != 'top'})

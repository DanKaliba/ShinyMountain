"""Adresní místa RÚIAN (ČÚZK, CSV za obec) se souřadnicemi WGS84 a přiřazením do volebních okrsků.

Souřadnice v RÚIAN jsou v S-JTSK (Křovák, EPSG:5514, kladné Y/X). Převod do WGS84 bez pyproj:
inverzní Křovákovo zobrazení na Besselův elipsoid + 7prvková Helmertova transformace (přesnost ~1 m).
Zdroj: https://vdp.cuzk.cz/vymenny_format/csv/<datum>_OB_<kód obce>_ADR.csv.zip
"""
import os, json
import numpy as np
import pandas as pd


def jtsk_to_wgs(Y, X, H=300.0):
    Y, X = np.asarray(Y, float), np.asarray(X, float)
    # inverzní Křovák → zeměpisné souřadnice na Besselově elipsoidu
    e, n, ro0 = 0.081696831215303, 0.97992470462083, 12310230.12797036
    sinUQ, cosUQ, sinVQ, cosVQ = 0.863499969506341, 0.504348889819882, 0.420215144586493, 0.907424504992097
    alfa, k = 1.000597498371542, 1.003419163966575
    ro = np.sqrt(X * X + Y * Y)
    eps = 2 * np.arctan(Y / (ro + X))
    D = eps / n
    S = 2 * np.arctan(np.exp(1 / n * np.log(ro0 / ro))) - np.pi / 2
    sinS, cosS = np.sin(S), np.cos(S)
    sinU = sinUQ * sinS - cosUQ * cosS * np.cos(D)
    cosU = np.sqrt(1 - sinU ** 2)
    sinDV = np.sin(D) * cosS / cosU
    cosDV = np.sqrt(1 - sinDV ** 2)
    sinV = sinVQ * cosDV - cosVQ * sinDV
    cosV = cosVQ * cosDV + sinVQ * sinDV
    L = 2 * np.arctan(sinV / (1 + cosV)) / alfa
    t = np.exp(2 / alfa * np.log((1 + sinU) / cosU / k))
    pom = (t - 1) / (t + 1)
    for _ in range(30):
        sinB = pom
        pom = t * np.exp(e * np.log((1 + e * sinB) / (1 - e * sinB)))
        pom = (pom - 1) / (pom + 1)
    B = np.arctan(pom / np.sqrt(1 - pom ** 2))
    # Bessel → pravoúhlé souřadnice
    a, f1 = 6377397.15508, 299.152812853
    e2 = 1 - (1 - 1 / f1) ** 2
    N = a / np.sqrt(1 - e2 * np.sin(B) ** 2)
    x = (N + H) * np.cos(B) * np.cos(L)
    y = (N + H) * np.cos(B) * np.sin(L)
    z = ((1 - e2) * N + H) * np.sin(B)
    # Helmert S-JTSK → WGS84
    dx, dy, dz = 570.69, 85.69, 462.84
    wz, wy, wx = (-5.2611 / 3600 * np.pi / 180, -1.58676 / 3600 * np.pi / 180, -4.99821 / 3600 * np.pi / 180)
    m = 3.543e-6
    xn = dx + (1 + m) * (x + wz * y - wy * z)
    yn = dy + (1 + m) * (-wz * x + y + wx * z)
    zn = dz + (1 + m) * (wy * x - wx * y + z)
    # pravoúhlé → zeměpisné na WGS84
    a, f1 = 6378137.0, 298.257223563
    ab = f1 / (f1 - 1)
    e2 = 1 - (1 - 1 / f1) ** 2
    p = np.sqrt(xn ** 2 + yn ** 2)
    th = np.arctan(zn * ab / p)
    B = np.arctan((zn + e2 * ab * a * np.sin(th) ** 3) / (p - e2 * a * np.cos(th) ** 3))
    L = 2 * np.arctan(yn / (p + xn))
    return np.degrees(B), np.degrees(L)


def load(path):
    """Adresní místa obce: ulice, číslo domovní/orientační, část obce, lat/lon."""
    A = pd.read_csv(path, sep=';', encoding='cp1250', dtype=str)
    A.columns = ['adm', 'obec', 'nazev_obce', 'momc', 'nazev_momc', 'mop', 'nazev_mop', 'kod_casti', 'cast_obce', 'kod_ulice', 'ulice',
                 'typ_so', 'cd', 'co', 'co_znak', 'psc', 'Y', 'X', 'plati_od']
    A = A[A.Y.notna() & A.X.notna()].copy()
    A['lat'], A['lon'] = jtsk_to_wgs(A.Y.astype(float), A.X.astype(float))
    A['cd'] = A.cd.astype(int)
    A['co'] = A.co.fillna('') + A.co_znak.fillna('')
    A['ulice'] = A.ulice.fillna('')
    return A.reset_index(drop=True)


# ---------------------------------------------------------------- bod v polygonu (okrsky z geojsonu)
def polygons(geojson_path, key='o'):
    g = json.load(open(geojson_path, encoding='utf8'))
    out = []
    for f in g['features']:
        polys = f['geometry']['coordinates'] if f['geometry']['type'] == 'MultiPolygon' else [f['geometry']['coordinates']]
        # každý polygon = (vnější hranice, [díry]) – okrsek uvnitř jiného okrsku je v tom vnějším dírou
        out.append((f['properties'][key], [(np.array(p[0]), [np.array(h) for h in p[1:]]) for p in polys]))
    return out


def _pip_many(x, y, ring):
    xs, ys = ring[:, 0], ring[:, 1]
    xj, yj = np.roll(xs, 1), np.roll(ys, 1)
    inside = np.zeros(len(x), bool)
    for i in range(len(xs)):
        c = ((ys[i] > y) != (yj[i] > y)) & (x < (xj[i] - xs[i]) * (y - ys[i]) / (yj[i] - ys[i] + 1e-15) + xs[i])
        inside ^= c
    return inside


def assign(lon, lat, polys):
    """Vektorově: index polygonu (klíč) pro každý bod, jinak None."""
    lon, lat = np.asarray(lon, float), np.asarray(lat, float)
    res = np.full(len(lon), None, dtype=object)
    for key, parts in polys:
        parts = [p if isinstance(p, tuple) else (p, []) for p in parts]
        x0 = min(r[:, 0].min() for r, _ in parts); x1 = max(r[:, 0].max() for r, _ in parts)
        y0 = min(r[:, 1].min() for r, _ in parts); y1 = max(r[:, 1].max() for r, _ in parts)
        cand = np.nonzero((lon >= x0) & (lon <= x1) & (lat >= y0) & (lat <= y1) & (res == None))[0]  # noqa: E711
        if not len(cand):
            continue
        hit = np.zeros(len(cand), bool)
        for outer, holes in parts:
            h = _pip_many(lon[cand], lat[cand], outer)
            for hole in holes:
                h &= ~_pip_many(lon[cand], lat[cand], hole)
            hit |= h
        res[cand[hit]] = key
    return res


if __name__ == '__main__':
    import sys
    A = load(sys.argv[1])
    print(len(A), A.iloc[0][['ulice', 'cd', 'co', 'cast_obce', 'lat', 'lon']].to_dict())

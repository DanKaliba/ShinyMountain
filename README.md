# ShinyMountain – Piráti Liberec, komunální volby 2026

Analýza výsledků společné kandidátky „Liberec otevřený lidem a Piráti“ v komunálních volbách 2026 v Liberci po volebních okrscích:
srovnání s rokem 2022 (Piráti a LOL samostatně) a se sněmovními volbami 2025, mandátové hrany, odhad přesunů voličů a preferenční hlasy.

**Web:** https://dankaliba.github.io/ShinyMountain/

Sesterský projekt: [ShinySpace](https://github.com/DanKaliba/ShinySpace) (Piráti Praha 5).

## Struktura

| Složka | Co v ní je |
|---|---|
| [`zjisteni/`](zjisteni/) | zjištění a metodika v Markdownu – web je zobrazuje přímo |
| [`data/`](data/) | vygenerovaná data: `liberec.json` (web), hranice okrsků `okrsky_liberec.geojson` |
| [`scripts/`](scripts/) | výpočet: `liberec.py`; pomocné `ei.py` (ekologická inference), `mandaty.py` (přepočet mandátů), `jsonio.py` |
| [`web/`](web/) | stránka (HTML, JS, CSS) – čte `../data/` a `../zjisteni/` |

## Lokální náhled

```bash
python -m http.server 8000      # v kořeni repozitáře
# http://localhost:8000/web/
```

## Přegenerování dat

Zdrojová data ČSÚ (rozbalené zipy z [volby.gov.cz](https://volby.gov.cz/opendata/opendata.htm)) ve složce `dl/`:
`KV2026_data_20261011_csv`, `KV2026reg20261011_csv`, `KV2022_data_20260328_csv`, `KV2022reg20260328_csv`,
`PS2025data20251005_csv`, `PS2025reg20251005_csv` a `geo/kv2022_geo_vol_okrsky_2022g100.geojson`.

```bash
python scripts/liberec.py dl data       # ~3 min (bootstrap ekologické inference)
```

Zdroje: ČSÚ – [volby.gov.cz](https://volby.gov.cz/opendata/opendata.htm), podkladové mapy © Esri.

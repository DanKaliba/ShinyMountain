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

Pro doplňky navíc `dl/rpss/rpss.json` (registr sociálních služeb MPSV), `dl/davky/*.xml` (dávky výsledků KV 2026 s časem zpracování okrsků)
a složka `dl_liberec/`:

| Soubor | Zdroj |
|---|---|
| `ruian/20260930_OB_563889_ADR.csv` | adresní místa RÚIAN – https://vdp.cuzk.cz/vymenny_format/csv/20260930_OB_563889_ADR.csv.zip |
| `skoly/ms.html`, `skoly/zs.html` | https://zapisyms.liberec.cz/materske-skoly, https://zapisyzs.liberec.cz/zakladni-skoly |
| `skoly/vyhlaska.txt` | text OZV č. 1/2025 o školských obvodech (Sbírka právních předpisů, `…/detail/SPPNYNWNNUUQF4Z2/text` je .docx) |
| `census/*.geojson` | Statistický atlas ČSÚ, 1km grid SLDB 2021 (vrstvy 15948, 25948, 245948, 175948) pro obálku Liberce |
| `telefony_vo.txt` | text PDF „Telefonní čísla do volebních místností“ z liberec.cz |

```bash
python scripts/liberec.py dl data                 # ~3 min (bootstrap ekologické inference)
python scripts/doplnky.py dl dl_liberec data      # části města, školy, senioři, demografie, kontrola dat, kuriozity, statutární města (~3 min)
```

Zdroje: ČSÚ – [volby.gov.cz](https://volby.gov.cz/opendata/opendata.htm), ČÚZK – RÚIAN, MPSV – registr poskytovatelů sociálních služeb,
statutární město Liberec (portály zápisů, OZV č. 1/2025, seznam volebních místností), Statistický atlas ČSÚ, podkladové mapy © Esri.

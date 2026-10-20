"""Bezpečný zápis JSON: NaN a ±inf → null (prohlížeč jinak celý data.json odmítne)."""
import json, math


def _clean(o):
    if isinstance(o, float):
        return None if math.isnan(o) or math.isinf(o) else o
    if isinstance(o, dict):
        return {k: _clean(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_clean(v) for v in o]
    if hasattr(o, 'item') and not isinstance(o, (str, bytes)):  # numpy skalár
        return _clean(o.item())
    return o


def save(obj, path, **kw):
    kw.setdefault('ensure_ascii', False)
    if 'indent' not in kw:
        kw.setdefault('separators', (',', ':'))
    with open(path, 'w', encoding='utf8') as f:
        json.dump(_clean(obj), f, allow_nan=False, **kw)

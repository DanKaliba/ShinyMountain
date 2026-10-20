"""Přepočet mandátů v zastupitelstvech obcí (zákon o volbách do zastupitelstev obcí) a mandátové hrany."""


def allocate(votes, ncands, seats):
    """Mandáty: 5% klauzule s přepočtem pro neúplné kandidátky, D'Hondt, strop počtem kandidátů.

    votes, ncands: {kandidátka: hlasy / počet kandidátů}; vrací {kandidátka: mandáty}.
    """
    adj = {p: (v / ncands[p] * seats if ncands[p] < seats else v) for p, v in votes.items()}
    tot = sum(adj.values())
    ok = [p for p in votes if tot and adj[p] / tot * 100 >= 5]
    s = {p: 0 for p in votes}
    q = sorted([(votes[p] / d, votes[p], p) for p in ok for d in range(1, seats + 1)], reverse=True)
    for _, _, p in q:
        if sum(s.values()) == seats:
            break
        if s[p] < ncands[p]:
            s[p] += 1
    return s


def margins(votes, ncands, seats, party):
    """(mandáty, kolik hlasů navíc dá další mandát, o kolik hlasů může kandidátka přijít bez ztráty mandátu); ostatní beze změny."""
    base = allocate(votes, ncands, seats)[party]

    def with_(x):
        v = dict(votes)
        v[party] = max(v[party] + x, 0)
        return allocate(v, ncands, seats)[party]
    lo, hi = 0, max(votes.values()) * 2
    while hi - lo > 1:
        mid = (lo + hi) // 2
        lo, hi = (lo, mid) if with_(mid) > base else (mid, hi)
    plus = hi
    lo, hi = 0, votes[party] + 1
    while hi - lo > 1:
        mid = (lo + hi) // 2
        lo, hi = (mid, hi) if with_(-mid) >= base else (lo, mid)
    return base, plus, lo


def votes_needed(votes, ncands, seats, party, target, changes=None, limit=20000):
    """Nejmenší počet hlasů navíc pro `party`, se kterým má `target` mandátů (s volitelnými změnami jiných kandidátek)."""
    def seats_with(a):
        v = dict(votes)
        for k, d in (changes or {}).items():
            v[k] = max(v[k] + d, 0)
        v[party] += a
        return allocate(v, ncands, seats)[party]
    lo, hi = -1, limit
    if seats_with(hi) < target:
        return None
    while hi - lo > 1:
        mid = (lo + hi) // 2
        lo, hi = (lo, mid) if seats_with(mid) >= target else (mid, hi)
    return hi

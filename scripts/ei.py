"""Ekologická inference – Goodmanova regrese s omezeními (jen numpy).

Y ≈ X · B, kde řádky X a Y jsou složení jednotek (okrsků) a B je matice přesunů
s řádky na simplexu (každý řádek ≥ 0 a součet 1). Řeší se projekcí gradientu.
Bootstrap používá stejný počet iterací jako hlavní odhad, aby intervaly odpovídaly bodovému odhadu.
"""
import numpy as np

ITERS = 6000


def proj_rows(V):
    """Projekce každého řádku matice na pravděpodobnostní simplex."""
    n = V.shape[1]
    U = -np.sort(-V, axis=1)
    css = np.cumsum(U, axis=1) - 1
    cond = U * np.arange(1, n + 1) > css
    rho = n - 1 - np.argmax(cond[:, ::-1], axis=1)
    theta = css[np.arange(len(V)), rho] / (rho + 1)
    return np.maximum(V - theta[:, None], 0)


def fit(X, Y, w, iters=ITERS):
    X, Y = np.asarray(X, float), np.asarray(Y, float)
    W = np.sqrt(np.asarray(w, float) / np.mean(w))[:, None]
    Xw, Yw = X * W, Y * W
    B = np.tile(Y.mean(0), (X.shape[1], 1))
    step = 1 / np.linalg.norm(Xw.T @ Xw, 2)
    for _ in range(iters):
        B = proj_rows(B - step * (Xw.T @ (Xw @ B - Yw)))
    return B


def bootstrap(X, Y, w, rng, n=200, iters=ITERS, lam=None, B0=None):
    X, Y, w = np.asarray(X, float), np.asarray(Y, float), np.asarray(w, float)
    out = []
    for _ in range(n):
        ix = rng.integers(0, len(X), len(X))
        out.append(fit(X[ix], Y[ix], w[ix], iters=iters) if lam is None else fit_shrink(X[ix], Y[ix], w[ix], lam, B0, iters=iters))
    return np.array(out)


# ---------------------------------------------------------------- smrštění k neutrálnímu výchozímu bodu
def neutral_prior(X, Y, w):
    """Výchozí bod bez informace: každá kategorie 2022 se rozdělí podle celkového složení 2026."""
    y = np.average(np.asarray(Y, float), axis=0, weights=np.asarray(w, float))
    return np.tile(y / y.sum(), (np.asarray(X).shape[1], 1))


def fit_shrink(X, Y, w, lam, B0, iters=ITERS):
    """Goodman s omezeními + penalizace lam·||B − B0||² (lam je relativní k velikosti dat)."""
    X, Y = np.asarray(X, float), np.asarray(Y, float)
    W = np.sqrt(np.asarray(w, float) / np.mean(w))[:, None]
    Xw, Yw = X * W, Y * W
    scale = (Xw ** 2).sum() / X.shape[1]
    pen = lam * scale
    B = np.array(B0, float).copy()
    step = 1 / (np.linalg.norm(Xw.T @ Xw, 2) + pen)
    for _ in range(iters):
        B = proj_rows(B - step * (Xw.T @ (Xw @ B - Yw) + pen * (B - B0)))
    return B


def cv_lambda(X, Y, w, grid, rng, k=5, repeats=2, iters=3000):
    """Křížová validace přes okrsky: vrátí λ s nejmenší váženou chybou predikce na vynechaných okrscích."""
    X, Y, w = np.asarray(X, float), np.asarray(Y, float), np.asarray(w, float)
    err = {lam: 0.0 for lam in grid}
    for _ in range(repeats):
        folds = rng.permutation(len(X)) % k
        for f in range(k):
            tr, te = folds != f, folds == f
            B0 = neutral_prior(X[tr], Y[tr], w[tr])
            for lam in grid:
                B = fit(X[tr], Y[tr], w[tr], iters=iters) if lam == 0 else fit_shrink(X[tr], Y[tr], w[tr], lam, B0, iters=iters)
                err[lam] += float((w[te][:, None] * (X[te] @ B - Y[te]) ** 2).sum())
    best = min(err, key=err.get)
    return best, {str(l): e for l, e in err.items()}

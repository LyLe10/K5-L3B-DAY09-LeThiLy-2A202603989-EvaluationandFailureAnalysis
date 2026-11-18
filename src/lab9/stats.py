"""Statistics students implement (M2 judge calibration, M4 paired bootstrap).

Rules: a judge is a classifier -- measure it like one. A higher mean is not
"better" until the paired CI of the difference excludes 0.
Reference values to self-check are in tests/test_lab9_stats.py.
"""

from __future__ import annotations

from collections.abc import Sequence

POS = "FAIL"   # the judge's job is to FIND failures, so FAIL is the positive class


def confusion(human: Sequence[str], judge: Sequence[str]) -> dict[str, int]:
    """tp/fp/fn/tn with FAIL as positive."""
    if len(human) != len(judge):
        raise ValueError("human and judge must have equal lengths")
    result = {"tp": 0, "fp": 0, "fn": 0, "tn": 0}
    for h, j in zip(human, judge):
        if h not in ("PASS", "FAIL") or j not in ("PASS", "FAIL"):
            raise ValueError("labels must be PASS or FAIL")
        key = "tp" if h == POS and j == POS else (
            "fn" if h == POS else "fp" if j == POS else "tn")
        result[key] += 1
    return result


def precision_recall(human: Sequence[str], judge: Sequence[str]) -> tuple[float, float]:
    cm = confusion(human, judge)
    tp, fp, fn = cm["tp"], cm["fp"], cm["fn"]
    return (tp / (tp + fp) if tp + fp else 0.0,
            tp / (tp + fn) if tp + fn else 0.0)


def cohen_kappa(human: Sequence[str], judge: Sequence[str]) -> float:
    """kappa = (p_o - p_e) / (1 - p_e). Raise ValueError when undefined (p_e == 1):
    a constant judge has no signal and must FAIL calibration, not pass on a technicality."""
    cm = confusion(human, judge)
    tp, fp, fn, tn = (cm[k] for k in ("tp", "fp", "fn", "tn"))
    n = tp + fp + fn + tn
    if n == 0:
        raise ValueError("kappa is undefined for empty inputs")
    observed = (tp + tn) / n
    expected = ((tp + fn) * (tp + fp) + (tn + fp) * (tn + fn)) / (n * n)
    if expected == 1:
        raise ValueError("kappa is undefined when expected agreement is 1")
    return (observed - expected) / (1 - expected)


def rogan_gladen(observed_rate: float, sensitivity: float, specificity: float) -> float:
    """Correct an observed failure rate for judge error; clip to [0, 1]."""
    denominator = sensitivity + specificity - 1
    if denominator == 0:
        raise ValueError("Rogan-Gladen correction is undefined when sensitivity + specificity is 1")
    return max(0.0, min(1.0, (observed_rate + specificity - 1) / denominator))


def paired_bootstrap(a: Sequence[float], b: Sequence[float], *, n_resamples: int = 1000,
                     rng: int = 2027, confidence: float = 0.95) -> tuple[float, float, float]:
    """a[i], b[i] = per-item mean over seeds, SAME items, SAME order.
    Return (mean(a)-mean(b), lo, hi) with scipy.stats.bootstrap(paired=True, method="percentile",
    rng=numpy.random.default_rng(rng)). If a == b everywhere return (0.0, 0.0, 0.0)."""
    import numpy as np
    from scipy.stats import bootstrap

    x = np.asarray(a, dtype=float)
    y = np.asarray(b, dtype=float)
    if x.ndim != 1 or y.ndim != 1 or len(x) != len(y) or len(x) == 0:
        raise ValueError("paired samples must be nonempty, one-dimensional and equal length")
    if not np.isfinite(x).all() or not np.isfinite(y).all():
        raise ValueError("paired samples must contain finite numbers")
    if n_resamples <= 0 or not 0 < confidence < 1:
        raise ValueError("invalid bootstrap parameters")
    if np.array_equal(x, y):
        return 0.0, 0.0, 0.0
    if len(x) < 2:
        raise ValueError("bootstrap needs at least two paired observations")
    delta = float(np.mean(x) - np.mean(y))
    interval = bootstrap((x, y), lambda u, v, axis: np.mean(u - v, axis=axis),
                         paired=True, vectorized=True, method="percentile",
                         n_resamples=n_resamples, confidence_level=confidence,
                         rng=np.random.default_rng(rng)).confidence_interval
    return delta, float(interval.low), float(interval.high)


def pass_at_k(n: int, c: int, k: int) -> float:
    """Probability that AT LEAST ONE of k trials drawn from n (c of them passing) passes.
    Unbiased estimator (Chen et al. 2021): 1 - C(n-c, k) / C(n, k). Raise ValueError if k > n."""
    from math import comb

    if any(type(v) is not int for v in (n, c, k)) or n < 1 or not 0 <= c <= n or not 1 <= k <= n:
        raise ValueError("expected integer n >= 1, 0 <= c <= n, and 1 <= k <= n")
    total = comb(n, k)
    failures = comb(n - c, k) if k <= n - c else 0
    return (total - failures) / total


def pass_hat_k(n: int, c: int, k: int) -> float:
    """pass^k (tau-bench, Yao et al. 2024): probability that ALL k trials drawn from n pass.
    Unbiased estimator: C(c, k) / C(n, k). Raise ValueError if k > n.
    pass^k <= pass@1 <= pass@k; a reliable agent keeps pass^k close to pass@1."""
    from math import comb

    if any(type(v) is not int for v in (n, c, k)) or n < 1 or not 0 <= c <= n or not 1 <= k <= n:
        raise ValueError("expected integer n >= 1, 0 <= c <= n, and 1 <= k <= n")
    return comb(c, k) / comb(n, k) if c >= k else 0.0

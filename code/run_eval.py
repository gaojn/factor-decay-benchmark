#!/usr/bin/env python3
"""Rank six decay indicators on noise taken from the 100 simulated excess curves."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import norm

OUT = Path(__file__).resolve().parents[1] / "data"
ANN = 244.0
WARMUP = 504
TAU = 756
T = 2200
D = 488
ARL0_TARGET = 1220
IR = 1.0
BLOCK = 21
N_CAL = 400
N_EVAL = 250
SEED = 20260923

NAMES = ["CUSUM", "CUSUM_EWMA", "RollT252", "SignRate12", "Drawdown", "Kalman"]


def highpass(eps: np.ndarray, win: int = 756) -> np.ndarray:
    df = pd.DataFrame(eps)
    mu = df.rolling(win, center=True, min_periods=252).mean()
    return (df - mu).fillna(0.0).to_numpy()


def boot_paths(pool: np.ndarray, n: int, length: int, rng: np.random.Generator) -> np.ndarray:
    """pool: (n_series, n_time). Block-bootstrap each path from a random series."""
    n_series, n_time = pool.shape
    out = np.empty((n, length))
    usable = n_time - BLOCK
    for i in range(n):
        series = pool[int(rng.integers(0, n_series))]
        pos = 0
        while pos < length:
            s = int(rng.integers(0, usable))
            take = min(BLOCK, length - pos)
            out[i, pos : pos + take] = series[s : s + take]
            pos += take
    return out


def alpha_path(kind: str, mu: float, length: int, tau: int, rng: np.random.Generator) -> np.ndarray:
    a = np.full(length, mu)
    if kind == "H":
        return a
    if kind == "N":
        return np.zeros(length)
    if kind == "D0":
        a[tau:] = 0.0
    elif kind == "Dhalf":
        a[tau:] = 0.5 * mu
    elif kind == "A":
        span = 400
        for t in range(tau, length):
            w = min(1.0, (t - tau) / span)
            a[t] = mu * (1 - 0.5 * w)
    elif kind == "C":
        # bad spells of 126 days at -0.5 mu, good spells of 378 days, start bad at tau
        t = tau
        bad = True
        while t < length:
            span = 126 if bad else 378
            if bad:
                a[t : t + span] = -0.5 * mu
            t += span
            bad = not bad
    elif kind == "E":
        a[tau:] = mu - 0.6 * mu  # IR drop of 0.6, since mu scales with IR
    elif kind == "Hvol":
        pass
    return a


def make_panel(noise: np.ndarray, kind: str, rng: np.random.Generator) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    n, length = noise.shape
    # scale noise to unit then to each path sigma, but noise already has its own scale.
    # Re-standardize each path to its own sigma so IR is exact, keep the shape.
    sig = noise.std(axis=1)
    sig = np.maximum(sig, 1e-8)
    z = noise / sig[:, None]
    mu = IR * sig / np.sqrt(ANN)
    if kind == "N":
        mu = np.zeros(n)  # placeholder; alpha is 0, sigma still sig
        # use a reference mu equal to IR=1 scale for loss denominators of N? N is not scored by L.
        mu_ref = IR * sig / np.sqrt(ANN)
    else:
        mu_ref = mu
    alpha = np.vstack([alpha_path(kind, mu_ref[i], length, TAU, rng) for i in range(n)])
    x = alpha + z * sig[:, None]
    if kind == "Hvol":
        x = x.copy()
        x[:, TAU:] = alpha[:, TAU:] + 2.0 * (z[:, TAU:] * sig[:, None])
    return x, alpha, mu_ref


def first_alarm(score: np.ndarray, thr: float, warmup: int) -> np.ndarray:
    """score: (n, T), alarm when score > thr. Return index or -1."""
    above = score[:, warmup:] > thr
    hit = above.any(axis=1)
    idx = np.argmax(above, axis=1) + warmup
    return np.where(hit, idx, -1).astype(int)


def rolling_t_score(x: np.ndarray, win: int = 252) -> np.ndarray:
    n, length = x.shape
    c = np.cumsum(x, axis=1)
    c2 = np.cumsum(x * x, axis=1)
    score = np.zeros_like(x)
    for t in range(win, length):
        s = c[:, t] - c[:, t - win]
        s2 = c2[:, t] - c2[:, t - win]
        mean = s / win
        var = s2 / win - mean ** 2
        var = np.maximum(var, 1e-12)
        tstat = mean / np.sqrt(var / win)
        score[:, t] = -tstat
    return score


def sign_score(x: np.ndarray, month: int = 21, look: int = 12) -> np.ndarray:
    n, length = x.shape
    n_m = length // month
    monthly = x[:, : n_m * month].reshape(n, n_m, month).sum(axis=2)
    down = (monthly < 0).astype(float)
    score = np.zeros_like(x)
    c = np.cumsum(down, axis=1)
    for m in range(look, n_m):
        frac = (c[:, m] - c[:, m - look]) / look
        # assign this month's days
        score[:, m * month : (m + 1) * month] = frac[:, None]
    return score


def drawdown_score(x: np.ndarray, sigma: np.ndarray) -> np.ndarray:
    c = np.cumsum(x, axis=1)
    peak = np.maximum.accumulate(c, axis=1)
    dd = peak - c
    return dd / sigma[:, None]


def cusum_score(x: np.ndarray, sigma: np.ndarray, k: float, ewma: bool) -> np.ndarray:
    n, length = x.shape
    if ewma:
        lam = 1 - 0.5 ** (1 / 60)
        var = np.repeat(sigma ** 2, length).reshape(n, length)
        v = sigma ** 2
        for t in range(1, length):
            v = (1 - lam) * v + lam * x[:, t - 1] ** 2
            var[:, t] = np.maximum(v, 1e-12)
        scale = np.sqrt(var)
    else:
        scale = sigma[:, None]
    z = x / scale
    s = np.zeros(n)
    score = np.zeros_like(x)
    for t in range(length):
        s = np.maximum(0.0, s + k - z[:, t])
        score[:, t] = s
    return score


def kalman_score(x: np.ndarray, sigma: np.ndarray, mu: np.ndarray) -> np.ndarray:
    n, length = x.shape
    v = sigma ** 2
    k_gain = 1.0 / 504.0
    q = (k_gain ** 2) * v / (1 - k_gain)
    m = mu.copy()
    p = v.copy()
    score = np.zeros_like(x)
    half = 0.5 * mu
    for t in range(length):
        p = p + q
        kk = p / (p + v)
        m = m + kk * (x[:, t] - m)
        p = (1 - kk) * p
        z = (half - m) / np.sqrt(np.maximum(p, 1e-18))
        score[:, t] = norm.cdf(z)
    return score


def scores_for(x: np.ndarray, sigma: np.ndarray, mu: np.ndarray) -> dict[str, np.ndarray]:
    k = 0.5 * IR / np.sqrt(ANN)
    return {
        "CUSUM": cusum_score(x, sigma, k, ewma=False),
        "CUSUM_EWMA": cusum_score(x, sigma, k, ewma=True),
        "RollT252": rolling_t_score(x),
        "SignRate12": sign_score(x),
        "Drawdown": drawdown_score(x, sigma),
        "Kalman": kalman_score(x, sigma, mu),
    }


def arl0_of(alarm: np.ndarray, length: int, warmup: int) -> float:
    hit = alarm >= 0
    # censored MLE on post-warmup length
    exposed = np.where(hit, alarm - warmup, length - warmup).astype(float)
    n_hit = hit.sum()
    if n_hit == 0:
        return 1e9
    return float(exposed.sum() / n_hit)


def calibrate(score_fn_paths: dict[str, np.ndarray], length: int) -> dict[str, float]:
    """Binary search one threshold per indicator on healthy scores."""
    thresholds = {}
    for name, score in score_fn_paths.items():
        col = score[:, WARMUP:]
        lo = float(np.quantile(col, 0.01))
        hi = float(np.quantile(col, 0.995))
        if hi <= lo:
            hi = lo + 1.0
        for _ in range(6):
            if arl0_of(first_alarm(score, hi, WARMUP), length, WARMUP) >= ARL0_TARGET:
                break
            hi = hi + max(hi - lo, 0.5)
        best = hi
        for _ in range(22):
            mid = 0.5 * (lo + hi)
            arl = arl0_of(first_alarm(score, mid, WARMUP), length, WARMUP)
            if arl < ARL0_TARGET:
                lo = mid
            else:
                hi = mid
                best = mid
        thresholds[name] = best
        alarm = first_alarm(score, best, WARMUP)
        print(f"  cal {name:12} thr={best:.4f} ARL0={arl0_of(alarm, length, WARMUP):.0f}")
    return thresholds


def summarize(alarm: np.ndarray, alpha: np.ndarray, mu: np.ndarray, kind: str) -> dict:
    n = len(alarm)
    pre = (alarm >= 0) & (alarm < TAU)
    detected = (alarm >= TAU) & (alarm <= TAU + D)
    # conditional on no pre-alarm
    ok = ~pre
    if kind == "N":
        hit = (alarm >= WARMUP) & (alarm <= TAU + D)
        return {
            "n": n,
            "pre_alarm": float(((alarm >= 0) & (alarm < WARMUP)).mean()),
            "hit_2y": float(hit.mean()),
            "delay_med": None,
            "loss_mean": None,
        }
    if kind in ("H", "Hvol"):
        fa = detected[ok].mean() if ok.any() else 0.0
        return {
            "n": int(ok.sum()),
            "pre_alarm": float(pre.mean()),
            "hit_2y": float(fa),
            "delay_med": None,
            "loss_mean": None,
        }
    if ok.sum() == 0:
        return {"n": 0, "pre_alarm": 1.0, "hit_2y": None, "delay_med": None, "loss_mean": None}
    delays = []
    losses = []
    for i in np.where(ok)[0]:
        end = TAU + D
        if alarm[i] >= 0:
            end = min(alarm[i], TAU + D)
            if alarm[i] <= TAU + D:
                delays.append(int(alarm[i] - TAU))
        seg = mu[i] - alpha[i, TAU:end]
        losses.append(float(seg.sum() / (ANN * mu[i])))
    hit = len(delays) / ok.sum()
    return {
        "n": int(ok.sum()),
        "pre_alarm": float(pre.mean()),
        "hit_2y": float(hit),
        "delay_med": float(np.median(delays)) if delays else None,
        "loss_mean": float(np.mean(losses)),
    }


def shock_test(excess: pd.DataFrame, lam: np.ndarray, dev_end: int) -> dict:
    """Real Feb 2024 common crash: how many factors alarm within 63 days."""
    dates = excess.index
    loc = dates.get_indexer([pd.Timestamp("2024-02-05")], method="nearest")[0]
    start = loc - 756
    window = excess.iloc[start : loc + 63].to_numpy()
    f = excess.mean(axis=1).to_numpy()
    resid = excess.to_numpy() - np.outer(f, lam)
    resid_w = resid[start : loc + 63]
    out = {}
    for label, panel in (("raw", window), ("stripped", resid_w)):
        sigma = panel[:252].std(axis=0)
        mu = IR * sigma / np.sqrt(ANN)  # reference only; series keeps its own mean
        # run CUSUM with sigma from first 252 days; k uses IR=1 reference
        k = 0.5 * IR / np.sqrt(ANN)
        score = cusum_score(panel.T, sigma, k, ewma=False)  # wait panel is (T, N)
        # fix: cusum expects (n, T)
        score = cusum_score(panel.T if False else panel.transpose(1, 0), sigma, k, ewma=True)
        # Use threshold later; count with a fixed h from calibration passed in by caller
        out[label] = score
    return out


def main() -> None:
    rng = np.random.default_rng(SEED)
    excess = pd.read_parquet(OUT / "excess_wide.parquet")
    dates = excess.index
    x = excess.to_numpy()  # (T, N)
    t_len, n_fac = x.shape
    dev_end = t_len // 2
    f = x.mean(axis=1)
    # loadings on dev only
    var_f = np.var(f[:dev_end])
    lam = np.array([np.cov(x[:dev_end, i], f[:dev_end])[0, 1] / var_f for i in range(n_fac)])
    eps = x - np.outer(f, lam)
    noise = highpass(eps)
    # drop burn-in of the filter
    dev_pool = noise[252:dev_end].T  # (N, time)
    test_pool = noise[dev_end + 252 :].T
    print("pools", dev_pool.shape, test_pool.shape, "median |lambda|", float(np.median(np.abs(lam))))

    print("calibrating on healthy paths from the first half of the noise")
    healthy_noise = boot_paths(dev_pool, N_CAL, T, rng)
    x_h, a_h, mu_h = make_panel(healthy_noise, "H", rng)
    sigma_h = x_h[:, :252].std(axis=1)
    sc_h = scores_for(x_h, sigma_h, mu_h)
    thr = calibrate(sc_h, T)

    kinds = ["H", "N", "D0", "Dhalf", "A", "C", "Hvol", "E"]
    rows = []
    for kind in kinds:
        print("eval", kind)
        nz = boot_paths(test_pool, N_EVAL, T, rng)
        xx, aa, mu = make_panel(nz, kind, rng)
        sigma = xx[:, :252].std(axis=1)
        sc = scores_for(xx, sigma, mu)
        for name in NAMES:
            alarm = first_alarm(sc[name], thr[name], WARMUP)
            stat = summarize(alarm, aa, mu, kind)
            stat.update({"kind": kind, "indicator": name})
            rows.append(stat)
            print(f"  {name:12} hit={stat['hit_2y']} delay={stat['delay_med']} loss={stat['loss_mean']} pre={stat['pre_alarm']:.2f}")

    # common shock on the real February 2024 window, CUSUM_EWMA threshold
    loc = dates.get_indexer([pd.Timestamp("2024-02-05")], method="nearest")[0]
    start = max(0, loc - 756)
    raw = x[start : loc + 63]
    stripped = (x - np.outer(f, lam))[start : loc + 63]
    shock = {}
    h = thr["CUSUM_EWMA"]
    for label, panel in (("raw", raw), ("stripped", stripped)):
        pan = panel.T  # (N, T)
        sigma = pan[:, :252].std(axis=1)
        mu = IR * sigma / np.sqrt(ANN)
        score = cusum_score(pan, sigma, 0.5 * IR / np.sqrt(ANN), ewma=True)
        # alarm in the last 63 days
        tail = score[:, -63:]
        n_alarm = int((tail.max(axis=1) > h).sum())
        shock[label] = n_alarm
        print("shock", label, n_alarm)

    df = pd.DataFrame(rows)
    df.to_csv(OUT / "eval_scores.csv", index=False)
    payload = {"thresholds": thr, "shock_feb2024_cusum_ewma": shock, "rows": rows,
               "settings": {"ARL0": ARL0_TARGET, "IR": IR, "N_CAL": N_CAL, "N_EVAL": N_EVAL,
                            "warmup": WARMUP, "tau": TAU, "T": T, "D": D}}
    (OUT / "eval_results.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2))
    print("wrote eval_scores.csv")


if __name__ == "__main__":
    main()

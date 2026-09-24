#!/usr/bin/env python3
"""Simulate 100 optimizer NAV curves and matching daily excess curves.

excess_t = portfolio_return_t - benchmark_return_t
nav_t = nav_{t-1} * (1 + portfolio_return_t)

The embedded alpha is saved in sim_truth.parquet for audit only.
The evaluation dataset injects its own labels on top of these curves.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

OUT = Path(__file__).resolve().parents[1] / "data"
SEED = 20260923
N = 100
NU = 5
ANN = 244
START_NAV = 1.0


def garch_t(rng: np.random.Generator, length: int, a: float = 0.06, b: float = 0.92) -> np.ndarray:
    z = rng.standard_t(NU, size=length) * np.sqrt((NU - 2) / NU)
    sig2 = np.empty(length)
    sig2[0] = 1.0
    for t in range(1, length):
        sig2[t] = (1 - a - b) + a * (sig2[t - 1] * z[t - 1] ** 2) + b * sig2[t - 1]
        sig2[t] = min(sig2[t], 25.0)
    return np.sqrt(sig2) * z


def crash(level: np.ndarray, dates: pd.DatetimeIndex, day: str, total: float, span: int = 3) -> None:
    start = dates.get_indexer([pd.Timestamp(day)], method="nearest")[0]
    start = int(np.clip(start, 0, len(dates) - span))
    level[start : start + span] += total / span


def main() -> None:
    rng = np.random.default_rng(SEED)
    dates = pd.bdate_range("2015-01-05", "2025-12-31")
    t_len = len(dates)

    r_bench = 0.08 / ANN + (0.18 / np.sqrt(ANN)) * garch_t(rng, t_len)
    crash(r_bench, dates, "2015-06-26", -0.12, 4)
    crash(r_bench, dates, "2016-01-04", -0.08, 2)
    crash(r_bench, dates, "2024-02-05", -0.06, 3)

    f = (0.0035) * garch_t(rng, t_len)
    crash(f, dates, "2015-06-26", -0.025, 4)
    crash(f, dates, "2016-01-07", -0.015, 2)
    crash(f, dates, "2024-02-05", -0.030, 5)

    lam = rng.normal(0.8, 0.25, size=N)
    sigma_e = rng.uniform(0.0035, 0.0065, size=N)

    # 40 steady, 20 half-decay, 15 step-to-zero, 15 never, 10 regime
    order = np.arange(N)
    rng.shuffle(order)
    groups = {
        "steady": order[:40],
        "half": order[40:60],
        "step0": order[60:75],
        "never": order[75:90],
        "regime": order[90:],
    }
    ir0 = np.zeros(N)
    ir0[groups["steady"]] = rng.uniform(0.4, 1.3, size=40)
    ir0[groups["half"]] = rng.uniform(0.6, 1.2, size=20)
    ir0[groups["step0"]] = rng.uniform(0.6, 1.2, size=15)
    ir0[groups["regime"]] = rng.uniform(0.5, 1.1, size=10)

    tau = np.full(N, -1)
    for idx in groups["half"]:
        tau[idx] = int(rng.integers(750, 1800))
    for idx in groups["step0"]:
        tau[idx] = int(rng.integers(750, 1800))
    for idx in groups["regime"]:
        tau[idx] = int(rng.integers(600, 1400))

    alpha = np.zeros((t_len, N))
    sim_type = np.array(["steady"] * N, dtype=object)
    for name, idxs in groups.items():
        sim_type[idxs] = name
    for i in range(N):
        mu = ir0[i] * sigma_e[i] / np.sqrt(ANN)
        if sim_type[i] == "never":
            continue
        if sim_type[i] == "steady":
            alpha[:, i] = mu
        elif sim_type[i] == "half":
            path = np.full(t_len, mu)
            path[tau[i] :] = 0.5 * mu
            alpha[:, i] = path
        elif sim_type[i] == "step0":
            path = np.full(t_len, mu)
            path[tau[i] :] = 0.0
            alpha[:, i] = path
        else:
            path = np.full(t_len, mu)
            bad = False
            left = 0
            t = tau[i]
            while t < t_len:
                span = int(rng.integers(80, 180)) if bad else int(rng.integers(200, 450))
                if bad:
                    path[t : t + span] = -0.4 * mu
                t += span
                bad = not bad
            alpha[:, i] = path

    e = np.column_stack([sigma_e[i] * garch_t(rng, t_len, a=0.05, b=0.93) for i in range(N)])
    excess = alpha + f[:, None] * lam[None, :] + e
    r_port = r_bench[:, None] + excess

    nav_b = np.empty(t_len)
    nav_p = np.empty((t_len, N))
    nav_b[0] = START_NAV
    nav_p[0] = START_NAV
    for t in range(1, t_len):
        nav_b[t] = nav_b[t - 1] * (1.0 + r_bench[t])
        nav_p[t] = nav_p[t - 1] * (1.0 + r_port[t])

    factor_id = np.array([f"F{i:03d}" for i in range(N)])
    date_col = np.repeat(dates.values, N)
    fid_col = np.tile(factor_id, t_len)

    curves = pd.DataFrame(
        {
            "date": date_col,
            "factor_id": fid_col,
            "nav": nav_p.reshape(-1),
            "excess": excess.reshape(-1),
            "port_return": r_port.reshape(-1),
        }
    )
    benchmark = pd.DataFrame({"date": dates, "nav": nav_b, "benchmark_return": r_bench, "common_factor": f})
    truth = pd.DataFrame(
        {
            "factor_id": factor_id,
            "sim_type": sim_type,
            "ir_start": ir0,
            "tau_index": tau,
            "tau_date": [dates[k] if k >= 0 else pd.NaT for k in tau],
            "lambda": lam,
            "sigma_e": sigma_e,
        }
    )

    # Reconstruction check: excess == port_return - benchmark_return
    merged_b = r_bench[np.repeat(np.arange(t_len), N)]
    gap = np.max(np.abs(curves["excess"].to_numpy() - (curves["port_return"].to_numpy() - merged_b)))
    if gap > 1e-12:
        raise SystemExit(f"excess identity failed: {gap}")

    curves.to_parquet(OUT / "curves.parquet", index=False)
    benchmark.to_parquet(OUT / "benchmark.parquet", index=False)
    truth.to_parquet(OUT / "sim_truth.parquet", index=False)
    truth.to_csv(OUT / "sim_truth.csv", index=False)

    # Wide NAV and excess for direct viewing (date x factor)
    nav_wide = pd.DataFrame(nav_p, index=dates, columns=factor_id)
    nav_wide.index.name = "date"
    ex_wide = pd.DataFrame(excess, index=dates, columns=factor_id)
    ex_wide.index.name = "date"
    nav_wide.to_parquet(OUT / "nav_wide.parquet")
    ex_wide.to_parquet(OUT / "excess_wide.parquet")

    # Cross-sectional correlation on a quiet year
    quiet = (dates >= "2019-01-01") & (dates <= "2019-12-31")
    corr = np.corrcoef(excess[quiet].T)
    iu = np.triu_indices(N, k=1)
    med_corr = float(np.median(corr[iu]))

    manifest = {
        "seed": SEED,
        "n_factors": N,
        "n_days": int(t_len),
        "start": str(dates[0].date()),
        "end": str(dates[-1].date()),
        "calendar": "weekdays, not the exchange holiday calendar",
        "nav_start": START_NAV,
        "excess_identity_max_abs_error": gap,
        "median_pairwise_excess_corr_2019": med_corr,
        "files": {
            "curves.parquet": "long: date, factor_id, nav, excess, port_return",
            "nav_wide.parquet": "100 NAV curves, columns F000-F099",
            "excess_wide.parquet": "100 daily excess curves",
            "benchmark.parquet": "benchmark nav and return, plus the common active factor",
            "sim_truth.parquet": "simulator audit; not an evaluation label",
        },
    }
    raw = json.dumps(manifest, ensure_ascii=False, indent=2).encode()
    (OUT / "manifest.json").write_bytes(raw)
    digest = hashlib.sha256((OUT / "curves.parquet").read_bytes()).hexdigest()
    manifest["curves_sha256"] = digest
    (OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2))

    print(json.dumps({k: manifest[k] for k in ("n_days", "start", "end", "median_pairwise_excess_corr_2019", "excess_identity_max_abs_error")}, ensure_ascii=False))
    print(truth.groupby("sim_type").size().to_string())
    print("nav_end_median", float(np.median(nav_p[-1])))
    print("bench_end", float(nav_b[-1]))


if __name__ == "__main__":
    main()

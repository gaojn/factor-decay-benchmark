#!/usr/bin/env python3
"""Day-by-day decay judgment for one excess curve.

The daily result is weak_today: the past 252 days have t < -threshold.
It uses only data up to that day, and it can turn off on a later day.

A latched CUSUM is also written to the csv as cusum_latched. On these raw
curves that latch stays on for 37 of 40 healthy series, so it is not the
judgment shown in the report.

  python3 code/daily_judge.py
  python3 code/daily_judge.py --factor F000
  python3 code/daily_judge.py --csv my.csv --date-col date --value-col excess
"""
from __future__ import annotations

import argparse
import html
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_eval import cusum_score, rolling_t_score

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OUT = DATA / "daily"
REPORT = ROOT / "reports" / "单曲线逐日判断.html"

WARMUP = 504
WIN = 252
ANN = 244.0
K = 0.5 / np.sqrt(ANN)
DEMO = ("F000", "F002", "F001")


def load_thresholds() -> tuple[float, float]:
    payload = json.loads((DATA / "eval_results.json").read_text())
    thr = payload["thresholds"]
    return float(thr["CUSUM_EWMA"]), float(thr["RollT252"])


def judge_panel(excess: np.ndarray, thr_cusum: float, thr_roll: float) -> dict[str, np.ndarray]:
    """excess: (n, T). Scores use only the past. Sigma is frozen from the first 252 days."""
    n, length = excess.shape
    if length <= WARMUP:
        raise SystemExit(f"need more than {WARMUP} days, got {length}")
    sigma = excess[:, :WIN].std(axis=1)
    sigma = np.maximum(sigma, 1e-8)
    cusum = cusum_score(excess, sigma, K, ewma=True)
    roll = rolling_t_score(excess, WIN)  # -t ; larger means weaker
    weak = np.zeros((n, length), dtype=np.int8)
    crossed = np.zeros((n, length), dtype=np.int8)
    weak[:, WARMUP:] = (roll[:, WARMUP:] > thr_roll).astype(np.int8)
    crossed[:, WARMUP:] = (cusum[:, WARMUP:] > thr_cusum).astype(np.int8)
    alarm = np.maximum.accumulate(crossed, axis=1)
    tstat = -roll
    return {"sigma": sigma, "cusum": cusum, "roll_t": tstat, "weak_today": weak, "alarm": alarm}


def first_on(flag: np.ndarray) -> int:
    hit = np.flatnonzero(flag)
    return int(hit[0]) if len(hit) else -1


def frame_one(dates: pd.DatetimeIndex, excess: np.ndarray, judged: dict[str, np.ndarray], i: int) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": dates,
            "excess": excess[i],
            "cum_excess": np.cumsum(excess[i]),
            "roll_t": judged["roll_t"][i],
            "cusum": judged["cusum"][i],
            "weak_today": judged["weak_today"][i],
            "cusum_latched": judged["alarm"][i],
        }
    )


def load_curve_csv(path: Path, date_col: str, value_col: str) -> tuple[pd.DatetimeIndex, np.ndarray]:
    df = pd.read_csv(path)
    if date_col not in df.columns or value_col not in df.columns:
        raise SystemExit(f"columns needed: {date_col}, {value_col}; got {list(df.columns)}")
    df[date_col] = pd.to_datetime(df[date_col])
    df = df.sort_values(date_col)
    values = df[value_col].to_numpy(dtype=float)
    if np.isnan(values).any():
        raise SystemExit("excess column has missing values")
    return pd.DatetimeIndex(df[date_col]), values.reshape(1, -1)


def summarize(ids: list[str], dates: pd.DatetimeIndex, judged: dict[str, np.ndarray], truth: pd.DataFrame) -> pd.DataFrame:
    rows = []
    truth = truth.set_index("factor_id")
    for i, fid in enumerate(ids):
        alarm_i = first_on(judged["alarm"][i])
        meta = truth.loc[fid]
        tau = int(meta["tau_index"])
        weak = judged["weak_today"][i]
        if tau < 0:
            weak_before = float(weak[WARMUP:].mean())
            weak_after = np.nan
        else:
            weak_before = float(weak[WARMUP:tau].mean()) if tau > WARMUP else np.nan
            weak_after = float(weak[tau:].mean())
        row = {
            "factor_id": fid,
            "sim_type": meta["sim_type"],
            "tau_date": "" if tau < 0 else str(pd.Timestamp(meta["tau_date"]).date()),
            "alarm_date": "" if alarm_i < 0 else str(dates[alarm_i].date()),
            "delay_days": "" if tau < 0 or alarm_i < 0 else int(alarm_i - tau),
            "early": int(tau >= 0 and 0 <= alarm_i < tau),
            "weak_before": weak_before,
            "weak_after": weak_after,
            "weak_days": int(weak.sum()),
        }
        rows.append(row)
    return pd.DataFrame(rows)


def _runs(flag: np.ndarray) -> list[tuple[int, int]]:
    spans = []
    start = None
    for i, v in enumerate(flag):
        if v and start is None:
            start = i
        elif not v and start is not None:
            spans.append((start, i))
            start = None
    if start is not None:
        spans.append((start, len(flag)))
    return spans


def _svg(dates: pd.DatetimeIndex, cum: np.ndarray, roll_t: np.ndarray, weak: np.ndarray, tau: int, thr_roll: float) -> str:
    width, height = 980, 400
    left, right, top = 58, 16, 18
    plot_h = 230
    inner_w = width - left - right
    n = len(cum)
    y = cum * 100
    y0, y1 = float(y.min()), float(y.max())
    pad = max(2.0, 0.08 * (y1 - y0 if y1 > y0 else 1))
    y0 -= pad
    y1 += pad

    def X(i: float) -> float:
        return left + inner_w * (i / max(n - 1, 1))

    def Y(v: float) -> float:
        return top + plot_h * (1 - (v - y0) / (y1 - y0))

    pts = " ".join(f"{X(i):.1f},{Y(v):.1f}" for i, v in enumerate(y))
    shade = []
    for a, b in _runs(weak):
        shade.append(
            f'<rect x="{X(a):.1f}" y="{top}" width="{max(X(b - 1) - X(a), 1):.1f}" height="{plot_h}" fill="#f5e4d9"/>'
        )
    if tau >= 0:
        shade.append(
            f'<line x1="{X(tau):.1f}" y1="{top}" x2="{X(tau):.1f}" y2="{top + plot_h}" stroke="#a33f39" stroke-dasharray="4 3"/>'
        )
    zero = Y(0)
    if top <= zero <= top + plot_h:
        shade.append(f'<line x1="{left}" y1="{zero:.1f}" x2="{left + inner_w}" y2="{zero:.1f}" stroke="rgba(24,42,50,.18)"/>')

    ticks = []
    for year in range(dates[0].year, dates[-1].year + 1):
        loc = dates.searchsorted(pd.Timestamp(f"{year}-01-01"))
        if 0 <= loc < n and abs((dates[min(loc, n - 1)] - pd.Timestamp(f"{year}-01-01")).days) < 10:
            ticks.append(f'<text x="{X(loc):.1f}" y="{top + plot_h + 16}" font-size="11" fill="#53636a">{year}</text>')

    # rolling t panel
    t_top = top + plot_h + 62
    t_h = 78
    t0, t1 = -4.0, 4.0

    def TY(v: float) -> float:
        v = min(max(v, t0), t1)
        return t_top + t_h * (1 - (v - t0) / (t1 - t0))

    t_pts = " ".join(f"{X(i):.1f},{TY(v):.1f}" for i, v in enumerate(roll_t))
    thr_y = TY(-thr_roll)
    weak_strip_y = t_top + t_h + 28
    weak_rects = []
    for a, b in _runs(weak):
        weak_rects.append(
            f'<rect x="{X(a):.1f}" y="{weak_strip_y}" width="{max(X(max(b - 1, a)) - X(a), 1):.1f}" height="10" fill="#c66032"/>'
        )

    y_labels = []
    for val in (y0, 0.0, y1):
        if y0 - 1 <= val <= y1 + 1:
            y_labels.append(f'<text x="{left - 8}" y="{Y(val):.1f}" text-anchor="end" font-size="11" fill="#53636a">{val:.0f}</text>')

    return f'''<svg viewBox="0 0 {width} {height}" width="100%" role="img">
      {''.join(shade)}
      <line x1="{left}" y1="{top + plot_h}" x2="{left + inner_w}" y2="{top + plot_h}" stroke="rgba(24,42,50,.35)"/>
      <polyline fill="none" stroke="#0b6f69" stroke-width="1.6" points="{pts}"/>
      {''.join(y_labels)}
      {''.join(ticks)}
      <text x="{left}" y="12" font-size="12" fill="#53636a">累计超额（%）</text>
      <line x1="{left}" y1="{t_top + t_h}" x2="{left + inner_w}" y2="{t_top + t_h}" stroke="rgba(24,42,50,.35)"/>
      <line x1="{left}" y1="{thr_y:.1f}" x2="{left + inner_w}" y2="{thr_y:.1f}" stroke="#c66032" stroke-dasharray="3 3"/>
      <polyline fill="none" stroke="#315c75" stroke-width="1.3" points="{t_pts}"/>
      <text x="{left}" y="{t_top - 6}" font-size="12" fill="#53636a">过去 252 日 t 值（橙虚线 = -{thr_roll:.2f}）</text>
      <text x="8" y="{weak_strip_y + 9}" font-size="11" fill="#53636a">当日偏弱</text>
      <rect x="{left}" y="{weak_strip_y}" width="{inner_w}" height="10" fill="#dceeea"/>
      {''.join(weak_rects)}
    </svg>'''


TYPE_NAME = {
    "step0": "阶跃归零",
    "half": "超额减半",
    "steady": "一直健康",
    "never": "从未有效",
    "regime": "好坏切换",
}


def _pct(series: pd.Series) -> str:
    vals = pd.to_numeric(series, errors="coerce").dropna()
    if len(vals) == 0:
        return "—"
    return f"{100 * float(vals.mean()):.0f}%"


def _spell(weak: np.ndarray, start: int, end: int) -> str:
    if end <= start:
        return "没有可判断的日子"
    rate = 100 * float(weak[start:end].mean())
    best = cur = 0
    for v in weak[start:end]:
        cur = cur + 1 if v else 0
        best = max(best, cur)
    return f"{rate:.0f}% 的交易日偏弱，最长连续 {best} 天"


def build_report(dates, excess_by_id, judged_by_id, truth: pd.DataFrame, summary: pd.DataFrame, thr_cusum: float, thr_roll: float) -> None:
    truth = truth.set_index("factor_id")
    cards = []
    for fid in DEMO:
        j = judged_by_id[fid]
        tau = int(truth.loc[fid, "tau_index"])
        kind = TYPE_NAME.get(str(truth.loc[fid, "sim_type"]), str(truth.loc[fid, "sim_type"]))
        weak = j["weak_today"]
        if tau < 0:
            where = "这条曲线没有埋入失效日。"
            detail = "热身之后，" + _spell(weak, WARMUP, len(weak)) + "。"
        else:
            where = f"埋入失效日是 {pd.Timestamp(truth.loc[fid, 'tau_date']).date()}。"
            detail = (
                "埋入之前，" + _spell(weak, WARMUP, tau) + "。"
                "埋入之后，" + _spell(weak, tau, len(weak)) + "。"
            )
        last_t = float(j["roll_t"][-1])
        last = "当天标成偏弱" if weak[-1] == 1 else "当天不标偏弱"
        figure = _svg(dates, np.cumsum(excess_by_id[fid]), j["roll_t"], weak, tau, thr_roll)
        if tau < 0:
            note = "这条没有红虚线。橙底和底部色带是当天「过去一年偏弱」，可以断开，后一天允许恢复。"
        else:
            note = "红虚线是模拟时埋入的失效日，真实曲线没有这条线。橙底和底部色带是当天「过去一年偏弱」，可以断开，后一天允许恢复。"
        cards.append(f'''
        <section class="card" id="{html.escape(fid)}">
          <h2>{html.escape(fid)} · {html.escape(kind)}</h2>
          <p>{html.escape(where)}{html.escape(detail)}最后一天的一年 t 值是 {last_t:.2f}，{last}。</p>
          {figure}
          <p class="note">{html.escape(note)}</p>
        </section>''')

    steady = summary[summary["sim_type"] == "steady"]
    step = summary[summary["sim_type"] == "step0"]
    half = summary[summary["sim_type"] == "half"]
    never = summary[summary["sim_type"] == "never"]
    steady_latched = int(steady["alarm_date"].astype(str).str.len().gt(0).sum())

    doc = f'''<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>单条超额曲线的逐日判断</title>
<style>
  :root {{
    --paper: #f5f2ea; --paper-deep: #ebe6da;
    --solid: #fffefa; --ink: #182a32; --soft: #53636a; --line: rgba(24,42,50,.14);
    --teal: #0b6f69; --orange: #c66032; --red: #a33f39; --max: 1080px;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0; color: var(--ink); background: var(--paper);
    font-family: "PingFang SC","Hiragino Sans GB","Microsoft YaHei",system-ui,sans-serif;
    font-size: 16.5px; line-height: 1.7;
  }}
  .wrap {{ width: min(calc(100% - 32px), var(--max)); margin: 0 auto; }}
  header {{ padding: 28px 0 8px; }}
  h1 {{ font-size: 32px; line-height: 1.25; margin: 0 0 8px; }}
  h2 {{ font-size: 22px; margin: 0 0 8px; }}
  .sub {{ color: var(--soft); margin: 0; }}
  .card {{
    background: var(--solid); border: 1px solid var(--line); border-radius: 16px;
    padding: 18px 18px 8px; margin: 16px 0 22px;
  }}
  .note {{ color: var(--soft); font-size: 14px; }}
  table {{ border-collapse: collapse; width: 100%; font-size: 15px; }}
  th, td {{ border-bottom: 1px solid var(--line); text-align: left; padding: 8px 10px; }}
  th {{ color: var(--soft); font-weight: 650; }}
  code {{ font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; font-size: 13.5px; }}
</style>
</head>
<body>
<div class="wrap">
  <header>
    <h1>单条超额曲线，每天是否偏弱</h1>
    <p class="sub">只看这一条曲线，不用别的因子。每个交易日只用当天及之前的数据。前 504 个交易日不判断。当天标成偏弱，是指过去 252 个交易日的 t 值低于 -{thr_roll:.2f}。</p>
  </header>
  <section class="card">
    <h2>这一天的 0 和 1 是什么</h2>
    <p>1 表示过去一年整体偏弱，不是「今天的 alpha 变成了 0」。窗口每天往前挪一天，所以这个 1 可以在后面灭掉。</p>
    <p>没有把第一次越线锁死。若用上次校准的波动更新 CUSUM（阈值 {thr_cusum:.2f}）锁死，40 条一直健康的曲线里有 {steady_latched} 条会被标到样本结束。那个结果写在 csv 的 cusum_latched 列里，不作为每天的判断。</p>
    <p class="note">下面三张图用的是模拟曲线，红虚线是生成时埋进去的失效日。换上真实曲线就没有这条线。阈值是在注入信息比 1 的噪声上定的，曲线波动差很多时，同样的 -{thr_roll:.2f} 会偏松或偏紧。</p>
  </section>
  {''.join(cards)}
  <section class="card">
    <h2>同一规则在 100 条模拟曲线上</h2>
    <table>
      <thead><tr><th>模拟类型</th><th>条数</th><th>埋入前，偏弱天数占比</th><th>埋入后，偏弱天数占比</th></tr></thead>
      <tbody>
        <tr><td>一直健康</td><td>{len(steady)}</td><td>{_pct(steady["weak_before"])}</td><td>—</td></tr>
        <tr><td>阶跃归零</td><td>{len(step)}</td><td>{_pct(step["weak_before"])}</td><td>{_pct(step["weak_after"])}</td></tr>
        <tr><td>超额减半</td><td>{len(half)}</td><td>{_pct(half["weak_before"])}</td><td>{_pct(half["weak_after"])}</td></tr>
        <tr><td>从未有效</td><td>{len(never)}</td><td>{_pct(never["weak_before"])}</td><td>—</td></tr>
      </tbody>
    </table>
    <p class="note">健康曲线没有埋入日，第一列是热身之后的整天占比。阶跃归零之后，偏弱的日子明显变多。只减半的时候，埋入前后几乎一样，单靠这一天的 0/1 分不出来。</p>
  </section>
  <section class="card">
    <h2>换一条自己的曲线</h2>
    <p>CSV 至少两列：日期、日超额。日超额是当天组合收益减去基准收益。</p>
    <p><code>python3 code/daily_judge.py --csv 你的文件.csv --date-col date --value-col excess</code></p>
    <p class="note">结果写到 <code>data/daily/</code>。每天的判断是 weak_today。cusum_latched 是上面说的锁死版本，不要把它当成当天是否失效。</p>
  </section>
</div>
</body>
</html>
'''
    REPORT.write_text(doc)


def main() -> None:
    parser = argparse.ArgumentParser(description="Daily decay judgment for one excess curve")
    parser.add_argument("--factor", help="column name in data/excess_wide.parquet, e.g. F000")
    parser.add_argument("--csv", type=Path, help="your own curve")
    parser.add_argument("--date-col", default="date")
    parser.add_argument("--value-col", default="excess")
    args = parser.parse_args()
    thr_cusum, thr_roll = load_thresholds()
    OUT.mkdir(parents=True, exist_ok=True)

    if args.csv is not None:
        dates, panel = load_curve_csv(args.csv, args.date_col, args.value_col)
        judged = judge_panel(panel, thr_cusum, thr_roll)
        out = frame_one(dates, panel, judged, 0)
        dest = OUT / (args.csv.stem + "_daily.csv")
        out.to_csv(dest, index=False)
        weak = judged["weak_today"][0]
        print(f"wrote {dest}")
        print(f"weak_days {int(weak.sum())}  last_weak {int(weak[-1])}  last_t {judged['roll_t'][0, -1]:.2f}")
        return

    wide = pd.read_parquet(DATA / "excess_wide.parquet")
    dates = pd.DatetimeIndex(wide.index)
    ids = list(wide.columns)
    panel = wide.to_numpy().T.astype(float)
    judged = judge_panel(panel, thr_cusum, thr_roll)
    truth = pd.read_csv(DATA / "sim_truth.csv")

    if args.factor is not None:
        if args.factor not in ids:
            raise SystemExit(f"unknown factor {args.factor}")
        i = ids.index(args.factor)
        out = frame_one(dates, panel, judged, i)
        dest = OUT / f"{args.factor}.csv"
        out.to_csv(dest, index=False)
        print(f"wrote {dest}")
        return

    summary = summarize(ids, dates, judged, truth)
    summary.to_csv(OUT / "summary.csv", index=False)
    judged_by_id = {}
    excess_by_id = {}
    for fid in DEMO:
        i = ids.index(fid)
        judged_by_id[fid] = {k: judged[k][i] for k in ("roll_t", "cusum", "weak_today", "alarm")}
        excess_by_id[fid] = panel[i]
        frame_one(dates, panel, judged, i).to_csv(OUT / f"{fid}.csv", index=False)
    build_report(dates, excess_by_id, judged_by_id, truth, summary, thr_cusum, thr_roll)
    print(f"wrote {REPORT}")
    print(summary.groupby("sim_type").size().to_string())
    for kind in ("steady", "step0", "half", "never"):
        sub = summary[summary["sim_type"] == kind]
        alarmed = sub["alarm_date"].astype(str).str.len().gt(0).sum()
        early = int(sub["early"].sum()) if "early" in sub else 0
        print(kind, "n", len(sub), "alarmed", int(alarmed), "early", early)


if __name__ == "__main__":
    main()

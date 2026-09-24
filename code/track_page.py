#!/usr/bin/env python3
"""HTML tracking page: one excess curve, its own IR, two daily indicators."""
from __future__ import annotations

import html
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_eval import cusum_score, rolling_t_score

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
REPORT = ROOT / "reports" / "单曲线指标跟踪.html"

WARMUP = 504
WIN = 252
ANN = 244.0
# Normal-noise calibration at about 1220 trading days to a false alarm.
# t_cut: alarm when one-year t is below this. h: alarm when CUSUM is above this.
GRID = (
    (0.5, -1.2239, 32.8464),
    (1.0, -0.7483, 27.8095),
    (2.0, 0.3358, 19.5648),
)
DEMO = ("F009", "F014", "F025", "F001", "F091")
ROLE = {
    "F009": "健康对照。两个指标在热身之后都不越过自己的线。",
    "F014": "也是健康曲线，但一年 t 值和 CUSUM 都会长时间越过线。这是误报长什么样。",
    "F025": "超额在埋入日被设成 0。埋入前两个指标都不亮，埋入后都亮。",
    "F001": "超额减半。埋入之后一年 t 值几乎不亮，CUSUM 也只轻轻碰到。",
    "F091": "同样是超额减半。一年 t 值只占一成多的日子，CUSUM 很快升过线并停住。",
}
TYPE_NAME = {
    "step0": "阶跃归零",
    "half": "超额减半",
    "steady": "一直健康",
    "never": "从未有效",
    "regime": "好坏切换",
}


def lines_for(ir: float) -> tuple[float, float, float]:
    """Return k, t_cut, cusum_h for a frozen historical IR."""
    k = 0.5 * ir / np.sqrt(ANN)
    if ir <= GRID[0][0]:
        return k, GRID[0][1], GRID[0][2]
    if ir >= GRID[-1][0]:
        return k, GRID[-1][1], GRID[-1][2]
    for (ir0, t0, h0), (ir1, t1, h1) in zip(GRID, GRID[1:]):
        if ir0 <= ir <= ir1:
            w = (ir - ir0) / (ir1 - ir0)
            return k, t0 + w * (t1 - t0), h0 + w * (h1 - h0)
    return k, GRID[-1][1], GRID[-1][2]


def score_one(excess: np.ndarray, ir: float) -> dict[str, np.ndarray | float]:
    k, t_cut, h = lines_for(ir)
    sigma = float(excess[:WIN].std())
    sigma = max(sigma, 1e-8)
    tstat = -rolling_t_score(excess.reshape(1, -1), WIN)[0]
    cusum = cusum_score(excess.reshape(1, -1), np.array([sigma]), k, ewma=True)[0]
    weak = np.zeros(len(excess), dtype=np.int8)
    hot = np.zeros(len(excess), dtype=np.int8)
    weak[WARMUP:] = (tstat[WARMUP:] < t_cut).astype(np.int8)
    hot[WARMUP:] = (cusum[WARMUP:] > h).astype(np.int8)
    return {"k": k, "t_cut": t_cut, "h": h, "sigma": sigma, "tstat": tstat, "cusum": cusum, "weak": weak, "hot": hot}


def _runs(flag: np.ndarray) -> list[tuple[int, int]]:
    spans: list[tuple[int, int]] = []
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


def chart(
    dates: pd.DatetimeIndex,
    series: np.ndarray,
    thr: float | None,
    tau: int,
    shade: np.ndarray | None,
    y0: float,
    y1: float,
    color: str,
    start: int,
    thr_label: str,
) -> str:
    width, height = 980, 250
    left, right, top, bottom = 64, 18, 16, 28
    inner_w = width - left - right
    plot_h = height - top - bottom
    n = len(series)

    def X(i: float) -> float:
        return left + inner_w * (i / max(n - 1, 1))

    def Y(v: float) -> float:
        v = min(max(v, y0), y1)
        return top + plot_h * (1 - (v - y0) / (y1 - y0))

    parts = []
    if shade is not None:
        for a, b in _runs(shade):
            parts.append(
                f'<rect x="{X(a):.1f}" y="{top}" width="{max(X(max(b - 1, a)) - X(a), 1):.1f}" height="{plot_h}" fill="#f5e4d9"/>'
            )
    if y0 < 0 < y1:
        parts.append(
            f'<line x1="{left}" y1="{Y(0):.1f}" x2="{left + inner_w:.1f}" y2="{Y(0):.1f}" stroke="rgba(24,42,50,.18)"/>'
        )
    if thr is not None and y0 <= thr <= y1:
        parts.append(
            f'<line x1="{left}" y1="{Y(thr):.1f}" x2="{left + inner_w:.1f}" y2="{Y(thr):.1f}" stroke="#c66032" stroke-dasharray="5 3"/>'
        )
        parts.append(
            f'<text x="{left + inner_w - 4:.1f}" y="{Y(thr) - 4:.1f}" text-anchor="end" font-size="11" fill="#c66032">{html.escape(thr_label)}</text>'
        )
    if tau >= 0:
        parts.append(
            f'<line x1="{X(tau):.1f}" y1="{top}" x2="{X(tau):.1f}" y2="{top + plot_h}" stroke="#a33f39" stroke-dasharray="4 3"/>'
        )
    pts = " ".join(f"{X(i):.1f},{Y(float(series[i])):.1f}" for i in range(start, n))
    parts.append(f'<polyline fill="none" stroke="{color}" stroke-width="1.6" points="{pts}"/>')
    parts.append(
        f'<line x1="{left}" y1="{top + plot_h}" x2="{left + inner_w}" y2="{top + plot_h}" stroke="rgba(24,42,50,.35)"/>'
    )
    for val in (y0, (y0 + y1) / 2, y1):
        parts.append(
            f'<text x="{left - 8}" y="{Y(val) + 4:.1f}" text-anchor="end" font-size="11" fill="#53636a">{val:.1f}</text>'
        )
    for year in range(int(dates[0].year), int(dates[-1].year) + 1):
        loc = int(dates.searchsorted(pd.Timestamp(f"{year}-01-01")))
        if 0 <= loc < n and abs((dates[min(loc, n - 1)] - pd.Timestamp(f"{year}-01-01")).days) < 10:
            parts.append(
                f'<text x="{X(loc):.1f}" y="{height - 8}" font-size="11" fill="#53636a">{year}</text>'
            )
    return f'<svg viewBox="0 0 {width} {height}" width="100%" role="img">{"".join(parts)}</svg>'


def y_limits(series: np.ndarray, start: int, extra: list[float]) -> tuple[float, float]:
    sl = series[start:]
    lo = float(np.quantile(sl, 0.02))
    hi = float(np.quantile(sl, 0.98))
    for v in extra:
        lo = min(lo, v)
        hi = max(hi, v)
    pad = max(0.15, 0.12 * (hi - lo if hi > lo else 1))
    return lo - pad, hi + pad


def spell(flag: np.ndarray, a: int, b: int) -> str:
    if b <= a:
        return "没有可判断的日子"
    rate = 100 * float(flag[a:b].mean())
    best = cur = 0
    for v in flag[a:b]:
        cur = cur + 1 if v else 0
        best = max(best, cur)
    return f"{rate:.0f}% 的交易日越过自己的线，最长连续 {best} 天"


def recent_table(dates: pd.DatetimeIndex, excess: np.ndarray, scored: dict, n_rows: int = 10) -> str:
    tstat = scored["tstat"]
    cusum = scored["cusum"]
    weak = scored["weak"]
    hot = scored["hot"]
    t_cut = float(scored["t_cut"])
    h = float(scored["h"])
    rows = []
    for i in range(len(dates) - n_rows, len(dates)):
        rows.append(
            "<tr>"
            f"<td>{dates[i].date()}</td>"
            f"<td>{excess[i] * 100:.3f}</td>"
            f"<td>{tstat[i]:.2f}</td>"
            f"<td>{'偏弱' if weak[i] else '否'}</td>"
            f"<td>{cusum[i]:.1f}</td>"
            f"<td>{'越线' if hot[i] else '否'}</td>"
            "</tr>"
        )
    return (
        "<table><thead><tr>"
        "<th>日期</th><th>日超额（%）</th>"
        f"<th>一年 t 值（线 {t_cut:.2f}）</th><th>t 值判断</th>"
        f"<th>CUSUM（线 {h:.1f}）</th><th>CUSUM 判断</th>"
        "</tr></thead><tbody>"
        + "".join(rows)
        + "</tbody></table>"
    )


def library_rows(wide: pd.DataFrame, truth: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for fid in wide.columns:
        excess = wide[fid].to_numpy(dtype=float)
        ir = float(truth.loc[fid, "ir_start"])
        tau = int(truth.loc[fid, "tau_index"])
        scored = score_one(excess, ir)
        end = len(excess)
        if tau < 0:
            before = (WARMUP, end)
            after = (end, end)
        else:
            before = (WARMUP, max(tau, WARMUP))
            after = (max(tau, WARMUP), end)

        def rate(flag: np.ndarray, span: tuple[int, int]) -> float:
            a, b = span
            if b <= a:
                return np.nan
            return float(flag[a:b].mean())

        rows.append(
            {
                "kind": truth.loc[fid, "sim_type"],
                "weak_before": rate(scored["weak"], before),
                "weak_after": rate(scored["weak"], after),
                "hot_before": rate(scored["hot"], before),
                "hot_after": rate(scored["hot"], after),
            }
        )
    return pd.DataFrame(rows)


def build() -> None:
    wide = pd.read_parquet(DATA / "excess_wide.parquet")
    dates = pd.DatetimeIndex(wide.index)
    truth = pd.read_csv(DATA / "sim_truth.csv").set_index("factor_id")
    cards = []
    for fid in DEMO:
        excess = wide[fid].to_numpy(dtype=float)
        ir = float(truth.loc[fid, "ir_start"])
        kind = TYPE_NAME.get(str(truth.loc[fid, "sim_type"]), str(truth.loc[fid, "sim_type"]))
        tau = int(truth.loc[fid, "tau_index"])
        scored = score_one(excess, ir)
        t_cut = float(scored["t_cut"])
        h = float(scored["h"])
        k = float(scored["k"])
        cum = np.cumsum(excess) * 100
        role = ROLE.get(fid, "")
        if tau < 0:
            fact = "没有埋入失效日。"
            detail = (
                "热身之后，一年 t 值有 " + spell(scored["weak"], WARMUP, len(excess))
                + "；CUSUM 有 " + spell(scored["hot"], WARMUP, len(excess)) + "。"
            )
            cap_excess = "橙底是一年 t 值低于这条曲线自己的线的日子。"
        else:
            fact = f"埋入失效日是 {pd.Timestamp(truth.loc[fid, 'tau_date']).date()}。"
            detail = (
                "埋入前，一年 t 值有 " + spell(scored["weak"], WARMUP, tau)
                + "，CUSUM 有 " + spell(scored["hot"], WARMUP, tau) + "。"
                "埋入后，一年 t 值有 " + spell(scored["weak"], tau, len(excess))
                + "，CUSUM 有 " + spell(scored["hot"], tau, len(excess)) + "。"
            )
            cap_excess = "橙底是一年 t 值低于这条曲线自己的线的日子。红虚线是模拟埋入的失效日。"
        t_lo, t_hi = y_limits(scored["tstat"], WIN, [t_cut, 0.0])
        c_lo, c_hi = y_limits(scored["cusum"], 0, [h, 0.0])
        c_lo = min(0.0, c_lo)
        e_lo, e_hi = y_limits(cum, 0, [0.0])
        figs = (
            chart(dates, cum, None, tau, scored["weak"], e_lo, e_hi, "#0b6f69", 0, ""),
            chart(dates, scored["tstat"], t_cut, tau, None, t_lo, t_hi, "#315c75", WIN, f"t = {t_cut:.2f}"),
            chart(dates, scored["cusum"], h, tau, None, c_lo, c_hi, "#6b4f8a", 0, f"h = {h:.1f}"),
        )
        cards.append(f'''
        <section class="card" id="{html.escape(fid)}">
          <h2>{html.escape(fid)} · {html.escape(kind)}</h2>
          <p class="pills">
            <span class="pill t">历史信息比 {ir:.2f}</span>
            <span class="pill o">一年 t 值 &lt; {t_cut:.2f} 为偏弱</span>
            <span class="pill p">CUSUM &gt; {h:.1f} 为越线</span>
            <span class="pill b">参考漂移 k = {k:.3f}</span>
          </p>
          <p>{html.escape(role)}{html.escape(fact)}{html.escape(detail)}</p>
          <h3>累计超额</h3>
          {figs[0]}
          <p class="caption">{html.escape(cap_excess)}</p>
          <h3>一年 t 值</h3>
          {figs[1]}
          <p class="caption">蓝线只画满 252 个交易日之后。橙虚线是这条曲线的判断线。低于线的当天记为偏弱，第二天可以恢复。</p>
          <h3>波动更新的 CUSUM</h3>
          {figs[2]}
          <p class="caption">紫线高于橙虚线的当天记为越线。这里不把第一次越线锁死。</p>
          <h3>最近 10 个交易日</h3>
          {recent_table(dates, excess, scored)}
        </section>''')

    library = library_rows(wide, truth)
    order = (("steady", "一直健康"), ("step0", "阶跃归零"), ("half", "超额减半"), ("never", "从未有效"))

    def pct(sub: pd.DataFrame, col: str) -> str:
        vals = sub[col].dropna()
        if len(vals) == 0:
            return "—"
        return f"{100 * float(vals.mean()):.0f}%"

    lib_rows = []
    for key, name in order:
        sub = library[library["kind"] == key]
        lib_rows.append(
            "<tr>"
            f"<td>{name}</td><td>{len(sub)}</td>"
            f"<td>{pct(sub, 'weak_before')}</td><td>{pct(sub, 'weak_after')}</td>"
            f"<td>{pct(sub, 'hot_before')}</td><td>{pct(sub, 'hot_after')}</td>"
            "</tr>"
        )
    grid_rows = "".join(
        f"<tr><td>{ir:.1f}</td><td>一年 t 值 &lt; {tcut:.2f}</td><td>{h:.1f}</td><td>{0.5 * ir / np.sqrt(ANN):.3f}</td></tr>"
        for ir, tcut, h in GRID
    )
    doc = f'''<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>单条曲线的指标跟踪</title>
<style>
  :root {{
    --paper: #f5f2ea; --paper-deep: #ebe6da; --solid: #fffefa;
    --ink: #182a32; --soft: #53636a; --line: rgba(24,42,50,.14);
    --teal: #0b6f69; --teal-soft: #dceeea;
    --orange: #c66032; --orange-soft: #f5e4d9;
    --blue: #315c75; --blue-soft: #e0eaf0;
    --purple: #6b4f8a; --purple-soft: #eae2f2;
    --max: 1080px;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0; color: var(--ink); background: var(--paper);
    font-family: "PingFang SC","Hiragino Sans GB","Microsoft YaHei",system-ui,sans-serif;
    font-size: 16.5px; line-height: 1.65;
  }}
  a {{ color: var(--teal); text-decoration: none; }}
  .topbar {{ position: sticky; top: 0; z-index: 20; background: rgba(245,242,234,.94); border-bottom: 1px solid var(--line); }}
  .topbar-inner, .wrap {{ width: min(calc(100% - 32px), var(--max)); margin: 0 auto; }}
  .topbar-inner {{ min-height: 56px; display: flex; align-items: center; gap: 16px; flex-wrap: wrap; }}
  .brand {{ font-weight: 760; }}
  .nav {{ display: flex; gap: 4px; flex-wrap: wrap; }}
  .nav a {{ color: var(--soft); font-size: 13.5px; font-weight: 650; padding: 4px 9px; border-radius: 8px; }}
  header {{ padding: 28px 0 8px; }}
  h1 {{ font-size: 32px; line-height: 1.25; margin: 0 0 8px; }}
  h2 {{ font-size: 24px; margin: 0 0 8px; }}
  h3 {{ font-size: 16px; margin: 16px 0 4px; }}
  .sub, .caption {{ color: var(--soft); }}
  .caption {{ font-size: 13.5px; margin: 4px 0 0; }}
  .card {{
    background: var(--solid); border: 1px solid var(--line); border-radius: 16px;
    padding: 18px 18px 14px; margin: 16px 0 22px;
  }}
  .pills {{ display: flex; flex-wrap: wrap; gap: 8px; }}
  .pill {{ font-size: 13px; font-weight: 700; padding: 3px 10px; border-radius: 999px; }}
  .t {{ background: var(--teal-soft); color: var(--teal); }}
  .o {{ background: var(--orange-soft); color: var(--orange); }}
  .p {{ background: var(--purple-soft); color: var(--purple); }}
  .b {{ background: var(--blue-soft); color: var(--blue); }}
  table {{ border-collapse: collapse; width: 100%; font-size: 14.5px; margin-top: 8px; }}
  th, td {{ border-bottom: 1px solid var(--line); text-align: left; padding: 7px 8px; }}
  th {{ color: var(--soft); font-weight: 650; }}
  svg {{ display: block; }}
</style>
</head>
<body>
<div class="topbar"><div class="topbar-inner">
  <div class="brand">单条曲线跟踪</div>
  <nav class="nav">
    <a href="#verdict">是否可用</a>
    <a href="#F009">健康</a>
    <a href="#F014">健康误报</a>
    <a href="#F025">归零</a>
    <a href="#F001">减半看不出</a>
    <a href="#F091">减半能看出</a>
  </nav>
</div></div>
<div class="wrap">
  <header>
    <h1>这套单曲线跟踪，能用在什么地方</h1>
    <p class="sub">100 条模拟超额曲线都按自己的历史信息比定了线。下面先给结论，再抽 5 条放在一起看。每天只用当天及以前的数据，前 504 个交易日不判断。</p>
  </header>
  <section class="card" id="verdict">
    <h2>是否可用</h2>
    <p>可以当作「超额是不是已经接近归零」的跟踪，不能当作「某一天已经失效」的结论，也不能用来判断超额只剩一半。</p>
    <p>一年 t 值在健康曲线上平均只有约 4% 的日子低于自己的线，但 40 条里大多数至少会亮过一段。超额被设成 0 之后，偏弱的日子从大约 4% 升到 22%，第一次亮通常还要再等大约一年。超额只减半时，埋入前后几乎一样，都在 5% 上下。</p>
    <p>CUSUM 对归零更贴：埋入后平均大约六成的日子停在线以上。减半时平均能升到四成多，但曲线之间差很大，有的几乎不动。健康曲线平均也有大约 15% 的日子停在线以上。这个统计量会累积，一旦靠近线，就会连着许多天不下去；健康曲线里也能连着停一两年，所以连续停在线上仍然不是失效。</p>
    <table>
      <thead><tr><th>模拟类型</th><th>条数</th><th>埋入前，t 值偏弱</th><th>埋入后，t 值偏弱</th><th>埋入前，CUSUM 在线上</th><th>埋入后，CUSUM 在线上</th></tr></thead>
      <tbody>{"".join(lib_rows)}</tbody>
    </table>
    <p class="caption">健康和从未有效没有埋入日，前一列是热身之后的整天占比。数字是该类型全部曲线的平均。从未有效的历史信息比是 0，判断线被放到信息比 0.5 那一档，和「健康但波动大」叠在一起，分不开。</p>
  </section>
  <section class="card" id="rule">
    <h2>判断线怎么来</h2>
    <p>参考漂移放在「这条曲线的健康日超额」和 0 的中点。判断线按同一标准重解：假如超额一直停在原来的信息比上，平均大约 1220 个交易日才误报一次。下表是正态噪声上的三档。图里的曲线落在两档之间时，按信息比线性插值。</p>
    <table>
      <thead><tr><th>历史信息比</th><th>一年 t 值</th><th>CUSUM 的线</th><th>参考漂移 k</th></tr></thead>
      <tbody>{grid_rows}</tbody>
    </table>
    <p class="caption">这批模拟曲线的历史信息比大约在 0.5 到 1.2，没有信息比等于 2 的样本。信息比 2 的线仍列在表里：一年 t 值低于 0.34 就标偏弱。历史信息比取生成时写入的起始信息比，监控期间不改。</p>
  </section>
  {"".join(cards)}
</div>
</body>
</html>
'''
    REPORT.write_text(doc)
    print(f"wrote {REPORT}")


if __name__ == "__main__":
    build()

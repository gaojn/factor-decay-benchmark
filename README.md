# 因子失效检测基准

用 100 条同一优化器的超额曲线，做成能比较统计指标的标准数据集，并在同一误报预算下比过六个指标。

桌面路径：`~/Desktop/因子失效检测基准`

## 先看哪份

| 文件 | 内容 |
|---|---|
| `reports/指标比较做法图解.html` | 这次实际跑过的做法和结果，图解 |
| `reports/超额曲线标准数据集与指标评测.html` | 数据集怎么造、标签怎么写、两周执行单 |
| `reports/因子失效检测标准数据集与评测基准规划.html` | 完整规划（文献、三层数据、团队） |
| `docs/2026-09-23-factor-decay-benchmark-Fable5.md` | 规划全文 |

用浏览器直接打开 html。

## 这次比出来的结论

发现超额变小的速度，滚动一年 t 值、会更新波动的 CUSUM、固定波动 CUSUM、回撤深度分不开。波动变大而超额没变时，前两个误报少很多。阈值是在这批模拟噪声上定的，不能直接套到实盘复合因子的净超额上。

## 数据

`data/` 里是已经生成好的输入和评测结果。

- `nav_wide.parquet` / `excess_wide.parquet`：100 条净值、100 条日超额
- `curves.parquet`：长表 `date, factor_id, nav, excess, port_return`
- `benchmark.parquet`：基准
- `sim_truth.csv`：模拟时埋进曲线的类型，只供核对，不是评测标签
- `eval_scores.csv` / `eval_results.json`：六个指标的评分

区间：2015-01-05 到 2025-12-31。日超额等于组合日收益减基准日收益。

## 重新跑

```bash
cd ~/Desktop/因子失效检测基准
pip install -r requirements.txt
python3 code/generate_input.py
python3 code/run_eval.py
```

`generate_input.py` 写出 100 条曲线。`run_eval.py` 抽出噪声、注入已知失效、把六个指标校准到大约 5 年误报一次，再写出 `data/eval_scores.csv`。

单条曲线的指标跟踪看 `reports/单曲线指标跟踪.html`。每条曲线按自己的历史信息比定一年 t 值和 CUSUM 的判断线。`python3 code/track_page.py` 会重写这页。

固定一条共用判断线的逐日结果在 `reports/单曲线逐日判断.html`。`python3 code/daily_judge.py` 会重写那页和 `data/daily/F000.csv`。换自己的曲线：

```bash
python3 code/daily_judge.py --csv 你的文件.csv --date-col date --value-col excess
```

每天的结果在 `weak_today`。它表示过去一年偏弱，第二天可以恢复。

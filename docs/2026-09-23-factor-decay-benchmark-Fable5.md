# 因子失效检测标准数据集与评测基准（FDB）建设规划——10 人团队 × agent 协作（截至 2026-09-23）

> 编排说明：主会话（Fable5）定框架并分派 5 个并行子 agent（A1 基准建法调研、A2 因子衰减文献与 A 股案例、A3 合成 DGP 与功效仿真、A4 评测协议、A5 团队组织），回收后交叉复核、裁决矛盾、综合成本文。引用约定：[B#] 变点/异常检测基准与 SPC 文献；[F#] 因子衰减/A 股案例文献；[P#] 评测协议补充文献；[S] 本项目原型仿真（A3，可复现，见 §3.1）；[I#] 内部推断。文献均于 2026-09-23 实际打开核实；T1 同行评审 / T2 工作论文与机构白皮书 / T3 卖方研报与媒体。

---

## 1. 执行摘要

1. **要做的东西**：一套三层标准数据集（L1 参数化合成、L2 真实健康期 + 注入失效的半合成、L3 A 股真实标注案例）+ 一套多任务评测协议 + 一个多维排行榜，用来客观回答"哪种统计指标 / 检测器 / ML 方法判断因子超额失效更好"。评出的赢家经 6 个月影子运行后进入生产监控。
2. **先承认物理极限**。健康 IR=1 的因子日均超额/日波动≈0.063。原型仿真 [S]：在"5 年一次误报"预算下，参考检测器（CUSUM）对"IR 1→0 阶跃"的稳态中位延迟≈258 个交易日、均值≈320 日、P90≈679 日，报警前已损失约 1.1 年的健康超额；对"衰减一半（IR 1→0.5）"未直接仿真，按 KL 缩放与 Siegmund 近似推断约 2.5–3 年（与 Philips–Yashchin–Stein 2003 月频表量级一致 [F8][I2b]），v1 L1 必须补此场景。任何声称"3 个月内识别失效"且只用日收益的方法，在 L1 上必然是误报预算失控。这条要写进 dataset card 首页。
3. **检测器之间的差异远小于误报预算的差异**。五个基线（CUSUM、EWMA-CUSUM、滚动 t、月同号率、Kalman）在同一 ARL0 下的条件延迟相差 ≤15%，而 ARL0 从 5 年放到 10 年就让延迟增加 40–100 日 [S]。所以评测重心不是"谁的均值检验更灵敏"，而是：匹配 ARL0 后的延迟–检出曲线、对波动 regime / 共同冲击 / 类型混淆的鲁棒性、是否用了 IC / 实施链 / 风格暴露等辅助通道。
4. **三个能真正缩短延迟的杠杆**（均已在 L1 上量化 [S]）：(a) IC 通道 SNR 约为收益通道 4 倍，阶跃检出延迟从≈340 日降到≈84 日（IC 对照实验单独运行，其收益通道 CED 340/250 与主仿真 320/258 为不同 seed 的同一设定）；(b) 库级共同成分剥离在 2024-02 量级冲击下把系统性误报削减 89%，代价是库级同步衰减检出率 −5pp，应作并行通道而非替代；(c) 尺度自适应：σ×2 的波动 regime 迁移让固定 σ 的 CUSUM 误报 5.2×，比厚尾/GARCH（±15%）重要一个量级。
5. **文献先验修正 DGP**：因子衰减更像"离散阶跃 / 1.5 年内完成的 S 形过渡"而非慢线性 [F2][F3]；残留比例均值≈0.5（美国），A 股大概率更弱、方差更大 [F1][F5]；库里 30–45% 的"因子"可能从未有效（错误拒绝率 45% [F4]）；因子一年期正自相关是常态 [F11]，价值因子 13.5 年回撤后仍"未死" [F13]——L1 必须含"伪健康"分支、AR(1) 慢变 alpha、以及"长期回撤但未失效"的负例。
6. **数据集怎么切**：L1 按 seed 哈希 50/25/25 分 dev/cal/sealed；L2 按"因子 × 日历"两维切，sealed 含"未来时间块"与"未见因子块"；L3 中 2014–2017 年的案例开放为 dev（作 DGP 与注入幅度先验），2020 年后的案例封存、每季最多用 1 次、提交者只见聚合结果。阈值只能在 dev+cal 的 L1 健康路径 H 与 L2 未注入安慰剂路径 P 上校准到统一操作点（OP-5y = 1220 日、OP-10y = 2440 日，244 交易日/年）。
7. **怎么评**：五个任务 T1 在线报警 / T2 连续健康评分 / T3 离线定位 / T4 类型归因 / T5 经济价值。T1 主指标是"报警前累计损失"（以健康年 alpha 为单位）+ 安慰剂校正检出率 PDR（因为 ARL0=5 年、2 年观察窗下随机报警器有约 33% 的"免费检出率"）；常驻四基线（永不 / 始终 / 随机操作点 / 神谕）；按 seed 配对自助 + Holm；**禁止单一综合分**。
8. **防止基准被过拟合**：sealed 集物理隔离（QA 持钥）、提交次数限制 + 只追加账本、Blum–Hardt Ladder 释放分数 [B19]、隐藏 seed 每两季换代、因果截断审计、"合成好真实差"打 synthetic-only 标签并触发 DGP 评审。
9. **团队怎么干**：10 人（负责人 1 / 数据工程 2 / DGP 1 / 评测统计 1 / 检测器 2 / 标注 1+借调 1 / ML 1 / QA 1），8 条工作流，人—agent 四段式"规格（人）→ 初稿（agent）→ 复核门（人）→ 冻结（签发）"，12 周四阶段、四个 go/no-go。QA 与检测器开发严格隔离，排行结果不进绩效。
10. **v1.0 的成功定义是"基准可信"而不是"某方法赢"**：12 项 DoD 任一未达就发 v0.9 并明示缺项，不放宽阈值。

---

## 2. 背景与范围

### 2.1 为什么需要标准数据集

团队已有面向策略的《样本外策略监控计划》（CUSUM/EWMA + 失效注入校准 + 时间三分）和面向因子层的初步设计（五类失效 A–E、四条监控序列、多速度检测器、库级视角）。缺的是**裁判**：当有人说"Kalman 健康概率比同号率好"或"GRU 能提前发现失效"时，没有一套共同的数据和评分让这句话可被证伪。没有裁判的后果是（i）方法选择靠直觉和话语权；（ii）每个人在自己挑的历史片段上"验证"自己的方法；（iii）生产监控的阈值来自拍脑袋。

其他领域的经验是明确的：变点检测领域直到 TCPDBench（2020）才有第一个带人工标注、统一指标的基准，结论之一是**默认参数下没有任何方法显著优于"永不报警"的零基线** [B1]；时序异常检测领域被 Wu & Keogh 指出主流基准存在三元性（一行代码可解）、不现实的异常密度、标签错误、run-to-failure 偏差，制造了"进步幻觉" [B7]；M6 金融预测竞赛 163 队中仅 3 队全程跑赢朴素基准，且组织者承认一年样本分不开技能与运气 [B16]。FDB 要从第一天起避开这些坑。

### 2.2 目标与非目标

| 目标 | 非目标 |
|---|---|
| 给"因子超额是否失效"的检测方法一个可复现、防过拟合的评测环境 | 不是新的检测方法研发项目（方法是被评对象） |
| 量化每类失效在给定误报预算下的检出延迟物理下限，并公布 | 不替代策略层监控计划，只为其供给经评测的检测器 |
| 产出可直接进影子运行的赢家 + 方法卡 + dataset card | v1.0 不做状态机（黄/橙/红）评测、不做 B/C 类正式排名（放 v2） |
| 把 A 股真实失效事件沉淀为可复用的标注资产 | 不追求"真实案例上的统计显著"——L3 只做否决项 |

### 2.3 对象与口径

被检测对象：A 股多因子库约 100 个因子的日频序列，四条通道并行提供——原始超额（Top-N 或多空相对基准）、Barra CNE6 风格 + 行业中性的纯因子收益（主判定序列）、rank IC（1/5/20 日前向）、实施链（毛 / 净 / 换手 / 容量）。因子定义版本 hash 冻结，定义一改即新因子 [I0]。

失效类型（沿用已定框架）：**A** 被套利（渐进）/ **B** 风格劫持 / **C** regime 依赖（暂时）/ **D** 结构断点（突变）/ **E** 实施与数据故障。三类对照路径，符号严格区分：**H** 健康对照（alpha ≡ μ_good）；**H_vol** 波动 regime 迁移但 alpha 不变；**N** 伪健康 / 从未有效（L1 中 alpha ≡ 0 但有风格暴露与换手，对应文献中"错误拒绝"的因子 [F4]）；**P** 安慰剂（L2 中未注入任何失效的真实健康段，专用于 L2 的 ARL0 校准与误报估计）。N 与 P 不可混用：N 上报警是正确行为，P 上报警是误报。

---

## 3. 关键事实与仿真结论（Findings）

### 3.1 原型仿真：收益通道的物理极限 [S]

设定：健康 IR=1、日波动 0.5%、噪声 t5 + GARCH(0.06, 0.92)、每条路径独立库级共同成分含"2024-02 型"跳跃；校准 2000 条健康路径 × 30 年，每个失效场景 2000 条 × 9 年，失效起点 tau 在第 3 年；全部仿真单机约 40 秒。检测器均在"σ 已知或 burn-in 估计"的前提下运行。仿真按 252 日/年计，协议统一为 244 日/年，差异 3%，不影响结论。

**阈值校准（ARL0 ≈ 5 年 / 10 年）**

| 检测器 | 参数 | ARL0≈5 年 | ARL0≈10 年 |
|---|---|---|---|
| CUSUM（k = 0.0315σ） | h（σ 单位） | 24.6 | 32.4 |
| CUSUM + EWMA 尺度 | h | 24.6 | 32.0 |
| 滚动 252 日 t 值 | c | −0.71 | −1.09 |
| 滚动 12 月同号率 < 0.5 | 连续 n 月 | 3 | 6 |
| Kalman 局部水平 P(alpha < μ_good/2) | p | 0.523 | 0.647 |

读法：健康期 252 日 t 值均值为 +1.0，"滚动一年 t 值跌到 −0.7 以下"才能把误报控制在 5 年一次；Kalman 阈值 0.52 意味着"后验认为 IR<0.5 的概率刚过半"就报警。ARL0=5 年已经是很宽松的预算。

**功效（ARL0=5 年，以 tau 前无报警为条件；下表为参考检测器 CUSUM 的值，CUSUM+EWMA 在全部 5 个场景略优 1–4pp，五个检测器 CED 差距 ≤15%）**

| 场景 | CUSUM 3 年检出 | CED 均值 / 中位 / P90（日） | 报警前机会损失（健康年 alpha） |
|---|---|---|---|
| H 健康对照（基线误报） | 0.50 | — | 0 |
| D 阶跃 IR 1→0 | 0.92 | 320 / 258 / 679 | 1.08 |
| D 阶跃 IR 1→−0.5 | 0.98 | 240 / 201 / 471 | 1.37 |
| A 线性 24 月→0 | 0.83 | 472 / 440 / 883 | 0.69 |
| A 指数半衰期 12 月 | 0.75 | 526 / 475 / 996 | 0.66 |
| C regime（好态 IR 1.5 / 坏态 −0.5，坏态均 6 月） | 0.62 | 490 / 363 / 1091 | 0.63 |

必须一起读的三点：
- **健康基线**：ARL0=5 年时健康因子 3 年内"被检出"的概率本身为 0.45–0.50（几何近似 1−e^{−3/5}≈0.45，CUSUM 实测 0.50）。"D 阶跃三年检出 92%"的净增量是 +42pp，不是 92%。评分必须用"检出率 − 同期健康误报率"或匹配 ARL0 的延迟–检出曲线。
- **C 类是分水岭**：约 1/3 的 C 类报警落在因子已回到好态之后。标签必须保留 regime 序列，单独给"报警时是否处于坏态"打分。
- **Kalman 在 T1 上不优于 CUSUM**（C 类甚至更差，3 年检出 0.47 vs 0.62）。它的价值在 T2（连续健康评分）与权重收缩，不在报警速度。这修正了前期设计里"Kalman 健康概率为核心指标"的定位。

ARL0=10 年档：D 1→0 三年检出降到 0.79，CED 468/396 日；tau 前 3 年误报降到 0.20–0.27；各场景 CED 比 5 年档长 40–100 日。

**理论对照**：Siegmund 近似给出高斯零态 CUSUM h≈24.9、阶跃到 0 的零态 CED≈420 日，与仿真一致；CUSUM 在已知后变均值下为 Lorden 最优 [B9][B11]，所以≈250–320 日是**只用收益通道**判定 IR 1→0 的延迟下限量级。同一近似对"衰减一半"（IR 1→0.5，KL 缩小 4 倍）给出零态 CED≈670 日≈2.7 年 [I2b]；对治理要求"100 因子库每年 ≤1 次误报"（单因子 ARL0≈25,000 日）给出≈1520 日≈6 年——在那种预算下，收益通道检测器确实不可用（见 §4 X1）。

**逐配置公布理论下界**：每个 L1 配置（类型 × 强度 × 健康 IR）在标签中附 `kl_per_day` 与 `siegmund_ced_zero_state`（闭式一行代码）；排行榜上若该配置的理论下界 > 观察截止 D，格子标灰为"仅靠收益不可检"，防止对不可能任务排名 [B1 启示 10]。

### 3.2 厚尾不可怕，波动 regime 迁移才可怕 [S]

用高斯 iid 校准的 ARL0=5 年阈值放到其他噪声下：t5+GARCH 使 CUSUM 实际 ARL0 +5%，t4+GARCH +14%，方向多为"误报更少"（聚合窗口 ≥1 月，CLT 抹平尾部；单位方差 t 分布肩部反而更薄）。只有依赖极值的回撤类统计在 GARCH 下误报略增（−8%~−12% ARL0）。

真正打穿阈值的是 alpha 不变、σ 整体放大：

| | CUSUM（固定 σ） | CUSUM + EWMA | 滚动 t | 同号率 | Kalman（固定 σ） |
|---|---|---|---|---|---|
| σ×1.5 | 误报 2.8× | 1.7× | 1.8× | 1.5× | 1.8× |
| σ×2.0 | **5.2×** | 2.2× | 2.5× | 2.1× | 2.7× |

σ×2 使 IR 从 1 变 0.5，尺度自适应检测器多报一半是"合理的"；固定 σ 版本再多出的 2.4× 才是纯粹模型误设。**L1 必须含 H_vol 对照，方法卡必须声明尺度估计方式。**

### 3.3 库级剥离：针对共同冲击，作并行通道 [S]

100 因子中 30 个暴露于共同成分 F，第 1890 日 F 遭 5 日累计 20σ 下跌、随后 10 日反弹 50%（2024-02 量级 [I5]）。逐因子 CUSUM 在 63 个交易日内报警 18.1 个（无冲击基线 4.1）；先对库等权收益做滞后 252 日滚动回归取残差再检测 → 5.6 个。超额误报 −89%，10 年全样本总报警数基本不变（20σ 场景 88 vs 86；无冲击基线 86 vs 84）。代价：100 个因子同日全部 IR 1→0 时（库级同步被套利的极端形式）检出率 0.90→0.85。结论：做成"个体报警 × 库级报警"的 2×2 并行判定，不替换个体检测。文献侧的提醒：因子动量集中在高特征值主成分 [F11][F12]，PCA 剥离会同时剥掉因子动量与 MP2016 发现的"衰减期相关性上升" [F1]，L1 要显式测试这一交互 [I3]。

### 3.4 IC 通道是最便宜的加速器 [S]

无约束 rank IC 典型量级：均值 0.02–0.03、日标准差 0.08–0.12，日 SNR≈0.25，是可实施组合收益（0.063）的 4 倍 [I2]。同一 CUSUM、ARL0=5 年、阶跃到 0：收益通道 1 年检出 0.50、CED 340/250 日；IC 通道 1 年检出 0.98、CED 84/72 日。前提是失效同步出现在 IC 与收益（A/C/D 成立；B 只在纯因子通道、E 只在净值/波动通道）——这正是 FDB 要检验"多通道检测器是否更强"的设计点，L1/L2 都必须生成 IC 与收益双通道并标注失效体现在哪个通道。

### 3.5 文献先验：衰减长什么样 [F]

| 事实 | 数值 | 对 DGP 的含义 |
|---|---|---|
| 发表后衰减幅度（美国） | MP2016：样本外 −26%、发表后 −58% [F1]；FRT2022：Sharpe −43%~−50% [F3]；JM2020：美国 −62%~−66%，38 个国际市场无稳健衰减，中国仅市值加权版边际显著（t −1.74）[F5] | A 型残留比例 a₁/a₀ 用 Beta 分布，均值 0.5、5–95% 区间 0.25–0.9，几乎不放 0；A 股中心上移到 0.6–0.8、方差更大 [I7] |
| 衰减形状 | MP 工作稿："离散变化而非线性趋势" [F2]；FRT Fig.5：发表前约 1.5 年开始、发表后迅速完成 [F3] | 阶跃 30% / 逻辑斯蒂 S 形 50%（过渡 250–600 日）/ 指数半衰期 20%（1–3 年）；慢线性只作低权重对照 |
| 衰减驱动 | FRT：发表年份解释 30%（每晚一年 +5pp 折价）、过拟合变量 +15%、拥挤边际 [F3]；CGS2020：未校正错误拒绝率 45%，t 门槛 3.4–3.8 [F4]；HLZ t>3 [F6] | 必须有"伪健康（从未有效）"分支，占库 30–45% |
| 基线折价 | DSR：E[max SR]≈√(2lnN)·σ_SR；N=500–2000、σ_SR=0.3–0.5 → 1.0–1.8 [F7][I1] | 库因子 IR≈1 与选择偏差同量级，μ_good 必须折价 |
| CUSUM 量级 | PYS2003 Table 2：月频、IR 0.5→0、误报 84 月 → 检出 41 月；IR→−0.5 → 25 月 [F8] | IR 1→0 约 10–12 月（与 [S] 的 258–320 日一致）、IR 1→0.5 约 41 月 [I2b]（[S] 未仿真，v1 补） |
| 拥挤 | Lou–Polk comomentum 高 → 12 月内反转、坏日比例 8.4%→22.5% [F9]；MSCI 五指标模型，拥挤后 12 月显著回撤频率约 7 倍（T3 二手）[F10][F10b]；MSCI 2021 示例：残差波动因子拥挤极高后 5 月回撤 [F10c] | 拥挤预测 B/C 型而非 A 型；A 股空头数据稀薄用配对相关/估值价差/换手替代 |
| 因子动量 | 过去一年负/正后月均 6bp vs 51bp [F11]；HML 13.5 年回撤 55% 后被估值价差完全解释、仍"未死" [F13] | alpha 含 AR(1)/慢变成分；L3 必须保留"长期回撤未失效"负例，测"过早判死" |

### 3.6 基准建设的教训 [B]

| 来源 | 做对了什么 | 被批评什么 | FDB 采纳 |
|---|---|---|---|
| TCPD / TCPDBench [B1][B2] | 37 真实序列 + 5 暗藏质控序列；每条 5 人盲标（隐去日期/名称/纵轴）；covering + F1(margin)、弃 Hausdorff；Default vs Oracle 两套设置 | Oracle 不代表实际性能 | Frozen/Oracle 双设置只按 Frozen 排名；L3 隐去因子名与年份、混入 L1 序列盲标；多标注者"并集算精确率、宏平均算召回" |
| NAB [B3][B4] | perfect=100 / null=0 归一化；FP/FN 权重 profile 由人设 | sigmoid 早检出加分是 magic number、无下界、难解释 [B5][B6][B7] | 只借归一化与"权重由治理设"，延迟直接以交易日报 |
| Wu & Keogh [B7][B8] | UCR 档案：每条恰 1 异常、带外证据 | 三元性（Yahoo 86% 一行解）、不现实密度、错标、run-to-failure | L2 每条 ≤1 事件且 ≥30% 无失效；"一行代码"三元性检验，能一行解的单独统计不进主榜；强制零基线 |
| SPC / QCD [B9]–[B14] | ARL0 / CED / WADD；(ARL0, CED) 操作曲线；CUSUM 对已知偏移精确最优；zero-state vs steady-state | — | 已知偏移 CUSUM 作 D 类理论标尺；同时报 zero/steady-state；阈值用健康段 Monte Carlo 反解 |
| M6 / Jane Street [B16][B17][B18] | 滚动实时窗口、赛后 live 重跑 | 一年分不开技能与运气 | 前向直播段：每季新增因子-年自动进 sealed；样本量以"因子-年"计 [I4] |
| Ladder / Datasheets [B19][B20] | 只在改善 > η 时释放分数，误差 (log k/n)^{1/3} 而非 √k；七节 datasheet | — | 私有榜 Ladder 释放；dataset card 随版本更新 |

---

## 4. 矛盾与裁决

| # | 矛盾 | 裁决 |
|---|---|---|
| X1 | A1 用一阶渐近 CADD≈\|log α\|/KL 推出"单因子 ARL0=10 年时 CUSUM 延迟≈15.6 年、库级年误报 ≤1 时≈20 年、收益类检测器基本不可用"；A3 仿真给出 ARL0=5 年、IR 1→0 的中位延迟 258 日 | **采 A3，并经复核 agent 独立推导与 Monte Carlo 复现**（高斯 iid：ARL0 1220，稳态 CED 均值 330 / 中位 259 / P90 691）。一阶渐近 h≈log γ 只在 KL·γ ≫ 1 的渐近区成立，此处 KL=δ²/2≈0.002、γ≈1260，KL·γ≈2.5=O(1)，公式丢了 1/KL 因子，误差约 9×；Lorden 不等式 ARL0 ≥ e^{h_LLR} [B11] 在 h_LLR=0.063×24.6≈1.55 nat 时给出 4.7 vs 实际 1260，说明该界极松；Siegmund 近似 ARL0(h=24.6)=1233、零态 CED=413 与仿真一致。正确表述：**完全失效（IR 1→0）在 OP-5y 下中位≈1 年、均值 1.3 年、P90 2.8 年，OP-10y 中位≈1.6 年；衰减一半（1→0.5）按同一近似≈2.7 年**。A1 的悲观结论在 OP-5y/10y 下不成立；但若治理要求库级每年 ≤1 次误报（单因子 ARL0≈25,000 日），零态 CED≈6 年，A1 的"不可用"结论在该预算下成立——这正是 §6.4 把误报预算作为治理输入的原因 |
| X2 | A3 用 252 日/年、ARL0=1260；A4 用 244 日/年、OP-5y=1220 | 协议统一 244（A 股实际 242–245）；仿真数字保留原值并注明，差异 3% |
| X3 | A5 WS6 写"ARL0 目标值如 250 交易日"；sealed 提交"每方法 ≤1 次" | 以 A4 为准：OP-5y=1220 / OP-10y=2440；v1.0 发布时 sealed 由 QA 统一跑一次，之后每方法族每季 ≤2 次 |
| X4 | A3 DGP 默认 A 型只有线性与指数、P 占 10%；A2 文献先验说衰减以阶跃/S 形为主、伪健康占 30–45% | v1.0 参数表按 A2 修：新增 A_logistic 模板并作 A 类主档，伪健康（改名 N，见 X10）比例升到 30%，alpha 加 AR(1) 慢变成分；A_lin 降为对照 |
| X5 | A5 DoD L1 ≥2000 条；A4 分层功效要求每类型 ≥800 失效 episode；A4 OP-10y 校准需 H/P ≥5 万因子·年，而库中 H 占比只能给约 1.6 万 | 采 A4 的 ≥800/类型（5 类 ≈ 4000 失效 episode + 同量对照 ≈ 8000+ 条 [I9]）；**校准用 H 路径单独生成**（≥2000 条 × 30 年 = 6 万因子·年，A3 即如此做），不计入库比例表。A3 实测 2000 条 × 9 年仿真数十秒，算力不是约束 |
| X6 | A5 DoD 要求 L3 五类每类 ≥1；A2 指出纯"数据故障"E 型无公开案例 | E 型在 L3 以"对冲/成本断点"（2015-09 限仓、2022 基差收敛）为主，纯数据故障由团队内部事故记录补齐，补不齐则在 card 中声明并用 L2 注入覆盖 [I6b] |
| X7 | 前期设计把 Kalman 健康概率作核心 T1 指标；仿真显示其报警速度不优于 CUSUM | Kalman 定位为 T2 与权重收缩的输出，T1 主基线为 CUSUM/EWMA-CUSUM |
| X8 | A5 WS1 建议 dev/cal/sealed 按时间三分（最早 50% / 中间 25% / 最近 25%）；A4 §5.2 为"因子 × 时间"两维切分 | 采 A4 两维切法（同时测时间外推与因子外推）；WS1 的 `splits_v1.yaml` 需同时含因子分组（按族分层抽样）与日期边界 |
| X9 | A4 要求 L3 全部封存；A2 建议 2014–2017 案例可作 dev/cal 先验；A5 R4 职责写"先验来自 L3" | **分段**：2014–2017 五例（案例 1、2、6、7、8）开放为 dev，供 DGP 参数与注入幅度先验、并作"已知答案演示集"；2020 年后案例（3、4、5、9、11、13）及案例 10、12、14 封存，只做最终验收与否决 |
| X10 | A2/A3 用 P 表示 alpha≡0 的伪健康路径；A4 用 P 表示 L2 未注入的安慰剂路径，且拿它校准 ARL0 | 两者互斥（alpha≡0 上 CUSUM 应当报警，拿它校准会把阈值推到无穷）。改名：L1 伪健康 = **N**，L2 未注入 = **P**；L1 校准只用 H，L2 校准只用 P；N 的计分规则见 §6.2 |

---

## 5. 数据集设计

### 5.1 L1 参数化合成 [S][F]

**生成方程（单因子 i、日 t）**

```
r_raw_t  = alpha_t + beta_t' s_t + lambda_i F_t + m_t e_t      # 原始超额
r_pure_t = alpha_t            + lambda_i F_t + m_t e_t      # 纯因子收益（真 beta 已剔除）
r_net_t  = r_raw_t − cost_t                                  # 实施链净收益
ic_t     = (alpha_t / mu_good) · IC_bar + sd_IC · (rho z_t + sqrt(1−rho²) eta_t)
```

| 组件 | 规格 | 默认 / 范围 |
|---|---|---|
| 尺度 | 总日波动 σ_d；μ_good = IR_good·σ_d/√244 | σ_d=0.5%，IR_good∈{0.5, 1, 2}，主档 1 |
| 方差预算（健康） | F 25% / 风格 10% / 特质 65%，var(e) 下限 0.2σ_d² | — |
| 特质噪声 e_t | GARCH(1,1) × 标准化 Student-t | ν=5（4–6），a=0.06，b=0.92 |
| 风格收益 s_t（K=5） | size / value / momentum / volatility / liquidity；多元 t（共用 χ² 混合）× 逐风格 GARCH + 长期溢价 | 年化波动 4–8%、长期 IR ±0.2–0.3、相关矩阵按 Barra CNE 常见量级 [I1]；L2 用真实风格收益替换 |
| 库级共同成分 F_t | GARCH-t + 跳跃 J_t：日概率 1/756，幅度 U(4,8)σ_F 分 3 日下跌，5 日反弹 50% | λ_i ~ N(1, 0.3²) |
| IC 通道 | IC_bar=0.025，sd_IC=0.10，ρ=0.6；5/20 日 IC 由日 IC 重叠求和再标准化 | 作参数扫描 [I2] |
| alpha 慢变 | 在模板均值上叠加 AR(1) 成分，年度自相关 0.2–0.4 [F11] | v1.0 新增 |
| 衰减期共振 | A 类衰减期该因子对 F_t 的载荷 λ_i 或与库内配对相关上调 +0.1~+0.2 [F1] | v1.0 可选开关，用于测试库级剥离与 A 类衰减的交互 [I3] |

**alpha 路径模板（除 N 外，tau 前全部为 μ_good）**

| 模板 | 定义 | 参数 | 库中比例（v1.0）[I-v1] |
|---|---|---|---|
| H 健康 | alpha ≡ μ_good | — | 20% |
| H_vol 波动迁移 | alpha 不变，σ 在 tau 后 ×{1.5, 2} [S] | — | 5% |
| N 伪健康 / 从未有效 | alpha ≡ 0 全程，风格暴露与换手照常 | — | 30% [F4] |
| A_step 阶跃衰减 | alpha → a₁·μ_good | a₁ ~ Beta(均值 0.5–0.7) [F1][F3][I7] | 5% |
| A_logistic S 形（A 类主档） | alpha = μ_good·[a₁ + (1−a₁)·(1 − σ((t−tau−D/2)/w))]，σ 为 logistic 函数 | 过渡总长 D∈[250, 600] 日，w=D/8 [F3][I-v1] | 8% |
| A_exp 指数 | alpha = μ_good·[a₁ + (1−a₁)·2^{−(t−tau)/h}] | h∈{6,12,24} 月 [S] | 4% |
| A_lin 线性（对照） | alpha = μ_good·max(a₁, 1−(t−tau)/D) | D∈{12,24,36} 月 [S] | 3% |
| B 风格劫持 | alpha→μ_good(1−w_t)，某风格暴露 β 漂到使该风格占总方差 50%，w_t 在 D 内线性 [S] | D=6–18 月 [I4-A2]，k* 随机 | 7% |
| C regime | alpha = a·1[good] + b·1[bad]，两态马氏链，tau 强制进 bad [S] | a=IR 1.5，b=IR −0.5，E[bad]=126 日，E[good]=378 日 | 8% |
| D 阶跃断点 | alpha → IR_new，伴随波动跳升 2–4 倍持续 20–60 日 [F 案例 1/5/6/7] | IR_new∈{0, −0.5}（[S]）∪ {0.3, −0.3}（A2 先验表）| 4% |
| E_cost 成本断点 | 毛 alpha 不变，cost 由 c₀ 跳到 c₁ [S] | (0.2, 0.8) IR 单位 | 3% |
| E_cov 覆盖度骤降 | 毛 alpha 不变，噪声乘子 m 1→2 [S] | — | 3% |

库级生成：N=100，T=10 年，tau ~ U[W+244, 7 年]（W=504 日热身，见 §6.1；并保证 tau 之后 ≥ D+M_loose 日观测），因子间相关来自共享 F_t 与 s_t。每类失效 ≥3 档强度（弱/中/强），弱档要求"≥1 个基线在操作点下检出率 <50%"以保证难度（A5 设计选择 [I5-A5]）。**校准专用路径**：另生成 ≥2000 条 × 30 年纯 H 路径（含 H_vol 变体）专用于 §6.4 阈值校准，不计入上表比例。上表比例为综合稿设计选择，W3 冒烟跑后可调 [I-v1]。

**标签 schema**：逐因子 `factor_id, type, tau, lam, mu_good, sigma_d, beta0_*, 模板参数, kl_per_day, siegmund_ced_zero_state`；面板级 `alpha_true (T,N)`、`beta_true (T,N,K)`、`cost_true`、`regime (T,N) bool`、`styles`、`F`、`F_jumps`、`params(含 seed)`。派生真值：失效日、类型、失效后任一日真实 IR、regime 时段、失效体现通道（A/C/D：IC+收益；B：仅纯因子/IC；E：仅净值/波动）。

### 5.2 L2 半合成：真实健康期 + 注入

- **宿主**：WS1 提取的真实因子四通道序列。"健康期"用多准则联合界定：滚动 IC 均值 ≥ factor-judge 入库 μ_good 的 X%、无 L3 已知事件、Barra 暴露稳定；R8 人工复核 20 个因子；健康期定义写入 card 局限性并做收紧/放宽敏感性（风险 K1）。
- **注入机制**（综合稿设计，写入 WS3 规格 [I-inj]）：把 5.1 的 alpha 路径模板作用于宿主——收益通道按 alpha 差额逐日平移，IC 通道按 alpha_t/μ_good 比例缩放，B 类叠加真实风格收益 × 目标 β 漂移路径，E 类改净值（成本序列）或噪声乘子。每条 ≤1 个事件，起点随机，≥30% 不注入 [B7]——这些未注入的真实健康段就是 **P 安慰剂路径**，专用于 L2 的 ARL0 校准与 FA(D) 估计。
- **泄漏断言（CI）**：注入窗口与 L3 标注的真实失效区间零重叠；注入点前序列与原序列 bit 级一致。
- **三元性检验**：每条先过"一行代码"基线（滚动 252 日 IC 均值 <0），能一行解的单独统计、不进主榜 [B7]。
- **规模**：≥30 个真实因子 × ≥5 类模板 × ≥3 强度 ≥450 条（v1.0 下限），按"因子-年"公布有效样本量 [I4]。

### 5.3 L3 真实标注案例（A 股）[F]

候选 14 例（A2 检索，T1–T3 证据齐备）：

| # | 因子/族 | 日期或区间 | 主+次类型 | 置信 | 可逆 | 主要证据 |
|---|---|---|---|---|---|---|
| 1 | 小市值 / 壳价值 / 低价 | 2016-11（IPO 常态化、重组新规）→ 2017 全年 | A+D | 高 | 部分 | [F14][F15][F16][F17][F46] |
| 2 | 短期反转 / 低流动性 | 2017 起机构化衰减；2019 阶段性失效 | A+B | 中高 | 部分 | [F18][F19][F20][F38] |
| 3 | 质量 / 盈利成长（白马抱团） | 2021-02-18 → 2021-03 | C+B | 高（日期）/中（归因） | 是 | [F21][F22] |
| 4 | 高频量价 / 高换手 alpha | 2021-09-13 → 2021-11 中 | A+C | 中 | 部分 | [F42a][F42b][F43] |
| 5 | 小微盘暴露 + 中性对冲 | 2024-01-08 → 2024-02-07（微盘指数 −46~49%） | D+E | 高 | 指数可逆、alpha 分布永久改变 | [F23]–[F27] |
| 6 | 全部对冲类 | 2015-09-07 中金所限仓（IC 贴水 12.9%） | E | 高 | 缓慢 | [F28a][F28b][F29] |
| 7 | 市值/成长 vs 金融蓝筹（中性） | 2014-12-01 → 12-05 | C+E | 高 | 是 | [F30a][F30b] |
| 8 | 全市场 | 2016-01-04 / 01-07 熔断 | E | 高 | 是 | [F31a][F31b] |
| 9 | 反转 / 涨停量价（创业板） | 2020-08-24 涨跌幅 20% | D（局部） | 中 | 否 | [F39][F40][F41] |
| 10 | 大市值+高 ROE+低估值（外资偏好） | 2017–2019 累积；2020–2022 转向 | B | 中 | 是 | [F36a][F36b][F37] |
| 11 | 红利 / 高股息 / 低波 | 2021-11 起强势；2024-05 拥挤 95.7 分位；2024-07-09 超额回撤；2024-09-24 后跑输 | C+B | 高/中 | 是 | [F32][F33][F34b] |
| 12 | 低波 / 低特质波动 | 2015H2–2018 占优；2017、2019 弱；2020 组合失效 | C | 中 | 是 | [F34][F35] |
| 13 | 中性策略 / 需对冲因子 | 2022-05/06 基差快速收敛 | E | 中 | 是 | [F44] |
| 14 | 价值 / PB（负例：长期回撤未失效） | 2019–2021 低估值持续跑输（映射 US HML 2007–2020）| C（负例） | 中 [I5'] | 是 | [F13][F33][F34b] |

候选需 ≥20（WS4 验收），上表 14 例之外的 ≥6 例由 R8 从团队内部记录补齐（含纯数据故障 E 型：复权错误、财报重述、行业分类切换等）[I6b]。

**标注协议**（WS4）：
- agent 检索线索、生成候选与叙事初稿；两名研究员**独立**标注（不看初稿日期），字段：主/次类型、起始区间 [τ_lo, τ_hi]、确认日、强度、置信度、`reverted_24m`（24 个月内是否回到健康期均值的 50%，二值，替代模糊的"复原日"）、"实时可得信息"版本叙事（防后见泄漏）。
- A 型起点锚定：A 股没有"论文发表日"，用本土公开代理——卖方研报首发、公募量化规模拐点、被主流风险模型纳入——作为"公开事件"锚点写入 guideline [F3 启示]。
- 收录条件：类型 Cohen's κ ≥ 0.6 且起始区间重叠 ≥50% [I6a]；不一致由 QA 主持仲裁，仍不一致标"争议"只进 dev。
- 盲标：隐去因子名与年份，混入 L1 合成序列作质控 [B1]。
- 日期一律为区间不为点；过程型事件（1、2、10）区间 ±3–6 个月。
- 样本外可用性（X9 裁决）：2014–2017 案例（1、2、6、7、8）开放为 dev，作 DGP 与注入幅度先验；2020 年后案例（3、4、5、9、11、13）业内众所周知，与 10、12、14 一起封存，只做最终验收。
- 因子级证据 vs 策略级证据：案例 4、5、13 的公开证据是产品超额而非因子 IC，需用自有因子库回算确认哪些因子在这些日期出现断点后再进 L3。
- B 类目前仅案例 10 一例（中置信）支撑，DoD D5 "每类 ≥1" 对 B 类是勉强达标，需在 card 中注明。

### 5.4 切分与封存

| 层 | dev | cal | sealed |
|---|---|---|---|
| L1 | hash(seed) mod 4 ∈ {0,1}（50%） | =2（25%） | =3（25%），seed 列表仅评测服务器持有；另含"隐藏变体"子集（同 DGP 族、参数在公布范围内扰动，类别公布取值不公布） |
| L2 | F_dev × ≤2018 健康段 | F_cal × 2015–2021 | 两块：**未来时间块**（全部因子 × 2022 起）测时间外推；**未见因子块**（F_sealed × 全时段）测因子外推；因子分组按族分层抽样 |
| L3 | 2014–2017 五例（作先验与演示集）+ 争议案例 | — | 2020 年后案例与 10/12/14 封存；每方法版本每季 ≤1 次；不可再生，每次登记；**提交者只见聚合结果，永不见逐案例结果**（案例仅十余个，逐案例结果等于泄漏答案） |

dev 无限使用；cal 只用于阈值校准与 T2 校准；sealed 每方法族每季 ≤2 次、团队总额 ≤8 次，只追加账本记录提交 hash（代码 + 方法卡 + θ*）；v1.0 发布时 sealed 由 R10 统一运行一次。生成器版本化：FDB-v1.0 = 代码 hash + 参数文件 + seed 规则 + 校准常数一起冻结；补丁号不改任何输出数值，次版本可增类型/通道但旧 episode 逐位可复现，主版本才可改 DGP；每版本独立排行榜永久保留。

---

## 6. 评测协议

### 6.1 约定

244 交易日/年 [I0]；热身期 W=504 日不计分，DGP 保证 tau > W+244 且 tau 之后 ≥ D+M_loose 日；观察截止 D=488 日（2 年）主档、244 日副档，E 类缩到 60 日（故障应快检）；容差 M_strict=60 日（D/E 类）、M_loose=250 日（≈1/δ²，A 类的变点定位理论下限量级 [I10]）。**容差必须小于同序列真变点最小间距** [B15][B1 启示 6]：C 类有两个真变点（tau_start、tau_end）且 E[bad]=126 日 < 250，故 C 类 T3 用 M_C = min(M_loose, 0.5 × 坏态段长) 并以范围型 P/R [B6] / covering 为主指标。评测单元 episode = 带元数据的一条序列；库级方法的单元为面板 × 因子；所有方法在同一 seed 上评以便配对。

**N（伪健康，alpha ≡ 0）路径的计分语义**（X10）：T1 不计入 DR/FA，单独报"N 上 D 内报警率"（越高越好，作辅报）；T2 神谕标签 y_t ≡ 0（h_t 应低）；T4 归为第六类"从未有效"或允许弃权；T5 面板中 N 因子的权重收缩越彻底越好。

### 6.2 任务

| 任务 | 输出 | 标签 | 主指标 | L1 | L2 | L3 |
|---|---|---|---|---|---|---|
| T1 在线报警 | 每日 a_t∈{0,1}，首次报警即停时 | (tau, k)；L3 为区间 | 报警前累计损失 ℒ @OP-5y, D=2y；PDR | 完整 | 完整（ARL0 用 P 路径） | 报警落在区间前/内/后三分类 + 延迟上下界 |
| T2 连续健康评分 | 每日 h_t = P(alpha_t ≥ 0.5·alpha_0) 或 α̂_t | 神谕 y_t=1{alpha_t ≥ 0.5 alpha_0}；实现 y^fwd=1{未来 244 日 IR>0} | BSS（神谕）；对 α̂_t 另报 nRMSE=RMSE/alpha_0 与断点后跟踪半衰期（D 类专用） | 神谕+实现 | 神谕+实现 | 仅实现（描述性） |
| T3 离线变点定位 | 断点集合（可用未来数据） | {tau}（C 类两点） | covering − 无断点基线 | 完整 | 完整 | 区间容差 F1 |
| T4 类型归因 | 五类分布或硬标签，可弃权；截断于 T_a+κ，κ∈{0,120} | k∈{A..E}；L3 主/次双标 | macro-F1 @κ=120 | 完整 | 完整（E 依赖实施链注入） | macro-F1（主或次命中皆算） |
| T5 经济价值 | 无额外输出；协议固定映射 w_{i,t} ∝ h_{i,t−1}（收缩型）或 1{T_a,i > t}（开关型） | 对照：静态等权、神谕 | ΔIR_net（配对自助 CI）；MaxDD、权重换手、捕获率 CR | 面板 | 面板 | 一次描述 |

C 类在 T1 中判"检出"的条件是 T_a ∈ [tau_start, tau_end + D]；恢复识别放 T2 与 v2 状态机评测。

### 6.3 指标（公式 / 奖励 / gaming / 堵）

| 指标 | 定义 | 被怎么 gaming | 怎么堵 |
|---|---|---|---|
| ARL0 [P4][B11] | 删失几何 MLE：(Σ min(T_a, L) − W·n)/Σ1{T_a ≤ L}；同报"前端质量" P(T_a − W ≤ 244) 应≈1−e^{−244/ARL0}；同时报 zero-state 与 steady-state 两种口径 [B14]（新因子上线即监控 vs 运行多年后失效） | 永不报警→∞；固定日报警；热身期狂报后安静 | 只作操作点验收不排名；前端质量暴露初始化报警 |
| DR(D) | P(tau ≤ T_a ≤ tau+D \| T_a ≥ tau)，tau 前报警计误报 | 报警越勤越高 | 固定 ARL0 |
| **PDR(D)** | DR(D) − FA(D)，FA(D) 为该方法在 H/P 路径上任取长 D 窗的经验报警概率（OP-5y、D=2y 下几何近似≈33%） | — | 主报 PDR，DR 辅报 |
| CED 与 KM 分位 | E[T_a − tau \| 检出]，按 tau 早/中/晚分桶；q50/q90 用 Kaplan–Meier 处理 tau+D 处删失 | 只对检出者平均把漏检丢掉 | CED、KM 分位、DR 同一表格缺一不排名 |
| **ℒ 报警前累计损失** | (1/(244·alpha_0))·Σ_{tau}^{min(T_a, tau+D)}(alpha_0 − alpha_t)，单位"健康年 alpha 倍数"；漏检在 tau+D 截断 | 越早报越好 | 固定 ARL0；L3 无 alpha_t 不算 |
| 容差 F1 | TCPDBench 定义，一对一匹配防重复计数；多标注者并集算 P、宏平均算 R；t=1 作平凡断点 [B1] | 每 2M 撒一个断点 | 精度惩罚 + 同报 \|X\|−\|T\| 与 covering |
| Covering | (1/T)Σ_A \|A\|·max_A' J(A,A') [B1] | 零断点时长健康段虚高 | 排名用 C − C_无断点基线 |
| BSS / AUC / ECE [P9] | Brier 与基率参照；10 桶可靠性图 | 恒输出基率；极端 0/1 毁校准；用未来数据 | 三指标同报；因果截断审计 |
| 实现标签 AUC | 对 y^fwd；未来 12 月实现 IR 自身 SD≈1，神谕 AUC 也远低于 1 | — | 只报 AUC/AUC_oracle，不跨层排名 |
| macro-F1 / log-loss / 弃权曲线 | 五类均衡；覆盖率 0.5/0.8/1.0 下准确率；单列 A↔D、B↔A 混淆率 | 猜多数类；全弃权；A/D 二选一 | macro；固定覆盖率点；κ 两档同报 |
| ΔIR_net / MaxDD / TO / CR | r_p = Σ w r_net − c_w Σ\|Δw\|；CR = (IR_m − IR_static)/(IR_oracle − IR_static) | 自定权重映射；频繁开关；集中到少数因子 | 协议固定映射；换手成本；报有效因子数 1/Σw² |

### 6.4 统一操作点

| 档位 | ARL0（日） | 单因子年化误报 | 100 因子库年化误报期望 |
|---|---|---|---|
| OP-5y | 1220 | 0.20 | 20 |
| OP-10y | 2440 | 0.10 | 10 |

两档必交；用哪档做决策是治理输入（人定）。库级期望误报数直接展示，让"5 年一次"的直觉与"库里每年 20 次复评"的运营负担对齐 [I13]。

校准程序：方法卡声明唯一单调标量阈值 θ（报警概率随 θ 单调；多阈值方法须固定其它阈值的相对关系只留一维路径；**不满足单调性的方法（部分 BOCPD / ML）在 T1 只能以"固定网格 + 最近点"参与并标注**）→ 仅用 dev+cal 的 **L1 校准专用 H 路径**与 **L2 未注入 P 路径**、L1/L2 **分别**校准（真实噪声下同一 θ 的 ARL0 明显更低）→ OP-10y 校准需 H/P 总时长 ≥5 万因子·年（L1 由专用 H 路径满足；L2 靠不同因子 × 不同起始年切块，不足时只校准 OP-5y 并标注）→ 二分求 ARL0(θ)∈[0.9,1.1]×目标 → 在 cal 独立 H/P 上验收（自助 90% CI 覆盖目标且点估计 ≥0.8×目标；前端质量不超几何预期 1.5×；库级方法"同日 ≥5 因子报警"频率不超独立假设 3×）→ 不过允许重校准一次，再不过标"未达操作点"不进结论 → θ* 写入方法卡并 hash。跨层迁移诊断（θ*_L1 跑 L2 的实际 ARL0 / 目标）只报告，作鲁棒性指标。

### 6.5 统计推断与判定规则

- 重抽样单元：L1 = seed；L2 = 簇（因子 × 日历年块）；库级 = 面板 seed；L3 不给 CI，只报胜/负/平与符号检验。比值型指标（ARL0、CED、CR）对每个重抽样样本**整体重算**，不对逐 episode 的比值取平均。
- B=2000 百分位自助，95% CI。每对比较报三件事：效应量（原单位 + 标准化）、胜率及 CI、预注册的最小重要差异 MID（T1 ℒ 0.1 年 alpha 或 CED 20 日；T2 BSS 0.02；T3 covering 0.02；T4 macro-F1 0.03；T5 ΔIR 0.05）[I16]。
- **"X 优于 Y"当且仅当**：(i) 主指标 Holm 校正后 p<0.05 [P6]；(ii) 效应量 CI 下界超过 MID；(iii) 任一失效类型分层上 X 不比 Y 差超过 MID。否则报"有取舍"或"不可区分"。
- 探索网格（任务 × 层 × 类型 × 操作点）用 Benjamini–Yekutieli q=0.10 [P7]，标"探索性"；多方法总排位 Friedman + Nemenyi，CD 图展示不可区分簇 [P8][B1]。
- 分层强制：类型 A–E、tau 位置、严重度（25/50/100%）、健康期 IR（0.5/1/2）。**每类型 ≥800 episode** 才能在 5pp 上分辨胜率差（80% 功效）[I17]；其余更细分层只报告不作显著性判定，除非该格 n ≥ 800。
- 常驻基线：永不报警、始终报警（t=W+1）、操作点随机报警（几何停时）、神谕。**任何方法必须显著优于随机报警才可声称"有效"。** 子期一致性（M6 教训 [B16]）：L2 按日历年块分层，任一年块显著劣于随机报警即标"不稳定"。

### 6.6 提交、排行与治理

- 方法卡（YAML，预注册于首次 sealed 评测前）：method_id、family、tasks、inputs_used、causal、hyperparameters、threshold_param、tuning_data、calibration（两档 θ 与 ARL0 CI）、runtime、generator_version、预期失败场景、局限性、尺度估计方式 [B23]。超参 >10 的方法额外提交 dev 调参轨迹。**`tuning_data` 与代码不符者结果作废。**
- 结果 JSON 由评测服务器产出，含分层指标点估计 + CI + n + 删失比例、常驻基线、成对判定、Ladder 释放标志、审计结果。
- 排行榜维度：任务 × 层 × 类型 × 操作点；颜色只表示"显著优于随机 / 不可区分 / 更差"；**禁止单一综合分**（允许一张标注"仅展示"的雷达图）。
- Ladder：每方法族维护 sealed 最好成绩，步长 η = 主指标 sealed 自助 1 个标准误，未过步长只返回"未显著改善" [B19][I20]。
- 隐藏 seed 每 2 季换代，跨代下降超 CI 宽度标"代间不稳定"；L2 未来时间块每年自然延长一年。
- 现实差距 RG：L2-sealed 排名与 L3 胜负排名之差超出 L3 符号检验分辨范围 → 打 synthetic-only 标签、不得进生产候选，并触发 DGP 评审（多方法族同向 RG 优先怀疑 L1/L2 缺了真实现象）；反向（L3 好、合成差）标 unexplained，不得据此提拔 [I21]。
- 因果截断审计：随机抽 episode 与 t₀，比较用 x_{1:t₀} 与 x_{1:T} 运行时截至 t₀ 的输出是否逐位相同；不同则该提交 T1/T2 全部作废并登记 [I22]。

### 6.7 指标—类型—层适用矩阵（要点）

- B 类的"失效"在纯因子通道上不存在（风格剥离后 alpha 仍在），只在原始超额通道显现；所有 B 类指标必须注明所用通道。
- C 类需要两个时点：T1 只评进入，T2 评进入与恢复，ℒ 截断到 tau_end。
- E 类 D 与 M 都缩到 60 日；用 2 年 D 评 E 类没有区分度。
- L3 一切延迟只给区间 [T_a − tau_hi, T_a − tau_lo]，不算 CED 点估计、ℒ、神谕 BSS。
- H 上 F1 应为空集，报误报数；covering 应≈1；T5 的 H/P 面板上方法不应降 IR，N 因子权重应被压到接近 0。

### 6.8 v1（MVP）与 v2

| | v1（12 周内） | v2 |
|---|---|---|
| 层 | L1 全部（无隐藏变体）；L2 dev/cal/sealed-未来时间块；L3 只做 T1 三分类与 T3 区间 F1 的一次描述性验收 | L1 隐藏变体、seed 换代；L2 未见因子块；L3 正式使用规则 |
| 类型 | A、D、E 正式排名 + H/H_vol/P；B、C 生成但只作探索 | B、C 完整接入；五类归因 |
| 任务 | T1、T2（神谕）、T3；T5 仅 L1 收缩型；T4 仅 A vs D 二分 | T4 五类 κ=0/120；T2 实现标签相对技能；C 类恢复识别与观察名单/退库状态机评测 |
| 操作点 | OP-5y 必做，OP-10y 视 P 路径样本量 | 两档 |
| 推断 | 配对自助 + Holm + 常驻基线；按类型与 tau 位置分层 | BY、Friedman/Nemenyi CD 图、严重度与 IR 分层 |
| 任何版本不做 | 单一综合分；L3 上的 CED/ℒ/神谕 BSS；实现 12 月 IR 标签的排名 | |

---

## 7. 团队与执行

### 7.1 角色（10 人）

| # | 角色 | 职责 | 配对的 agent 任务 | 主要 WS |
|---|---|---|---|---|
| R1 | 项目负责人 / 方法论 Owner | 冻结规格；主持 go/no-go；仲裁；对外接口；签发 v1.0 | 起草规格、方法卡模板、决策备忘录初稿；文献综述后人抽查 | WS8、全部决策点 |
| R2 | 数据工程 A（契约与提取） | 数据契约 schema；从 ClickHouse the_quant / barra_cne6 提取 100 因子四通道；版本化与校验和 | 写提取 SQL、ETL、schema 校验器 | WS1 |
| R3 | 数据工程 B（基础设施与 CI） | 仓库骨架、CI、确定性测试、算力调度、registry、排行榜渲染 | 写 CI、pytest fixtures、Makefile、lockfile | WS1 下半、WS6 工程、WS8 |
| R4 | DGP 与仿真 | L1 参数化（先验来自 L3 的 2014–2017 开放案例与真实 dev 段，不得来自 cal/sealed）；生成器确定性；L2 注入模板 | 写生成器与分布检查脚本；人跑 KS/ACF 对真实健康期 | WS2、WS3 |
| R5 | 评测协议与统计 | 操作点标定；配对自助；多任务指标；Ladder 实现 | 实现指标与自助；人用玩具例子手算核对 | WS6 |
| R6 | 检测器 A（统计/在线） | CUSUM/EWMA、滚动 IC、HAC t、回撤分位、Kalman，统一接口 | 实现 + 单测；人用解析解校核（iid 正态 ARL0 表） | WS5 |
| R7 | 检测器 B（贝叶斯/变点/领先指标） | BOCPD、PELT/BinSeg、拥挤/暴露漂移/IC 半衰期、库级剥离 | 移植实现；人对照原论文伪代码逐行审 | WS5 |
| R8 | 真实案例标注（研究员兼任，+借调 1 名第二标注者） | L3 清单、标注指南、双标注、分歧仲裁；提供每类失效的 A 股叙事作 DGP 先验 | 检索线索出初稿、生成标注界面；两位研究员独立标注 | WS4 |
| R9 | ML 方法 | 面板 GBM / GRU 检测器；特征复用 WS5 领先指标；只用 dev 训练 | 写训练 pipeline；人审 split 与特征时点 | WS7 |
| R10 | 复核 / QA / 文档 | 盲审所有复核门；**持 sealed 密钥**；方法卡 / dataset card；agent 产出抽检；发布报告；**不参与任何检测器开发** | 起草 card 模板与检查清单；人抽查 | WS8、全部复核门 |

RACI 要点：数据契约 R2 执行 R1 签发；DGP 参数表 R4 执行、R10 盲审（不看代码只看参数表判断是否用了 cal/sealed 信息）；排行榜 R5+R3 执行；v1.0 报告 R10 执行 R1 签发。

### 7.2 工作流（输入 → 输出 → 验收）

| WS | 内容 | 关键验收 |
|---|---|---|
| WS1 数据契约与真实序列提取（R2 主） | `contracts/data_contract_v1.yaml`；`data/real/v1/*.parquet` + MANIFEST（sha256）；`splits_v1.yaml`（**因子分组 + 日期边界两维**，X8）哈希入 git tag | schema 100% 通过；随机 10 因子对 ClickHouse 原值误差 0；rank IC 与 factor-judge 报告同期一致（1e-6）；**时点可得性审计**（任一日期只依赖 ≤t 信息，R10 抽 5 个） |
| WS2 L1 生成器（R4） | `fdb/dgp/`；`configs/dgp_v1.yaml` 冻结参数 + seed 列表；库面板 + 校准专用 H 路径；每条附 ground-truth（含 kl_per_day、siegmund_ced） | 同 seed bit 级确定性（CI）；健康段 KS/ACF 对真实 dev 段在容差内（R10 盲审）；每类 ≥3 档强度，弱档"≥1 基线检出 <50%"；参数表不含 cal/sealed 统计量；W3 用 oracle 检验五类可分性（K11） |
| WS3 L2 注入器（R4 主，R8 辅） | `fdb/inject/`；`health_windows_v1.yaml`；`data/L2/v1/` | 健康期规则可执行且 R8 复核 20 因子；注入点前 bit 级一致；**与 L3 真实失效零重叠断言在 CI**（R10 故意造一个重叠案例验证断言真的会失败）；强度校准只用 dev |
| WS4 L3 标注（R8 + 借调，R10 仲裁） | `annotation/guideline_v1.md`；候选 ≥20；独立标注；`adjudicated_v1.yaml` ≥8 案例；分歧记录 | κ ≥0.6 且区间重叠 ≥50%；每类 ≥1（E 允许内部事故）；全部日期为区间；每案例附"实时可得信息"版叙事与依据链接 |
| WS5 检测器库（R6、R7） | `fdb/detectors/base.py`：`fit(dev) / update(x_t)→score / alarm(θ) / locate() / attribute()`；≥6 基线；方法卡；ARL0 标定曲线 | 接口测试；**未来数据投毒测试**（t+1 后改 NaN 不改变 score_t）；CUSUM/EWMA iid 正态 ARL0 与理论误差 <5%；参数只在 dev 选且选参脚本入库；复用监控计划已有 CUSUM/EWMA 实现按接口包装。实现注记 [S]：Kalman 阈值用 P(alpha < μ_good/2) 而非 P(alpha < 0)——alpha 恰为 0 时后者渐近 0.5 无法与健康区分；原型记忆 504 日未调优，须在 dev 上选 |
| WS6 评测引擎与排行榜（R5 主，R3 工程） | `fdb/eval/`：操作点标定器、指标、配对自助、`results/registry.csv`（只追加）、多维渲染 | `make reproduce RUN=xxx` 重跑一致（1e-9）；R5 手算 3 个指标核对；自助 CI 覆盖率仿真 ∈[92%, 98%]；sealed 只能由 R10 触发 |
| WS7 ML（R9） | 面板 GBM、GRU（统一接口）；训练协议；特征时点审计表 | 只用 dev；每特征标注"t 日可得"并抽查；相对最佳统计基线的提升有 CI 支持才可声称；"L1 好、L2/L3 不好"必须写入方法卡局限性 |
| WS8 治理/文档/复核（R10 主，R1 签发） | dataset card（Datasheets 七节 [B20]）；方法卡；`reviews/`；agent 抽检记录；发布报告；接口文档 | 每个复核门有记录；引用抽检 20% 零编造；文档 CI（"显著/优于/更好"附近必须有 run_id 或 [R#]）；R1 签发 |

### 7.3 人—agent 协作

**四段式**：规格（人写，≤1 页含验收标准）→ 初稿（agent：代码/文档/检索）→ 复核门（人按检查清单）→ 冻结（owner 签发，git tag）。无规格不派 agent；每次 agent 会话的 prompt 与输出摘要归档 `agent_logs/` 供 R10 抽检。

| 任务类型 | agent 做 | 人做 | 复核门 |
|---|---|---|---|
| 数据提取 | SQL、ETL、校验器 | 定契约；跑；抽 10 因子对原库 | R10 抽 5 因子时点可得性；R2+R10 双签 MANIFEST |
| DGP 生成器 | 代码、单测、分布检查脚本 | 跑 KS/ACF；写参数表 | **第二人盲审参数表**；R5 抽 1 类 DGP 数学定义与代码一致 |
| 注入器 | 注入逻辑、泄漏断言 | 跑；R8 复核健康期 | R10 验证断言会失败 |
| 文献检索 | 检索、表格、引用 | 判断相关性 | **R10 抽 20% 引用核真**（URL 可达、题名作者一致、引文确在文中）；不达 100% 整篇退回 |
| L3 标注 | 线索、候选、叙事初稿、界面 | 两人独立标注（不看 agent 日期） | κ ≥0.6 收录；R10 仲裁 |
| 检测器 | 实现、单测、方法卡初稿 | 对照原论文逐行审；解析解校核 | R5 审 ARL0 标定；CI 投毒测试；R10 审"局限性"是否写实 |
| 评测指标 | 实现指标与自助 | 手算玩具例子 | R3 复现测试；R10 审 registry 不可篡改 |
| ML | 训练/推断 | 审 split、特征时点 | R10 抽查；R5 审提升是否有 CI |
| 文档/card | 模板、初稿 | owner 修改 | 文档 CI；R10 通读 |

**agent 失败模式与防线**

| 失败模式 | 防线 | 责任 |
|---|---|---|
| 编造引用 | 20% 抽检，任一编造整批退回并 100% 核对；引用必须附 URL 且 CI 检查可达 | R10 |
| 静默改需求（实现更容易的 A'，测试也按 A' 写） | 规格与验收标准先入 `specs/`；复核门第一项逐条对照；**≥30% 单测由人写且不给 agent 看** | WS owner |
| 过拟合基准（隐式用了 cal/sealed） | sealed 物理隔离，agent 无访问权限；cal 查询计数；参数表盲审 | R10、R5 |
| 单测全绿但逻辑错（用了未来数据 / 符号反 / 索引偏移） | 未来数据投毒测试；解析解校核；L1 强档"必须报警"冒烟测试；R6/R7 互审 | R6、R7、R3 |
| 过度自信文字（"显著优于"无 CI） | 文档 CI 关键词检查 | R10 |
| 静默降级（依赖装不上就 fallback） | 禁止 try/except ImportError fallback；lockfile | R3 |
| 生成器伪随机不确定 | 确定性 CI；强制显式 `np.random.Generator(seed)` | R4、R3 |
| 重复造轮子 / 风格不一 | 接口冻结后写入 CONTRIBUTING 与 agent 提示模板；R3 每周扫描；ruff/mypy | R3 |
| 单位/口径混淆（日 vs 年化、IC vs rank IC、毛 vs 净） | 契约每列带单位；校验器检查数值范围 | R2 |

**对人同样适用的防线**：排行不进绩效；提交限制对内部方法同样生效；每张方法卡必须有"预期失败场景"，WS6 针对该场景生成对抗路径验证。

### 7.4 12 周时间线

| 阶段 | 周 | 里程碑 | go/no-go |
|---|---|---|---|
| P1 契约与规格冻结 | W1–2 | M1：数据契约 v1 + 切分边界哈希入 tag；检测器接口 v1 冻结；L1 五类 DGP 数学定义；L3 候选 ≥20；仓库 + CI 骨架 | **G1**：契约与接口是否冻结？未冻结则 P2 不启动（宁延 1 周） |
| P2 三层 v0.1 与基线 | W3–6 | M2a（W4）：L1 生成器确定性通过；≥3 基线接口通过；L3 指南 v1 + 首轮独立标注开始。M2b（W6）：L1/L2 v0.1 全量 + MANIFEST；≥6 基线；L3 首轮 κ 报告；ML 特征清单 | **G2**：L1 健康段分布检查通过？L2 泄漏断言在 CI？L3 κ≥0.6 案例 ≥5？任一不满足则 P3 只做引擎不做排行 |
| P3 引擎、校准、首轮排行 | W7–10 | M3a（W8）：标定器 + 指标 + 自助通过复现测试；dev 内部排行。M3b（W10）：cal 排行 v0.9（每方法 ≤5 次查询）；ML 进入；方法卡齐全；L3 仲裁 ≥8 | **G3**：复现测试通过？sealed 未被触碰（R10 审计日志）？方法卡齐全？不满足则延期不放宽 |
| P4 封存验收、报告、发布 | W11–12 | M4a（W11）：R10 一次性运行 sealed；结果入 registry；dataset card 定稿。M4b（W12）：v1.0 报告（多维排行、赢家影子运行建议）、tag `v1.0.0`、接口文档双签 | **G4**：R1 签发；DoD 任一未达发 v0.9 |

```
WS / 周      1  2  3  4  5  6  7  8  9  10 11 12
WS1 契约提取  ■  ■★ ▫  ▫
WS2 L1 DGP    ▫  ■  ■  ■  ■  ★  ▫
WS3 L2 注入          ▫  ■  ■  ★  ▫
WS4 L3 标注   ■  ■  ■  ■  ■  ■  ■  ■  ■  ★
WS5 检测器    ▫  ★  ■  ■  ■  ■  ▫  ▫  ▫  ▫
WS6 评测引擎     ▫  ▫  ▫  ■  ■  ■  ★  ■  ★
WS7 ML                 ▫  ▫  ■  ■  ■  ■  ★
WS8 治理文档  ■  ■  ▫  ▫  ▫  ▫  ▫  ■  ■  ■  ■  ★
sealed+发布                                  ★  ★
决策点           G1          G2          G3    G4
```

每周节律：周一 30 分钟状态同步与复核门排期；周三集中复核门；周五 agent 抽检报告（R10）+ registry 周报（R3）；阶段末 go/no-go 逐条勾。

### 7.5 仓库与工程

- 目录：`contracts/ configs/ specs/ fdb/{dgp,inject,detectors,eval} data/{real,L1,L2}/v1 annotation/ results/registry.csv reviews/ agent_logs/ docs/cards/`。
- 数据版本化：parquet + MANIFEST sha256 + DVC（或等价）；seed 显式列表；sealed 加密隔离，R10 持钥。
- CI 八项：生成器确定性、检测器接口、未来数据投毒、L2/L3 不重叠、结果复现、文档来源检查、契约校验、sealed 访问审计。
- registry 只追加；每行：run_id、method_version、config_sha、generator_version、partition、指标、触发人、时间。

### 7.6 v1.0 验收定义（DoD）

| # | 项 | 阈值 |
|---|---|---|
| D1 | L1 规模 | 库面板：每类失效 ≥800 episode（≥3 强度）+ 同量 H/H_vol/N；**校准专用**：≥2000 条 × 30 年纯 H 路径（含 H_vol 变体），满足 OP-5y 与 OP-10y 校准 |
| D2 | L1 健康段真实性 | 与 dev 真实健康期 KS / ACF 差异在参数表预设容差内；R10 盲审记录 |
| D3 | L2 规模 | ≥30 真实因子 × ≥5 模板 × ≥3 强度 ≥450 条；≥30% 无注入 |
| D4 | L2 泄漏 | 与 L3 真实失效区间零重叠（CI） |
| D5 | L3 | ≥8 案例双人 κ≥0.6 且区间重叠 ≥50%；五类每类 ≥1（E 允许内部事故；B 类目前仅单例支撑，card 注明） |
| D6 | 基线 | ≥6 方法（CUSUM/EWMA、滚动 IC、HAC t、回撤分位、Kalman、BOCPD、离线变点中至少 6）在统一操作点下有 L1/L2 全部任务结果 + L3 描述性结果 |
| D7 | 复现 | `make leaderboard` 一键渲染；随机抽 3 run 重跑一致 |
| D8 | 方法卡 | 原理、参数选择过程（只用 dev）、ARL0 标定曲线、预期失败场景、局限性 |
| D9 | dataset card | Datasheets 七节 [B20]，首页写明 §3.1 的物理极限 |
| D10 | 时间三分 | sealed 访问日志显示 v1.0 前仅 R10 一次运行 |
| D11 | 治理记录 | 全部复核门有记录；agent 抽检报告 ≥10 份；引用抽检零编造 |
| D12 | 接口文档 | 与 factor-gate / 监控计划接口经 R1 与对方 owner 双签 |

任一未达 → 发 v0.9 并明示缺项与补齐计划，不放宽阈值。

### 7.7 风险与缓解

| # | 风险 | 缓解 | Owner |
|---|---|---|---|
| K1 | 真实"健康期"难界定（因子本来就在缓慢衰减） | 多准则联合 + R8 复核 20 因子 + 收紧/放宽敏感性 + card 局限性 | R4、R8 |
| K2 | L3 案例少且日期模糊 | 区间标注；L3 只作否决项不作主排名；持续补案例；争议案例进 dev | R8、R1 |
| K3 | agent 编造 / 静默改需求 | §7.3 防线 | R10 |
| K4 | 基准被过拟合 | sealed 隔离 + 限次 + Ladder + 弱档难度 + 对抗路径 + L3 否决 + 影子运行裁决 | R5、R10 |
| K5 | 团队把"在基准上赢"当目标 | 排行不进绩效；QA 与开发隔离；成功=DoD 达成 | R1 |
| K6 | 泄漏（注入期与真实失效重叠 / 特征用未来） | CI 断言；投毒测试；特征时点审计 | R4、R9、R3 |
| K7 | 算力 / 时间 | A3 原型显示 2000 路径 × 9 年仿真数十秒，主要开销在 BOCPD/ML；W3 起 10% seed 冒烟；向量化；自助在指标层；W10 留缓冲 | R3 |
| K8 | 与 factor-gate / 监控计划口径不一致 | W1 对齐纯因子收益定义、ARL0 目标、报警语义并写入契约；D12 双签 | R1、R2 |
| K9 | 接口过早冻结装不进 BOCPD/ML | W1 让 R7、R9 用伪代码走一遍；接口留 `state` 扩展字段 | R6、R7、R9 |
| K10 | 借调研究员不到位 | W1 前锁定承诺；备选 R1 兼第二标注者并在 card 披露非独立性 | R1 |
| K11 | 五类在 DGP 中不可分（A 与 C 弱档相似） | W3 用 oracle 检验可分性；不可分档合并标"A/C"并在协议说明 | R4、R5 |
| K12 | 收益类检测器在合理误报预算下延迟以年计，团队预期落空 [S] | dataset card 首页写明 §3.1；评测重心转向 IC 通道、实施链、领先指标、库级剥离；v1.0 成功定义不含"找到快检测器" | R1 |

---

## 8. 与现有流程的接口

| 接口 | 内容 |
|---|---|
| FDB 赢家 → 生产监控（影子运行条款） | 入口：sealed 上 L1/L2 主任务前 3 且 L3 无否决（≥6 个 L3 案例上于确认日前报警或不晚于确认日 + 20 交易日 [I8]）。影子期 6 个月，与现有 CUSUM/EWMA 并行，输出到独立表，不触发交易；每月对比报警数，每次报警由研究员事后标真/假（沿用 WS4 指南）；转正条件：实际误报 ≤ 设计 ARL0 的 1.5 倍、影子期内真实失效检出且不晚于现有监控、R1 与监控计划 owner 双签；失败 → 回流为新 L3 案例。生产部署版本 = registry 中 method_version + config_sha，生产侧不得私改参数 |
| factor-judge → FDB | 入库时的 μ_good、σ、入库日期、best direction、Barra 残差报告 → 契约字段 `baseline_mu_good / baseline_sigma / admission_date`；健康期从入库日起算。反向建议 factor-judge 新增 `health_window_ref` 字段（v1.0 报告提出，不在本项目内改） |
| factor-gate ↔ FDB | 实盘因子的净超额 IR、换手、容量 → 实施链口径对齐；FDB 方法报警（附方法名、健康分、类型概率、定位区间）→ 触发 factor-gate 复评；复评结论回写为 L3 新标注候选 |
| 《样本外策略监控计划》 | 复用其 CUSUM/EWMA 实现（按接口包装）与失效注入脚本（作 WS3 起点）；ARL0 目标、报警语义、时间三分边界 W1 对齐；分工：监控计划面向策略层，FDB 面向因子层并供给方法选择依据 |
| 前期因子层设计 | 五类失效、四条序列、多速度检测器、库级视角沿用；修正：Kalman 由 T1 核心改为 T2 输出；R13 "IC 同号率"降为可解释哨兵（仿真显示其在同一 ARL0 下延迟最长）；新增 H_vol 对照与尺度估计声明 |

---

## 9. 局限与开放项

**局限**
- L1 风格收益、相关矩阵、IC 通道 SNR 是按 Barra CNE 与 A 股经验量级设定的，未用真实数据校准 [I1][I2a]；L2 用真实数据替换后要重跑校准表。
- 功效仿真把风格暴露折入噪声、每条路径独立 F_t（保证 ARL0 估计无偏）；B 类的功效未仿真，其检测本质要求风格回归通道 [I3]；"衰减一半"场景未仿真，只有 Siegmund 推断 [I2b]。
- 库级剥离只测了"对库等权平均的滞后滚动回归"一种；PCA 与全样本回归的掩蔽更强是推断 [I6c]。
- L3 案例 2021 年后部分业内熟知，隐含泄漏不可完全排除；只能靠封存 + 使用限制 + 前向直播段缓解。
- 纯"数据故障"E 型真实案例缺位，靠内部记录与 L2 注入。
- 案例 14（价值"假死"）向 A 股的映射是类比推断 [I5']。

**开放项（需 R1 / 治理层决定）**
1. 误报预算用 OP-5y 还是 OP-10y 做生产决策；"库里每年 20 次复评"是否可承受。
2. C 类的"正确行为"是降仓还是下线——决定 T1 对 C 的计分与 v2 状态机评测。
3. μ_bad 两档（衰减一半 vs 成本门槛）在评测中的权重。
4. 健康期界定的 X%（相对入库 μ_good）与敏感性档位。
5. 借调第二标注者能否在 W1 前落实。
6. 是否把原型 DGP/检测器代码（约 600 行 numpy，40 秒跑完全部仿真）作为 WS2/WS5 起点直接入库。
7. 面板 ML 在 v1 只作探索；何时允许其进入影子运行（建议：v2 上在 L2 两块 sealed 与 L3 上均不劣于最佳统计基线）。

---

## 10. 参考文献

### B：基准建法、变点与 SPC（A1 / A4 核实）
- [B1] van den Burg, G. J. J. & Williams, C. K. I. (2020). An Evaluation of Change Point Detection Algorithms. arXiv:2003.06222. https://arxiv.org/abs/2003.06222
- [B2] Alan Turing Institute. TCPDBench. https://github.com/alan-turing-institute/TCPDBench
- [B3] Lavin, A. & Ahmad, S. (2015). Evaluating Real-time Anomaly Detection Algorithms – the Numenta Anomaly Benchmark. ICMLA; arXiv:1510.03336. https://arxiv.org/abs/1510.03336
- [B4] Numenta. NAB README / Scoreboard v1.1. https://raw.githubusercontent.com/numenta/NAB/master/README.md
- [B5] Singh, N. & Olinsky, C. (2017). Demystifying Numenta Anomaly Benchmark. IJCNN. https://doi.org/10.1109/ijcnn.2017.7966038 （摘要核实，批评条目经 [B6] 转述）
- [B6] Tatbul, N., Lee, T. J., Zdonik, S., Alam, M., Gottschlich, J. (2018). Precision and Recall for Time Series. NeurIPS; arXiv:1803.03639. https://arxiv.org/html/1803.03639v3
- [B7] Wu, R. & Keogh, E. J. (2021/2022). Current Time Series Anomaly Detection Benchmarks are Flawed and are Creating the Illusion of Progress. IEEE TKDE / ICDE; arXiv:2009.13807. https://arxiv.org/abs/2009.13807
- [B8] Benchmarking Anomaly Detection Methods: Insights From the UCR Time Series Anomaly Archive. Expert Systems (2024/2025). https://doi.org/10.1111/exsy.13767
- [B9] Moustakides, G. V. (1986). Optimal Stopping Times for Detecting Changes in Distributions. Annals of Statistics 14(4). https://doi.org/10.1214/aos/1176350164
- [B10] Moustakides, Polunchenko, Tartakovsky (2009). Numerical Comparison of CUSUM and Shiryaev–Roberts Procedures. arXiv:0908.4119. https://arxiv.org/html/0908.4119
- [B11] Veeravalli, V. V. & Banerjee, T. (2012). Quickest Change Detection. arXiv:1210.5552. https://arxiv.org/abs/1210.5552
- [B12] Polunchenko & Tartakovsky (2010). On optimality of the Shiryaev–Roberts procedure. arXiv:0904.3370. https://arxiv.org/html/0904.3370
- [B13] Moustakides, G. V. (2008). Sequential change detection revisited. Annals of Statistics 36(2). https://www.ssp.ece.upatras.gr/moustakides/downloads/journals/seq2008.pdf
- [B14] Lucas, J. M. & Saccucci, M. S. (1990). Exponentially Weighted Moving Average Control Schemes. Technometrics 32(1). https://www.stat.cmu.edu/technometrics/90-00/vol-32-01/v3201001.pdf
- [B15] Truong, C., Oudre, L., Vayatis, N. (2020). Selective review of offline change point detection methods. Signal Processing 167. https://arxiv.org/abs/1801.00718
- [B16] Makridakis, S. et al. (2023/2024). The M6 forecasting competition. IJF; arXiv:2310.13357. https://arxiv.org/html/2310.13357v1
- [B17] Kaggle. Jane Street Market Prediction. https://www.kaggle.com/competitions/jane-street-market-prediction/overview/citation
- [B18] Kaggle. Jane Street Real-Time Market Data Forecasting. https://www.kaggle.com/competitions/jane-street-real-time-market-data-forecasting
- [B19] Blum, A. & Hardt, M. (2015). The Ladder: A Reliable Leaderboard for Machine Learning Competitions. ICML; arXiv:1502.04585. https://arxiv.org/abs/1502.04585
- [B20] Gebru, T. et al. (2018/2021). Datasheets for Datasets. CACM; arXiv:1803.09010. https://arxiv.org/abs/1803.09010
- [B21] Tartakovsky, A. G. & Moustakides, G. V. (2010). State-of-the-Art in Bayesian Changepoint Detection. https://www3.stat.sinica.edu.tw/sstest/oldpdf/A21n25.pdf （BOCPD 基线实现参考，WS5 R7）
- [B23] Mitchell, M. et al. (2019). Model Cards for Model Reporting. FAT*. https://arxiv.org/abs/1810.03993

### P：评测协议补充（A4 核实）
- [P4] NIST/SEMATECH e-Handbook §6.3.2 / §6.3.2.1（ARL 定义）. https://www.itl.nist.gov/div898/handbook/pmc/section3/pmc32.htm
- [P6] Holm, S. (1979). A simple sequentially rejective multiple test procedure. Scand. J. Statist. 6(2). https://en.wikipedia.org/wiki/Holm–Bonferroni_method
- [P7] Benjamini, Y. & Yekutieli, D. (2001). The control of the false discovery rate in multiple testing under dependency. Ann. Statist. 29(4). https://doi.org/10.1214/aos/1013699998
- [P8] Demšar, J. (2006). Statistical Comparisons of Classifiers over Multiple Data Sets. JMLR 7. https://jmlr.org/papers/volume7/demsar06a/demsar06a.pdf
- [P9] Brier score / BSS 定义. https://en.wikipedia.org/wiki/Brier_score

### F：因子衰减与 A 股案例（A2 核实；T1/T2/T3 见括注）
- [F1] McLean, R.D., Pontiff, J. (2016). Does Academic Research Destroy Stock Return Predictability? JF 71(1). https://doi.org/10.1111/jofi.12365 （T1）
- [F2] McLean & Pontiff 工作论文版. https://www.hec.ca/finance/Fichier/McLean.pdf （T2）
- [F3] Falck, A., Rej, A., Thesmar, D. (2022). When do systematic strategies decay? QF 22(11). https://doi.org/10.1080/14697688.2022.2098810 ；预印本 https://arxiv.org/abs/2105.01380 （T1/T2）
- [F4] Chordia, T., Goyal, A., Saretto, A. (2020). Anomalies and False Rejections. RFS 33(5). https://doi.org/10.1093/rfs/hhaa018 （T1）
- [F5] Jacobs, H., Müller, S. (2020). Anomalies across the globe: Once public, no longer existent? JFE 135(1). https://doi.org/10.1016/j.jfineco.2019.06.004 （T1）
- [F6] Harvey, C.R., Liu, Y., Zhu, H. (2016). …and the Cross-Section of Expected Returns. RFS 29(1). https://academic.oup.com/rfs/article/29/1/5/1843824 （T1）
- [F7] Bailey, D.H., López de Prado, M. (2014). The Deflated Sharpe Ratio. JPM 40(5). https://davidhbailey.com/dhbpapers/deflated-sharpe.pdf （T1）
- [F8] Philips, T.K., Yashchin, E., Stein, D.M. (2003). Using Statistical Process Control to Monitor Active Managers. JPM 30(1). https://www.northinfo.com/documents/144.pdf （T1）；R 包 cusumActMgr https://rdrr.io/github/chindhanai/cusumActiveManager/man/cusumActMgr.html （T3）
- [F9] Lou, D., Polk, C. (2022). Comomentum. RFS 35(7). https://doi.org/10.1093/rfs/hhab117 （T1）
- [F10] Bonne, G. et al. (2018). MSCI Integrated Factor Crowding Model. https://www.msci.com/research-and-insights/paper/msci-integrated-factor-crowding-model （T2）；[F10b] 二手摘要 http://thefjg.blogspot.com/2018/06/msci-integrated-factor-crowding-model.html （T3）；[F10c] MSCI blog 2021 https://www.msci.com/research-and-insights/blog-post/eyeing-the-crowds-from-multiple-perspectives （T2）
- [F11] Ehsani, S., Linnainmaa, J.T. (2022). Factor Momentum and the Momentum Factor. JF 77(3). https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3014521 （T1）
- [F12] Arnott, Clements, Kalesnik, Linnainmaa (2023). Factor Momentum. RFS 36(8). https://doi.org/10.1093/rfs/hhad006 （T1）
- [F13] Arnott, Harvey, Kalesnik, Linnainmaa (2021). Reports of Value's Death May Be Greatly Exaggerated. FAJ 77(1). https://www.tandfonline.com/doi/full/10.1080/0015198X.2020.1842704 （T1）
- [F14] Liu, J., Stambaugh, R.F., Yuan, Y. (2019). Size and Value in China. JFE 134(1). https://www.sciencedirect.com/science/article/pii/S0304405X19300625 （T1）
- [F15] Lee, C.M.C., Qu, Y., Shen, T. (2017). Reverse Mergers, Shell Value, and Regulation Risk in Chinese Equity Markets. Stanford GSB WP 3604. https://www.gsb.stanford.edu/faculty-research/working-papers/reverse-mergers-shell-value-regulation-risk-chinese-equity-markets （T2）
- [F16] 东方证券金工, 2018-03. A 股小市值溢价的来源. https://pdf.dfcfw.com/pdf/H3_AP201803051098280707_1.pdf （T3）
- [F17] 中证网, 2017-12-13. 市值效应博弈加剧 小股票估值体系裂变. https://cs.com.cn/xwzx/201712/t20171213_5620502.html （T3）
- [F18] 国信证券金工, 2021-12. 动量类因子全解析. https://bigquant.com/wiki/doc/QCazSo8N8z （T3）
- [F19] 国信证券金工. 反转因子全解析. http://houtai.microbell.com/data/8ad051ed8ffd66b66f170c48475aab2e.html （T3）
- [F20] 东吴证券金工. 反转因子的精细结构. https://bigquant.com/wiki/doc/wA2Xh0NuAT （T3）
- [F21] 中信建投金工, 2021-03. 多因子跟踪月报：盈利成长表现不佳，缘于机构抱团回撤. https://file.iyanbao.com/pdf/1d9cc-cc74e46a-64e5-419b-aa04-fc5c1420dc74.pdf （T3）
- [F22] 中证网, 2021-02-23. 白马股"失前蹄". https://webtestone.cs.com.cn/xwzx/hg/202102/t20210223_6140632.html （T3）
- [F23] 信达证券, 2024-02. 本轮小市值风格与量化策略历史性回撤的分析与展望. https://fxbaogao.com/detail/4150220 （T3）
- [F24] 华尔街见闻, 2024-02. 春节前，量化基金究竟发生了什么？ https://wallstreetcn.com/articles/3708810 （T3）
- [F25] 国海证券, 2024-02-26. DMA 策略带来的小微盘股风险释放及前景展望. http://m.microbell.com/wap_detail.aspx?id=16d6841ebd1d0cc36d761b900e4f36a7 （T3）
- [F26] 海通证券 荀玉根, 2024-02. 反弹的时空和亮点. https://www.7hcn.com/article/455205-1.html （T3）
- [F27] 第一财经, 2024-02-07. 市场企稳下微盘仍跌 10%. https://www.yicai.com/news/101990110.html （T3）
- [F28a] 央广网, 2015-09-02. 中金所：进一步加大市场管控. http://finance.cnr.cn/jjgd/20150902/t20150902_519752973.shtml （官方公告转载）；[F28b] 财新周刊, 2015-09-04. 股指期货名存实亡. https://weekly.caixin.com/m/2015-09-04/100846432_all.html （T3）
- [F29] 全景网, 2015-09-09. 期指成交萎缩重创量化对冲. https://www.p5w.net/futures/zhzx/201509/t20150909_1187772.htm （T3）
- [F30a] 好买基金研究中心, 2015-01. 2014 年 12 月私募月报. https://www.p5w.net/fund/smjj/201501/t20150115_915691.htm （T3）；[F30b] 全景网, 2014-12-24. 衍生工具缺席 量化对冲基金折戟期指. https://www.p5w.net/futures/zhzx/201412/t20141224_889505.htm （T3）
- [F31a] 金融研究, 2017(9). 我国股票市场熔断机制的磁力效应. http://www.jryj.org.cn/CN/10.12094/1002-7246(2017)09-0161-17 （T1）；[F31b] IREF (2020). Intraday price jumps, market liquidity, and the magnet effect of circuit breakers. https://www.sciencedirect.com/science/article/abs/pii/S1059056020301428 （T1）
- [F32] 信达证券金工, 2024-08-04. 揭秘红利近期为何走弱. https://finance.sina.com.cn/roll/2024-08-04/doc-inchqank5921967.shtml （T3）
- [F33] 海通证券, 2024-12-24. 风格择时年度复盘. https://pdf.dfcfw.com/pdf/H3_AP202412241641419789_1.pdf （T3）
- [F34] 华泰证券金工, 2020-03-31. 重剑无锋：低波动 Smart Beta. https://finance.sina.cn/2020-03-31/detail-iimxxsth2924448.d.html （T3）；[F34b] 格隆汇, 2024. 红利低波还能持续跑赢吗？ https://www.gelonghui.com/p/681715 （T3）
- [F35] 中信建投金工, 2017-11-13. 如何正确理解近期热度极高的低波动率因子. http://www.7788jpj.com/xw_2/n/37585224.htm （T3）
- [F36a] 广发策略, 2017-08-03. 外资"北上"影响几何？ http://www.cs.com.cn/gppd/201708/t20170803_5407249.html （T3）；[F36b] 兴证策略. 16 年以来，外资配置思路如何变化？ https://m.zhitongcaijing.com/contentnew/appcontentdetail.html?content_id=866787 （T3）
- [F37] Smart money or chasing stars: Evidence from northbound trading in China. IJFE 29(2), 2024. https://ideas.repec.org/a/wly/ijfiec/v29y2024i2p1781-1803.html （T1）
- [F38] Li, B. et al. (2023). The evolvement of momentum effects in China. RIBAF 64. https://centaur.reading.ac.uk/109131/8/RIBAF-D-22-00201-R2.pdf （T1）
- [F39] 东方证券金工, 2020-11-16. 涨停板事件对股票价格行为的影响. http://m.microbell.com/wap_detail.aspx?id=3073860 （T3）
- [F40] 金融研究. 涨跌停制度变革、股票流动性与资本市场表现. http://www.jryj.org.cn/CN/abstract/abstract1316.shtml （T1）
- [F41] 深交所创业板交易特别规定, 2020-08-22. https://stock.pingan.com/upload/20200822/202008221598099998952.pdf （官方规则转载）
- [F42a] 中证网, 2021-10-15. 量化私募业绩回撤真相起底. https://www.cs.com.cn/tzjj/smjj/202110/t20211015_6210595.html （T3）；[F42b] 中国证券报, 2021-11-29. 量化私募面临膨胀之困. https://epaper.cs.com.cn/zgzqb/html/2021-11/29/nw.D110000zgzqb_20211129_1-J04.htm （T3）
- [F43] 国金证券, 2022-01. 股票量化策略私募基金年报（2021）. http://pdf.dfcfw.com/pdf/H301_AP202201241542344684_1.pdf （T3）
- [F44] 国金证券, 2023-01. 波动与分化加剧，高超额渐行渐远——股票量化策略 2022 年回顾. https://pdf.dfcfw.com/pdf/H301_AP202301181582105609_1.pdf （T3）
- [F46] 朱昂（财新博客）, 2017. A 股正在发生变化 小市值因子开始失效. http://zhuang.blog.caixin.com/archives/162912 （T3）

---

## 11. 内部推断日志

- [I0] 244 交易日/年约定；"因子定义 hash 冻结、改定义即新因子"为治理规则设计。
- [I1] L1 风格年化波动 4–8%、相关矩阵、长期 IR ±0.2–0.3 为 Barra CNE 常见量级的经验设定；DSR 代入 N=500–2000、σ_SR=0.3–0.5 得健康期 IR 选择偏差量级 1.0–1.8。
- [I2a] IC 通道 SNR 0.25（均值 0.025 / 日标准差 0.10）为 A 股日频 rank IC 经验区间，应作参数扫描。
- [I2b] CUSUM 延迟按 KL=δ²/2 缩放：IR 1→0 约为 0.5→0 的 1/4，IR 1→0.5 与 0.5→0 相同（≈41 月）；Siegmund 近似在 ARL0=1260 下给 IR 1→0.5 零态 CED≈670 日。未仿真。
- [I3] 功效仿真 beta=0、路径独立 F_t 以保证 ARL0 估计无偏；库级剥离与因子动量共同成分、A 类衰减期相关性上升的交互需在 L1 显式测试。
- [I4] 数据集规模以"因子-年"与"注入事件数"公布，而非序列条数。
- [I4-A2] B 类风格暴露漂移 |β| 0→0.3–0.5、历时 6–18 月，为 A2 基于案例 3/10/11 的定性工作区间。
- [I5] "2024-02 量级 = 暴露因子 20 日 σ 累计回撤、修复一半"为粗略折算；[I5'] 案例 14 的 A 股映射为类比推断；[I5-A5] 弱档"≥1 基线检出 <50%"为 A5 的经验性难度阈值。
- [I6a] κ≥0.6（substantial agreement 常用下限）与区间重叠 ≥50% 为设计选择；[I6b] 纯数据故障 E 型靠内部记录与 L2 注入；[I6c] 库级剥离只测一种方法，PCA / 全样本回归掩蔽更强为推断。
- [I7] JM2020 中国 VW 系数 −0.275（t −1.74）只是边际显著，作为 A 股残留比例中心上移的方向性依据而非幅度。
- [I8] 影子运行入口"前 3 且 L3 无否决"、"确认日 + 20 交易日"为设计选择。
- [I9] "≈8000+ 条"为按 ≥800/类型 × 5 类 + 同量对照的推算。
- [I10] 容差 M 两档：变点 MLE 定位误差 O(1/δ²) ≈ 250 日。
- [I13] 操作点两档与 100 因子库误报换算。
- [I16] MID 数值与"优于"三条件。
- [I17] 每类型 800 episode 的功效计算（5pp 胜率差、80% 功效、双侧 5%）。
- [I20]–[I22] Ladder 步长、RG 处理规则、因果截断审计为 FDB 落地设计。
- [I-v1] §5.1 库比例表 12 个百分数、A_logistic 公式与 w=D/8 为综合稿设计选择，W3 冒烟后可调。
- [I-inj] §5.2 L2 注入机制（收益差额平移 / IC 比例缩放 / B 类叠加真实风格收益 / E 类改净值或噪声）为综合稿设计，需写入 WS3 规格并由 R4 实现、R10 复核。
- [X1 裁决] 一阶渐近 CADD≈|log α|/KL 在 KL·γ=O(1) 区不适用，以 Siegmund 近似与仿真为准；复核 agent 独立 Monte Carlo 复现。

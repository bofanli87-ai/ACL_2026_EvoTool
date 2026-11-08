# g15-caller 进化轨迹审计

结论：g15-caller 被保留且被用于最终测试，但没有得到充分的父代搜索预算。其 Selection 平均 Reward 较高，父代抽样却按逐题 Win Count 分配；它始终只有 1/30 的抽样概率。三个直接后代均未留存，继承链在下一代中断。现有日志能够定位这两个环节，但不能证明改 Selection 后一定提分，也不能确认并列得分是主要原因。

## 数据来源和口径

- 1 epoch：`tmp/evotool_latest_audit/results/feedback_fixed_1ep`，30 代。
- 3 epochs：`tmp/evotool_latest_audit/results/aligned_comparison_3ep`，90 代。
- 两次均为 seed 42、90 train / 30 selection / 30 test、diversity Selection。
- 排除 `aligned_comparison_1ep`：这是修复反馈前的旧实验，不是导师此次讨论的 25/30 结果。
- 以原始 `runlog.jsonl`、`evolution.json` 和测试 episodes 为依据，不依赖可能陈旧的 comparison 汇总。源日志 SHA256 保存在 `audit.json`。
- generation 使用原日志从 0 开始的编号；表格 epoch 改为从 1 开始。g15 是第 16 次 Mutation。
- 每代 Population snapshot 是选择结束后的快照。因此分析第 g 代抽样时使用第 g−1 代快照。概率按整数 Win Count / 30 计算，避免日志四位小数舍入。
- no-op Mutation 可能返回 Parent 本身，Child ID 与 Parent ID 相同；这种记录不构成新的继承边。

## 1. 两次运行的总体对照

| 指标 | 1 epoch | 3 epochs |
|---|---:|---:|
| 总代数 | 30 | 90 |
| Initial 被选作 Parent | 27 | 74 |
| g4-planner 被选作 Parent | 2 | 12 |
| g15-caller 被选作 Parent | 1 | 3 |
| g67-caller 被选作 Parent | 0 | 1 |
| 通过训练 mini-batch 接受门槛 | 11 | 28 |
| 通过接受门槛且当代保留下来的新 Child | 2 | 3 |
| 接受后当代立即淘汰 | 9 | 25 |
| 最终部署 | g15-caller | g15-caller |
| 测试成功数 | 25/30 | 25/30 |
| 总 Token（含测试，原始结果口径） | 1,487,395 | 3,048,933 |

3 epochs 中各 epoch 的 Parent 分布：

| Epoch | Initial | g4 | g15 | g67 | 接受 / 新 Child 留存 |
|---|---:|---:|---:|---:|---:|
| 1 | 27 | 2 | 1 | 0 | 11 / 2 |
| 2 | 25 | 4 | 1 | 0 | 9 / 0 |
| 3 | 22 | 6 | 1 | 1 | 8 / 1 |

额外 60 代只有两次以 g15 为 Parent。新增的唯一留存策略是 g67，并未替代最终部署的 g15。

## 2. 为什么 Reward 高却很少被抽到

g15 在 g15 代由 Initial 直接变异产生，训练 mini-batch Reward 从 0.3833 提升至 0.6167，进入 Population。

| 代末区间 | Initial：Wins / 权重 | g4：Wins / 权重 | g15：Wins / 权重 | g67：Wins / 权重 |
|---|---|---|---|---|
| g0–g3 | 30 / 100% | — | — | — |
| g4–g14 | 26 / 86.67% | 4 / 13.33% | — | — |
| g15–g66 | 25 / 83.33% | 4 / 13.33% | 1 / 3.33% | — |
| g67–g89 | 24 / 80% | 4 / 13.33% | 1 / 3.33% | 1 / 3.33% |

Selection 平均 Reward：Initial=0.6362，g4=0.7062，g15=0.7063；后加入的 g67=0.7063。这里是四位小数的 Reward，不是成功率；g15 与 g4 差距很小，不能据此声称存在显著质量差异。

默认父代抽样使用 Win Count，而非平均 Reward。每道 Selection 题只给一个策略记一次胜利。因此平均 Reward 排名与抽样权重排名不一致，是代码允许的结果。

- 1 epoch：g15 在 g16–g29 有 14 次可抽样机会，概率和为 14/30=0.467，实际抽到 1 次（g17）。
- 3 epochs：g15 在 g16–g89 有 74 次可抽样机会，概率和为 74/30=2.467，实际抽到 3 次（g17、g44、g89）。
- 从产生到结束，g15 未被淘汰：分别出现在 15 和 75 个代末快照中。

这说明日志没有显示“抽样器异常地跳过 g15”。低利用程度主要体现为预先分配的概率很低。上述概率和是沿已观察 Population 轨迹计算的条件预算，不是其他随机种子或其他 Selection 下的反事实结果。

## 3. 三个后代在哪里消失

| Child | 改动模块 | Parent → Child 批次 Reward | 接受 | 留存 | 中断环节 |
|---|---|---|---|---|---|
| g17-caller | Caller | 0.6167 → 0.6167 | 否 | 否 | 严格提升门槛未通过 |
| g44-planner | Planner | 0.6000 → 0.8500 | 是 | 否 | Population Selection 当代淘汰 |
| g89-planner | Planner | 0.1208 → 0.3708 | 是 | 否 | Population Selection 当代淘汰 |

继承关系均为 `init → g15-caller → Child`；没有留存的孙代。完整 Prompt before/after 见 `3ep_g15_descendants.csv`。

- g17 在 g15 的去重规则后追加“重复 points/subgoal 时使用不同 identifier 或 context”。已发生有效文本修改，但未改善当前批次，日志记录 rejected。
- g44 修改 Planner，要求对每个 case number/court 分别查询状态和庭审日期。它继承 g15 的 Caller，并在批次上提高 0.25，但未留存。
- g89 修改 Planner，加入天气、家电和事件检索的具体工具选择规则。它同样继承 g15 的 Caller，批次提高 0.25，但未留存。

按归档代码，只有取得至少一次逐题胜利的策略才被 diversity 保留。因此 g44、g89 当代被淘汰意味着它们在当时竞争集合中没有获得分配给自己的逐题胜利。这是由代码和留存结果推导的，原始日志未保存这两个被淘汰策略的逐题 Reward 或淘汰前完整矩阵。

“没有获分配的胜利”不等于“所有题都退化”，也不等于“与 Parent 完全相同”：它可能与既有策略并列，也可能在部分题优于 Parent 但仍低于其他候选。现有日志无法区分。

## 4. 1 epoch 与 3 epochs 是否只是总分相同

前 30 代的 Parent、Child、batch IDs、接受判定、Population snapshot 全部一致。Prompt after 在 g0 有差异，其他 29 代一致；因此不能称两次运行逐字完全相同。

两次 g15 的 Caller 文本完全相同，且均直接来自 Initial，最终部署 ID 也相同。30 道测试题的成功/失败向量一致，29 道的 predicted calls 完全相同，只有 bfcl_149 调用记录不同。两次测试 mean_reward 分别为 72.0 和 72.25，所以“结果相同”应限定为部署策略及成功率/成败分布相同，而非全部输出完全相同。

g15 之后日志中的最佳 Selection Reward 保持在 0.7063（四位小数），新增两轮没有产生最终被部署的更优策略。

## 5. 并列偏差：已证实的机制与未证实的归因

归档 `src/evolve/select.py` 使用 `max(range(len(population)), key=...)`，并列时选择排列最前面的策略。新接受的 Child 被追加在 Population 末尾；Initial 在所有快照中始终排第一。这确实构成先来策略在并列时占优的机制。

但日志只存每个存活策略的平均 Reward、Wins 和权重，未保存 Selection 的逐题 Reward 矩阵。归档 agent 的 `_EPISODE_CACHE` 是进程内字典，本次查找未发现相应落盘矩阵。因此不能从 25/30 的 Initial Wins 推断其中多少来自并列，也不能离线算出随机打破并列或平分胜利后的真实权重。

已完成：确认实现规则、确认 Population 顺序、量化实际预算与继承中断。

尚需数据：逐策略、逐 Selection 题的 Reward，包括被接受后淘汰的 Child，才能量化并列比例及替代 tie-breaking 的影响。这需要补评或恢复其他实际缓存；不能用已有测试集输出冒充 Selection 结果。

## 6. 下一项最有针对性的实验

1. 补评 Initial、g4、g15、g44、g67、g89 在相同 30 道 Selection 题上的逐题 Reward，形成 6×30 矩阵；固定原模型与执行配置。新生成矩阵是复评结果，不是原始缓存的精确恢复。
2. 在此矩阵上统计并列、复算当前赢家及替代 tie-breaking，检查 g44/g89 为什么没有获得胜利。
3. 重新进化时，先做 `diversity + win` 与 `diversity + val_acc` 对照，保持接受门槛等其他设置一致，检验提高 g15 类策略利用率的作用。注意 val_acc 实际按平均 Reward 抽样，且无法挽回已经被 Population Selection 淘汰的策略。

当前证据支持“低父代预算 + 后代留存失败”是已观察到的积累中断路径，尚不足以把根因排他地归为搜索、规则冲突或 Mutation 能力不足。

## 交付与复现

- `1ep_generations.csv` / `3ep_generations.csv`：每代 Parent、Child、接受/留存、训练 Reward、Selection 最优值、抽样前权重、g15 状态、继承链。
- `1ep_population.csv` / `3ep_population.csv`：每代每个存活策略的平均 Selection Reward、Win Count、权重和顺序。
- `1ep_g15_descendants.csv` / `3ep_g15_descendants.csv`：g15 后代及完整修改文本。
- `audit.json`：来源校验和、统计、Population 变化阶段和两次运行对照。
- `analyze_trace.py`：仅使用 Python 标准库读取归档文件，不调用模型。

在项目根目录复现：`python outputs/evotool_review/g15_trace_20261103/analyze_trace.py`。

验证包括：代数连续性、每代 Parent 必须存在于上一代 Population、各代 Wins 合计等于 Selection 大小、测试任务 ID 集合一致。全部通过。

# Self-Evolving Agent 能力积累：现阶段总分析

## 分析范围

补了三组分析：

1. 完整检查了 90 代进化过程中的所有候选。
2. 对关键历史策略和组合策略，在原 30 道及 56 道独立未见任务上各重复评测 3 次。
3. 对 Seed 42、43、44 的三个 30 代搜索轨迹做完整谱系矩阵，比较不同搜索轨迹中能力的产生和流失。

## 一、进化产生了多少新改进，主要在哪里流失？

### 1.1 90 代完整记录

90 次迭代中，有 84 次真正修改了 Prompt。

- 37/84 次修改相对自己的 Parent 至少多做对了 1 题，说明 Mutation 确实经常能产生局部收益。
- 但只有 4/84 次扩大了“历史上所有策略的成功任务并集”。大部分所谓新增，只是在重新找到历史上已经出现过的能力。
- 一共出现 47 个新增任务事件，同时出现 11 个回归任务事件。也就是说，新能力产生的同时，旧能力也会被改坏。
- Initial 是 22/30，历史并集达到 26/30，说明进化过程确实发现过 4 个 Initial 不会的新任务。
- 最终 Population 只覆盖 24/30，历史上发现过的 `bfcl_13`、`bfcl_16` 最后丢失。

最关键的是流失位置：

| 局部有效 Mutation 的去向 | Mutation 数 |
|---|---:|
| 有收益，但没有通过训练批次门槛 | 23 |
| 通过训练门槛，但没有进入 Population | 12 |
| 最终进入 Population | 2 |

也就是 37 个局部有效 Mutation 中，35 个没有进入 Population，比例为 94.6%。因此在这个 90 代轨迹里，最明显的瓶颈不是“完全产生不了改进”，而是**当前评价和选择过程没有可靠识别、保留这些改进**。

另一个重要现象是，真正扩大历史任务覆盖的 4 次修改全部发生在前 13 代。后面 77 代仍然会产生相对 Parent 的局部收益，但历史任务并集不再增长。这说明在原 30 题上，后续进化越来越像重复发现已有行为，而不是持续拓展能力边界。

> **原始数据对应：**
> - 总数及比例：[`audit_summary.json`](https://github.com/bofanli87-ai/ACL_2026_EvoTool/blob/codex/mentor-intervention-report/reports/capability_accumulation/audit_summary.json) 中的 `capability_generation`、`regression_and_net`、`selection_and_retention` 和 `final_coverage`。
> - 90 次 Parent→Child 明细：[`generation_ledger_30tasks.csv`](https://github.com/bofanli87-ai/ACL_2026_EvoTool/blob/codex/mentor-intervention-report/reports/capability_accumulation/generation_ledger_30tasks.csv)，主要字段为 `prompt_changed`、`gains`、`regressions`、`historically_novel`、`accepted_on_batch`、`entered_population`、`gain_ids` 和 `regression_ids`。
> - 37 个有效 Mutation 的流失位置：[`loss_stage_30tasks.csv`](https://github.com/bofanli87-ai/ACL_2026_EvoTool/blob/codex/mentor-intervention-report/reports/capability_accumulation/loss_stage_30tasks.csv)，按 `stage` 字段汇总得到 23、12、2。
> - 4 项历史新能力及最终状态：[`capability_first_discoveries_30tasks.csv`](https://github.com/bofanli87-ai/ACL_2026_EvoTool/blob/codex/mentor-intervention-report/reports/capability_accumulation/capability_first_discoveries_30tasks.csv)。
> - 历史并集、Population 并集及最佳单策略的逐代变化：[`coverage_curves_30tasks.csv`](https://github.com/bofanli87-ai/ACL_2026_EvoTool/blob/codex/mentor-intervention-report/reports/capability_accumulation/coverage_curves_30tasks.csv)。

### 1.2 不同 Seed 是否也有类似现象？

三个 30 代轨迹的结果如下：

| Seed | 有局部新增的候选 | 历史新增任务数 | 历史并集 | 最终 Population 并集 | 最终最佳单策略 | 历史最佳单策略 |
|---:|---:|---:|---:|---:|---:|---:|
| 42 | 13 | 4 | 26 | 26 | 24 | 25 |
| 43 | 9 | 4 | 26 | 23 | 23 | 25 |
| 44 | 7 | 3 | 25 | 23 | 23 | 24 |

三条轨迹一共产生 29 个有局部新增的候选，只有 5 个进入 Population，约 82.8% 没有进入。10 次真正扩大历史并集的事件中，也只有 2 次对应候选进入了 Population。

三个 Seed 的具体表现不同：

- Seed 43 和 44 是明显的“发现了，但最终 Population 丢了”，历史并集分别比最终 Population 多 3 题和 2 题。
- Seed 42 没有丢掉 Population 层面的并集，但 26 题能力分散在多个策略里，最佳单策略只有 24 题。
- 三个 Seed 的历史最佳单策略都高于最终 Population 中的最佳单策略，差距分别为 1、2、1 题。

因此其实可以判断：每条轨迹都发现过比最终单策略更好的历史信息，而现有流程没有稳定地把它变成最终单策略能力。有时是能力没进入或没留在 Population，有时是留在多个策略中却没有整合起来。

> **原始数据对应：**
> - 三个 Seed 的汇总表：[`seed_comparison.json`](https://github.com/bofanli87-ai/ACL_2026_EvoTool/blob/codex/mentor-intervention-report/reports/capability_accumulation/seed_comparison.json)。
> - 各 Seed 的历史并集、最终 Population、历史最佳单策略及丢失任务：[`seed42_lineage/summary.json`](https://github.com/bofanli87-ai/ACL_2026_EvoTool/blob/codex/mentor-intervention-report/reports/capability_accumulation/seed42_lineage/summary.json)、[`seed43_lineage/summary.json`](https://github.com/bofanli87-ai/ACL_2026_EvoTool/blob/codex/mentor-intervention-report/reports/capability_accumulation/seed43_lineage/summary.json)、[`seed44_lineage/summary.json`](https://github.com/bofanli87-ai/ACL_2026_EvoTool/blob/codex/mentor-intervention-report/reports/capability_accumulation/seed44_lineage/summary.json)。
> - “29 个有局部新增候选、5 个进入 Population、10 次扩大历史并集、其中 2 次进入 Population”来自三个 `edges.csv` 的合并统计：筛选 `gains > 0`、`entered_population = 1`、`historically_novel > 0`。对应文件为 [`Seed 42`](https://github.com/bofanli87-ai/ACL_2026_EvoTool/blob/codex/mentor-intervention-report/reports/capability_accumulation/seed42_lineage/edges.csv)、[`Seed 43`](https://github.com/bofanli87-ai/ACL_2026_EvoTool/blob/codex/mentor-intervention-report/reports/capability_accumulation/seed43_lineage/edges.csv) 和 [`Seed 44`](https://github.com/bofanli87-ai/ACL_2026_EvoTool/blob/codex/mentor-intervention-report/reports/capability_accumulation/seed44_lineage/edges.csv)。
> - 最终最佳单策略由三个 Seed 的 `summary.json` 中 `final_population_ids`，对应各自 [`matrix.csv`](https://github.com/bofanli87-ai/ACL_2026_EvoTool/blob/codex/mentor-intervention-report/reports/capability_accumulation/seed42_lineage/matrix.csv) 的 `successes` 字段计算；Seed 43、44 的矩阵分别见 [`seed43_lineage/matrix.csv`](https://github.com/bofanli87-ai/ACL_2026_EvoTool/blob/codex/mentor-intervention-report/reports/capability_accumulation/seed43_lineage/matrix.csv) 和 [`seed44_lineage/matrix.csv`](https://github.com/bofanli87-ai/ACL_2026_EvoTool/blob/codex/mentor-intervention-report/reports/capability_accumulation/seed44_lineage/matrix.csv)。

## 二、不同有效改进能否稳定积累？阻碍在哪里？

偶尔可以，但没有保证，而且对上下文非常敏感。

### 2.1 自然谱系中存在成功积累

90 代自然谱系中，`g21`、`g32`、`g48`、`g64` 都曾在保留 `g4` 已有改进的基础上继续新增成功，达到 25/30。这证明有效修改并非天然互斥，进化过程有能力产生更强 Child。

问题是，这 4 个成功积累的策略最后全都没有进入 Population。

> **原始数据对应：**[`generation_ledger_30tasks.csv`](https://github.com/bofanli87-ai/ACL_2026_EvoTool/blob/codex/mentor-intervention-report/reports/capability_accumulation/generation_ledger_30tasks.csv) 中筛选 `gen = 21, 32, 48, 64`。这四行的 Parent 均为 `g4-planner`，`gains > 0`、`regressions = 0`、`success_child = 25`，且 `entered_population = 0`。

### 2.2 Selection 分数没有可靠反映真实价值

原 30 题重复评测中：

- `g4` 三轮都是 24/30。
- `g21` 三轮也是 24/30，原先单次评测中看到的 Selection 增益没有稳定复现。
- `g32` 三轮都是 25/30，稳定高于 `g4`。

但在 56 道独立未见任务上：

- `g4` 三轮都是 46/56。
- 被淘汰的 `g21` 三轮都是 49/56，是所有 8 个被测策略中最好。
- `g32` 三轮都是 47/56。

这说明：**Selection 集上看不出优势的候选，可能在未见任务上反而更好。**`g21` 不是没有价值，而是当前 Selection 没有识别出它的泛化价值。这也是“有效改进为何被丢掉”的一部分原因。

> **原始数据对应：**
> - 三轮汇总：[`stability_eval/policy_summary.csv`](https://github.com/bofanli87-ai/ACL_2026_EvoTool/blob/codex/mentor-intervention-report/reports/capability_accumulation/stability_eval/policy_summary.csv)，按 `split` 和 `policy` 查看 `mean_successes`、`min_successes`、`max_successes`。
> - Parent–Child 的稳定新增与回归：[`stability_eval/analysis.json`](https://github.com/bofanli87-ai/ACL_2026_EvoTool/blob/codex/mentor-intervention-report/reports/capability_accumulation/stability_eval/analysis.json) 中的 `repeated_parent_child_comparisons`。
> - 每道题、每个策略、每轮的原始结果：[`stability_eval/episodes.jsonl`](https://github.com/bofanli87-ai/ACL_2026_EvoTool/blob/codex/mentor-intervention-report/reports/capability_accumulation/stability_eval/episodes.jsonl)。

### 2.3 简单组合不能保证把收益相加

未见任务上的组合结果更直接：

| 组合 | 两个组件各自成功任务的并集 | 组合后实际成功 | 丢失 |
|---|---:|---:|---:|
| `g4_g23` | 49 | 48 | 1 |
| `g44_g21` | 51（按共同可评的 55 题） | 45 | 6 |

`g4_g23` 有一定积累效果：组合后的 48/56 高于 `g4` 的 46 和 `g23` 的 43，但仍没有完全达到两个组件的理想并集。

`g44_g21` 的问题更明显：`g21` 的 Caller 在 `g4` Planner 下有效，换到 `g44` Planner 后，它在未见任务上的 6 项互补收益全部没有保留下来，组合结果几乎退化成 `g44` 本身。

这说明局部修改不是可以随意拼接的独立零件。一个 Caller 修改是否有效，可能依赖 Parent Planner 产生什么样的中间计划；Planner 一变，Caller 原本依赖的输入形式也会变，原来的收益就可能失效。

> **原始数据对应：**[`stability_eval/analysis.json`](https://github.com/bofanli87-ai/ACL_2026_EvoTool/blob/codex/mentor-intervention-report/reports/capability_accumulation/stability_eval/analysis.json) 中的 `repeated_combination_analysis` 和 `combination_analysis`。三轮结果分别查看 `component_union_by_repeat`、`combo_successes_by_repeat`、`gap_by_repeat` 和 `stable_lost_ids`；单轮明细对应 `component_union`、`combo_successes`、`combination_gap` 和 `lost_from_component_union`。逐题原始输出仍在 [`stability_eval/episodes.jsonl`](https://github.com/bofanli87-ai/ACL_2026_EvoTool/blob/codex/mentor-intervention-report/reports/capability_accumulation/stability_eval/episodes.jsonl)。

## 三、目前看到的四个阻碍因素

### 3.1 训练批次和 Selection 覆盖太窄

一个修改可能只改善少量任务，也可能改善训练批次没有覆盖到的行为。当前门槛容易把这类候选判成“没有价值”。90 代中，23/37 个局部有效 Mutation 首先死在训练批次门槛。

### 3.2 选择过程更关注完整策略分数，没有单独记住局部贡献

一个 Child 即使有新能力，只要总分没有明显上升，或者同时有小幅回归，就可能无法进入 Population。当前系统基本把整个 Prompt 当成一个整体判断，没有可靠记录“这次修改具体带来了哪项能力”。

### 3.3 新增和回归会同时发生

90 代中有 10/84 次实际修改丢失了 Parent 至少一项成功，共发生 11 个回归任务事件。跨 Seed 的 86 次实际修改中，也有 13 次候选发生回归。修改不是单向变好，而是在不同能力之间做交换。

### 3.4 不同模块之间存在上下文和接口依赖

Caller 修改不是脱离 Planner 独立工作的。换 Parent、换计划结构或换 Prompt 顺序后，同一句修改可能不再有效。`g44_g21` 的结果说明，这种非线性交互不只是原 30 题中的偶然现象，在未见任务上也会稳定出现。

> **原始数据对应：**
> - 训练门槛与 Population 流失：[`loss_stage_30tasks.csv`](https://github.com/bofanli87-ai/ACL_2026_EvoTool/blob/codex/mentor-intervention-report/reports/capability_accumulation/loss_stage_30tasks.csv) 的 `stage`、`accepted_on_batch`、`entered_population`。
> - 90 代回归：[`generation_ledger_30tasks.csv`](https://github.com/bofanli87-ai/ACL_2026_EvoTool/blob/codex/mentor-intervention-report/reports/capability_accumulation/generation_ledger_30tasks.csv) 的 `regressions` 和 `regression_ids`；总体汇总见 [`audit_summary.json`](https://github.com/bofanli87-ai/ACL_2026_EvoTool/blob/codex/mentor-intervention-report/reports/capability_accumulation/audit_summary.json) 的 `regression_and_net`。
> - 跨 Seed 回归：三个 Seed 的 `edges.csv`，筛选 `regressions > 0` 后合计 13 个候选。
> - 跨模块上下文依赖：[`stability_eval/analysis.json`](https://github.com/bofanli87-ai/ACL_2026_EvoTool/blob/codex/mentor-intervention-report/reports/capability_accumulation/stability_eval/analysis.json) 中 `g44_g21` 的组合分析及稳定丢失任务。

## 四、两个研究问题的当前回答

### 4.1 进化过程中产生了多少新改进，收益主要在哪个环节流失？

- Mutation 能产生局部改进，但真正拓展历史能力边界的比例很低。
- 最大规模的流失发生在训练门槛和进入 Population 之前。
- 历史发现的能力还会在后续 Population 中丢失。
- Selection 分数不能稳定识别候选的未见任务价值。

### 4.2 不同有效改进能否稳定积累，哪些因素会阻碍积累？

- 自然谱系和部分组合都证明改进可以积累。
- 但积累不是稳定过程；有的收益会回归，有的只分散保留在不同策略中，有的换一个 Parent 就失效。
- 主要阻碍包括评价覆盖不足、完整策略级选择、能力回归，以及跨模块上下文依赖。

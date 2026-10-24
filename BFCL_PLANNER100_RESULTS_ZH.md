# BFCL Planner 工具感知与结构化历史：100 题实验结果

日期：2026-10-24。实验设计见 `BFCL_PLANNER100_EXPERIMENT_ZH.md`，机器可读结果见 `results/planner100/`。

## 1. 实验设置

本实验使用 `evotool-qwen3:8b`、temperature 0、Caller Schema、冻结的初始四模块策略和同一批 100 道 BFCL 题，不运行 evolution，不使用 Repair。100 题与此前逐题分析的 30 题交集为 0。

两个实验因素为：

1. Planner 工具上下文：提供精确工具名、能力描述和完整参数 Schema，并要求按工具能完成的操作确定步骤粒度；
2. 结构化历史：向 Selector 和 Caller 保留此前调用的 subgoal、tool、arguments、status 和 output。

## 2. 总体结果

| 条件 | 成功率 | mean reward | tokens | 时间 | 平均 plan 步数 | 平均调用数 |
|---|---:|---:|---:|---:|---:|---:|
| Control | 36/100 | 37.99 | 301,897 | 674.5 s | 3.68 | 3.38 |
| Planner tools | 43/100 | 43.95 | 251,538 | 521.0 s | 2.68 | 2.58 |
| History | 38/100 | 39.31 | 330,458 | 689.9 s | 3.68 | 3.45 |
| Planner tools + History | **57/100** | **53.84** | 265,773 | 545.1 s | 2.68 | 2.58 |

相对 Control：

| 条件 | 新增成功 | 回归 | 净提升 | 双侧精确 McNemar p |
|---|---:|---:|---:|---:|
| Planner tools | 24 | 17 | +7 | 0.3489 |
| History | 3 | 1 | +2 | 0.6250 |
| Planner tools + History | 31 | 10 | **+21** | **0.00145** |

组合条件还显著优于两个单因素：相对 Planner tools 为新增 15、回归 1，p=0.000519；相对 History 为新增 31、回归 12，p=0.00540。

2×2 成功率交互为：

```text
57% - 43% - 38% + 36% = +12 percentage points
```

这是描述性的正交互效应，说明两项信息在当前设置下具有互补关系；不能把该数值本身当成交互项显著性检验。

## 3. 错误类型变化

| 条件 | Planning 失败标签 | Selection | Semantic argument | Schema/interface |
|---|---:|---:|---:|---:|
| Control | 45 | 47 | 14 | 7 |
| Planner tools | 10 | 14 | 39 | 9 |
| History | 47 | 48 | 11 | 5 |
| Planner tools + History | 10 | 14 | 25 | 7 |

Planner 工具上下文将 planning 标签从 45 降到 10、selection 从 47 降到 14，同时把平均 plan 从 3.68 步缩短到 2.68 步。这与“工具能力信息帮助 Planner 避免把一次工具操作拆成多个抽象步骤”的解释一致。

剩余主要错误转移到了 semantic argument。这里并不是工具信息造成了 25–39 个全新的参数错误；错误分类存在层级效应：调用数量和工具多重集合正确之后，诊断器才有条件进一步暴露参数值差异。

## 4. 正交互来自哪里

共有 8 题仅在组合条件下成功：

```text
bfcl_102, bfcl_111, bfcl_116, bfcl_143,
bfcl_31, bfcl_52, bfcl_91, bfcl_92
```

典型轨迹表现为：

- `bfcl_102`：分别预测纽约 3000 平方英尺和洛杉矶 4000 平方英尺房价；
- `bfcl_111`：分别检查 HSBC 与 Wells Fargo 的贷款资格；
- `bfcl_31`：分别查询 Charles Dickens/Boston 与 University of California/Los Angeles 的案件；
- `bfcl_92`：使用 4 秒和 10 秒分别计算电磁力。

Control 会产生大量数据收集、过滤或中间计算步骤。Planner tools 正确压缩成两次目标工具调用，但两个子目标都只写成相同的工具名，导致 Caller 两次生成第一组参数。History 单独保留参数，却无法修复原 Planner 的过度拆分。组合条件同时减少步骤，并让第二次 Caller 看到第一次实际参数，因此能生成另一实体或另一数值的调用。

另有 7 题在 Control 成功、Planner tools 回归后，被组合条件重新救回。这进一步说明历史信息能缓解部分由同名子目标造成的参数重复。

## 5. 回归原因

组合条件相对 Control 仍有 10 题回归：

```text
bfcl_105, bfcl_110, bfcl_124, bfcl_15, bfcl_35,
bfcl_62, bfcl_64, bfcl_65, bfcl_79, bfcl_86
```

例如 `bfcl_105` 要计算 10、20、30 年的现值，`bfcl_110` 要计算 15、20、30 年的房贷，`bfcl_86` 包含四组不同的 GCD/LCM 参数。Planner tools 输出多个相同工具名，Caller 会反复生成第一组参数。即使有历史，三组或四组并行要求仍可能无法稳定恢复当前步骤对应的目标值。

这暴露出新的信息瓶颈：当前 Planner 输入已经包含完整工具信息，但输出仍是无结构的字符串列表。模型把步骤压缩成工具名后，丢失了每一步与用户实体、数值和约束之间的绑定。结构化历史只能事后推断“哪些参数已使用”，无法明确表示“本步骤应该处理哪一组参数”。

## 6. 可以向导师报告的结论

这轮 100 题结果支持以下判断：

1. 公开代码中 Planner 看不到工具定义是实质性缺口。补充工具名、能力描述和完整 Schema 后，planning/selection 错误明显下降，步骤和调用也更紧凑。
2. 单独增加工具上下文还不稳定：成功率仅从 36% 到 43%，配对检验不显著，并产生 17 题回归。
3. 单独保留历史参数收益较小；但与工具感知 Planner 组合后达到 57%，相对 Control 的 +21 题具有显著配对差异。
4. 两者的作用不是简单相加。工具信息决定“需要几次调用”，历史帮助下游区分“此前已经调用了哪组参数”。
5. 当前更一般的共性问题是模块之间的信息表示不完整：Planner 输入缺少工具能力时会过度拆分；Planner 输出缺少实体与约束绑定时，下游会重复第一组参数；历史缺少调用参数时又无法识别已覆盖需求。

这些结果比单纯继续优化 Planner Prompt 更有研究价值，因为它们指向模块化 Agent 的信息接口设计，而不只是一条任务特定提示词。

## 7. 下一步实验

下一步应把 Planner 输出从字符串列表升级为结构化步骤，例如：

```json
{
  "plan": [
    {
      "goal": "predict the New York house price",
      "tool": "ml.predict_house_price",
      "argument_intent": {"location": "New York", "size": 3000}
    },
    {
      "goal": "predict the Los Angeles house price",
      "tool": "ml.predict_house_price",
      "argument_intent": {"location": "Los Angeles", "size": 4000}
    }
  ]
}
```

`argument_intent` 只来自用户任务和工具 Schema，不读取 gold。Selector 可验证工具名，Caller 根据本步骤的 goal、argument intent 和历史生成最终参数。

应在相同 100 题上先增加两个条件：`structured_plan` 与 `structured_plan + history`。主要目标不是继续抬高总分，而是检查当前 10 个组合回归能否恢复，同时保持 8 个组合独有成功。若结果稳定，再在新的 BFCL 原始样本上建立严格的 90/30/100 train/selection/test 划分，并扩展到其他 benchmark。

## 8. 结果文件

- `results/planner100/comparison.json`：总体、配对和交互统计；
- `results/planner100/*.episodes.jsonl`：四组逐题轨迹；
- `results/planner100/manifest.json`：样本 ID、配置和数据哈希；
- `configs/bfcl_planner100_*.yaml`：四组配置。

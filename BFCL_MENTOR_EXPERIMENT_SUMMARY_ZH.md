# BFCL 错误机制诊断与分层干预实验汇总

更新时间：2026-10-13（Asia/Shanghai）

## 1. 导师提出的研究问题

本轮实验不是继续叠加新的 LLM 或单纯追求更高分数，而是回答以下问题：

1. EvoTool 的提升主要来自 reasoning/planning 改善，还是来自输出格式、参数类型和接口约束修复？
2. Schema、EvoTool 和简单 Repair 的收益是重复还是互补？
3. 不同错误是否应在不同层干预：reasoning 错误修改 prompt，格式错误提供 Schema，确定性接口
   错误修改 code/validator？

为此，我们完成了 Baseline、Schema、简单 Repair、EvoTool、EvoTool+Schema 五个核心条件，并保存
了 held-out 测试集的逐题预测，进行严格配对比较。

## 2. 统一实验设置

| 项目 | 设置 |
|---|---|
| 模型 | `evotool-qwen3:8b`，Ollama，Qwen3-8B Q4_K_M |
| 温度 | 0.0 |
| 随机种子 | 42 |
| 数据 | `data_schema/bfcl/samples.json`，共 150 条 |
| 划分 | train/selection/test = 90/30/30 |
| 泄漏检查 | 所有条件 `held_out_leak=0` |
| 测试集 | 五个条件使用相同的 30 条 held-out 样本 |
| 进化预算 | EvoTool 条件为 1 epoch、batch size 3、30 generations |
| 部署方式 | selection mean reward 最高的单策略，不使用 ensemble |
| 评测 | BFCL 严格 AST 匹配 |

Schema 条件只把数据中原始工具参数 Schema 提供给 Caller，不增加修复模型，也不使用 gold。
Offline Repair 直接作用于同一次 Baseline 输出，只进行由 Schema 唯一确定的类型转换、递归容器
修复和受约束字段删除；它不补缺失参数、不猜参数值、不调用 LLM。gold 只在输出完成后用于评分和
错误分析。

## 3. 五个核心实验

### 3.1 Baseline

初始四模块策略 `init`，不向 Caller 提供 Schema，不执行 Repair，也不运行 prompt evolution。

- 成功：2/30（6.67%）
- mean reward：16.77
- tokens：78,656
- 时间：188.5 秒

失败样本的多标签错误分布为：schema/interface 21、planning 14、selection 14、semantic argument 3。
这表明初始模型既有接口构造错误，也有规划和工具选择错误。

对应文件：

- 配置：`configs/bfcl_diag_baseline.yaml`
- 汇总：`results/diag_baseline.json`
- 逐题结果：`results/diag_baseline.episodes.jsonl`
- 运行日志：`results/logs/bfcl__bfcl_diag_baseline.log`
- 结构化日志：`results/logs/bfcl__bfcl_diag_baseline.runlog.jsonl`
- 日志汇总：`results/logs/bfcl__bfcl_diag_baseline.runlog.summary.json`

### 3.2 Baseline + Schema

保持初始策略不变，只向 Caller 提供每个工具的原始参数 Schema。

- 成功：13/30（43.33%）
- mean reward：42.43
- tokens：91,203
- 时间：191.9 秒
- 相对 Baseline：新增成功 11，回归 0

Schema 将失败样本中的 schema/interface 标签从 21 个降为 0。剩余 17 个失败中，14 个属于
planning/tool-selection，3 个属于 semantic argument。

对应文件：

- 配置：`configs/bfcl_diag_schema.yaml`
- 汇总：`results/diag_schema.json`
- 逐题结果：`results/diag_schema.episodes.jsonl`
- 运行日志：`results/logs/bfcl__bfcl_diag_schema.log`
- 结构化日志：`results/logs/bfcl__bfcl_diag_schema.runlog.jsonl`
- 日志汇总：`results/logs/bfcl__bfcl_diag_schema.runlog.summary.json`

### 3.3 Baseline + 简单 Offline Repair

为排除 Ollama 即使在 temperature 0 下重复生成仍可能出现的输出波动，最终 Repair 结论不采用
独立在线重跑，而是把修正后的确定性 Repair 直接应用于同一次 Baseline 的逐题输出。

- Repair 前：2/30
- Repair 后：13/30（43.33%）
- 17 个样本发生修改，共 74 个 edit
- 新增成功 11，回归 0
- 不增加 LLM tokens

Schema 和 Offline Repair 修复的 11 个失败样本完全相同；二者最终 13 个成功样本的集合也完全
相同。把 Repair 应用于 Schema 输出时没有产生任何 edit，成功数仍为 13/30。这说明两种方法在
本测试集上的格式与接口收益几乎完全重复。

对应文件：

- Repair 实现：`src/schema_repair.py`
- 应用脚本：`scripts/apply_bfcl_repair_offline.py`
- 输入：`results/diag_baseline.episodes.jsonl`
- 输出：`results/diag_baseline_offline_repair.episodes.jsonl`
- Schema 输出上的审计结果：`results/diag_schema_offline_repair.episodes.jsonl`

说明：`results/diag_repair.json` 和 `results/diag_repair.episodes.jsonl` 是早期 Repair v1 在线重跑
结果。v1 当时未覆盖 BFCL 方言中的 `float`，且独立重跑混有生成波动，因此只保留作审计，不作为
最终 Repair 结论。

### 3.4 EvoTool

不提供 Schema，不执行 Repair；运行 blame-aware mutation 和 diversity-aware selection，共
30 generations。

- 成功：13/30（43.33%）
- mean reward：42.55
- tokens：1,107,334
- 时间：3,000.2 秒（约 50.0 分钟）
- 接受 mutation：8/30
- 最终部署：`g26-caller`

Mutation 分布：

| 模块 | 尝试 | 接受 |
|---|---:|---:|
| Planner | 9 | 6 |
| Selector | 2 | 0 |
| Caller | 19 | 2 |
| Synthesizer | 0 | 0 |

对应文件：

- 配置：`configs/bfcl_diag_evotool.yaml`
- 汇总：`results/diag_evotool.json`
- 逐题结果：`results/diag_evotool.episodes.jsonl`
- 运行日志：`results/logs/bfcl__bfcl_diag_evotool.log`
- 结构化日志：`results/logs/bfcl__bfcl_diag_evotool.runlog.jsonl`
- 日志汇总：`results/logs/bfcl__bfcl_diag_evotool.runlog.summary.json`

### 3.5 EvoTool + Schema

使用相同进化预算，同时向 Caller 提供 Schema，不执行 Repair。

- 成功：16/30（53.33%）
- mean reward：49.77
- tokens：1,463,943
- 时间：3,490.4 秒（约 58.2 分钟）
- 接受 mutation：11/30
- 最终部署：`g12-planner`

Mutation 分布：

| 模块 | 尝试 | 接受 |
|---|---:|---:|
| Planner | 16 | 10 |
| Selector | 2 | 1 |
| Caller | 12 | 0 |
| Synthesizer | 0 | 0 |

对应文件：

- 配置：`configs/bfcl_diag_evotool_schema.yaml`
- 汇总：`results/diag_evotool_schema.json`
- 逐题结果：`results/diag_evotool_schema.episodes.jsonl`
- 运行日志：`results/logs/bfcl__bfcl_diag_evotool_schema.log`
- 结构化日志：`results/logs/bfcl__bfcl_diag_evotool_schema.runlog.jsonl`
- 日志汇总：`results/logs/bfcl__bfcl_diag_evotool_schema.runlog.summary.json`

## 4. 汇总对比

| 条件 | 成功数 | 成功率 | 相对 Baseline 新增成功 | 相对 Baseline 回归 |
|---|---:|---:|---:|---:|
| Baseline | 2/30 | 6.67% | — | — |
| Schema | 13/30 | 43.33% | 11 | 0 |
| Offline Repair | 13/30 | 43.33% | 11 | 0 |
| EvoTool | 13/30 | 43.33% | 11 | 0 |
| EvoTool + Schema | 16/30 | 53.33% | 14 | 0 |

核心 2×2 interaction：

```text
(EvoTool+Schema - Schema) - (EvoTool - Baseline)
= (53.33% - 43.33%) - (43.33% - 6.67%)
= -26.67 percentage points
```

负交互说明 Schema 和 EvoTool 的主要收益并非独立叠加，而是高度重叠：EvoTool 在没有 Schema 时
带来 +36.67 个百分点，但 Schema 已经提供后，EvoTool 的边际收益为 +10 个百分点。

完整机器可读对比：

- 静态条件比较：`results/diag_static_comparison.json`
- 五条件完整比较：`results/diag_full_comparison.json`
- 分析脚本：`scripts/analyze_bfcl_conditions.py`

## 5. 逐题重叠与互补

### 5.1 Schema 与 Repair

Schema 与 Offline Repair 的 13 个成功样本完全一致，说明静态条件下两者的收益完全重合。二者
均修复以下 11 个 Baseline 失败：

```text
bfcl_98, bfcl_2, bfcl_72, bfcl_57, bfcl_60, bfcl_24,
bfcl_8, bfcl_9, bfcl_109, bfcl_27, bfcl_36
```

另有 `bfcl_90` 和 `bfcl_7` 在 Baseline 中已经成功，因此构成共同的 13 个成功样本。

### 5.2 Schema 与 EvoTool

Schema 和 EvoTool 都成功 13 题，其中 12 题相同：

```text
Schema 独有：  bfcl_24
EvoTool 独有： bfcl_21
共同成功：     12 题
```

二者总分相同且逐题集合几乎相同，进一步表明无 Schema 时 EvoTool 学到的主要有效规则与接口和
参数约束修复高度重叠。

### 5.3 Schema 与 EvoTool + Schema

EvoTool + Schema 保留了 Schema 的全部 13 个成功样本，没有 observed regression，并新增：

```text
bfcl_108
bfcl_21
bfcl_63
```

这三个新增成功均来自消除过度拆分或重复调用：

- `bfcl_108`：将三个公司的 price 和 volume 从 6 次调用合并为正确的 3 次；
- `bfcl_21`：删除重复的 median 调用；
- `bfcl_63`：删除重复的 displacement 调用。

最终部署的 `g12-planner` 明确增加了避免过度拆分、使子目标与工具输入对应的规则。这三个逐题
变化与 planning/selection 失败从 14 个降到 11 个一致，属于可定位的 planning 改善。

## 6. 结论

### 6.1 EvoTool 的主要收益来自哪里

当前证据表明，EvoTool 在无 Schema 条件下的大部分收益来自对参数类型、输出格式和工具接口规则
的隐式学习，而不是广泛的 reasoning 改善。主要依据是：

1. Schema、Offline Repair、EvoTool 都得到 13/30；
2. Schema 与 Repair 修复完全相同的 11 个失败；
3. Schema 与 EvoTool 的成功集合只有一个样本的交换；
4. 2×2 interaction 为 −26.67 个百分点，显示强烈收益重叠；
5. 无 Schema 时最终部署策略为 Caller mutation。

### 6.2 是否还存在 reasoning/planning 收益

存在初步证据，但幅度较小。Schema 已清除接口错误后，EvoTool 仍把成功数从 13 提高到 16，且
新增的三个成功均属于过度拆分或重复工具调用。与此同时，最终部署模块从 Caller 转为 Planner，
Caller 的 12 次 mutation 没有一次被接受。

因此，更准确的表述不是“EvoTool 没有 reasoning 收益”，而是：

> EvoTool 在无 Schema 时的主要收益与格式/接口修复重叠；当接口约束由 Schema 显式处理后，
> prompt evolution 会转向规划错误，并表现出小规模、可解释的增量收益。

### 6.3 分层干预假设

实验结果支持以下设计方向：

| 错误类型 | 更合适的干预位置 | 本轮证据 |
|---|---|---|
| 序列化、参数类型、额外字段 | Schema 或确定性 Repair/validator | Schema 与 Repair 均无 LLM 地修复相同 11 题 |
| 工具接口的确定性约束 | code/validator | 离线 Repair 可审计、无 token 成本、无回归 |
| 过度拆分、重复调用、任务规划 | Planner prompt evolution | EvoTool+Schema 新增修复 3 个 planning 样本 |
| 参数语义错误 | 尚未确定，可能需更强语义推理或数据 | 五条件下仍有约 3 个相关失败 |

相较于继续增加一个 LLM 来生成 Schema，这种按错误来源选择干预位置的方案更可解释，也更容易
控制成本和避免把确定性接口问题交给概率模型重复解决。

## 7. 有效性边界与下一步

本轮是单模型、单 seed、30 条 held-out 样本。Schema 相对 Baseline 的 +11 题，以及同一次输出上
Offline Repair 的严格配对结果，已经足以支持当前阶段的机制判断；但 EvoTool+Schema 相对 Schema
只有 3 个改善、0 个回归，双侧精确 McNemar 检验 p=0.25，暂不能声称该增量具有统计显著性。

因此当前实验已经满足导师提出的第一轮诊断与简单对照要求，可以先汇报。若导师认可方向，再进行
多 seed 验证，重点确认 +3 个 planning 成功是否稳定，而不是立即投入完整 3-epoch 实验。

多 seed 前还应先解决日志覆盖问题：当前 runlog 文件名由 config basename 决定，直接用同一配置
切换 seed 会覆盖 seed 42 的日志。应为不同 seed 使用独立配置名，或修改 `run.py` 使日志名跟随
`--out`。

## 8. 关键结果文件索引

| 内容 | 文件 |
|---|---|
| Baseline 汇总 | `results/diag_baseline.json` |
| Baseline 逐题结果 | `results/diag_baseline.episodes.jsonl` |
| Schema 汇总 | `results/diag_schema.json` |
| Schema 逐题结果 | `results/diag_schema.episodes.jsonl` |
| Offline Repair 逐题结果 | `results/diag_baseline_offline_repair.episodes.jsonl` |
| EvoTool 汇总 | `results/diag_evotool.json` |
| EvoTool 逐题结果 | `results/diag_evotool.episodes.jsonl` |
| EvoTool + Schema 汇总 | `results/diag_evotool_schema.json` |
| EvoTool + Schema 逐题结果 | `results/diag_evotool_schema.episodes.jsonl` |
| 静态配对分析 | `results/diag_static_comparison.json` |
| 五条件完整配对分析 | `results/diag_full_comparison.json` |
| EvoTool 进化汇总 | `results/logs/bfcl__bfcl_diag_evotool.runlog.summary.json` |
| EvoTool + Schema 进化汇总 | `results/logs/bfcl__bfcl_diag_evotool_schema.runlog.summary.json` |

更完整的复现历史、环境、成本和校验值见 `REPRODUCTION_REPORT_ZH.md`；静态实验细节见
`BFCL_STATIC_DIAGNOSTIC_RESULTS_ZH.md`。

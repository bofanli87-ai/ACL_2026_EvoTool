# BFCL 接口补齐后 Static vs Evolution 实验分析

分析日期：2026-10-31
实验目录：`results/aligned_comparison_3ep/`

## 1. 结论摘要

本轮 3 epochs Evolution 实验在同一数据划分上将 BFCL 测试成功率从 Static 的 **76.67%（23/30）** 提升到 **83.33%（25/30）**，绝对提升 **6.66 个百分点**，净增加 **2 道正确题**。逐题配对结果为 4 题修复、2 题退化、24 题不变。

最终部署策略是第 15 代产生的 `g15-caller`。它在 Caller 提示中增加了“每次工具调用应根据参数保持唯一且彼此不同”的规则，直接针对多次调用时错误复用第一组参数的问题。4 个修复案例都符合这一模式；与此同时，它也造成了 2 个新的参数值错误，说明该规则改善了跨调用参数区分，但不能保证每个参数都忠实保留用户原文。

这次结果支持“Evolution 在当前接口补齐后的代码上带来正向增益”这一观察，但证据仍属于单次、小测试集结果。测试集只有 30 题，且只使用 seed 42；对 6 个结果发生变化的样本做配对精确检验，双侧 p 值约为 0.6875，不能据此声称增益已经具有统计显著性。下一步应固定测试划分，使用多个独立演化种子重复实验。

## 2. 实验设置与数据来源

| 项目 | Static | Evolution |
|---|---:|---:|
| 配置 | `bfcl_aligned_static` | `bfcl_aligned_evolution` |
| 模型 | `evotool-qwen3:8b` | `evotool-qwen3:8b` |
| 数据划分 | 90 train / 30 selection / 30 test | 相同 |
| Seed | 42 | 42 |
| Planner tool context | 开启 | 开启 |
| Structured history | 开启 | 开启 |
| Caller JSON Schema | 开启 | 开启 |
| Caller deterministic repair | 关闭 | 关闭 |
| 进化预算 | 无 | 3 epochs，共 90 generations |
| Mutation / Selection | none / static | blame / diversity |
| 测试部署 | 初始策略 | 单策略 `g15-caller` |

分析直接读取以下文件：

- `static.json` 与 `evolution.json`：总体指标；
- `static.episodes.jsonl` 与 `evolution.episodes.jsonl`：30 道测试题的逐题结果；
- `logs/bfcl__bfcl_aligned_evolution.runlog.jsonl` 及其 summary：90 代进化轨迹、模块归因、接受情况与 token；
- `evolution_console.log`：运行完成信息。

当前目录中的 `comparison.json` 是前一次实验遗留文件，其中 Evolution 成功率仍为 73.33%，与 2026-10-31 新生成的 `evolution.json` 不一致。本报告不使用该过期文件，所有对比均由当前 `static.json` 和 `evolution.json` 重新计算。

## 3. 总体结果

| 指标 | Static | Evolution | 差值或倍率 |
|---|---:|---:|---:|
| 测试成功率 | 76.67% | 83.33% | +6.66 个百分点 |
| 正确题数 | 23/30 | 25/30 | +2 |
| Mean reward | 67.58 | 72.25 | +4.67 |
| Token | 72,687 | 3,048,933 | 41.95× |
| 运行时间 | 187.1 秒 | 6,209.4 秒 | 33.19× |
| Held-out leak | 0 | 0 | 无检测到泄漏 |

Evolution 相比 Static 多使用 2,976,246 token。按净增加 2 道正确题计算，平均每增加一道正确题约对应 1,488,123 个额外 token。这个数字只描述本次运行的成本效率，不能外推到其他模型、数据集或种子。

BFCL 此处是 `no_execution` AST/调用匹配通道，`mean_reward` 还包含代码定义的 shaping 项，因此论文或汇报中的主要准确率应使用独立的 `success_rate`，不要把 mean reward 当成任务成功率。

## 4. 逐题变化

### 4.1 修复的 4 题

| 样本 | Static 错误 | Evolution 修复 |
|---|---|---|
| `bfcl_104` | 两次置信区间调用都使用 `sample_size=50` | 第二次正确改为 `sample_size=150` |
| `bfcl_115` | 两次案件查询都使用案号 `28473` | 第二次正确使用案号 `64725` |
| `bfcl_8` | 汽车和子弹两次计算都复用 `velocity=50, distance=600` | 第二次正确使用 `velocity=400, distance=1000` |
| `bfcl_58` | 巴黎和纽约两次酒店查询都使用 `Paris, France` | 第二次正确使用 `New York, USA` |

这 4 题的共同点很强：Planner 已经生成正确数量的同名工具步骤，但初始 Caller 在第二次调用时复制了第一次调用的参数。`g15-caller` 的新增规则正好抑制这种重复，因此修复与提示变异之间存在清晰、可解释的因果对应。

### 4.2 退化的 2 题

| 样本 | Static 正确行为 | Evolution 退化 |
|---|---|---|
| `bfcl_149` | 两次事件查询均保留城市 `San Diego, CA` | 两次都截断为 `San Diego`，与 gold 不匹配 |
| `bfcl_109` | 三次投资计算分别使用 1、5、10 年 | 第二次错误改为 10 年，形成 1、10、10 |

`bfcl_109` 表明“避免重复”规则不是硬保证：模型仍可能在一组连续调用中复制错误参数。`bfcl_149` 则属于参数忠实度问题，与跨调用去重没有直接关系。后续 Caller 规则应同时强调两点：逐项绑定用户给出的实体/数值，以及在重复工具调用之间执行参数覆盖检查。

### 4.3 剩余错误

Evolution 最终仍有 5 道失败题，错误分析的主标签全部是 `semantic_argument`：

- `bfcl_55`：可选参数不应出现，且第二个游戏名称/条件绑定错误；
- `bfcl_149`：城市从 `San Diego, CA` 被错误截断；
- `bfcl_56`：菜谱对象在准备时间和营养信息调用之间传递错误；
- `bfcl_109`：1、5、10 年中的 5 年被错误替换为 10 年；
- `bfcl_29`：犯罪记录查询包含错误的可选参数值。

错误类型从 Static 的 7 个 `semantic_argument` 降到 Evolution 的 5 个，说明工具选择和调用数量已经不是当前测试集的主要瓶颈；下一轮优化应集中在多调用参数绑定、可选参数省略规则和实体原文保真。

## 5. 进化过程分析

### 5.1 变异归因与接受率

| 模块 | 尝试次数 | 接受次数 | 接受率 |
|---|---:|---:|---:|
| Planner | 50 | 15 | 30.0% |
| Caller | 39 | 13 | 33.3% |
| Synthesizer | 1 | 0 | 0% |
| Selector | 0 | 0 | — |
| 合计 | 90 | 28 | 31.1% |

Blamer 将 89/90 次问题归因到 Planner 或 Caller，与最终测试错误主要属于参数语义问题基本一致。Selector 从未被选中，Synthesizer 只被选中一次且未被接受。62 次变异被拒绝，说明接受门能够过滤多数无收益或负收益修改。

### 5.2 每个 epoch 的搜索效率

| Epoch | 尝试 | 接受 | Child 优于 Parent | 相等 | 更差 | 搜索 token |
|---:|---:|---:|---:|---:|---:|---:|
| 1（gen 0–29） | 30 | 11 | 11 | 16 | 3 | 1,413,094 |
| 2（gen 30–59） | 30 | 9 | 9 | 17 | 4 | 846,234 |
| 3（gen 60–89） | 30 | 8 | 8 | 19 | 3 | 715,572 |

接受次数逐 epoch 下降，平局次数上升，说明后期搜索的边际收益减少。这里的“优于”是当前三题 mini-batch reward，不代表一定提高 selection 或 held-out test 表现。

### 5.3 最佳策略出现得较早

验证集最佳分数的关键节点如下：

| Generation | 策略 | 变异模块 | Selection mean reward |
|---:|---|---|---:|
| 初始 | `init` | — | 0.6362 |
| 4 | `g4-planner` | Planner | 0.7062 |
| 15 | `g15-caller` | Caller | 0.7063 |
| 67 | `g67-caller` | Caller | 0.7063 |

`g15-caller` 在第 15 代已经达到最终最高验证分数 0.7063；第 16–89 代没有再提高这一数值。到第 15 代累计搜索 token 为 656,098，而完整搜索结束时为 2,974,900，之后的搜索约占搜索 token 的 77.9%；再加最终测试后，本轮总 token 为 3,048,933。

这提示可以增加基于 selection score 的 early stopping，例如连续若干代或一个 epoch 没有刷新最佳分数就停止。不过本次只有一条轨迹，不能仅凭这一结果直接确定 patience，应先在多种子实验上验证是否会过早停止。

## 6. 最终种群与部署行为

最终种群包含：

| 策略 | Selection wins | 采样权重 | Selection mean reward |
|---|---:|---:|---:|
| `init` | 24 | 0.8000 | 0.6362 |
| `g4-planner` | 4 | 0.1333 | 0.7062 |
| `g15-caller` | 1 | 0.0333 | 0.7063 |
| `g67-caller` | 1 | 0.0333 | 0.7063 |

多样性选择保留了 4 个互补策略，且初始策略在按题胜出次数上占主导；测试阶段关闭 ensemble，最终按 selection mean reward 部署单一策略 `g15-caller`。`g15-caller` 与 `g67-caller` 的四舍五入分数相同，当前实现选择了前者。报告结果时应明确这是单策略测试结果，不能描述成种群集成结果。

`g15-caller` 的核心变更为：

> Ensure that each tool call is unique and distinct based on its arguments to prevent duplicate calls.

该变更从初始策略直接产生，在生成它的 mini-batch 上 reward 从 0.3833 提升到 0.6167，selection score 达到 0.7063。逐题测试证据也表明它主要修复第二次同名工具调用重复使用第一组参数的问题。

## 7. 结果解释边界

本实验可以支持以下陈述：在 seed 42 的固定 90/30/30 划分和当前 Qwen3-8B/Ollama 服务上，接口补齐后的 Evolution 单次运行比匹配 Static 对照高 6.66 个百分点，并且改进可追溯到 Caller 的去重参数规则。

本实验暂不能支持以下更强结论：

- 不能声称平均提升为 6.66 个百分点，因为尚无多次重复的均值和方差；
- 不能声称统计显著，30 题测试集上的净变化只有 2 题；
- 不能将本结果直接等同于论文完整 benchmark 或论文模型结果；
- 不能把先前 36%→57% 的静态接口改进与本次 Evolution 的 +6.66 合并成一个进化增益；
- 不能使用当前过期的 `comparison.json` 作为本轮数字来源。

## 8. 建议的下一步

1. 固定现有 train/selection/test 划分，只改变 evolution seed，至少运行 3–5 次，报告成功率均值、标准差、逐题配对结果和 token 成本。
2. 为 Caller 增加更一般的参数绑定规则：对用户列出的实体和数值建立逐调用映射；同名工具重复调用时逐字段核对；未要求的 optional 参数默认省略。
3. 将 early stopping 作为独立效率实验，在多种子上比较完整 3 epochs 与不同 patience，避免用单次轨迹选择停止阈值。
4. 重新生成或更新 `comparison.json`，确保汇总文件与当前 `evolution.json` 一致，并在归档时保留本轮逐题文件和 runlog。

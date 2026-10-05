# EvoTool 本地复现实验记录

## 1. 实验目的

本实验用于复现论文仓库 **EvoTool: Self-Evolving Tool-Use Policy Optimization in
LLM Agents via Blame-Aware Mutation and Diversity-Aware Selection** 的代码流程，验证以下
环节能够在无远程服务器的 Windows 计算机上运行：

1. 四模块工具调用策略（Planner、Selector、Caller、Synthesizer）；
2. 基于轨迹的失败归因；
3. 针对被归因模块的提示词变异；
4. 子策略接受门控与多样性选择；
5. BFCL 严格评测、结果保存和逐代日志记录。

本阶段定位为**小规模流程复现**，不是论文完整数据规模下的指标复现。

## 2. 复现时间与代码版本

- 记录日期：2026-10-05（UTC+08:00）
- 项目路径：`D:\EVotool\ACL_2026_EvoTool`
- Git commit：`6a82719ea6e22cf23f963078e2527094e50b47f6`
- 代码状态：在上述 commit 上增加了本地 Ollama 适配、Windows UTF-8 读取和复现配置；
  因此实验工作区包含未提交的本地修改。

## 3. 实验环境

| 项目 | 配置 |
|---|---|
| 操作系统 | Microsoft Windows 10.0.26200.8655，x64 |
| 逻辑处理器数 | 28 |
| Python | 3.13.15，仓库内虚拟环境 `.venv` |
| OpenAI Python SDK | 3.24.0 |
| PyYAML | 6.0.3 |
| Ollama | 0.35.1，本机端点 `http://127.0.0.1:11434/v1` |
| 模型 | `evotool-qwen3:8b`，基于 `qwen3:8b` |
| 模型规模 | 8.2B parameters |
| 模型格式 | GGUF，Q4_K_M 量化 |
| 模型文件大小 | 5,225,387,815 bytes（约 4.87 GiB） |
| 模型摘要 | `d4086d1a2305702c527154af5f05be9f5e8d9de00bf68a6a05694dce01324d79` |
| 上下文与采样 | `num_ctx=8192`、`temperature=0`、`seed=42` |

本地模型使用量化权重和 Ollama，而论文的 Qwen3-8B 实验使用 vLLM。因此本实验可以验证
方法与代码路径，但推理后端、量化方式及小样本设置均会导致指标与论文存在差异。

## 4. 本地环境配置过程

### 4.1 Python 环境

```powershell
cd D:\EVotool\ACL_2026_EvoTool
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

系统 PATH 中原有的 `python` 指向 Python 3.9，不符合仓库要求，因此实验全程显式使用
`.\.venv\Scripts\python.exe`。

### 4.2 Ollama 模型

```powershell
ollama pull qwen3:8b
ollama create evotool-qwen3:8b -f .\configs\Modelfile.qwen3-8b
```

`configs/Modelfile.qwen3-8b` 将上下文窗口固定为 8192，并设置温度 0、随机种子 42。
运行配置为 `configs/local_ollama.yaml`。客户端针对 Ollama 使用
`reasoning_effort="none"`，避免 Qwen3 思考内容干扰 JSON 格式的规划、选工具和变异输出。

### 4.3 环境与代码检查

```powershell
powershell -ExecutionPolicy Bypass -File scripts\check_local.ps1
.\.venv\Scripts\python.exe -m pytest -q
```

验证结果：离线全链路 smoke test 通过；项目测试共 **7 passed**。

## 5. 实验一：Dummy 最小流程验证

### 5.1 命令

```powershell
.\.venv\Scripts\python.exe run.py `
  --config configs\local_ollama.yaml `
  --benchmark dummy
```

### 5.2 结果

| 指标 | 数值 |
|---|---:|
| generations | 2 |
| train / selection / test | 6 / 0 / 6 |
| success rate | 83.33% |
| mean reward | 86.79 |
| 模型 tokens | 21,102 |
| 耗时 | 85.7 秒 |
| 最终策略 | `init` |
| accepted mutations | 0 |

两次变异分别针对 Planner 和 Synthesizer，但子策略与父策略的 batch reward 均持平，故均被
接受门控拒绝。

该实验的 `held_out_leak=6`：Dummy 数据总共只有 6 条，测试集回退复用了训练数据。因此
83.33% **只能说明程序链路可运行，不能作为泛化性能结果**。

## 6. 实验二：BFCL 小规模实验

### 6.1 命令

```powershell
.\.venv\Scripts\python.exe run.py `
  --config configs\local_ollama.yaml `
  --benchmark bfcl `
  --override `
    evolve.generations=1 `
    evolve.batch_size=1 `
    n_train=3 `
    n_sel=3 `
    n_test=3 `
    max_steps=2 `
    verbose=true
```

### 6.2 最终结果

| 指标 | 数值 | 说明 |
|---|---:|---|
| train / selection / test | 3 / 3 / 3 | 三个集合互不重叠 |
| held-out leak | 0 | 无数据泄漏 |
| generations | 1 | 仅验证一次完整进化迭代 |
| success rate | 33.33% | 3 个测试样本严格通过 1 个 |
| mean reward | 36.67 | 成功奖励与部分工具调用进度的组合 |
| selection mean reward | 0.1119 | 最终策略在选择集上的平均奖励 |
| 模型 tokens | 11,550 | 本次运行累计用量 |
| 总耗时 | 41.5 秒 | 端到端运行时间 |
| population size | 1 | 最终仅保留初始策略 |
| deployed policy | `init` | 未产生被接受的新策略 |

BFCL 的 `success_rate` 使用严格 AST 判定，要求预测的函数调用数量、函数名、参数名、参数
类型和值均与标注匹配。本次 33.33% 即 3 个测试样本中有 1 个严格通过。

`mean_reward` 是进化使用的连续信号：

```text
reward = 0.7 × success + 0.3 × tool-call progress
```

因此未严格通过的样本仍可能因部分正确的工具调用获得少量奖励。论文最终指标应优先查看
`success_rate`；分析训练过程时再结合 `mean_reward`。

### 6.3 唯一一代的变异记录

| 项目 | 内容 |
|---|---|
| generation | 0 |
| parent | `init` |
| 训练样本 | `bfcl_134` |
| 归因模块 | Selector |
| 子策略 | `g0-selector` |
| parent batch reward | 0.12 |
| child batch reward | 0.12 |
| 是否接受 | 否 |

诊断器认为 Selector 没有选择 `HNA_WQA.search`，导致关于 Imjin War 的信息不完整。变异器
将 Selector 从：

```text
You are a tool selection agent. Given the current subgoal and the list of
available tools, select the most appropriate tool.
```

修改为：

```text
You are a tool selection agent. Given the current subgoal and the list of
available tools, select the most appropriate tool. Use the 'HNA_WQA.search'
tool for queries about historical events or up-to-date information.
```

子策略的 reward 没有严格高于父策略（0.12 = 0.12），故接受门控将其拒绝。这条修改还把
单个样本中的具体工具名写进了通用 Selector prompt，存在明显过拟合风险；拒绝该变异符合
算法设计。最终部署的仍是初始策略 `init`，所以本次 BFCL 的 33.33% 是初始策略结果，
**不能表述为 EvoTool 已取得性能提升**。

## 7. 实验三：BFCL 10-generation 中等规模实验

### 7.1 命令与设置

在实验二验证完整闭环后，将数据规模扩大为 20/10/20，并运行 10 generations：

```powershell
.\.venv\Scripts\python.exe run.py `
  --config configs\local_ollama.yaml `
  --benchmark bfcl `
  --override `
    evolve.generations=10 `
    evolve.batch_size=2 `
    n_train=20 `
    n_sel=10 `
    n_test=20 `
    max_steps=6 `
    verbose=true `
  --out results\bfcl__evo_10gen.json
```

本实验仍使用 seed 42、Qwen3-8B Q4_K_M、EvoTool 的 blame mutation 与 diversity
selection。train、selection 和 test 三个集合互不重叠。

### 7.2 最终结果

| 指标 | 数值 | 说明 |
|---|---:|---|
| train / selection / test | 20 / 10 / 20 | 无数据泄漏 |
| generations | 10 | 每个 batch 包含 2 个样本 |
| accepted / rejected | 3 / 7 | 变异接受率 30% |
| test success rate | 10.0% | 20 个测试样本严格通过 2 个 |
| test mean reward | 19.67 | 即归一化 reward 0.1967 |
| tokens | 225,536 | 全流程累计 token |
| 总耗时 | 689.5 秒 | 约 11.5 分钟 |
| 最终种群大小 | 3 | `init`、`g3-caller`、`g4-planner` |
| 最终部署策略 | `g3-caller` | selection mean reward 最高 |

由 `reward = 0.7 × success + 0.3 × progress` 可估算本次测试集的平均工具调用进度：

```text
progress ≈ (0.1967 - 0.7 × 0.10) / 0.3 ≈ 0.422
```

即模型平均取得约 42.2% 的工具调用进度，但仅有 10% 的样本满足 BFCL 对函数名、调用数、
参数名、参数类型和参数值的全部严格要求。

### 7.3 模块归因与接受情况

| 模块 | 尝试变异 | 占全部变异 | 被接受 |
|---|---:|---:|---:|
| Caller | 8 | 80% | 1 |
| Planner | 1 | 10% | 1 |
| Selector | 1 | 10% | 1 |
| Synthesizer | 0 | 0% | 0 |

80% 的失败被归因到 Caller。具体错误主要包括参数名错误、数值被输出成字符串、参数类型不
符合 schema，以及参数值不符合工具要求。这与 BFCL 的严格函数调用评测方式一致，表明当前
模型的主要瓶颈是参数构造，而不是最终自然语言回答。

### 7.4 三次被接受的变异

**Generation 3，Caller：** parent batch reward 从 0.15 提升到 0.50。新规则要求所有数值
参数（例如 `days`）以整数而非字符串形式输出。这是本轮最有效的变异，使最佳 selection
mean reward 从 0.203 提升到 0.413；最终部署策略即为 `g3-caller`。

**Generation 4，Planner：** parent batch reward 从 0.1125 提升到 0.135。新规则要求生成
更少、更必要的子目标，并注意工具参数 schema。该策略的 selection mean reward 为 0.206，
仅略高于 `init` 的 0.203，跨样本收益有限；参数格式约束本身也更接近 Caller 的职责。

**Generation 6，Selector：** parent batch reward 从 0.125 提升到 0.15。变异要求历史事件
问题优先使用 `HNA_WQA.search`。它通过了训练 batch gate，但未进入最终种群，说明其在
selection 集上没有取得独特胜场，随后被 diversity selection 淘汰。该修改包含具体工具名，
也表现出一定的单样本过拟合倾向。

### 7.5 最终种群与多样性选择

| 策略 | Selection wins | Selection mean reward | 最终状态 |
|---|---:|---:|---|
| `init` | 6 | 0.203 | 保留 |
| `g3-caller` | 3 | 0.413 | 保留并部署 |
| `g4-planner` | 1 | 0.206 | 保留 |

`init` 虽然平均 reward 较低，但在 10 个 selection 样本中的 6 个样本上获胜，因此被多样性
选择保留。`g3-caller` 只赢得 3 个样本，但平均 reward 最高，最终作为单策略部署。这证明
实现保留的是具有互补胜场的策略，而不是简单只保留平均分最高的策略。

### 7.6 学习曲线

最佳 selection mean reward 的变化为：

```text
Generation 0–2: 0.203
Generation 3–9: 0.413
```

主要提升发生在 Generation 3，此后进入平台期。各代 `train_batch_reward` 使用不同样本，
因此不能直接横向解释为单调学习曲线；例如 Generation 8 的 0.85 更可能说明该 batch 较易，
不表示整体性能突然上升。测试集只在最后记录一次 reward 0.1967，符合不反复利用测试集做
选择的原则，但也意味着本次无法绘制逐代 test 曲线。

### 7.7 与实验二的关系

实验二的测试成功率为 33.33%（1/3），本实验为 10.0%（2/20）。两者的 train 和 selection
大小不同，导致随机打乱后截取的测试样本区间不同，因此不能解释为性能从 33.33% 下降到
10%。本实验的 20 个测试样本更稳定，但仍不足以代替完整 benchmark 和多随机种子实验。

## 8. 实验四：BFCL 静态基线

### 8.1 实验设计与命令

为判断实验三的 `g3-caller` 是否真正改善 held-out 测试表现，本实验在相同模型、seed 42、
20/10/20 划分和 `max_steps=6` 下关闭进化，仅部署初始策略 `init`。使用不同 config basename
保存日志，避免覆盖实验三产物：

```powershell
Copy-Item configs\local_ollama.yaml configs\local_ollama_static.yaml

.\.venv\Scripts\python.exe run.py `
  --config configs\local_ollama_static.yaml `
  --benchmark bfcl `
  --override `
    evolve.mutation_target=none `
    evolve.selection=static `
    evolve.generations=0 `
    evolve.batch_size=2 `
    n_train=20 `
    n_sel=10 `
    n_test=20 `
    max_steps=6 `
    verbose=true `
  --out results\bfcl__static_20test.json
```

### 8.2 Static 与 EvoTool 公平对照

| 指标 | Static `init` | EvoTool `g3-caller` | 变化 |
|---|---:|---:|---:|
| Test success count | 1/20 | 2/20 | +1 个样本 |
| Test success rate | 5.0% | 10.0% | +5 个百分点 |
| Test mean reward | 16.17 | 19.67 | +3.50（+21.6%） |
| Tokens | 53,556 | 225,536 | EvoTool 为 4.21 倍 |
| 时间 | 167.2 秒 | 689.5 秒 | EvoTool 为 4.12 倍 |
| Generations | 0 | 10 | — |
| 最终部署策略 | `init` | `g3-caller` | — |

由于两次实验使用相同 seed 和相同的 train/selection/test 大小，数据打乱与切片完全一致，
测试集可以直接比较。结果表明 EvoTool 在本次划分上将严格成功率从 5.0% 提高到 10.0%。
“相对提升 100%”在数值上成立，但实际只对应从 1 个成功样本增加到 2 个，因此报告结果时
必须同时给出原始计数，避免夸大效果。

### 8.3 Reward 分解

根据 `reward = 0.7 × success + 0.3 × progress` 反推：

```text
Static progress  ≈ (0.1617 - 0.7 × 0.05) / 0.3 ≈ 0.422
EvoTool progress ≈ (0.1967 - 0.7 × 0.10) / 0.3 ≈ 0.422
```

在结果保留两位小数造成的误差范围内，两者平均工具调用进度均约为 42.2%。因此 mean reward
的提升几乎全部来自额外通过的一个严格成功样本，而不是所有测试样本的部分调用质量普遍
改善。结合 Generation 3 的变异内容，可以推测 Caller 的整数类型约束修复了至少一个临界
样本，但现有日志没有保存逐测试样本结果，无法确认两个策略分别通过了哪些样本。

### 8.4 统计不确定性

在仅有 20 个测试样本时，success rate 的 95% Wilson 区间为：

| 方法 | Success rate | 95% Wilson interval |
|---|---:|---:|
| Static | 5.0% | 0.89%–23.61% |
| EvoTool | 10.0% | 2.79%–30.10% |

两个区间高度重叠，当前只能说明提升方向为正，不能认为提升具有统计显著性。由于缺少每个
测试样本的配对成功记录，也暂时无法执行 McNemar 配对检验。

### 8.5 成本与部署解释

EvoTool 比 static 多消耗 171,980 tokens 和 522.3 秒。在本次单次实验中，每 10 万 tokens
对应的测试成功数约为 static 1.87 个、EvoTool 0.89 个，故搜索阶段的即时 token 效率更低。
不过进化搜索是一次性成本，得到的 prompt 策略可以复用于后续任务；在大规模部署时，搜索
成本可以被摊薄。因此本结果同时支持“测试效果有小幅正向变化”和“搜索成本明显增加”这两点。

Static summary 中的 `final_population=[]` 是零 generation 路径没有生成逐代 population
snapshot 所致；最终 JSON 已正确记录 `population_ids=["init"]` 和部署策略 `init`，不是运行
错误。

## 9. 实验五：BFCL 论文规模划分、1 epoch 实验

### 9.1 实验设计与命令

本实验将数据划分、batch size 和单个 epoch 的预算对齐仓库论文配置：90 条训练样本、30 条
selection 样本、30 条 held-out test 样本，batch size 为 3。`generations=0` 表示根据数据量
自动推导 `1 × ceil(90/3) = 30` generations：

```powershell
Copy-Item configs\local_ollama.yaml configs\local_ollama_paper1ep.yaml

.\.venv\Scripts\python.exe run.py `
  --config configs\local_ollama_paper1ep.yaml `
  --benchmark bfcl `
  --override `
    evolve.epochs=1 `
    evolve.generations=0 `
    evolve.batch_size=3 `
    n_train=90 `
    n_sel=30 `
    n_test=30 `
    max_steps=6 `
    evolve.log_test_eval=true `
    verbose=true `
  --out results\bfcl__evo_paper1ep.json
```

本实验与论文完整预算的主要区别是只运行 1 epoch / 30 generations；论文配置为 3 epochs /
90 generations。模型仍为本地 Ollama Qwen3-8B Q4_K_M，而不是论文 vLLM 推理设置。

### 9.2 最终结果

| 指标 | 数值 | 说明 |
|---|---:|---|
| Train / selection / test | 90 / 30 / 30 | 与仓库论文划分一致 |
| Held-out leak | 0 | 三个集合无交集 |
| Generations | 30 | 1 个完整 epoch |
| Accepted / rejected | 8 / 22 | 接受率 26.67% |
| Test success count | 13/30 | BFCL 严格 AST 成功数 |
| Test success rate | 43.33% | 最终 headline 指标 |
| Test mean reward | 42.55 | 归一化 mean reward 0.4255 |
| Tokens | 1,107,334 | 本地模型累计 token |
| 总耗时 | 3,051 秒 | 50 分 51 秒 |
| 平均生成速度 | 约 363 tokens/s | 按总 tokens / 总时间估算 |
| 最终种群大小 | 7 | 初始策略加 6 个进化策略 |
| 最终部署策略 | `g26-caller` | selection mean reward 最高 |

根据 reward 公式反推，测试集平均工具调用 progress 约为：

```text
(0.4255 - 0.7 × 13/30) / 0.3 ≈ 0.407
```

即在 43.33% 的严格成功率之外，所有样本平均约有 40.7% 的工具调用进度。
13/30 成功率的 95% Wilson 区间约为 27.38%–60.80%；30 条测试样本比此前更稳定，但区间
仍然较宽，应结合相同划分的 static baseline 和后续多随机种子结果判断。

### 9.3 归因和变异分布

| 模块 | 尝试变异 | 占比 | 接受 | 模块内接受率 |
|---|---:|---:|---:|---:|
| Planner | 9 | 30.0% | 6 | 66.67% |
| Selector | 2 | 6.67% | 0 | 0% |
| Caller | 19 | 63.33% | 2 | 10.53% |
| Synthesizer | 0 | 0% | 0 | — |

Caller 仍是最常被归因的模块，说明参数构造是主要失败来源。但 Caller 的接受率只有 10.53%，
大量变异只是重复“校验 schema/参数格式”等宽泛建议，没有在 batch 上产生严格提升。Planner
只占 30% 的尝试，却有 6/9 被接受，主要修复过度拆分、冗余步骤以及重复工具调用。

### 9.4 被接受的关键变异

| Gen | 模块 | Parent → child reward | Selection 影响 | 最终保留 |
|---:|---|---:|---|---|
| 0 | Planner | 0.1186 → 0.1500 | best=0.2098 | 是，`g0-planner` |
| 3 | Planner | 0.1333 → 0.1400 | best 不变 | 是，`g3-planner` |
| 6 | Planner | 0.1042 → 0.1075 | best=0.2310 | 是，`g6-planner` |
| 12 | Planner | 0.1119 → 0.3733 | best 不变 | 否，selection 淘汰 |
| 17 | Planner | 0.1250 → 0.1333 | best=0.2578 | 是，`g17-planner` |
| 23 | Caller | 0.1167 → 0.3500 | best 不变 | 是，`g23-caller` |
| 26 | Caller | 0.1286 → 0.3667 | best=0.3658 | 是，`g26-caller` |
| 29 | Planner | 0.3483 → 0.3567 | best 不变 | 否，selection 淘汰 |

Generation 26 是最关键的变异。它把 Caller prompt 从通用参数生成规则改为额外强调：

```text
Ensure that all numeric parameters, such as 'year', are passed as integers.
Validate the input format before making the tool call.
```

这与实验三中成功的 `g3-caller` 结论一致：Qwen3 在 BFCL 上经常将数字参数生成为字符串，
而显式要求整数类型能修复部分严格 AST 匹配失败。该变异将最佳 selection mean reward 从
0.2578 提高到 0.3658，并成为最终部署策略。

Generation 12 和 29 虽然通过训练 batch gate，但没有在 selection 集上获得独特胜场，因此
未进入最终种群。这再次验证 accept gate 与 diversity selection 承担不同职责：前者判断局部
训练 batch 是否改善，后者过滤不能在 held-out selection 样本上提供互补价值的策略。

### 9.5 学习曲线

最佳 selection mean reward 的主要台阶为：

```text
初始 init:       0.1791
Generation 0:    0.2098
Generation 6:    0.2310
Generation 17:   0.2578
Generation 26:   0.3658
Generation 29:   0.3658
```

最终最佳 selection reward 相对 `init`：

```text
绝对提升 = 0.3658 - 0.1791 = 0.1867
相对提升 ≈ 104.24%
```

与实验三在 Generation 3 后长期停滞不同，本轮在 Generation 6、17 和 26 仍出现新的台阶，
说明增加训练覆盖范围和搜索预算确实发现了更多有效策略。其中最大一次泛化提升发生在后期的
Generation 26，表明只运行 10 generations 可能过早停止。

### 9.6 最终种群与多样性

| 策略 | Selection wins | Selection mean reward | 角色 |
|---|---:|---:|---|
| `init` | 13 | 0.1791 | 覆盖最多独特样本 |
| `g0-planner` | 6 | 0.2098 | 减少过度拆分 |
| `g3-planner` | 1 | 0.2029 | 预约流程规划特化 |
| `g6-planner` | 1 | 0.2310 | 税务计算规划特化 |
| `g17-planner` | 1 | 0.2578 | 区域/时间段规划特化 |
| `g23-caller` | 1 | 0.2024 | 必需参数完整性特化 |
| `g26-caller` | 7 | 0.3658 | 数值类型约束，最终部署 |

`init` 赢得 13/30 个 selection 样本，说明进化策略并未全面支配初始策略；多样性选择因此保留
`init`。最终测试仍按论文 headline 设置部署单个平均 reward 最高的 `g26-caller`，而不是
使用七策略 ensemble。

### 9.7 Token 与时间成本

实际 token 消耗 1,107,334，落在实验前估计的 80万–150万范围内。平均每代约 36,911
tokens，但不同类型 generation 成本差异明显：

| Generation 类型 | 数量 | 平均 tokens/代 |
|---|---:|---:|
| Accepted | 8 | 92,489 |
| Rejected | 22 | 16,701 |

被接受的 child 需要在完整 selection 集上进行种群评估，因此平均成本约为 rejected generation
的 5.5 倍。后续扩大到 3 epochs 时，token 成本高度依赖新接受策略的数量，不能只按代数线性
外推。

### 9.8 有效性边界

本次 43.33% 对应 13/30 个 held-out 测试样本，是目前最接近仓库论文数据划分的本地结果。
实验五刚完成时尚缺少同一个 90/30/30 划分上的 static `init`，因此不能立即归因；随后实验六
补齐了该对照，测得 static 为 10.0%（3/30），从而确认本轮进化策略多通过了 10 个样本。
此前实验四的 static 5.0% 使用 20/10/20 划分，测试样本区间不同，仍不能与本轮直接比较。

同理，本轮也不能直接与论文表格中的 Qwen3-8B BFCL 数值比较：本地实验使用 Q4_K_M 量化
Ollama 模型、仓库演示子集和 1 epoch，而论文使用不同推理后端、完整评测设置和 3 epochs。

## 10. 实验六：BFCL 论文规模划分静态基线

### 10.1 实验设计与命令

本实验补充实验五所需的严格同划分 static baseline。模型、seed 42、90/30/30 数据划分、
batch size 和 `max_steps=6` 均保持一致，仅关闭进化并部署初始策略 `init`：

```powershell
Copy-Item configs\local_ollama.yaml configs\local_ollama_static_full.yaml

.\.venv\Scripts\python.exe run.py `
  --config configs\local_ollama_static_full.yaml `
  --benchmark bfcl `
  --override `
    evolve.mutation_target=none `
    evolve.selection=static `
    evolve.generations=0 `
    evolve.batch_size=3 `
    n_train=90 `
    n_sel=30 `
    n_test=30 `
    max_steps=6 `
    verbose=true `
  --out results\bfcl__static_full.json
```

Static 路径不执行 generation、blame、mutation 或 diversity selection，但仍在 selection 和
test 数据上评估初始策略。三个数据集合之间无泄漏。

### 10.2 Static full 结果

| 指标 | 数值 |
|---|---:|
| Train / selection / test | 90 / 30 / 30 |
| Held-out leak | 0 |
| Generations | 0 |
| Test success count | 3/30 |
| Test success rate | 10.0% |
| Test mean reward | 19.08 |
| Tokens | 78,533 |
| 总耗时 | 234.5 秒（3 分 54.5 秒） |
| Population | `init` |
| Deployed policy | `init` |

实际耗时低于实验前估计的 5–10 分钟，token 消耗也低于估计的 10万–14万。

### 10.3 与实验五的严格同划分对照

| 指标 | Static `init` | EvoTool `g26-caller` | 变化 |
|---|---:|---:|---:|
| Test success count | 3/30 | 13/30 | +10 个样本 |
| Test success rate | 10.0% | 43.33% | +33.33 个百分点 |
| 相对 success 提升 | — | +333.3% | 4.33 倍于 static |
| Test mean reward | 19.08 | 42.55 | +23.47（+123.0%） |
| Tokens | 78,533 | 1,107,334 | EvoTool 为 14.10 倍 |
| 时间 | 234.5 秒 | 3,051.0 秒 | EvoTool 为 13.01 倍 |
| 部署策略 | `init` | `g26-caller` | 进化策略替代初始策略 |

由于两次运行使用相同 seed、相同数据量和相同切片逻辑，因此测试集是相同的 30 个样本。
这是当前复现中最关键的公平对照：EvoTool 比 static 多严格通过 10 个样本，将成功率从 10.0%
提高到 43.33%。与此前 20-test 对照只增加 1 个成功样本不同，本轮变化已经相当明显。

### 10.4 Reward 分解

根据 reward 公式反推平均 progress：

```text
Static progress  ≈ (0.1908 - 0.7 × 0.10) / 0.3      ≈ 0.4027
EvoTool progress ≈ (0.4255 - 0.7 × 13/30) / 0.3     ≈ 0.4072
```

平均部分调用进度只从约 40.27% 提高到 40.72%，绝对变化约 0.46 个百分点。mean reward 的
主要提升来自 10 个额外严格成功样本，而不是对所有失败样本进行小幅、均匀的改进。这说明
进化策略更像是修复了一类关键的离散错误——尤其是数字参数类型和调用规划——使多个临界
样本跨过 BFCL 的严格成功边界。

### 10.5 统计分析

| 方法 | Success rate | 95% Wilson interval |
|---|---:|---:|
| Static | 10.0%（3/30） | 3.46%–25.62% |
| EvoTool | 43.33%（13/30） | 27.38%–60.80% |

两个 Wilson 区间不重叠。现有日志没有逐测试样本 success 明细，因此无法直接构建配对列联表；
但 static 仅成功 3 个、EvoTool 成功 13 个，两者可能共享的成功样本数只能是 0–3。对所有
可能重叠情况进行精确 McNemar 检验，其双侧 p 值范围约为 0.00195–0.02127，均低于 0.05。
因此，在这 30 个固定测试样本上，差异具有明确统计证据。

该统计结论只针对当前 seed、模型量化版本和测试样本；它不能替代跨随机种子、跨模型运行的
方差分析，也不能直接推广到论文完整官方评测。

### 10.6 效果—成本分析

EvoTool 相比 static 额外消耗：

```text
Tokens: 1,028,801
时间:   2,816.5 秒（约 46 分 57 秒）
额外严格成功: 10 个
每增加一个成功样本的搜索成本: 约 102,880 tokens
```

按单次运行计算，每 10 万 tokens 对应的测试成功数约为 static 3.82 个、EvoTool 1.17 个，
因此搜索阶段的即时 token 效率较低。不过 `g26-caller` 的 prompt 可以保存并在后续推理中
直接部署；若服务大量任务，110 万 token 的搜索成本可以被摊薄。实验结论应同时报告明显的
效果提升与约 14 倍的搜索 token 成本。

## 11. 结果解读与阶段性结论

截至实验六，已完成以下复现目标：

- 本地 Qwen3 模型能够通过 OpenAI 兼容接口驱动 EvoTool；
- BFCL 数据能够按 train/selection/test 无泄漏划分；
- 四个策略模块、失败归因、定向变异、接受门控和多样性选择均能执行；
- 10 代搜索产生了 3 个被接受的 mutation，并形成包含 3 个互补策略的种群；
- Caller 被识别为主要瓶颈，类型约束变异显著提高了 selection reward；
- 最终部署策略已从 `init` 变为进化得到的 `g3-caller`；
- 完成同模型、同 seed、同数据划分的 static baseline 公平对照；
- 完成论文规模 90/30/30 数据划分下的单 epoch、30-generation 搜索；
- 观察到 selection reward 在 Generation 0、6、17、26 的阶梯式提升；
- 在 30 条 held-out 测试样本上取得 13/30、43.33% 的严格成功率；
- 完成相同 90/30/30 划分的 static full 对照，并测得初始策略为 3/30、10.0%；
- 验证 EvoTool 在固定测试集上带来 +10 个成功样本、+33.33 个百分点的明显提升；
- 最终结果、逐代诊断、prompt diff 和学习曲线均被正确保存。

实验三与实验四的 20-test 对照表明，10-generation EvoTool 把 success rate 从 5.0% 提高到
10.0%，但只多成功 1 个样本。实验五与实验六扩大到相同的 90/30/30 划分后，最佳 selection
mean reward 从初始策略的 0.1791 提高到 0.3658；held-out success 从 static 的 10.0% 提高到
EvoTool 的 43.33%。当前最准确的结论是：

> 已完成 EvoTool 的本地工程流程复现、两组同划分 static 对照，以及论文规模 90/30/30
> 划分下的单 epoch 搜索。30 代实验产生 8 次有效 mutation，将 selection 最佳 reward 相对
> 初始策略提高约 104%；在相同的 30 条 held-out BFCL 样本上，严格成功率从 static 的
> 10.0%（3/30）提高到 43.33%（13/30），绝对提升 33.33 个百分点。该结果为 EvoTool 的
> 本地有效性提供了明确证据，但仍需多随机种子和论文完整 3-epoch 预算验证稳定性。

此外，本地模型为 Q4_K_M 量化版、推理后端为 Ollama，且当前使用演示子集，因此尚未完成
论文完整实验规模和论文数值的复现。

## 12. 后续实验计划

同划分 static full 已完成。下一阶段可在两条路线中选择：第一，运行 3 epochs / 90
generations，补齐仓库论文预算；第二，先以 30 generations 在多个随机种子上重复 EvoTool 与
static 对照，例如 seed 1、7、21、42、100，以验证稳定性。完整报告应包括：

- success rate 的均值与标准差；
- mean reward 的均值与标准差；
- 每个 seed 的原始成功数；
- mutation 接受率及模块分布；
- tokens、耗时和效果—成本关系。

同时建议扩展结果日志，保存每个测试样本的 ID、success、reward 和预测调用，以便进行配对
检验和失败类型分析。完成多 seed 实验后，再根据计算预算扩大 generations 和测试集。

## 13. 实验产物与完整性校验

| 文件 | 用途 | SHA-256 |
|---|---|---|
| `results/bfcl__local_ollama.json` | 实验二 BFCL 最终指标（未被覆盖） | `E43039E0CDB1C50BB45B0BA68B5BF056AEC7AD42817CACE7723FAE88FF8429E6` |
| `results/bfcl__evo_10gen.json` | 实验三最终指标 | `5B2410FD2352291699304970909B5C10B57C70D88E92B88B22BA779EF9CFAF32` |
| `results/logs/bfcl__local_ollama.log` | 实验三人类可读日志 | `B78A953F48F6E506C7A6D4DA46CCFE1405F8CA6059FF7B686794495D4E1909B3` |
| `results/logs/bfcl__local_ollama.runlog.jsonl` | 实验三逐代诊断与 prompt diff | `8792363ADC1DE6EC21641B12F90EE6B546283AD1712C6B3257375F978C9C942A` |
| `results/logs/bfcl__local_ollama.runlog.summary.json` | 实验三学习曲线汇总 | `3B9A5A9F00EF53133E6D699EB8EEEE08D8153E708F7CB1F06EE4698540EEF73A` |
| `results/bfcl__static_20test.json` | 实验四 static 最终指标 | `2E4B2F3F8B3F17F900A3D8D982E47C0A988DF5D31273E2FE4C67D6DC3AC455E4` |
| `results/logs/bfcl__local_ollama_static.log` | 实验四人类可读日志 | `0F5DC83195A6BA4E15CE6320EC78439F6D796E43BE646EB558735422D62F0640` |
| `results/logs/bfcl__local_ollama_static.runlog.jsonl` | 实验四结构化日志 | `D43D1F38C7DE4EE2FFD4B5A6709096E8E33841FB92B37FC84A0713066776864A` |
| `results/logs/bfcl__local_ollama_static.runlog.summary.json` | 实验四汇总 | `315E2E38B4F902E77CBA5FA74AFBF756A32DED5F90A2BD47A0D6C37774DE2520` |
| `results/bfcl__evo_paper1ep.json` | 实验五最终指标 | `123B98E4FFB3A4A771222C4951D28878A6D58F82C5DA27E8049BBBB48AF3065C` |
| `results/logs/bfcl__local_ollama_paper1ep.log` | 实验五人类可读日志 | `FE9470052B19847B2746E1CE18F2CB3CA782F3538BEA319134E75D38E4589C86` |
| `results/logs/bfcl__local_ollama_paper1ep.runlog.jsonl` | 实验五逐代诊断与 prompt diff | `6CE8B8C1760D8EA8CDC4FCC5F74FCDE1FC7B3F91E1467632EE911ED1AA478D4A` |
| `results/logs/bfcl__local_ollama_paper1ep.runlog.summary.json` | 实验五学习曲线汇总 | `33D806F77B95BA6A0A9D128E3E6DDE3BA6E41B19BE04F3C1651E2E2E2B5C530A` |
| `results/bfcl__static_full.json` | 实验六 static full 最终指标 | `6130FA987A3E6299699979CEE32DD36194444E3DFCC361CCEC7AF4B09A50FF13` |
| `results/logs/bfcl__local_ollama_static_full.log` | 实验六人类可读日志 | `34CD34A37517FDFDD29D1C5B4FC465814F4894D2C349521E7C4A814F5175BB00` |
| `results/logs/bfcl__local_ollama_static_full.runlog.jsonl` | 实验六结构化日志 | `03C192C93AE4F63ADA906BF10BD34732972784BEA3A51DC27DF669EEBCE4C5CE` |
| `results/logs/bfcl__local_ollama_static_full.runlog.summary.json` | 实验六汇总 | `707367A48199E3554A93893B0686D9892213FF60819B21699CE7CC884FEBA359` |
| `results/dummy__local_ollama.json` | Dummy 流程验证指标 | `29563DDAED5F434F4329E67E0701DE4F4E12BCB6E42EF1594A0CD7DB3162F839` |
| `configs/local_ollama.yaml` | 本地运行配置 | `38B50C47DA08E54B52D1B4E823E73255B57C6D9F295C99BD152298C361BF20F0` |
| `configs/local_ollama_static.yaml` | Static 运行配置（CLI 覆盖关闭进化） | `38B50C47DA08E54B52D1B4E823E73255B57C6D9F295C99BD152298C361BF20F0` |
| `configs/local_ollama_paper1ep.yaml` | 实验五配置（CLI 覆盖论文规模参数） | `38B50C47DA08E54B52D1B4E823E73255B57C6D9F295C99BD152298C361BF20F0` |
| `configs/local_ollama_static_full.yaml` | 实验六配置（CLI 覆盖关闭进化） | `38B50C47DA08E54B52D1B4E823E73255B57C6D9F295C99BD152298C361BF20F0` |
| `configs/Modelfile.qwen3-8b` | Ollama 模型运行参数 | `ED658899FE7684EF2E81676DF53E03E1FAF6CB6425757A81173B15CADA7B0A70` |

实验三虽然通过 `--out` 将最终 JSON 保存为新文件，但 runlog 文件名仍由 config basename
`local_ollama` 决定，因此实验二的三个同名日志已被实验三覆盖；实验二的最终 JSON 仍保留。
表中 runlog 校验值均对应实验三。后续实验应使用不同 config 文件名或在运行后立即归档整个
`results/`，并持续记录 seed、命令、Git commit 和文件哈希。

## 14. 实验七：静态策略 + JSON Schema 提示

### 14.1 实验目的与实现

本实验开始验证 JSON Schema 是否能帮助 Caller 正确构造工具参数。当前实现仅将工具原始
`parameters` JSON Schema 放入 Caller 提示词；不进行本地参数校验、不触发修复调用，也不使用
受约束解码，因此不会因校验或修复增加模型调用。实验开关为 `caller_schema: true`。

原始 BFCL 工具定义由 Gorilla/BFCL 仓库读取，schema 版数据单独写入
`data_schema/bfcl/samples.json`，不覆盖既有 `data/bfcl/samples.json`。重建后，150 个任务的
ID、query、gold_plan 和 gold_match 均与既有数据一致；333/333 个可用工具保留了参数 schema。

运行配置：`configs/local_ollama_static_schema.yaml`。命令：

```powershell
.\.venv\Scripts\python.exe run.py `
  --config configs/local_ollama_static_schema.yaml `
  --benchmark bfcl `
  --out results\bfcl__static_schema.json
```

### 14.2 结果

| 指标 | 静态 + Schema（本实验） | 静态无 Schema（实验六） |
|---|---:|---:|
| BFCL 成功数 | 14/30 | 3/30 |
| 成功率 | 46.67% | 10.00% |
| 平均 reward | 44.74 | 19.08 |
| tokens | 90,910 | 78,533 |
| 耗时 | 257.6 秒（约 4 分 18 秒） | 234.5 秒（约 3 分 55 秒） |

相较实验六，静态 + Schema 多成功 11 题，成功率提高 36.67 个百分点，平均 reward 提高
25.66；tokens 增加约 15.8%，耗时增加约 9.9%。两个结果均为 seed 42、90/30/30 划分、30 条
held-out test，且 held-out leak=0。数据核对确认两个版本的任务和 gold 完全相同，主要处理差异是
本实验向 Caller 提供了原始工具参数 schema。

### 14.3 阶段性解释与限制

这是单次本地运行，结果显示 Schema 提示有很强的正向信号，但尚不足以证明提升稳定或可泛化。
目前只完成静态策略条件下的对照；还需运行 EvoTool + Schema，判断进化是否能在 schema 已提供时
继续带来增益。后续可补跑多个 seed，并保存逐题预测与调用参数，分析被修复的失败是否主要属于
类型、必填参数或额外参数错误。

| 文件 | 用途 | SHA-256 |
|---|---|---|
| `data_schema/bfcl/samples.json` | 保留原始工具参数 schema 的 150 条 BFCL 样本 | `420DE7DE354868067B77CEE605507FA424232B4F612EB5E5D5A8698DF5F86D1D` |
| `results/bfcl__static_schema.json` | 实验七最终指标 | `E0630EB9BB64AC0485A869DB9139DD3A0FF1C8F57001234D208E3F0967546CFF` |
| `results/logs/bfcl__local_ollama_static_schema.runlog.jsonl` | 实验七结构化 runlog | `E5B55C7151D94F73B9A30D8FA02542ACC948CD869F5F7E0347C95FAE9022EB4C` |
| `results/logs/bfcl__local_ollama_static_schema.runlog.summary.json` | 实验七汇总 | `B8D6F7F513DA14C1E1E714263353DE2A26F63E5417D069E1F14BC060CA8C2001` |


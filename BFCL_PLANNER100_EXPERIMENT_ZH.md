# BFCL Planner 优化：100 题确认性实验

实验已完成。正式结果与逐题机制分析见 `BFCL_PLANNER100_RESULTS_ZH.md`。

## 研究问题

导师反馈指出，公开代码中的 Planner 看不到工具定义，因此即使 Prompt 要求“按工具能力决定步骤粒度”，模型也缺少做出该判断的信息。此前 4 个失败案例的小实验还显示，保留已调用参数的历史可能减少重复调用或遗漏请求。

本轮把这两个因素做成独立开关，在 100 道题上进行 2×2 配对消融：

| 条件 | Planner 获得工具名、能力描述、完整参数 Schema | 历史保留 subgoal/tool/args/status/output |
|---|---:|---:|
| control | 否 | 否 |
| planner_tools | 是 | 否 |
| history | 否 | 是 |
| tools_history | 是 | 是 |

四组都使用冻结的初始四模块 Prompt、Caller Schema、`evotool-qwen3:8b`、temperature 0、seed 42 和相同的 100 道题；不运行 evolution，不使用 Repair，也不向生成过程暴露 gold。这样可以把 Planner 输入架构的效果与 EvoTool 搜索过程分开。

Planner 工具条件增加三部分信息：精确工具名、能力描述、完整 `parameter_schema`。拆分规则要求一个子目标对应一次必要工具调用；若单次调用能覆盖多个字段或约束则合并；只有确实需要不同调用时才拆分，并覆盖每个实体一次。

历史条件把原先的文本摘要改为结构化记录，显式保留已经执行的参数、状态和输出。BFCL 不执行真实工具，因此 output 仍为空，但 args 足以检验重复调用和需求覆盖。

## 数据划分

原 30 题实验使用 seed 42 打乱后的第 121–150 个样本。本轮使用同一次打乱后的前 100 个样本，因此与先前已经逐题检查的 30 题交集为 0。运行脚本会在调用模型前再次检查四组样本完全一致、数量为 100、与旧 30 题无重叠，并把 ID 和数据 SHA-256 写入 manifest。

这 100 题曾属于旧 EvoTool 的 train/selection 区域，所以本轮结论应表述为“冻结静态策略上的架构确认实验”，不应称为原 EvoTool 进化策略的全新 held-out 成绩。若后续要重新运行 evolution 并报告严格泛化成绩，需要从 BFCL 原始数据另建至少 220 条样本，保持 90/30/100 三部分不重叠。

## 主要指标与人工排查

主指标是 BFCL 严格 AST 成功率。同时报告 mean reward、tokens、耗时、相对 control 的新增成功和回归、双侧精确 McNemar 检验，以及 2×2 交互效应 `tools_history - planner_tools - history + control`。对四组逐题结果继续按 `schema_interface`、`planning`、`selection`、`semantic_argument` 分类。

人工优先排查四类配对变化：Planner 条件独有改善、history 条件独有改善、组合条件才改善、control 成功但处理组回归。每类抽取 5–10 题，核对 query、工具 Schema、plan 和 predicted calls，判断变化来自合并字段、去重、补齐实体、工具选择还是参数语义。

若 `tools_history` 明显优于两个单因素，可以进一步研究跨模块信息流与耦合错误；若 `planner_tools` 已贡献大部分提升，则下一步重点研究工具能力表示与步骤粒度；若提升只集中在少数模式，应先扩展到其他 benchmark，再讨论论文层面的共性。

## 运行命令

先确认 Ollama 服务和模型：

```powershell
Set-Location D:\Evotool
ollama list
Invoke-RestMethod http://127.0.0.1:11434/api/tags
```

只检查配置、100 个样本 ID 和旧测试集交集，不调用模型：

```powershell
.\.venv\Scripts\python.exe scripts\run_bfcl_planner100.py --dry-run
```

顺序执行四组实验并自动生成配对分析：

```powershell
.\.venv\Scripts\python.exe scripts\run_bfcl_planner100.py
```

结果保存到 `results/planner100/`：每组各有汇总 JSON 和逐题 JSONL，另有 `manifest.json` 与 `comparison.json`。脚本发现已有同名结果时会拒绝覆盖；再次运行请指定新目录：

```powershell
.\.venv\Scripts\python.exe scripts\run_bfcl_planner100.py --outdir results/planner100_repeat_02
```

若希望逐组运行，可执行：

```powershell
.\.venv\Scripts\python.exe run.py --config configs/bfcl_planner100_control.yaml --benchmark bfcl --out results/planner100/control.json
.\.venv\Scripts\python.exe run.py --config configs/bfcl_planner100_tools.yaml --benchmark bfcl --out results/planner100/planner_tools.json
.\.venv\Scripts\python.exe run.py --config configs/bfcl_planner100_history.yaml --benchmark bfcl --out results/planner100/history.json
.\.venv\Scripts\python.exe run.py --config configs/bfcl_planner100_tools_history.yaml --benchmark bfcl --out results/planner100/tools_history.json
```

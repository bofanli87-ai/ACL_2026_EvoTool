# 学校电脑交接与实验运行手册

本文面向 `bofanli87-ai/ACL_2026_EvoTool`。目标是让学校电脑拉取当前代码后，先完成离线验收，再运行两组实验：

1. Planner Tool Context × Structured History 的 2×2 静态实验；
2. 在相同信息接口下，Static 与 EvoTool Evolution 的匹配对照。

## 1. 当前实现边界

当前代码已经实现并接入训练、选择、测试和结果日志：

- `planner_tool_context`：Planner 可读取工具名称、能力描述和完整参数 Schema；
- `structured_history`：后续模块保留已完成调用的 subgoal、tool、arguments、status 和 output；
- `caller_schema`：Caller 可读取源参数 Schema；
- BFCL 逐题输出、Caller trace 和错误诊断；
- 本手册中的匹配 Static/Evolution 配置与一键运行脚本。

这不等于已经实现论文附录描述的全部能力。结构化步骤依赖、真实工具响应写回 STATE、预算/终止约束、完整模块级轨迹归因等仍应按照
`docs/evotool_alignment/EVOTOOL_PAPER_CODE_ALIGNMENT_ZH.md` 继续验收和补齐。因此，以下实验应标记为“当前已实现接口补齐版”，不能写成“完整论文复现”。

## 2. 拉取与建立环境

第一次使用：

```powershell
git clone https://github.com/bofanli87-ai/ACL_2026_EvoTool.git
cd ACL_2026_EvoTool
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
```

已经克隆过：

```powershell
cd ACL_2026_EvoTool
git status --short
git pull origin main
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
```

如果 `git status --short` 显示学校电脑有未提交修改，先保存或提交，不要直接覆盖。

## 3. 模型服务

当前学校实验配置使用 Ollama 的 OpenAI-compatible 接口：

```powershell
ollama pull qwen3:8b
ollama create evotool-qwen3:8b -f configs/Modelfile.qwen3-8b
ollama list
```

Ollama 桌面版通常会自动启动服务。否则执行：

```powershell
ollama serve
```

配置要求模型名称为 `evotool-qwen3:8b`，接口为 `http://127.0.0.1:11434/v1`。不要只 pull `qwen3:8b` 后跳过 `ollama create`，否则配置中的模型名称不匹配。

## 4. 运行前验收

```powershell
.\.venv\Scripts\python.exe -m pytest -q
powershell -ExecutionPolicy Bypass -File scripts/check_local.ps1
```

预期：测试全部通过；offline smoke 通过；检查脚本能看到 `evotool-qwen3:8b`。

## 5. 实验一：2×2 信息接口静态实验

先检查数据划分与将要运行的命令：

```powershell
.\.venv\Scripts\python.exe scripts/run_bfcl_planner100.py --dry-run
```

正式运行：

```powershell
.\.venv\Scripts\python.exe scripts/run_bfcl_planner100.py --outdir results/planner100_school
```

四个条件分别为 Control、Planner Tools、Structured History、Tools + History。结果与汇总位于：

```text
results/planner100_school/manifest.json
results/planner100_school/control.json
results/planner100_school/planner_tools.json
results/planner100_school/history.json
results/planner100_school/tools_history.json
results/planner100_school/comparison.json
```

注意：这 100 题用于诊断和确认，不应作为从未接触过的最终测试集。

## 6. 实验二：接口补齐后的 Static vs Evolution

先执行 dry-run。脚本会验证两个配置除 Evolution 处理字段外完全一致：

```powershell
.\.venv\Scripts\python.exe scripts/run_bfcl_aligned_comparison.py --dry-run
```

先跑 1 epoch：

```powershell
.\.venv\Scripts\python.exe scripts/run_bfcl_aligned_comparison.py `
  --epochs 1 `
  --outdir results/aligned_comparison_1ep
```

确认流程无误后跑论文预算的 3 epochs：

```powershell
.\.venv\Scripts\python.exe scripts/run_bfcl_aligned_comparison.py `
  --epochs 3 `
  --outdir results/aligned_comparison_3ep
```

关键输出：

```text
results/aligned_comparison_1ep/manifest.json
results/aligned_comparison_1ep/static.json
results/aligned_comparison_1ep/static.episodes.jsonl
results/aligned_comparison_1ep/evolution.json
results/aligned_comparison_1ep/evolution.episodes.jsonl
results/aligned_comparison_1ep/comparison.json
```

`comparison.json` 中的 `evolution_minus_static` 是当前接口补齐后 Evolution 的独立增益。不要将它与 36%→57% 的静态接口改进混在一起报告。

## 7. 结果回传与错误归因

实验完成后至少保留并回传：

```text
manifest.json
comparison.json
static.json / evolution.json
static.episodes.jsonl / evolution.episodes.jsonl
results/**/logs/*.runlog.jsonl
results/**/logs/*.summary.json
```

逐题比较时优先检查：

- 参数绑定错误是否来自 Planner、信息传递还是 Caller；
- 重复/遗漏调用是否已经出现在 Planner plan；
- Caller trace 是否拿到了正确工具 Schema 和当前步骤；
- Evolution 的 Blamer 是否归因到正确模块；
- Mutation 是否实际修改了对应行为规则并修复原错误。

不要直接提交大体积运行日志和模型文件。先将结果目录压缩保存，再选择必要的汇总、manifest 和代表性轨迹进入 Git。

## 8. 常见问题

### 输出目录已存在

实验脚本默认拒绝覆盖。改用新的目录：

```powershell
--outdir results/aligned_comparison_3ep_seed42_r2
```

### 显存不足

不要降低两组对照中的上下文长度或模型而只重跑一组。Static 与 Evolution 必须使用同一个模型服务和同一组非处理配置。优先改到显存更大的学校服务器运行。

### 需要改模型接口

同时修改两个匹配配置：

```text
configs/bfcl_aligned_static.yaml
configs/bfcl_aligned_evolution.yaml
```

修改后必须重新执行 `--dry-run`；匹配检查失败时不要开始实验。

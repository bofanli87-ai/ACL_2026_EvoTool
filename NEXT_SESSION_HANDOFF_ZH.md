# 下一会话交接记录

更新时间：2026-10-12（Asia/Shanghai）

## 当前研究方向

导师要求先诊断 EvoTool 的提升来自 reasoning 还是格式/接口修复，并比较 Baseline、Schema、
EvoTool、EvoTool+Schema 和简单 Repair。进一步目标是验证：reasoning 错误改 prompt，格式错误用
schema，确定性接口错误改 code/validator，是否优于把所有规则累积到 prompt。

## 今天已经完成

### 代码与测试

- `run.py`：保存 held-out 逐题 `.episodes.jsonl`；
- `src/bfcl_error_analysis.py`：BFCL 确定性离线错误分类；
- `src/schema_repair.py`：无额外 LLM、无 gold 的保守 Schema Repair；
- `scripts/apply_bfcl_repair_offline.py`：对固定 Baseline 输出应用 Repair；
- `scripts/analyze_bfcl_conditions.py`：配对分析与 2×2 interaction；
- 六个 `configs/bfcl_diag_*.yaml` 配置；
- 测试结果：15 passed。

测试命令：

```powershell
.\.venv\Scripts\python.exe -m pytest tests -q -p no:cacheprovider
```

工作树存在尚未提交的新代码、配置和文档，不要执行 reset/checkout 清理。目录
`pytest-cache-files-s5u03nm7` 是 pytest 创建但无权限访问的缓存残留，与实验无关。

### 静态实验结果

| 条件 | 成功率 |
|---|---:|
| Baseline | 2/30（6.67%） |
| Schema | 13/30（43.33%） |
| Repair v1 在线重跑 | 8/30（26.67%，不是最终结论） |
| Schema + Repair v1 | 13/30（43.33%） |

初版 Repair 漏掉 BFCL schema 方言中的 `float`。修正 `float -> number`、`dict -> object`、
`tuple -> array` 后，在同一次 Baseline 输出上严格离线 Repair 得到 13/30。

关键发现：

- Schema 和修正后的离线 Repair 都从 2/30 提升到 13/30；
- 二者修复的 11 个样本完全相同，且没有回归；
- Schema 输出再应用 Repair 时 0 个 edit，仍为 13/30；
- Schema 剩余 17 个失败：14 个 planning/tool-selection 主错误，3 个 semantic-argument 主错误；
- 阶段性证据表明 Schema 与 Repair 的格式收益高度重复。

完整方法、结果、校验值见 `BFCL_STATIC_DIAGNOSTIC_RESULTS_ZH.md`。

## 明天第一步：检查 Ollama

重启后执行：

```powershell
cd D:\EVotool\ACL_2026_EvoTool
ollama list
Invoke-RestMethod http://127.0.0.1:11434/api/tags
```

模型列表应包含 `evotool-qwen3:8b`。若模型存在但服务没有启动，在单独 PowerShell 中运行并保持窗口：

```powershell
ollama serve
```

## 明天运行的两个大实验

### A. EvoTool 无 Schema

```powershell
.\.venv\Scripts\python.exe run.py `
  --config configs/bfcl_diag_evotool.yaml `
  --benchmark bfcl `
  --out results/diag_evotool.json
```

预期产物：

```text
results/diag_evotool.json
results/diag_evotool.episodes.jsonl
results/logs/bfcl__bfcl_diag_evotool.log
results/logs/bfcl__bfcl_diag_evotool.runlog.jsonl
results/logs/bfcl__bfcl_diag_evotool.runlog.summary.json
```

### B. EvoTool + Schema

```powershell
.\.venv\Scripts\python.exe run.py `
  --config configs/bfcl_diag_evotool_schema.yaml `
  --benchmark bfcl `
  --out results/diag_evotool_schema.json
```

控制台应显示：

```text
caller JSON Schema prompt: enabled (333/333 tools have schema)
split: train=90 sel=30 test=30 (held-out leak=0)
```

预期产物：

```text
results/diag_evotool_schema.json
results/diag_evotool_schema.episodes.jsonl
results/logs/bfcl__bfcl_diag_evotool_schema.log
results/logs/bfcl__bfcl_diag_evotool_schema.runlog.jsonl
results/logs/bfcl__bfcl_diag_evotool_schema.runlog.summary.json
```

两组均为 seed 42、90/30/30、batch size 3、1 epoch（30 generations），每组预计 50–90 分钟
或更久；`caller_repair` 都是 false，避免混入 Repair 因素。

## 两个实验完成后的分析

```powershell
.\.venv\Scripts\python.exe scripts/analyze_bfcl_conditions.py `
  --runs `
    baseline=results/diag_baseline.episodes.jsonl `
    schema=results/diag_schema.episodes.jsonl `
    repair_offline=results/diag_baseline_offline_repair.episodes.jsonl `
    evotool=results/diag_evotool.episodes.jsonl `
    evotool_schema=results/diag_evotool_schema.episodes.jsonl `
  --json-out results/diag_full_comparison.json
```

重点分析：

1. 核心四条件的 2×2 interaction；
2. EvoTool 与 Schema 修复样本的重叠和互补；
3. EvoTool 是否修复剩余 14 个 planning/selection 失败；
4. Schema 是否减少 Caller mutation 或改变接受率；
5. 新增成功、回归与 prompt 样本绑定；
6. tokens 和耗时。

最后将完整结果追加到 `REPRODUCTION_REPORT_ZH.md`。

## 关键文件

- `BFCL_STATIC_DIAGNOSTIC_RESULTS_ZH.md`：今天的正式结果记录；
- `BFCL_DIAGNOSTIC_EXPERIMENT_ZH.md`：完整实验操作说明；
- `NEXT_SESSION_HANDOFF_ZH.md`：本交接；
- `results/diag_static_comparison.json`：静态比较；
- `results/diag_baseline.episodes.jsonl`：Baseline 逐题；
- `results/diag_schema.episodes.jsonl`：Schema 逐题；
- `results/diag_baseline_offline_repair.episodes.jsonl`：严格配对 Repair。

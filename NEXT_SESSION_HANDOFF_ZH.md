# 明日实验交接记录

这份文件用于重启后重新开启对话时快速恢复进度。请先从个人 GitHub 仓库 clone 项目，再按“下一步”运行 EvoTool + JSON Schema 实验。

## 仓库与当前状态

- GitHub：<https://github.com/bofanli87-ai/ACL_2026_EvoTool>
- 本地项目：`D:\EVotool\ACL_2026_EvoTool`
- 实验方向：BFCL Caller 的 JSON Schema 提示消融。
- 代码已增加 `caller_schema` 开关；此实验只在 Caller prompt 中提供工具原始参数 JSON Schema，不做本地校验、自动修复或受约束解码。
- schema 数据已保存为 `data_schema/bfcl/samples.json`，不覆盖旧的 `data/bfcl/samples.json`。
- schema 数据含 150 条样本；所有 333 个可用工具均保留 `parameter_schema`。旧数据和新数据的 150 条样本 `id/query/gold_plan/gold_match` 已核对一致。
- 当前 `main` 的重要文件已上传到个人 GitHub 仓库，包括项目 `src/` 代码、schema 数据、实验配置、报告及静态组结果/runlog。上传时本机 Git Credential Manager 异常，因此通过 GitHub 接口逐文件保存；在新设备上请 clone 个人仓库，不要从旧电脑的本地分支直接 push。

## 已完成的 JSON Schema 静态实验

- 配置：`configs/local_ollama_static_schema.yaml`
- 结果：`results/bfcl__static_schema.json`
- 日志：`results/logs/bfcl__local_ollama_static_schema.log`
- 结构化逐代日志：`results/logs/bfcl__local_ollama_static_schema.runlog.jsonl`
- 汇总：`results/logs/bfcl__local_ollama_static_schema.runlog.summary.json`
- 指标：14/30 成功（46.67%），mean reward 44.74，90,910 tokens，257.6 秒；seed 42，train/sel/test=90/30/30，held-out leak=0。
- 无 Schema 静态历史对照（`results/bfcl__static_full.json`）：3/30（10.0%），mean reward 19.08，78,533 tokens，234.5 秒。
- 新旧数据样本一致，静态 Schema 结果是明显的初步正向信号；但目前各条件仅单次运行，不能据此声称统计稳定或普遍提升。
- 完整记录已写入 `REPRODUCTION_REPORT_ZH.md` 第 14 节。

## 明天下一步：运行 EvoTool + Schema（1 epoch）

在仓库根目录 PowerShell 中执行：

```powershell
.\.venv\Scripts\python.exe run.py `
  --config configs/local_ollama_evo_schema.yaml `
  --benchmark bfcl `
  --out results\bfcl__evo_schema_1ep.json
```

开跑前后确认控制台显示 Schema 已启用且覆盖数大于零，预期类似：

```text
caller JSON Schema prompt: enabled (333/333 tools have schema)
split: train=90 sel=30 test=30 (held-out leak=0)
```

此配置使用 seed 42、90/30/30 划分、batch size 3、1 epoch，即 30 generations。沿用此前本地 Ollama Qwen3-8B Q4_K_M 运行速度估算，约需 50–90 分钟；schema 较长时可能更久。请以最终 JSON 中的 `seconds` 为准。

预计产物：

- `results/bfcl__evo_schema_1ep.json`
- `results/logs/bfcl__local_ollama_evo_schema.log`
- `results/logs/bfcl__local_ollama_evo_schema.runlog.jsonl`
- `results/logs/bfcl__local_ollama_evo_schema.runlog.summary.json`

完成后，把控制台的 `runlog -> ...` / `saved -> ...` 信息或上述结果发给助手。分析时比较四个条件：静态无 Schema（3/30）、静态 + Schema（14/30）、EvoTool 无 Schema（历史结果 13/30），以及本次 EvoTool + Schema。重点看 Schema 是否对进化策略有额外收益、Caller mutation 接受情况、测试成功数、token/耗时与逐题回归。然后将新结果及分析追加到 `REPRODUCTION_REPORT_ZH.md`。

## 换设备恢复提示

仓库已备份项目代码、schema 样本和结果，但 `.venv` 与 Ollama 模型权重不会上传。新设备需要安装 Python 3.11+、依赖与 Ollama，并准备模型 `evotool-qwen3:8b`；本地部署说明见 `LOCAL_REPRO_ZH.md`。若电脑重启后模型不在 Ollama 列表，重新执行 `ollama pull qwen3:8b` 和 `ollama create evotool-qwen3:8b -f configs/Modelfile.qwen3-8b`。


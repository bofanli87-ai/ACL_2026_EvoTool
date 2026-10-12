# BFCL 错误诊断与干预位置实验

本轮实验回答两个问题：EvoTool 的收益主要来自 reasoning 还是接口格式修复；Schema、EvoTool
与确定性 Repair 的收益是重复还是互补。

## 运行前检查

在项目根目录 PowerShell 中确认 Ollama 服务与模型可用：

```powershell
ollama list
Invoke-RestMethod http://127.0.0.1:11434/api/tags
```

模型列表应包含 `evotool-qwen3:8b`。若没有：

```powershell
ollama pull qwen3:8b
ollama create evotool-qwen3:8b -f configs/Modelfile.qwen3-8b
```

## 第一批：四个静态条件

每个条件约需数分钟。四条命令应分别生成一个汇总 JSON 和一个同名的
`.episodes.jsonl` 逐题文件。

```powershell
.\.venv\Scripts\python.exe run.py --config configs/bfcl_diag_baseline.yaml --benchmark bfcl --out results/diag_baseline.json
.\.venv\Scripts\python.exe run.py --config configs/bfcl_diag_schema.yaml --benchmark bfcl --out results/diag_schema.json
.\.venv\Scripts\python.exe run.py --config configs/bfcl_diag_repair.yaml --benchmark bfcl --out results/diag_repair.json
.\.venv\Scripts\python.exe run.py --config configs/bfcl_diag_schema_repair.yaml --benchmark bfcl --out results/diag_schema_repair.json
```

## 第二批：两个一轮 EvoTool 条件

每个条件预计 50–90 分钟或更久：

```powershell
.\.venv\Scripts\python.exe run.py --config configs/bfcl_diag_evotool.yaml --benchmark bfcl --out results/diag_evotool.json
.\.venv\Scripts\python.exe run.py --config configs/bfcl_diag_evotool_schema.yaml --benchmark bfcl --out results/diag_evotool_schema.json
```

所有配置都使用 `data_schema` 中完全相同的 150 条样本，但只有对应开关开启时才向 Caller
展示 Schema 或执行 Repair。默认继承 seed 42、90/30/30 划分、temperature 0。

## 严格配对的离线 Repair

Ollama 即使在 temperature 0 下重复运行也可能有轻微输出波动。为了把 Repair 的效果与模型重跑
波动分开，应将 Repair 直接应用于同一次 Baseline 输出：

```powershell
.\.venv\Scripts\python.exe scripts/apply_bfcl_repair_offline.py `
  --episodes results/diag_baseline.episodes.jsonl `
  --out results/diag_baseline_offline_repair.episodes.jsonl
```

该脚本只读取工具 schema 来修改参数；gold 只在修改完成后用于重新评分。BFCL 源数据使用
`float`、`dict`、`tuple` 等 JSON-Schema-like 类型名，Repair 会分别规范化为
`number`、`object`、`array`。

## 汇总分析

六个实验完成后运行：

```powershell
.\.venv\Scripts\python.exe scripts/analyze_bfcl_conditions.py `
  --runs `
    baseline=results/diag_baseline.episodes.jsonl `
    schema=results/diag_schema.episodes.jsonl `
    repair=results/diag_repair.episodes.jsonl `
    schema_repair=results/diag_schema_repair.episodes.jsonl `
    evotool=results/diag_evotool.episodes.jsonl `
    evotool_schema=results/diag_evotool_schema.episodes.jsonl `
  --json-out results/diag_comparison.json
```

脚本会输出每个条件的成功数、失败主类别、相对 Baseline 的逐题转移表，以及核心 2×2
实验的交互效应。错误分析使用 held-out gold，只用于离线报告，绝不会进入模型提示或 Repair。

## 测试

```powershell
.\.venv\Scripts\python.exe -m pytest tests -q -p no:cacheprovider
```

当前 Repair 仅执行可审计的确定性操作：数字/布尔/JSON 容器的无歧义类型转换、递归元素
转换，以及仅在 `additionalProperties: false` 时删除未声明字段。它不会补全缺失参数、猜测值或
调用另一个 LLM。

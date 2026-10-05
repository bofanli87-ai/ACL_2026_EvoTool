# EvoTool 本地复现（Windows，无远程服务器）

本项目不需要真实工具 API 或单独的工具服务器：ToolBench、RestBench、BFCL 和
τ-bench 的工具响应都在本地离线执行或回放。唯一需要的“服务”是运行在本机的
OpenAI 兼容大模型端点。

## 1. Python 环境

在 PowerShell 中进入仓库根目录：

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe scripts\offline_smoke.py
```

不要直接使用本机 PATH 中的 `python`：本机当前解析到 Python 3.9，而项目要求
Python 3.11 或更高版本。

## 2. 本机模型：推荐 Ollama

安装 Windows 版 Ollama 后，新开一个 PowerShell：

```powershell
ollama pull qwen3:8b
ollama create evotool-qwen3:8b -f configs\Modelfile.qwen3-8b
ollama serve
```

如果桌面版已在后台运行，`ollama serve` 可能提示端口已占用，这是正常的，无需再启。
默认接口是 `http://127.0.0.1:11434/v1`，仓库已提供
`configs/local_ollama.yaml` 与之匹配。`Modelfile.qwen3-8b` 会把上下文固定为
8192 tokens，与原仓库 vLLM 配置一致；否则显存不足 24 GiB 时，Ollama 默认只分配
4K 上下文，τ-bench 的长提示会被截断。

内存建议：Qwen3-8B 的量化版通常需要约 6 GB 存储，并建议至少 8–12 GB 可用内存。
纯 CPU 可以运行，但完整进化会非常慢。内存不足时可先创建相同的 4B 自定义模型，
并通过命令行覆盖模型名；这只能验证流程，不能复现论文的 Qwen3-8B 数值。

```powershell
ollama pull qwen3:4b
ollama create evotool-qwen3:4b -f configs\Modelfile.qwen3-4b
```

检查全部本地依赖：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\check_local.ps1
```

## 3. 分层复现

先做最小流程验证（dummy，1 个 epoch）：

```powershell
.\.venv\Scripts\python.exe run.py --config configs/local_ollama.yaml --benchmark dummy
```

若使用上面的 4B 模型，在命令末尾加：

```powershell
--override llm.model_name=evotool-qwen3:4b
```

再跑仓库自带的 BFCL 150 条演示集：

```powershell
.\.venv\Scripts\python.exe run.py --config configs/local_ollama.yaml --benchmark bfcl
```

正式使用论文预算（3 epochs，共 90 generations）：

```powershell
.\.venv\Scripts\python.exe run.py --config configs/local_ollama.yaml --benchmark bfcl --override evolve.epochs=3
```

ToolBench 和 RestBench 的演示数据也已包含：把 `bfcl` 分别换成 `toolbench` 或
`restbench` 即可。τ-bench 数据未直接附带，需按 README 从官方仓库构建后再运行。

结果写入 `results/`，包括最终 JSON、文本日志以及每代演化的 JSONL 日志。

## 4. “跑通”与“复现论文结果”的区别

- `configs/local_ollama.yaml` 使用 Ollama 的量化 Qwen3-8B，适合无服务器的本地复现。
- 论文结果使用完整官方数据集和论文指定推理后端/模型；仓库内 150 条数据只是演示子集。
- 量化方式、模型版本、推理框架和硬件都会造成数值差异，因此本地方案主要复现方法与
  演化趋势，不保证逐项得到论文表格中的分数。
- 若以后有 NVIDIA GPU + WSL2/Linux，可改用仓库的 `scripts/launch_vllm.sh`，更接近论文设置。

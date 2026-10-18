# 学校电脑上的最小验证

## 需要带走什么

在学校电脑的仓库中执行 git pull --ff-only 后，使用仓库根目录下的 bad_cases 文件夹，无需解压。真正运行模型只需要其中的 `run_focused_validation.py`，其余文件供核对。使用原 EvoTool 完整仓库和原虚拟环境，保持原模型 evotool-qwen3:8b 与模型服务正常。

脚本已经通过 Python 语法检查，尚未在真实模型环境联调。默认只展示设置，不调用模型。它不修改仓库代码、不运行 evolution、不覆盖原结果，输出目录已存在时会拒绝运行。

## 第一步 核对版本并预览

将下面两个路径改成学校电脑的实际位置。示例是 Windows PowerShell：

```powershell
$repoPath = 'D:/research/ACL_2026_EvoTool'
$casePath = Join-Path $repoPath 'bad_cases'
Set-Location $repoPath
git rev-parse HEAD
.\.venv\Scripts\python.exe "$casePath/run_focused_validation.py" --repo "$repoPath" --out "$repoPath/results/badcase_pilot_01"
```

原始分析版本为 ede2328b8e54eafa6c91e8e0c8e9d42adb238c46。若版本已更新，不要为了匹配本报告强制 reset；先保存当前状态并告知差异。检查预览中的模型、服务地址、temperature、max_steps 是否与原运行一致。预览应显示 4 题 × 5 条件 × 1 次 = 20 episodes。API 调用次数不等于 episodes 数。

## 第二步 首批运行

```powershell
.\.venv\Scripts\python.exe "$casePath/run_focused_validation.py" --repo "$repoPath" --out "$repoPath/results/badcase_pilot_01" --execute
```

五个条件：control（冻结原策略）；strong_prompt（仅加强规划提示）；planner_tools（给 Planner 补充工具定义）；history_args（仅在历史中保留实际参数）；tools_and_history（后两者组合）。不向生成 prompt 提供 gold。学校本地评分过程仍使用原 gold。

实际输入长度不同，因此不属于严格等 token 预算实验。脚本会记录 tokens 和时间。先用这些小范围干预定位机制，勿作为新的 held-out 或论文成绩。

## 第三步 独立重复

首批流程正常后运行：

```powershell
.\.venv\Scripts\python.exe "$casePath/run_focused_validation.py" --repo "$repoPath" --repeats 3 --out "$repoPath/results/badcase_repeat_01" --execute
```

这会产生 60 episodes。每题每条件每次都清除本地 episode cache，避免“重复”实际读取缓存；模型温度仍为 0，仅检查服务和生成是否稳定。不要因为 dry run 不建目录就误以为模型任务已经运行。

如果中途报错，保留已经产生的目录，用新的输出目录重跑，勿手工删除已保存证据。运行时异常单独记录，不将其当作模型推理失败。不要把不完整结果与完整结果直接合计。

## 返回哪些结果

把新生成的整个目录发回，至少包含：

- manifest.json：实际模型设置、冻结 prompt、代码和数据哈希。
- episodes.jsonl：每步 subgoal、tool、args、observation，以及全部模型请求和原始输出。
- summary.json：各条件成功数和 tokens；只有正常结束才生成。

如异常中止，再附终端错误信息。无需发送 API 密钥或 .env。

## 人工需要核对的四个问题

1. bfcl_145：交换 GCD 两个参数应视为语义等价，但原严格分数保留不改。
2. bfcl_56：菜谱名称只是另一种表达，还是具体实体不一致？没有真实搜索返回，不能仅凭字符串确定。
3. bfcl_51：L.A. Lakers 与 L.A Lakers 的标点差异是否应算失败？
4. bfcl_140：generate_human_image 与 generate_image 的说明是否足以唯一决定选择？先确定工具歧义，再当作多模块错误案例。

这些都可以先在 Case_Evidence_ZH.md 和 case_evidence.json 中查看，不必马上询问导师。给出你的判断和依据即可。

## 暂时不需要做

不重跑完整进化、不扩成大规模 Prompt/Schema/Code 矩阵、不改 gold、不把手工修复当成自动方法。先得到上述小规模轨迹，再决定是否补充原成功样本回归测试和未查看测试集验证。

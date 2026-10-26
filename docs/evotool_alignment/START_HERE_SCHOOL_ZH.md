# 学校电脑接手入口

把整个 `evotool_alignment` 文件夹复制到学校电脑。建议放到完整 EvoTool 仓库的 `docs/evotool_alignment/`，先阅读同目录 `EVOTOOL_PAPER_CODE_ALIGNMENT_ZH.md`。本文中的命令在 EvoTool 仓库根目录执行。

此包包含一份详细对齐指南、此接手清单、`SOURCE_INDEX.json` 和 13 份固定版本的源码/实验说明文本快照。`reference_code/` 仅供离线核对，不要用它覆盖学校当前源码。

## 先确认你修改的是正确版本

本次审计基于你的 `bofanli87-ai/ACL_2026_EvoTool`，commit：

```text
4fb3fbb8d35874e4dc0aa50e5de9c9f3816c61c9
```

官方对照为 `SYang2000/ACL_2026_EvoTool`，commit：

```text
6a82719ea6e22cf23f963078e2527094e50b47f6
```

在学校执行以下只读检查，保存输出。旧实验路径为 `D:\Evotool`，若位置不同先进入实际仓库。

```powershell
Get-Location
git status --short
git rev-parse HEAD
git diff --stat
git diff -- src/policy/modules.py src/policy/agent.py src/evolve/loop.py src/evolve/mutate.py
rg -n 'planner_tool_context|structured_history|blame_rationale|gold_args|generations' src
```

有未提交修改就先核对并保留。此指南未检查学校电脑未提交内容；不要为了对齐审计版本而 reset、checkout 覆盖或直接 pull。

## 建议分六批实施

| 批次 | 对应主指南任务 | 交付 / 验收 |
|---|---|---|
| 1 | T0、T7 | 保存版本与配置；统一 run_id；四模块实际输入输出日志；缓存隔离 |
| 2 | T1、T2 | Blamer 理由到 Mutator；分数解析；重复工具调用诊断；fake client 测试 |
| 3 | T3、T4 | 结构化 plan；当前步骤到 Caller；Selector action 兼容 |
| 4 | T5、T6 | 保留历史；真实响应写回 STATE；依赖、预算、一次 fallback |
| 5 | 第 7 节 | 先离线契约测试，再 6–10 道开发题和少量成功题回归 |
| 6 | 第 8 节 | 固定新数据划分，运行 static/evolution 对比，生成逐题结果 |

每批保存 diff 摘要、实际修改项和验收结果；是否 commit/push 由你明确决定。

## 不能漏掉的实验约束

1. 36%→57% 来自冻结初始策略的静态实验，不能当作 Evolution 提升。
2. 这 100 题已处于旧 train/selection 范围，且经过错误分析；可以用于诊断，不作为未经接触的新测试集。
3. 现有 100 题配置 `n_train=0,n_sel=0,epochs=0`，不能只打开 blame 就开始有效进化。
4. 简单初始 Prompt 与论文最终 ToolBench Prompt 分开。先补运行时接口，最终 Prompt 直接加载另设条件。
5. 同一对照中的模型、初始规则、评分器、数据、非处理开关和调用预算保持一致。新版本增加输出 token 预算时同步调整对照。
6. BFCL 当前 AST 通道不执行真实工具；STATE 返回值和 fallback 用可执行环境另测，禁止用 gold 伪造 observation。
7. 核心接口实验完成不等于完整附录功能已实现；主指南 P2 项需要单独验收。

## 可直接交给学校电脑上助手的任务描述

```text
请先完整阅读 docs/evotool_alignment/EVOTOOL_PAPER_CODE_ALIGNMENT_ZH.md
及 SOURCE_INDEX.json，在当前完整 EvoTool 仓库实施论文对齐。

先检查 AGENTS.md、git status、HEAD 和学校现有未提交改动，
确认与审计 commit 4fb3fbb8d35874e4dc0aa50e5de9c9f3816c61c9 的差异。
不要覆盖当前改动，不自动 commit/push。

按 T0/T7、T1/T2、T3/T4、T5/T6 的顺序实现，优先保留已存在的
planner_tool_context、structured_history、Caller Schema 和旧实验兼容路径。
新增 profile/contract 字段必须贯穿训练、选择、测试、日志和缓存。

区分论文初始 Prompt、最终 ToolBench Prompt、工程兼容约定；
不要把最终策略直接塞进初始基线，也不要无标注修改评分器或奖励目标。
先通过 V01–V12 契约测试，再准备少量模型 smoke 测试。
输出修改摘要、测试证据、未完成项和完整的实验配置草案。
完整模型实验的实际预算与数据划分在配置明确后再安排，
不要直接用旧 100 题配置启动 Evolution。
```

## 接手记录

```text
School HEAD:
Uncommitted changes preserved:
Model / backend / context limit:
Data version / evaluator version:
Implemented task IDs:
Remaining task IDs:
Contract tests:
Smoke run directory:
Frozen experiment split manifest:
Interface profile:
Paper ambiguities and chosen conventions:
```

本包只提供审计与实施指南。本次没有在学校环境执行修改或实验，也没有自动同步到学校电脑或 GitHub。

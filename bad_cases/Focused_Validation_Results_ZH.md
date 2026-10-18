# Bad Case 聚焦验证结果

日期：2026-10-18

## 1 实验范围

本实验用于验证剩余失败案例中的候选机制，不作为新的 held-out 结果或总体准确率。
实验冻结 `g12-planner` 策略，不运行 evolution，不向生成 prompt 提供 gold。

运行设置：

- 仓库提交：`4d8a24cfee9473629a99839e74ba6a1bf689671d`
- 模型：`evotool-qwen3:8b`
- 服务：`http://127.0.0.1:11434/v1`
- temperature：0.0
- max_tokens：512
- max_steps：6
- 案例：`bfcl_58`、`bfcl_130`、`bfcl_149`、`bfcl_29`
- 条件：control、strong_prompt、planner_tools、history_args、tools_and_history

先完成 20 episodes 的 pilot，再用全新输出目录完成 3 次独立重复，共 60 episodes。
两轮均正常结束，没有 runtime error。

## 2 三次重复的主要结果

| 条件 | 成功数 | 成功率 | Tokens | 相对 control |
|---|---:|---:|---:|---:|
| control | 0/12 | 0.0% | 37,356 | — |
| strong_prompt | 5/12 | 41.7% | 22,894 | -38.7% |
| planner_tools | 3/12 | 25.0% | 37,017 | -0.9% |
| history_args | 2/12 | 16.7% | 40,394 | +8.1% |
| tools_and_history | 6/12 | 50.0% | 38,917 | +4.2% |

逐题成功次数：

| 案例 | control | strong_prompt | planner_tools | history_args | tools_and_history |
|---|---:|---:|---:|---:|---:|
| bfcl_58 | 0/3 | 2/3 | 3/3 | 0/3 | 3/3 |
| bfcl_130 | 0/3 | 3/3 | 0/3 | 0/3 | 0/3 |
| bfcl_149 | 0/3 | 0/3 | 0/3 | 2/3 | 3/3 |
| bfcl_29 | 0/3 | 0/3 | 0/3 | 0/3 | 0/3 |

## 3 逐题观察

### bfcl_58

control 对两个城市各产生一次正确查询后，又分别重复一次。Planner 获得工具定义后，
三次重复均把四次调用减少为正确的两次。组合条件同样稳定为 3/3。
strong_prompt 为 2/3，说明提示可以改善该问题，但本轮稳定性低于提供工具信息。

### bfcl_130

control 将每个城市的三个字段拆成六次调用。只有 strong_prompt 稳定地将其合并为
两个多字段调用，结果为 3/3。单纯给 Planner 工具定义没有改变拆分方式。
这说明工具可见性本身不足以保证模型利用数组参数进行任务合并。

### bfcl_149

control 重复 Music 并遗漏 Theater。history_args 在三次中成功两次；组合条件稳定成功
3/3。失败的 history_args 运行虽然生成了 Theater 调用，但遗漏日期。
本题支持工具信息和已调用参数历史可能存在互补作用。

### bfcl_29

planner_tools 和组合条件都将三次调用减少为两次，去除了重复的状态查询，但仍生成
`optional_param: true`，因此严格评分仍失败。本题说明修复规划层重复并不足以修复 Caller
的可选参数问题。

## 4 当前可以支持的判断

1. 模块信息流是一个真实候选因素。给 Planner 工具定义能够稳定修复 bfcl_58；保留历史
   参数能够部分修复 bfcl_149。
2. 不存在单一统一干预。bfcl_130 需要更强的合并提示，而工具定义没有奏效；bfcl_29
   的剩余问题位于参数生成层。
3. 多个局部错误可以同时存在。bfcl_29 中重复调用已经被修复，但整题仍因可选参数失败；
   bfcl_149 的正确结果需要同时覆盖 Music、Theater 及日期。
4. 最终整题 reward 会隐藏局部改善。这支持进一步研究细粒度信用分配和协同修复，但当前
   实验尚不能证明单模块修改必然无法一次解决多个问题。
5. Prompt、Schema 信息和结构化历史适合作为 Bad Case 的因果干预手段，而不是直接把本轮
   结果包装成新的总体 benchmark 成绩。

## 5 候选论文方向

- **接口感知或状态感知的进化**：除模块 prompt 外，允许优化模块间传递的工具能力、
  已调用参数和需求覆盖状态。
- **面向耦合错误的细粒度信用分配**：识别已经修复部分约束但最终仍失败的策略，并允许
  Prompt、Schema 与必要的 Code 机制进行受控协同干预。

这些方向已有具体案例和小规模干预证据，但新颖性与泛化性仍需结合相关工作、成功样本回归
及未查看测试集进一步验证。

## 6 原始输出

- `results/badcase_pilot_01/`：首次 20 episodes，包含 manifest、逐步轨迹和汇总。
- `results/badcase_repeat_01/`：三次独立重复的 60 episodes，包含 manifest、逐步轨迹和汇总。

pilot 与 repeat 应分别报告，不把两者直接合并为一个成功率。

# 从 Planner 修补转向论文问题：研究方向与人工失败审查

## 1. 当前结果应该怎样理解

100 题实验不能只写成“Planner tools + history 把成功率从 36% 提高到 57%”。更重要的机制是：

1. 给 Planner 完整工具信息后，planning 标签从 45 降到 10，平均 plan 从 3.68 步降到 2.68，说明模块输入决定了它能否按工具能力规划；
2. Planner 经常把不同实体的步骤压缩成相同工具名，导致任务约束在 Planner→Caller 边界丢失；
3. 历史参数可以恢复部分丢失信息，因此组合比单因素多出 +12 个百分点的正交互；
4. 组合仍有 43 个失败，其中 33 个已经具有正确调用数，主要瓶颈已从“做几步/选什么工具”转为“每一步绑定哪个实体、数值和约束”；
5. 现有终局奖励看不到这种局部改善。BFCL 没有执行输出，progress 只比较工具序列；参数从完全错误变成只错一个值时，只要整题仍失败，reward 可以完全不变；
6. EvoTool 每轮只改一个模块且要求 child reward 严格提高，多个约束需要联合修复时容易出现搜索障碍；
7. 一部分失败来自评测与任务语义，而非策略本身，例如嵌套容器的匹配、数学表达式规范化、交换律参数、地点语言/缩写和参考调用遗漏用户要求。

因此论文问题不应再表述成“怎样写出更好的 Planner prompt”，而应表述成：

> 模块化工具 Agent 在模块边界上会丢失哪些任务约束，终局奖励怎样掩盖局部修复，以及如何用约束级诊断和反事实干预共同优化 Prompt、通信接口和确定性执行层？

## 2. 建议的主方向

### 方向：接口感知、约束级的模块优化

把一个任务解析为需求单元，例如：

```text
(entity=New York, operation=predict_house_price, size=3000)
(entity=Los Angeles, operation=predict_house_price, size=4000)
```

跟踪每个需求单元在 `query → plan → selected tool → call arguments → observation` 中是否被保留、重复、遗漏或错误绑定。优化对象不再只有四段 Prompt，还包括模块间的消息 Schema、历史状态和必要的 validator/repair。

方法可以包含四部分：

1. **约束图**：表示实体、操作、参数、依赖和覆盖关系；
2. **边界诊断**：定位约束第一次在哪个模块边界消失或发生错误绑定；
3. **反事实信用分配**：分别替换 Planner 输出、Selector 选择或 Caller 参数，重放下游，测量该边界修复的边际贡献；
4. **协同修改与分层接受**：允许修改一个接口及其相邻模块；使用约束覆盖、工具正确、Schema 合法、参数正确和最终成功组成的向量奖励，保留局部真实改善，而不是只接受整题 reward 上升。

这个方向能统一现有发现：Schema/Repair 解决确定性接口约束；工具感知解决步骤粒度；结构化历史解决部分重复绑定；约束级信用解决“修了一部分但整题仍为 0”；协同修改解决跨模块耦合。

## 3. 哪些方向不适合单独作为论文创新

- 只给 Planner 增加工具名、描述和 Schema：这是必要基线，但属于公开实现补全；
- 只把 Planner 改成结构化 JSON：已有结构化规划与参数传递工作，单独新意较弱；
- 只做 step-level/process reward：Agent 细粒度信用分配已有较多工作；
- 只增加 deterministic schema repair：工程价值高，但范围偏窄；
- 只报告 BFCL 分数提升：BFCL 是无执行的严格 AST 匹配，无法单独证明真实多步 Agent 的一般性。

可能的新意位于它们的交叉处：**利用约束在模块边界上的保真度做因果定位，并联合优化 Prompt、消息接口与确定性层**。正式声称新颖性前仍需完整相关工作检索。

## 4. 人工排查方法

人工审查时不要从“哪个模块错了”开始，因为一题可能有多个错误。按以下顺序记录：

1. 从 query 手工列出所有需求单元：实体、操作、参数、约束、依赖；
2. 查看 Planner 是否完整覆盖每个需求单元，是否合并或拆分正确；
3. 找到第一个发生信息丢失的位置，而不是最后表现出错误的位置；
4. 检查 Selector 是否在正确需求单元上选择了正确工具；
5. 检查 Caller 参数属于当前步骤还是复制了上一步；
6. 分开记录 Schema/type 错误、参数值错误、可选参数错误和表示规范化错误；
7. 检查是否至少两个错误必须同时消除才能通过；
8. 最后判断 gold/评分器是否与用户语义、工具 Schema 或等价调用冲突。

每题至少填写以下字段：

| 字段 | 含义 |
|---|---|
| `human_primary_cause` | 最主要机制，不直接照抄自动标签 |
| `first_divergence_stage` | query→plan、plan→selector、selector→caller、caller→schema/execution、evaluator |
| `information_lost` | 丢失的实体、约束、依赖或历史状态 |
| `coupled_secondary_errors` | 其他必须共同修复的问题 |
| `benchmark_or_evaluator_issue` | gold 歧义、等价表达、严格匹配或本地评分问题 |
| `minimal_general_fix` | 不针对该题常量的最小通用修复 |
| `confidence` | high/medium/low |

已提供脚本生成预填表：

```powershell
.\.venv\Scripts\python.exe scripts\build_planner100_manual_audit.py
```

输出为 `results/planner100/manual_audit.csv`，包含组合条件的全部 43 个失败。自动 hints 只用于排序，最终原因必须人工填写。

另一个预填表 `results/planner100/manual_audit_all_changed.csv` 已覆盖四个条件间成功状态发生变化的全部 52 题，适合分析 8 个组合独有成功、10 个组合回归及其他条件差异。

## 5. 当前 43 个失败的优先审查簇

### A. 步骤—实体/参数绑定丢失

代表题：`bfcl_64, 110, 62, 86, 124, 128, 105, 137, 79, 35, 48`。调用数和工具通常正确，但相同工具的后续调用复制第一组参数。这一簇最直接支持“模块边界信息损失”。

### B. 需求覆盖与调用粒度

10 题调用数错误：少调用为 `bfcl_76, 117, 83, 32, 113`；多调用为 `bfcl_4, 65, 3, 15, 85`。需要区分真正的规划错误、用户要求与 gold 不一致、以及 max_steps/控制流限制。

### C. 工具选择与工具描述歧义

代表题：`bfcl_134, 142, 150, 30`。逐题判断错误来自工具语义重叠、Planner 意图丢失、Selector 决策，还是 gold 本身不合理。

### D. Schema、嵌套容器与可选参数

代表题：`bfcl_66, 67, 100, 120, 131, 43, 70`。必须同时核对 source parameter schema、预测 JSON、gold_match 和本地 AST checker。`bfcl_66/67/120` 出现 expected 与 actual 都显示 object 的异常标签，提示嵌套结构评分需要单独审计。

### E. 语义等价、规范化与 benchmark 噪声

代表题：`bfcl_5, 81, 84` 的数学表达式，`bfcl_144` 的 GCD 参数交换，`bfcl_132/135` 的语言和地点规范化，`bfcl_38` 的未指定数量，以及 `bfcl_30/85` 中用户要求与参考调用可能不一致。这些题不能直接归因给 Agent 推理能力。

### F. 状态依赖和不可执行评测

代表题：`bfcl_139` 的 clone 目录传递、`bfcl_73` 的生成文件到播放文件、`bfcl_85` 的中间计算结果。BFCL 不执行工具，不能验证真实 observation 驱动的参数传递；需要在 tau-bench 或 ToolSandbox 类环境复验。

## 6. 建议的实验路线

### 实验一：人工机制统计

先完成 43 个组合失败和 10 个回归的人工双层标注。主表报告“首次分歧边界”和“错误耦合数量”，不要只报告 Planner/Selector/Caller 标签。

### 实验二：已知故障注入

在原本成功的轨迹中分别注入：删除一个需求单元、交换工具、复制上一组参数、删除历史参数、制造 Schema 类型错误。故障来源是已知的，可直接测现有 Blamer 和新诊断器的定位准确率，避免用最终失败反推原因。

### 实验三：反事实边界修复

对失败轨迹逐层使用诊断 oracle：只修 Planner 结构、只修工具、只修参数、只修历史，再重放下游。测每次干预修复了多少约束和最终任务，从而估计模块及接口的边际贡献。

### 实验四：约束级接受规则

比较：终局 binary gate、现有 tool-sequence progress、约束向量 reward、允许协同修改。重点统计“最终仍失败但已修复若干约束”的 child 是否被保留，以及后续能否累积成成功策略。

### 实验五：跨环境泛化

至少覆盖三种环境：BFCL 的静态 AST、RestBench 的路径约束、tau-bench/ToolSandbox 的真实状态依赖。若方法只在 BFCL 有效，应收窄论文结论。

## 7. 论文可以形成的三个研究问题

- RQ1：模块化工具 Agent 的任务约束主要在哪些模块边界丢失，Prompt 优化是否会把错误从一个阶段转移到另一个阶段？
- RQ2：约束级、反事实信用分配能否比单一 Blamer 和终局 reward 更准确地定位并保留局部修复？
- RQ3：联合优化模块 Prompt、通信接口和确定性层，能否跨静态与状态化工具环境提高成功率并减少回归？

这三问可以构成“诊断发现—方法—跨环境验证”的完整论文结构，而不是继续堆叠单点修复。

## 8. 相关工作定位

- MIPRO（arXiv:2406.11695）已经研究多阶段 LM program 的联合 Prompt 优化与模块信用问题；
- Routine（arXiv:2507.14447）已经使用结构化规划和参数传递提高工具调用稳定性；
- Agent Lightning（arXiv:2508.03680）和 turn-level credit assignment（arXiv:2505.11821）已经研究 Agent 轨迹的细粒度信用；
- ToolSandbox（arXiv:2408.04682）已经强调状态依赖、动态中间里程碑和执行式评测。

因此应避免把“structured plan”“step reward”或“stateful evaluation”单独包装成新贡献。更有希望的差异点是模块边界上的约束保真、可控反事实定位，以及对 Prompt/接口/code 三层的联合选择。

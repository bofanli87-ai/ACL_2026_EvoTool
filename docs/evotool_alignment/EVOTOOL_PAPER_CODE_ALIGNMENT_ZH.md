# EvoTool 论文—代码对齐与学校电脑修改指南

审计日期：2026-10-26。交付范围：代码静态审计、论文核对、实现规格和验收方案；未修改 EvoTool 业务代码，未调用模型运行新实验。

## 1. 先读结论

建议以你 10 月 24 日的 EvoTool 仓库为起点，先补齐信息契约与 Evolution 数据传递，再进行受控实验。已经完成的 Planner 工具上下文和 Structured History 应保留为独立开关。

本次确认的主要缺口是：

1. Planner 仍输出字符串列表，没有可供程序使用的参数绑定、依赖和输出存储字段。
2. Selector 只返回工具名，Caller 无法接收结构化的当前步骤或 Selector action。
3. History 已保留参数，但没有实现命名变量、依赖解析、响应字段写回和失败恢复。
4. Blamer 的理由被记入日志，却未传给 Mutator；Blamer 输出分数也没有在程序中执行 `argmax` 一致性检查。
5. 诊断器按工具名合并参考参数，会丢失同一工具多次调用的信息。
6. 缓存、截断、日志和数据划分还存在影响实验解释的风险。

一个必要区分：论文 A.7 是初始 Prompt，A.8 第 17–20 页是 ToolBench 的最终 Prompt。最终 Prompt 中出现的复杂行为，不能直接全部放进初始策略，然后把结果称作 Evolution 从简单初始策略学到的收益。应先让运行时能表达和传递这些信息，冻结共同接口，再比较 Evolution 开关。[P1]

此外，论文正文、最终 Prompt 和公开实现之间存在不一致，不能承诺“唯一且完全相同”的还原。本指南为有歧义的部分提供明确的工程约定，并要求记录这些约定。

## 2. 审计对象与证据边界

| 对象 | 本次核查版本 | 用途 |
|---|---|---|
| 论文 | ACL 2026 正式版，20 页 | 主依据；正文、Algorithm 1、A.4–A.8 |
| 官方代码 | `SYang2000/ACL_2026_EvoTool`，HEAD `6a82719ea6e22cf23f963078e2527094e50b47f6` | 判断公开实现提供了什么 |
| 你的代码 | `bofanli87-ai/ACL_2026_EvoTool`，HEAD `4fb3fbb8d35874e4dc0aa50e5de9c9f3816c61c9` | 后续修改的主要参照 |
| 本机旧快照 | `outputs/evotool_review/source/`；manifest 记录 `ede2328b8e54eafa6c91e8e0c8e9d42adb238c46` | 对照旧实现；不是学校电脑最新工作区 |
| 100 题结果 | 你的仓库 `BFCL_PLANNER100_RESULTS_ZH.md`、实验设计与配置 | 核对 36/43/38/57 的实验语义 |

本机项目根目录是 MUSE，不能直接修改根目录 `agent.py` 来修复 EvoTool。学校电脑应进入完整 EvoTool 仓库；旧实验说明中的路径是 `D:\Evotool`，使用前核实实际位置。

下文 `src/...` 均是 **EvoTool 仓库相对路径**。行号主要对应你的 `4fb3fbb...` 版本；后续改变后优先按函数名定位。在线源码链接在第 12 节；随附证据快照可离线阅读。

学校电脑未提交的改动不在本次审计范围内。100 题原始 `results/planner100/manifest.json` 在 GitHub 请求返回 404，因此本次没有独立重算 100 题结果；36%→57% 引用的是现有报告，不能当作本次复现实验。[U1]

## 3. 论文依据索引与还原边界

以下为简短定位索引，具体修改方案是代码审计后的工程建议。

| 编号 | 正式版位置 | 核对重点 |
|---|---|---|
| P-A | §3，PDF 第 3 页 | 四模块、状态、冻结模型、任务评价 |
| P-B | §4.1–4.3，Algorithm 1（第 13 页） | 归因、单模块变异、批次接受、选择集保留及最终策略 |
| P-C | A.4，第 14 页 | 模块分数、证据、因果诊断 |
| P-D | A.5，第 15 页 | Mutator 的轨迹、反馈、Blamer 理由及分数 |
| P-E | A.6–A.7，第 15 页 | `G=8`、`B=3`、简单初始 Prompt |
| P-F | A.8，第 17 页 | 最终 Planner 的工具目录、状态、结构化步骤 |
| P-G | A.8，第 18 页 | 最终 Selector 的 action 对象 |
| P-H | A.8，第 19 页 | 最终 Caller 的验证、响应提取、状态写回 |
| P-I | A.8，第 20 页 | 最终 Synthesizer 的状态依据 |

来源：[正式论文 PDF][P1]。页码为 PDF 从 1 开始计数，不是印刷页号。

必须保留的四个边界：

- **初始与最终策略不同。** A.7 的简单初始规格与公开 `src/prompts.py` 基本对应；A.8 的复杂最终策略不能直接视作初始配置的遗漏。
- **输入可用性与规则强度不同。** 提供工具信息是一项接口改变；加入“覆盖全部实体、减少调用”等提示规则也是处理因素。你现有 `planner_tool_context` 同时改变二者，不能把其效果全部归因于信息量。
- **工具目录不等于所有 Schema。** A.8 Planner 的目录描述强调名称与简要能力；给 Planner 完整 JSON Schema 是合理的信息增强，但不能据此断言论文明确要求所有模块看到完整 Schema。
- **正文与附录角色有差异。** 正文 Caller 负责参数构造，而 A.8 Selector 已给出参数，Caller 更偏验证与执行。这需要兼容模式，不能悄悄改变职责后仍当作同一个实验条件。

## 4. 当前对齐矩阵

状态：“已有”指已检查实际数据通路；“部分”指部分字段或功能存在；“缺失”指本次所查路径没有实现；“待定”指论文未充分规定或需要学校环境补证。

| ID | 功能 / 依据 | 官方实现 | 你的最新实现 | 下一步与优先级 |
|---|---|---|---|---|
| A01 | 初始四模块规格 / P-E | 已有 | 沿用初始策略 | 保存 Prompt 哈希，勿用最终策略覆盖；P0 |
| A02 | Planner 工具上下文 / P-F | 缺失，还禁止具体工具名 | 已有 `planner_tool_context`，含完整 Schema 和规则 | 保留；拆分信息与规则开关；P0 |
| A03 | Planner 接收 STATE / P-F | 缺失 | 缺失 | 增加显式 state 参数；单轮开始为空是正常的；P1 |
| A04 | 结构化 plan / P-F | `list[str]` | 仍 `list[str]`，对象会被 `str()` | 建立有类型的 plan，保留绑定和依赖；P1 |
| A05 | 下游参数历史 / P-A、P-F–H | 摘要丢 args | 已有 `structured_history` | 保留并验证传入值与实际调用一致；P0 |
| A06 | 可寻址 STATE / P-F–H | 无命名变量 | 只有 `step_n` 历史条目 | 增加变量区及来源信息；P1 |
| A07 | Selector action / P-G | 只取 `tool/next_tool` | 同左 | 支持 action 对象及 `tool_name`，防止静默 NONE；P1 |
| A08 | Caller 消费步骤/action / P-H | 当前字符串子目标 | 同左；另有 Caller Schema | 显式传入步骤和参数建议；P1 |
| A09 | 调用后写回 / P-H | executor 执行，只有摘要 | executor 执行并保留历史 | 基于真实响应应用 `store_as`；P1 |
| A10 | 依赖与 fallback / P-F–H | 无显式调度 | 无显式调度 | 明确状态机和调用预算；P2 |
| A11 | Synthesizer 看参数与结果 / P-A、P-I | 已有 steps 渲染 | 已有 | 无需“从零补历史”；新增 state/plan 兼容；P2 |
| A12 | Blamer 分数和逐模块证据 / P-C | 返回 primary；无分数校验 | 同左 | 分数校验、argmax、证据结构、fallback 日志；P0 |
| A13 | Blamer → Mutator 理由和分数 / P-D | 未传入 | 未传入 | 接通并记录实际输入；P0 |
| A14 | 重复调用诊断 | 工具名覆盖参数 | 同左 | 基于调用实例匹配，保留重复次数；P0 |
| A15 | 单模块变异 / P-B、P-D | `with_module` 已限制目标 | 已有 | 校验返回目标和类型，保存 edit_summary；P0 |
| A16 | mini-batch 严格改进后接受 / P-B | 已有 | 已有，可选改成 selection set | 主实验保持 `accept_on=batch`；P0 |
| A17 | diversity、win sampling、单 Θ* / P-B | 已有 | 已有 | 主实验保留；不额外添加路由；P0 |
| A18 | 演化预算 / P-E | 默认按 epoch 派生 | 同左，有 `generations` 覆盖 | 论文预算设 8，另列更大预算；P0 |
| A19 | Reward / P-A | 0.7 success + 0.3 progress | 同左 | 与任务成功率分开；核对论文未给定的 shaping；P0 |
| A20 | 完整可追溯轨迹 / P-C–D | 主要是结果元组 | 增加 Caller raw/parse trace | 补齐各模块实际输入、输出和截断；P0 |

P0 表示解释实验前的必要工作；P1 表示信息与结构补齐；P2 表示完整附录功能兼容。日志应从第一次修改时同步接入。

## 5. 按文件修改的任务单

### T0. 冻结版本、接口和数据

涉及：`src/config.py`、`run.py`、`src/benchmarks.py`、实验 runner。

先记录学校工作区 HEAD、未提交 diff、模型标识、后端、配置展开值、工具数据哈希、初始 Prompt、评分器版本、每组样本 ID。不要先执行 pull 或覆盖旧文件；先了解学校是否有未同步改动。

建议增加 `interface_profile`，取值 `legacy`、`aligned_core`、`appendix_compat`。这是**建议新增配置，当前不存在**。对应契约必须写进 manifest；不得由模型自行切换。

- `legacy`：保留历史基线行为，用于追溯。
- `aligned_core`：四模块职责保持正文式分工，接通结构化步骤、工具上下文、参数历史和状态；Caller 仍构造最终参数。
- `appendix_compat`：额外支持 A.8 action 格式、Selector 参数建议、Caller 验证/执行/状态写回、依赖和有限恢复。

冻结同一 profile 的初始规则和 I/O 契约后，才开启 Evolution。最终 Prompt 的完整复用应成为单独标记的实验条件。

验收：结果文件能唯一确定“代码 + 配置 + Prompt + 数据 + 评分器 + profile”；所有新配置在 `run.py → evolve/mean_reward/select/best_policy/run_episode` 全链路一致传递。

### T1. 修复 Evolution 的归因到修改通路

涉及：`src/evolve/loop.py:57,165`；`src/evolve/mutate.py:32`；`src/evolve/blame.py:52`；`src/prompts.py`。

已确认：`_choose_target()` 返回 `(target, blame_rationale)`，但 `_make_child()` 没有 rationale 参数；`mutate()` 拼接的 packet 中没有它。`use_feedback=True` 只会选择带反馈指令的 system prompt，不能证明 Blamer 反馈真的被送入模型。[U4]

修改链：

```text
blame -> BlameResult -> _make_child -> mutate -> MutationResult -> runlog
```

推荐 `BlameResult` 包含 `scores`、`primary`、`evidence`、`diagnosis`、`resolved_by`。四模块分数检查为有限的 0–1 数值，拒绝 NaN、字符串和缺项；合法分数下由程序取最大值。平分使用固定模块顺序并记录；分数无效时走明确的解析失败策略。模型给出的 primary 与 argmax 不同则记录冲突，不能静默信任 primary。

将 rationale、分数、当前模块实际接口说明、成功标志、奖励、诊断事件和对应轨迹送入 Mutator。`use_feedback=False` 的对照组明确屏蔽新增 rationale 字段，避免开关失去含义。

`MutationResult` 保存目标、错误模式、修改摘要、修订规格、解析状态及验证失败原因。只接受字符串类型的非空 `revised_spec`；核对返回目标与请求目标相同；非目标三模块逐字不变。无效结果作为 rejected/no-op 记录，不伪装成有效 child。

验收：使用 fake client 检查 Mutator 实际收到预设 diagnosis 和四个分数；一次仅改变目标模块；分数/primary 冲突、空修改、错误目标均有测试。

### T2. 修复会误导归因的重复调用诊断

涉及：`src/evolve/diagnostics.py:24,51`；必要时复用 `src/eval_bfcl_ast.py` 的匹配辅助函数。

`gold_args = {tool: args ...}` 会把同名工具前面的参考调用覆盖；`missing = [t for t in gold_tools if t not in pred_tools]` 只检查存在性，不检查次数。两者都是代码可确定的问题，但不能仅据此断言它们造成了现有 13/11 道错误。

修改建议：

1. 诊断对象使用“调用实例列表”，不能以工具名作为唯一键。
2. 无序并行调用按工具名及参数可接受关系做一对一匹配，保留未匹配预测和 gold；有序任务额外检查顺序。
3. BFCL 的允许值集合优先使用 `gold_match`，不能把任取一组 gold 参数当成唯一合法答案。
4. 区分调用数量差异、参数不匹配、Schema 违规、工具执行错误和环境不可用。HTTP 成功或 `status=success` 不等于用户任务的参数语义正确。
5. 输出 `step_id`、匹配依据及证据；调用数不同只能标为症状，不能直接证明 Planner 有错。

验收：同一工具分别用 10/20/30 三组参数全部正确时零参数误报；第三组重复第一组时准确定位；少调用一次和多调用一次分别报告。合法调用顺序交换是否通过由任务类别决定。

### T3. 让 Planner 输出保留信息

涉及：`src/policy/modules.py:42,83`；`src/policy/agent.py:60,110`；建议新增 `src/policy/contracts.py`。

你当前已有工具信息，但最终仍执行 `return [str(s)...]`。即使模型返回对象，程序也会把它变成 Python 字典字符串，没有类型校验和字段消费。[U2]

将 `run_planner` 的输入扩展为 `query, tools, state, contract`；返回有类型的 Plan 对象，至少保留步骤标识、具体子目标、参数绑定、依赖和 notes。兼容字符串列表时显式转换为旧版步骤，并记录 `legacy_adapter_used`，不要静默将任意对象字符串化。

建议的核心步骤示例（本指南的工程示例，非论文逐字模板）：

```json
{
  "step_id": "s2",
  "subgoal": "Compute the value for the 20-year request",
  "tool_name": "finance.present_value",
  "arguments_template": {"years": 20},
  "required_inputs": [],
  "depends_on": [],
  "expected_outputs": [],
  "store_as": {},
  "success_criteria": [],
  "fallback": null
}
```

工具名与参数名应来自真实工具定义，上例只是说明结构。所有对象字段使用 JSON 序列化；数字、布尔、数组和嵌套对象不能统一转成字符串。`tool_name` 在核心模式下可作为建议交给 Selector 核验。

初始协议只规定字段意义与合法输出。不要强制生成最终 Prompt 的全部策略性行为。拆分现有“工具信息开关”和额外拆步启发式，分别记录；“每个实体一次”并非通用真理，同一实体可能需要多个不同操作。

验收：fake Planner 返回 10/20/30 三个结构化步骤后，三组意图逐字段到达对应 Caller；对象往返序列化不丢字段；非法计划、重复 step_id、未知依赖返回明确错误。

### T4. 接通 Selector → Caller

涉及：`src/policy/modules.py:86,105,108`；`src/policy/agent.py:137`。

当前 Selector 只读取 `tool` 或 `next_tool`；若照附录输出 `tool_name`，会落到 `NONE`，整步被跳过。Caller 目前只接收子目标字符串，不接收完整 action。[U2]

核心模式建议：Selector 输入完整当前步骤、工具目录、STATE、已有历史，返回选定工具及选择理由；Caller 输入当前步骤和选定工具完整文档，构造最终参数。

附录兼容模式：Selector 返回结构化 action，包括 `tool_name`、`arguments`、`store_as`、fallback 和 rationale；Caller 接收该 action，验证或调整参数。分别保存 `selector_arguments` 与 `caller_arguments`，避免把 Selector 参数错误全归因于 Caller。

兼容解析接受旧字段名，但内部统一命名；没有任何合法工具字段的输出标为解析错误，不自动当成主动跳过。明确区分 `SKIP` 与 episode `STOP`，记录原因及未完成步骤。

验收：`tool_name` 不再被当成 NONE；同名工具的两个步骤能分别收到不同参数意图；Caller 最终参数与上游建议的差异可查询。

### T5. 保留 History，并实现可验证的 STATE 写回

涉及：`src/policy/agent.py:99,159`；`modules.py:_state_brief`；建议新增 `src/policy/state.py`。

当前 `structured_history` 已保留 subgoal/tool/arguments/status/output，并传给 Selector/Caller。不要重复实现或把它写成“当前完全没有历史”。但它尚未处理命名变量和依赖引用。[U3]

建议内部 state 分为 `history`、`variables`、`step_status`。这是 episode 内状态组织，不需要增加一个独立 Agent。

- history 从实际提交给 executor 的 `args` 和实际 observation 建立；不要完全依赖 executor 是否回传 args；保存深拷贝。
- variables 中每个值保留来源 step、工具和响应路径。`store_as` 解析真实响应，缺失字段返回 missing，禁止从 gold 或模型猜测补值。
- 引用语法固定一种，例如 `{"$ref":"STATE.selected_id"}`；只支持白名单路径解析，不使用 `eval`。这是工程约定，论文没有给出完整解析器。
- 覆盖已有变量需要明确记录；同名工具多次执行使用不同 step_id，不能相互覆盖。
- Synthesizer 同时接收可核验的 state 和原始 steps；不得把未执行调用的参数当作返回值。

BFCL 当前通道只生成调用，不执行工具：必须保留 `no_execution`，不得人为补 observation、把它标成 success，或利用 gold 推导下一步依赖。需要真实返回值的状态功能，应使用可执行的合成环境或合适的有状态 benchmark 验证。

验收：mock 工具真实返回 id=7，下一步引用为整数 7；缺字段时不产生 id；两次同工具历史均保留。BFCL AST 通道没有虚构结果。

### T6. 明确依赖、恢复和停止语义

涉及：`agent.py:run_episode`；contracts/state；executor 包装层。

当前是 `for sub in plan[:max_steps]`：截的是计划步骤数，不是实际调用数；被跳过的步骤也占计划位置，没有依赖检查、状态驱动重试和 fallback。[U3]

建议增加步骤状态 `pending/ready/running/completed/failed/blocked/skipped`，并记录终止原因。只执行依赖满足的步骤；检测循环、未知 step 和未解析变量；保留计划顺序作为多个 ready 步骤的稳定优先级。

必须区分“AST 调用已记录”和“工具执行成功”。前者可以计为调用生成完成，但不能因此满足依赖于真实响应的变量。

附录 Caller 同时出现“一次调用”与“失败后 fallback”要求，调用预算语义不充分。本指南建议：每个 action attempt 最多一次实际调用；失败后若有 fallback，则在下一 attempt 执行，单独记数，每个计划步骤最多一次 fallback。该约定必须披露，不能声称是论文唯一实现。

保留旧 profile 的 max_steps 语义以追溯旧结果；新 profile 明确拆分 `max_plan_steps` 与 `max_tool_calls`，不要默默变更预算。验证条件若涉及语义推断，应单独记录使用哪个模型和额外调用，不把自然语言 success_criteria 假装成已执行的确定性检查。

验收：依赖失败后下游 blocked；有 fallback 时只增加一次调用；循环依赖不会死循环；超预算保留未执行步骤列表。BFCL AST 模式默认不执行会增加调用的工具恢复。

### T7. 补齐日志、缓存和截断可观测性

涉及：`src/llm/client.py:27,71,86`；四个 module wrapper；`agent.py:114`；`run.py:87`；`src/runlog.py`。

当前 Caller trace 只有原始输出与解析标志；`generate_json_with_trace` 本身没有保存实际 messages。现有客户端可能在上下文超限后删掉最长消息中间部分并重试。因此，“组装了完整信息”不能等同于“模型确实收到了完整信息”。

每次模块调用至少记录：

```text
run_id / episode_id / phase(train|selection|test) / policy_id
module / step_id / attempt_id / contract_version
messages_before_truncation / messages_sent / truncation_reason
raw_output / parsed_output / parse_error / finish_reason
state_before / state_after / selected_tool / submitted_arguments
observation / execution_status / dependency_status
prompt_tokens / completion_tokens / latency / cache_hit
```

这些是实际 API 输入输出日志；无需让模型生成额外的隐式推理文本。缓存命中也要写事件并引用原轨迹。

缓存 key 当前有四份 Prompt、题目 id、Schema/Repair/Planner/History 开关，但没有 max_steps、数据/工具内容、模型版本、新 profile、干预条件和 repeat。新增这些维度或在每个隔离 run 开始清空缓存；重复试验必须真实执行，不能反复取相同缓存。temperature=0 也不应当作所有服务端运行严格确定的证明。

`--out` 只控制部分输出位置；runlog 路径仍由 `output_path + config basename` 决定。每组使用独立 output_path 或统一 run_id，防止同配置不同实验互相覆盖日志。

结构化计划明显比旧字符串列表长，当前 512 completion tokens 可能不足。先在开发样本检查 `finish_reason`、完整 JSON 和最长计划需求，再冻结统一的模块预算；如果增加预算，也要在对照组应用同一预算，不能把额外输出空间的效果混入接口收益。

验收：一次模拟上下文截断能同时看到原始/实际请求；跨 profile、跨预算、跨 repeat 不共用旧 episode；四模块错误与空计划可区分；所有实验日志不覆盖。

## 6. 已有 Evolution 功能应保留，另有几个配置差异要明示

`loop.py` 已实现 parent 采样、同批次 child 对比和严格大于后接受；`select.py` 已实现逐题获胜者保留、胜率权重及基于 selection 平均 reward 的最终单策略选择。这些不需要重新设计。[U4][O2]

建议主实验设置：

```yaml
evolve:
  mutation_target: blame
  selection: diversity
  parent_select: win
  accept_on: batch
  use_trajectory: true
  use_feedback: true
  test_ensemble: false
  log_test_eval: false
  epochs: 1
  generations: 8
  batch_size: 3
```

以上字段在所查代码中已有。`epochs` 必须大于 0，否则函数提前返回，即使 generations=8 也不会进化。静态条件可用 mutation_target=none、selection=static；同时保留相同的数据划分和 actor 接口。

论文 A.6 的 G=8 与代码默认 `3 * ceil(n_train/3)` 不一致，90 个训练样本时后者为 90 代。8 代作为论文预算检查；若另跑原项目预算，另表报告，保持不同接口条件的 Evolution 预算相同。[P1][O2]

现有优化 reward 是 `0.7*success + 0.3*progress`，不是 headline success。所查正文定义任务相关 R，但未明确给出这组 shaping 系数；不要把代码系数说成论文规定。先固定当前 reward 做接口对照；另设二值 success 目标作为敏感性实验。不同目标会改变 child 接受与种群选择，不能只换报表名字。[P2][U3]

补充观察：BFCL 的 `no_execution` 使 progress 的执行成功比例为 0。因此成功率 57% 与 mean reward 53.84 并不矛盾。使用独立的 `success` 字段计算准确率。

同分时 `select.py` 的 max 会优先保留靠前候选。论文未充分规定平分规则；先冻结原规则并记录，后续才考虑同分随机或共享胜数。`route_episode` 以 reward 打破平分，会接触任务评分，不适合当作不看答案的正常测试路由；主实验关闭 ensemble。

## 7. 从第一步开始准备验证，不等跑完再补日志

建议完成顺序：T0 → T7 的基础日志与缓存 → T1/T2 → T3/T4/T5 → T6。每个阶段都保存可独立开关的修改记录。

### 第一层：不调用真实模型的契约测试

| 测试 | 输入 / 干预 | 必须通过的条件 |
|---|---|---|
| V01 | Planner 返回三个同工具步骤，参数 10/20/30 | 每个 Caller 收到对应 intent，类型不丢 |
| V02 | Selector 返回 `tool_name` | 正确识别，不退化为 NONE |
| V03 | 两次真实调用相同工具不同参数 | history 两条，值来自实际 args |
| V04 | 上一步工具返回 id，下一步引用 | 正确写回与读取；missing 不猜测 |
| V05 | Blamer primary 与最大分数不符 | 记录冲突，按冻结规则解析 |
| V06 | Mutator 输入检查 | rationale、分数、局部轨迹和接口确实进入消息 |
| V07 | 同工具多次正确/重复/遗漏 | 诊断器不覆盖 gold、不忽略次数 |
| V08 | 计划解析失败、截断、超预算 | 分别记录原因，不合并成“Planner 空计划” |
| V09 | 切换 profile、模型、预算、repeat | 不发生错误缓存复用 |
| V10 | 同组静态与进化路径 | actor 信息接口一致；变异仅改目标 spec |
| V11 | gold 在 actor 输入中放置唯一标记 | 四模块实际 messages 中均不存在该标记 |
| V12 | 依赖环、执行失败、一次 fallback | 正确终止和记账，不增加隐式无限重试 |

fake client 测试验证“信息接通”，不能证明真实模型会正确利用信息。下一层再检查模型行为。

### 第二层：6–10 道开发题试运行

从现有 43 道错误中优先选 `bfcl_105/110/124/128`（多组参数），`bfcl_32/76/113`（遗漏、空计划），以及 `bfcl_139`（状态相关症状）。这些标签来自现有报告，尚不是干预确认的因果归因。

同时加几道原本成功的题，检查回归。输出逐模块实际输入、输出、解析状态和 step 对齐。`bfcl_76` 必须先排除 token 截断/解析失败，不能看到空 plan 就认定模型主动选择不执行。

现有 bfcl_139 通道没有真实工具返回，只能检查任务约束和参数引用，不能用它单独验收完整状态执行能力。状态写回和 fallback 使用可执行的小型测试环境另验收。

## 8. 正式实验设计：先把接口与 Evolution 分开

**必须纠正之前对话中的建议：不要简单在当前 100 题上重新进化后，把成绩当作新 held-out 泛化结果。** 你的实验设计已经说明，这 100 题位于旧实验 train/selection 区域；目前又经过逐题人工分析，可用于开发诊断。[U1]

新的泛化实验建立固定 train/selection/test manifest，例如至少 90/30/100 个互不重叠的真实样本；对于曾被研究者分析过的题标记暴露情况，最终确认尽量使用新的 test。保持 benchmark 原始划分约束，按原始题号和规范化内容同时去重。样本不足就停止，不能使用 `split_instances` 的尾部复用 fallback。

新旧模型或服务配置不同，旧的 36/57 只能作历史参考。先复核静态条件，再比较新实验。

建议四组主实验如下；为与你已有研究衔接，Caller Schema 在四组统一开启，Repair 统一关闭。因此 C00 不叫“完全原封不动的官方代码”，而叫“旧 Planner/History 接口对照”。

| 组 | actor 信息接口 | Evolution | 初始策略 |
|---|---|---|---|
| C00 | 旧 Planner/History | 关闭 | 同一初始模块规格 |
| C01 | 旧 Planner/History | 开启 | 同一初始模块规格 |
| C10 | `aligned_core` | 关闭 | 同一初始模块规格，适配共同新契约 |
| C11 | `aligned_core` | 开启 | 与 C10 完全相同起点 |

T1/T2 等 Evolution 修复对 C01/C11 使用同一实现；预算、模型、评分器、数据、初始行为规则保持一致。接口 profile 变化必然要求部分格式说明变化，记录其内容，不能声称四组完整 system prompt 字节完全一致。

分别计算：

```text
旧接口下 Evolution 增益 = C01 - C00
完整核心接口下 Evolution 增益 = C11 - C10
静态接口补齐增益 = C10 - C00
描述性交互 = (C11 - C10) - (C01 - C00)
```

如果想知道 T1/T2 修复 Evolution 本身的影响，增加一组“旧接口 + 未修复 Evolution”的桥接实验，不能把新 C01 直接和旧报告的 EvoTool 成绩相减。

完成核心实验后，若要达到附录完整功能，再以同样方式比较 `appendix_compat` 的 static/evolution；另列“直接装载 A.8 最终 Prompt”的迁移检查。ToolBench 最终策略中的地理、候选查询、过滤等规则不能不加说明地移植到 BFCL 并称作原版。

重复实验应固定数据划分，改变演化采样种子或真实运行重复次数。当前 seed 同时影响 split 和 evolution，需要拆分，不能每换一个 seed 就悄悄换测试题。temperature=0 下重复必须禁用跨重复缓存。

主表报告成功率、逐题新增成功/回归、置信区间或配对检验；同时报告训练/选择/测试成本、调用数、截断率、解析失败率及错误类型。多次运行给每次值与均值/波动；单次 McNemar 显著不等于跨运行稳定。

现有 `bfcl_planner100_tools_history.yaml` 的 `n_train=0,n_sel=0,epochs=0` 会使进化直接返回。它只能用于静态诊断，不能只把 mutation_target 改成 blame 就当作 Evolution 实验。

## 9. 后续细粒度归因实验的记录模板

第一阶段完成后，在新错误集合上做干预。对相同题、相同非目标模块、相同环境初始状态分别运行：

| 条件 | 改变内容 | 能回答什么 |
|---|---|---|
| 原始轨迹 | 无 | 确认失败和可复现程度 |
| 正确 Planner 输出 | 仅替换计划 | 下游在正确计划下能否成功 |
| 恢复接口字段 | 仅补回丢失的实际信息 | 是否存在传输/解析缺陷 |
| 正确参数输入 Caller | 仅提供当前调用所需参数 | 下游验证/执行是否仍出错 |
| 单模块 Prompt | 仅修改一个模块的行为规则 | Prompt 是否足以修复 |
| 正确 blame → 原 Mutator | 固定人工归因 | Mutation 能否把正确诊断变为有效修复 |

若直接将最终工具参数替换成 gold，验证的是“绕过参数生成后的下游能力”，不能证明 Caller 理解了信息。所有 oracle 条件单独标记，不进入正常准确率主表。

每题保存：症状、最早可证实的错误位置、模块可见输入、上游输出、接口转换、干预、修复/未修复、回归与尚不能排除的解释。一次成功干预说明存在可行修复路径，不自动证明唯一根因。

TRUCE/PIPE 可在这之后辅助设计归因/接口扰动实验；本次文档没有复现或评审这两篇工作。

## 10. 学校电脑上的完成标准

- [ ] 已核对学校 HEAD 和未提交改动与审计版本的差异。
- [ ] Planner 工具信息、完整步骤、参数意图、依赖能到达下游。
- [ ] History 已保留真实 args；STATE 可追溯到真实响应。
- [ ] Selector action 与 Caller 输入输出契约一致。
- [ ] Blamer 分数和理由进入 Mutator，非目标模块保持不变。
- [ ] 同工具多次调用诊断通过反例测试。
- [ ] 记录实际送出的 messages、截断、解析错误、finish_reason 和调用预算。
- [ ] 新字段贯穿训练、选择、测试和缓存键。
- [ ] train/selection/test 无重叠；正式实验未使用尾部复用。
- [ ] 四组配置的非处理因素一致，使用独立 run 目录。
- [ ] `aligned_core` 与 `appendix_compat` 的已实现/未实现功能分别标注。
- [ ] 结果报告区分接口补齐、Evolution、额外规则、执行恢复和评分修订。

只有完成 P2 的依赖、状态写回、恢复、action 兼容并通过可执行环境验收，才能称“已支持附录所列完整功能”；仅达到 57% 或实现结构化 JSON 不能作为此结论的依据。

## 11. 尚未解决的论文复现问题

以下问题应在复现报告中保留，必要时向作者核实；不会阻止先完成已确定的接口修复。

1. 论文最终四模块 Prompt 与公开固定 I/O 不兼容，实际生成论文结果时的 wrapper、parser、调度器版本未由当前材料确定。
2. 官方 ToolBench `theta_star.json` 声明来自 Qwen3-4B testbed，90/30/30 split、2026-06-28；它不是论文 Qwen3-8B 的完整训练产物。[O3]
3. 公开 SPEC 的默认代数与论文 A.6 不同；采样方式、初始种群规模和 tie-break 等细节也需要按版本披露。
4. 论文与代码的奖励 shaping、Blamer 参考答案可见范围、代表 episode 选择细节，不能仅凭注释声称完全一致。
5. BFCL 当前实现针对特定 AST 类别；其他 benchmark 还有 replay/mock/离线 judge。对齐接口并不等于复现原论文所有环境、模型和数据集结果。[O2]
6. 本地 BFCL checker 是重实现，文件注释里的 official 不能代替与官方 checker 固定版本的逐题对照。先冻结评分器；若发现 bug，单独记录修订并给全部实验组重评，不能只给改进组换评分。

## 12. 可追溯来源

[P1]: https://aclanthology.org/2026.acl-long.2016.pdf
[P2]: https://arxiv.org/html/2603.04900v1
[U1]: https://github.com/bofanli87-ai/ACL_2026_EvoTool/blob/4fb3fbb8d35874e4dc0aa50e5de9c9f3816c61c9/BFCL_PLANNER100_EXPERIMENT_ZH.md
[U2]: https://github.com/bofanli87-ai/ACL_2026_EvoTool/blob/4fb3fbb8d35874e4dc0aa50e5de9c9f3816c61c9/src/policy/modules.py
[U3]: https://github.com/bofanli87-ai/ACL_2026_EvoTool/blob/4fb3fbb8d35874e4dc0aa50e5de9c9f3816c61c9/src/policy/agent.py
[U4]: https://github.com/bofanli87-ai/ACL_2026_EvoTool/blob/4fb3fbb8d35874e4dc0aa50e5de9c9f3816c61c9/src/evolve/loop.py
[O2]: https://github.com/SYang2000/ACL_2026_EvoTool/blob/6a82719ea6e22cf23f963078e2527094e50b47f6/SPEC.md
[O3]: https://github.com/SYang2000/ACL_2026_EvoTool/blob/6a82719ea6e22cf23f963078e2527094e50b47f6/evolved_policies/toolbench/theta_star.json

- [P1 正式版论文][P1]；[P2 arXiv v1 正文][P2]。
- [U1 100 题实验设计与暴露说明][U1]；[100 题结果报告](https://github.com/bofanli87-ai/ACL_2026_EvoTool/blob/4fb3fbb8d35874e4dc0aa50e5de9c9f3816c61c9/BFCL_PLANNER100_RESULTS_ZH.md)。
- [U2 四模块 wrapper][U2]；[U3 episode 执行器][U3]；[U4 Evolution loop][U4]。
- [Mutator](https://github.com/bofanli87-ai/ACL_2026_EvoTool/blob/4fb3fbb8d35874e4dc0aa50e5de9c9f3816c61c9/src/evolve/mutate.py)；[Blamer](https://github.com/bofanli87-ai/ACL_2026_EvoTool/blob/4fb3fbb8d35874e4dc0aa50e5de9c9f3816c61c9/src/evolve/blame.py)；[diagnostics](https://github.com/bofanli87-ai/ACL_2026_EvoTool/blob/4fb3fbb8d35874e4dc0aa50e5de9c9f3816c61c9/src/evolve/diagnostics.py)。
- [LLM client](https://github.com/bofanli87-ai/ACL_2026_EvoTool/blob/4fb3fbb8d35874e4dc0aa50e5de9c9f3816c61c9/src/llm/client.py)；[配置](https://github.com/bofanli87-ai/ACL_2026_EvoTool/blob/4fb3fbb8d35874e4dc0aa50e5de9c9f3816c61c9/src/config.py)；[静态 100 题组合条件](https://github.com/bofanli87-ai/ACL_2026_EvoTool/blob/4fb3fbb8d35874e4dc0aa50e5de9c9f3816c61c9/configs/bfcl_planner100_tools_history.yaml)。
- [官方四模块 wrapper](https://github.com/SYang2000/ACL_2026_EvoTool/blob/6a82719ea6e22cf23f963078e2527094e50b47f6/src/policy/modules.py)；[O2 官方 SPEC][O2]；[O3 官方 testbed 策略产物][O3]。

本指南没有将论文最终 Prompt 整段复制到初始策略。建议结构、测试样例、状态机和修复次序均为本次工程建议，实施时应以学校代码与实际运行证据补充状态。

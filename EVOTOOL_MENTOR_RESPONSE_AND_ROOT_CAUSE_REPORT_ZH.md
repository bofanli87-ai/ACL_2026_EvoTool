# EvoTool汇报

## 一、与论文对齐接口
- Planner 可见工具名、描述和完整参数 Schema；
- Selector、Caller 可见包含历史参数的结构化调用历史；
- Caller 可见 JSON Schema；
- Blamer 的分数由程序校验并执行 argmax；
- Blamer rationale 已实际传入 Mutator；
- Mutator 会拒绝错误目标、空规格和未变化规格；
- 重复工具调用按调用实例进行一对一匹配，不再用工具名覆盖多组参数；
- 运行日志保存 Mutation 请求、响应和校验结果。


## 二、Evolution 在完整接口下进行的新实验


### 2.1 Static vs Evolution

Static 和 Evolution 使用相同模型、90/30/30 划分、初始 Prompt、Planner 工具上下文、结构化历史、Caller Schema 和单策略测试部署。

| 实验 | Static | Evolution | Evolution−Static | Evolution token |
|---|---:|---:|---:|---:|
| 修复前 1 epoch | 76.67% | 70.00% | −6.67 | 914,450 |
| 修复反馈链后 1 epoch | 76.67% | 83.33% | +6.66 | 1,487,395 |
| 修复反馈链后 3 epochs | 76.67% | 83.33% | +6.66 | 3,048,933 |

修复后的 3 epochs 逐题变化：

- 修复：`bfcl_8、58、104、115`；
- 退化：`bfcl_109、149`；
- 其余 24 题不变；

### 2.2 3 epochs 没有提供额外收益

经过检查和判断，整理出以下原因：

1. 后续搜索没有围绕最佳策略继续优化，后续的最佳策略为g15-caller，只有 parent 恰好选中 g15-caller，新规则才可能累积到它上面。虽然 g15-caller 的平均 selection reward 最高，但它只赢了一个具体样本，因此被选为 parent 的概率很低。后续大量代数继续从 init 生成新策略。
2. 剩余 5 题并不属于同一种 Prompt 错误，g15-caller 解决的是“重复工具调用复用第一组参数”。剩余失败需要不同机制（可见问题分析），这些问题很难靠继续扩写一条“调用参数应不同”的 Prompt 统一解决。

## 三、问题分析

### 3.1 最终 5 道失败的最早分歧与根本修复

| 样本 | 原因 |
|---|---|
| `bfcl_55` | planner给出的工具数量和顺序正确，但两个 guide 步骤没有绑定各自游戏和条件（planner给出的绑定参数不正确） |
| `bfcl_109` | planner规划成功，但caller调用参数错误 |
| `bfcl_149` | planner规划的信息过少，也属于绑定参数不对 |
| `bfcl_29` | Caller参数绑定错误 |
| `bfcl_56` | 评分较为严格 |

---

## 四、对五道错题针对性实验

### 4.1 最终结论

| 题号 | 稳定根因 | 单纯修改 Prompt 是否解决 | 真正需要的修复 |
|---|---|---|---|
| `bfcl_55` | Planner 没有保存两个相同工具调用各自的 intent—argument binding；Caller 无法从含混步骤稳定恢复 | 否 | 结构化 PlanStep，给每一步绑定参数和明确省略字段 |
| `bfcl_109` | Caller 对步骤字符串表示敏感，`g15-caller` 把明确的 5 年替换成 10 年 | 否 | 将 Planner 参数作为 locked args 直接传递并校验 |
| `bfcl_149` | Caller 丢弃用户实体中的 `CA`，属于实体保真错误 | 是，本题 3/3 | 保留 source span，并对共享实体字段加锁；Prompt 只能作为辅助 |
| `bfcl_29` | Caller 无依据开启 optional boolean，属于 default/optional 语义错误 | 是，本题 3/3 | 非 required 参数的确定性 evidence/default gate |
| `bfcl_56` | BFCL 不执行搜索，后续步骤没有真实 recipe 对象，只能自行合成名称 | 否 | 真实响应写入 STATE；无执行环境使用 query-anchor fallback |

五题中：

- 两题可由针对性的 Caller 行为规则修复：`bfcl_149、bfcl_29`；
- 两题需要结构化参数绑定或 locked args：`bfcl_55、bfcl_109`；
- 一题需要对象引用/STATE 接口：`bfcl_56`。

### 4.2 实验条件

#### 4.2.1 `baseline`

直接使用最终 3ep 保存的 `g15-caller` episode。五题均失败。

#### 4.2.2 `oracle_args`

不调用模型，直接把人工核对的正确参数替换到原工具序列，再使用当前 BFCL AST 评分器重评。

用途：确认工具数量、工具名称、人工预期参数和评分器之间没有其他冲突。

结果：5/5 通过。

#### 4.2.3 `caller_hint`

冻结原始 Planner 输出和原始 Selector 工具序列，只给当前 Caller 增加：

```text
AUTHORITATIVE_BINDINGS_FOR_CURRENT_CALL: {...}
Copy these bindings exactly. Do not import values from sibling calls.
```

Caller 仍需自己生成 JSON 参数。这组用于区分“上游没传信息”和“Caller 拿到仍不使用”。

#### 4.2.4 `oracle_plan`

将 Planner 输出替换为人工正确、参数明确的自然语言步骤，但不替换 Caller 输出。

#### 4.2.5 `caller_prompt`

冻结原始 Plan 和工具序列，只给 Caller 增加一条与错误类型对应的通用规则。规则不包含题号、具体实体或 gold 答案。

#### 4.2.6 `caller_rollback`

冻结原始 Plan 和工具序列，只把 `g15-caller` 换回 Initial Caller。

#### 4.2.7 `query_anchor` / `simulated_state`

只用于 `bfcl_56`：

- `query_anchor`：在无真实搜索结果时明确使用 query 中最小实体 `spaghetti`；
- `simulated_state`：模拟第一步真实返回 `{"name":"spaghetti"}`，观察后续 Caller 是否复用。

### 4.3 三次重复的稳定结果

`✓` 表示三次全部通过，`✗` 表示三次全部失败；`—` 表示该条件不适用。

| 题号 | baseline | oracle args | Caller hint | Oracle Plan | Caller Prompt | Caller rollback | Query anchor | Simulated STATE |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `bfcl_55` | ✗ | ✓ | ✓ | ✓ | ✗ | ✗ | — | — |
| `bfcl_109` | ✗ | ✓ | ✗ | ✓ | ✗ | ✓ | — | — |
| `bfcl_149` | ✗ | ✓ | ✓ | ✗ | ✓ | ✓ | — | — |
| `bfcl_29` | ✗ | ✓ | ✗ | ✓ | ✓ | ✗ | — | — |
| `bfcl_56` | ✗ | ✓ | ✓ | ✗ | ✗ | ✗ | ✓ | ✓ |


### 4.4 `bfcl_55`

#### 4.4.1 原始错误

原 Plan 只有工具名：

```json
[
  "BattleReignGameAPI.update_player_equipment",
  "GameGuideAPI.search_guide",
  "GameGuideAPI.search_guide"
]
```

第二、三次 Caller 都生成：

```json
{"game":"Battle Reign","condition":"snowy weather","type":"strategy"}
```

#### 4.4.2 干预结果

- Caller hint：3/3 通过；
- Oracle Plan：3/3 通过；
- Caller Prompt-only：0/3；
- Caller rollback：0/3；
- Planner Prompt-only 的一次运行仍把 `strategy` 错误加入 Battle Reign 步骤。

#### 4.4.3 判因

Caller 在拿到每一步明确参数绑定时可以正确生成，因此不是“Caller 完全不具备能力”。最早且最关键的问题是 Planner 把两个相同工具调用压缩成相同字符串，丢失：

```text
Battle Reign ↔ snowy weather
Shadow Fall ↔ strategy
```

但普通 Caller Prompt 无法从原始含混 Plan 稳定重建绑定，因此这是 Plan 接口的信息损失。

#### 4.4.4 真正修复

Planner 应输出结构化步骤：

```json
{
  "step_id": "guide_1",
  "tool": "GameGuideAPI.search_guide",
  "args": {"game":"Battle Reign","condition":"snowy weather"},
  "omitted_args": ["type"],
  "intent_id": "battle_reign_weather"
}
```

第三步则绑定 `Shadow Fall/strategy`，并把 `condition` 放入 `omitted_args`。Caller 不再重新从完整 query 猜参数归属。

### 4.5 `bfcl_109`

#### 4.5.1 原始错误

Planner 已正确写出 1、5、10 年，但 Caller 生成 1、10、10。

#### 4.5.2 干预结果

- Caller hint：0/3，即使追加正确 `number_of_years=5`，仍输出 10；
- current-step Caller Prompt：0/3；
- Caller rollback：3/3；
- Oracle Plan：3/3。

Oracle Plan 与原 Plan 的参数语义相同，只是采用更清楚的自然语言调用表达。这说明 Caller 对步骤表示形式高度敏感。`g15-caller` 的“每个调用应 unique and distinct”规则并没有保证当前步骤忠实性，并且相较 Initial Caller 发生了回归。

#### 4.5.3 判因

根因不是 Planner 缺少参数，也不是 history 丢失。根因是 Caller 没有把 Planner 中已经确定的参数当作约束，而是再次生成。

#### 4.5.4 真正修复

不要继续依赖 Caller 从字符串复制参数。把 Planner 参数解析为：

```json
{
  "number_of_years": {
    "value": 5,
    "source": "planner",
    "locked": true
  }
}
```

Caller 只生成未锁定字段。生成完成后检查 locked 字段；若 Caller 返回 10，程序直接拒绝或只修正该字段。

### 4.6 `bfcl_149`

#### 4.6.1 原始错误

两次 Caller 都把：

```text
San Diego, CA
```

截断为：

```text
San Diego
```

#### 4.6.2 干预结果

- entity-fidelity Caller Prompt：3/3；
- Caller rollback：3/3；
- Caller hint：3/3；
- Oracle Plan：0/3，即使 Plan 明确写出 `San Diego, CA`，Caller 仍删除 `CA`。

#### 4.6.3 判因

Oracle Plan 失败排除了“只要 Planner 写详细就能解决”的解释。直接错误位于 Caller 的实体复制/规范化过程。工具 Schema 接受并示例了 `City, State (abbr)`，所以删除 `CA` 没有接口依据。

#### 4.6.4 有效 Prompt

```text
Preserve user-provided named-entity spans verbatim, including qualifiers such as
state abbreviations and country names, unless the tool schema explicitly requires
a different normalization. Across repeated calls, keep shared fields unchanged.
```

#### 4.6.5 真正修复

Prompt 在本题有效，但更可靠的方案是保存 source span：

```json
{"city":{"value":"San Diego, CA","source_span":"San Diego, CA","locked":true}}
```

两个重复调用只允许修改 `event_type`，共享的 `city/date` 保持锁定。

### 4.7 `bfcl_29`

#### 4.7.1 原始错误

用户没有请求 additional details，但 Caller 生成：

```json
{"criminal_name":"John Doe","optional_param":true}
```

#### 4.7.2 干预结果

- optional/default Caller Prompt：3/3；
- Oracle Plan 明确写“省略 optional 参数”：3/3；
- Caller hint 只提供 required 参数并要求原样复制：0/3，Caller 仍主动增加 `true`；
- Caller rollback：0/3。

#### 4.7.3 判因

这不是参数信息缺失，而是 Caller 对 optional 参数的行为语义错误。仅给正确 required 参数不能阻止模型主动开启可选功能；

#### 4.7.4 有效 Prompt

```text
For a non-required parameter, include it only when the user explicitly requests
the capability represented by that parameter or an earlier observation provides
its value. Otherwise omit it; if the interface requires it, use the documented
default. Never turn an optional boolean on merely because it is available.
```

#### 4.7.5 真正修复

增加确定性 optional gate：

```text
if parameter not in schema.required
and query/state has no evidence for the optional capability:
    omit parameter
    # or use an explicit schema default when the interface requires it
```

不能把所有 optional boolean 一律改成 false；用户明确请求该能力时必须保留 true。

### 4.8 `bfcl_56`

#### 4.8.1 原始错误

搜索条件正确，但后两步合成：

```json
{"recipe":"homemade gluten free spaghetti"}
```

该字符串语义合理，但不在 BFCL gold 的有限允许集合中。

#### 4.8.2 干预结果

- dependency-only Oracle Plan：0/3；
- 普通 Caller Prompt：0/3；
- Caller rollback：0/3；
- Caller hint 明确 recipe=`spaghetti`：3/3；
- query-anchor Plan：3/3；
- 模拟第一步向 STATE 写入 `{"name":"spaghetti"}`：3/3。

#### 4.8.3 判因

仅声明“后两步依赖第一步”并不够，因为 BFCL 根本不执行 `recipe_search`，没有真实 recipe name/ID 写入 STATE。Caller 只能根据 query 自行合成一个描述性名称，评分器又只接受有限字符串。

因此这题主要是 no-execution 环境下的对象引用接口问题，不是普通的步骤遗漏。

#### 4.8.4 真正修复

真实可执行环境应当：

```json
{
  "step_1": {
    "output": {"recipe_id":"...", "name":"..."}
  }
}
```

后续步骤引用：

```json
{"recipe":{"from_step":"step_1","field":"name"}}
```

BFCL 无执行模式下，采用通用 fallback：使用 query 中最小、原样的核心实体 `spaghetti`，不把 homemade、healthy、gluten-free 等约束重新拼成一个虚构对象名。

### 4.9 复现实验文件

实验 runner：

- `scripts/run_bfcl_targeted_interventions.py`

离线上界：

- `results/aligned_comparison_3ep/interventions/offline_upper_bound.jsonl`
- `results/aligned_comparison_3ep/interventions/offline_upper_bound.summary.json`

第一次关键实验：

- `results/aligned_comparison_3ep/interventions/bfcl_109_pilot.jsonl`
- `results/aligned_comparison_3ep/interventions/four_cases_primary.jsonl`

第二、三次重复：

- `results/aligned_comparison_3ep/interventions/five_cases_rep2.jsonl`
- `results/aligned_comparison_3ep/interventions/five_cases_rep3.jsonl`

Prompt-only 补充实验：

- `results/aligned_comparison_3ep/interventions/prompt_factorial.jsonl`





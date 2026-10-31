# 本轮 BFCL 失败案例与模块责任分析

分析对象：`results/aligned_comparison_3ep/evolution.episodes.jsonl` 中最终策略 `g15-caller` 的全部 5 个失败案例。

## 1. 总体结论

5 个案例均未发现明确的工具选错或调用步骤数量错误。直接评分失败均发生在调用参数，但不能因此简单认定所有问题都只有 Caller 的责任。

| 样本 | Planner 情况 | 直接失败位置 | 模块归因 |
|---|---|---|---|
| `bfcl_109` 投资年限 | 明确写出 1、5、10 年，计划正确 | 第二次调用把 5 年写成 10 年 | Caller 明确偏离当前子目标 |
| `bfcl_55` 游戏攻略 | 工具数量正确，但两个查询子目标没有区分游戏和条件 | 混用条件、重复查询同一游戏 | Planner 表达不足；Caller 直接参数绑定错误 |
| `bfcl_149` 活动查询 | 两次查询结构合理 | 城市参数遗漏 `CA` | Caller 未保留用户约束、未遵循工具文档 |
| `bfcl_29` 犯罪记录 | 查询状态与犯罪性质，计划合理 | 擅自将可选参数设为 `true` | Caller 可选参数启用判断错误 |
| `bfcl_56` 菜谱 | 搜索、时间、营养三步合理 | 菜谱名称不在允许答案集合中 | Caller 参数表述不匹配；真实语义错误程度待核验 |

本轮 BFCL 是 `no_execution` 调用匹配通道，工具没有真正执行。本文所说的失败是调用生成或参数匹配失败，不是工具运行报错。

## 2. 归因依据与信息流

本分析核对了逐题日志中的用户请求、Planner 计划、预测调用、gold、Caller 原始输出，以及 `data_schema/bfcl/samples.json` 中的工具文档。

当前代码的信息流为：

1. Planner 生成字符串列表形式的计划。
2. 程序依次取出每个子目标，由 Selector 选择工具。
3. Caller 接收完整用户请求、当前子目标、所选工具文档与 Schema，以及此前调用的结构化历史。
4. Caller 重新生成参数 JSON；程序没有把计划字符串中的参数解析为不可改写的执行约束。
5. BFCL 只记录调用，不产生真实工具输出；最后根据调用列表评分。

代码依据：

- [agent.py](../../src/policy/agent.py)：`run_episode` 将当前子目标 `sub` 直接传入 Caller；`executor is None` 时记录 `no_execution`。
- [modules.py](../../src/policy/modules.py)：`run_caller` 传入 `USER_TASK`、`CURRENT_SUBGOAL`、工具文档和 `OBSERVATIONS SO FAR`。
- [eval_bfcl_ast.py](../../src/eval_bfcl_ast.py)：检查调用数量、工具名和参数允许值；字符串采用严格相等判断。
- [evaluators.py](../../src/evaluators.py)：BFCL 分支使用预测调用列表评分。

失败案例的 Caller 原始输出已包含对应错误，JSON 解析成功，且没有 repair 修改。因此没有证据把这些错误归因于 JSON 解析或确定性后处理。日志未保存每次 Caller 请求的完整消息；其输入组成由当前代码和轨迹重建，而不是直接读取完整请求快照。

## 3. bfcl_109：Planner 正确，Caller 明确偏离计划

### 用户要求与计划

用户要求本金 1000、年利率 5%，分别计算 1、5、10 年的未来价值。

Planner 实际输出：

```text
financials.calculate_future_value(present_value=1000, annual_interest_rate=0.05, number_of_years=1)
financials.calculate_future_value(present_value=1000, annual_interest_rate=0.05, number_of_years=5)
financials.calculate_future_value(present_value=1000, annual_interest_rate=0.05, number_of_years=10)
```

### 实际错误

| 调用步骤 | 计划中的年限 | Caller 实际年限 | 判断 |
|---|---:|---:|---|
| 1 | 1 | 1 | 正确 |
| 2 | 5 | 10 | 错误 |
| 3 | 10 | 10 | 正确 |

第二次 Caller 原始输出已经包含 `number_of_years=10`。其余参数与工具名正确。

### 责任判定

**主要责任：Caller 的当前子目标到参数值的绑定，以及生成后的计划一致性检查。置信度高。**

Planner 已将每一步参数写清楚；按照当前代码，第二次 Caller 会收到明确包含 `number_of_years=5` 的当前子目标。因此不能将此题解释为 Planner 没有规划 5 年，或 Caller 缺少必要信息。

实现上的薄弱点是：计划中的参数仍只是自然语言字符串，Caller 可重新解释和改写，程序没有强制保持一致。日志不能证明模型内部为什么选择 10，例如是否因全局请求中的末尾数值而受到干扰；这类解释只能作为待验证假设。

## 4. bfcl_55：Planner 子目标欠具体，Caller 混淆对象和条件

### 用户要求与计划

用户要求：

1. 将 Battle Reign 的护甲等级改为 5。
2. 查询 Battle Reign 在 snowy weather 条件下的攻略。
3. 查询 Shadow Fall 的 strategy 类型攻略。

Planner 实际输出：

```text
BattleReignGameAPI.update_player_equipment
GameGuideAPI.search_guide
GameGuideAPI.search_guide
```

调用数量和顺序合理，但后两个子目标完全相同，未写出不同游戏及各自约束。

### 实际错误

| 步骤 | Caller 实际参数 | 判断 |
|---|---|---|
| 1 | `attribute=armor, level=5, playerID=123` | 正确；123 是工具默认值 |
| 2 | `game=Battle Reign, condition=snowy weather, type=strategy` | 按 gold，多加了第三个请求的类型约束 |
| 3 | 与第二步完全相同 | 未切换为 Shadow Fall，并错误沿用天气条件 |

按本地 gold，两个查询应分别为：

```json
{"game": "Battle Reign", "condition": "snowy weather"}
{"game": "Shadow Fall", "type": "strategy"}
```

工具仅将 `game` 列为必填项，因此没有必须填满 `condition` 和 `type` 的要求。

### 责任判定

**上游缺陷：Planner 未明确区分重复工具调用的对象和条件。直接失败：Caller 跨请求混用参数并重复生成相同调用。**

不能表述为“Caller 违反了明确写好的 Shadow Fall 计划”，因为计划没有写出该对象。但 Caller 仍能看到完整请求和此前调用历史，不能把错误全部解释为信息不可用。

准确结论是：Planner 的计划表达不足，迫使 Caller 自行恢复每一步的对象与条件；Caller 未能正确完成恢复。第三步完全重复第二步，也说明最终提示中的避免重复规则没有稳定生效。

要确定补全 Planner 是否足以修复本题，需要固定其他条件，仅替换为明确子目标后重放。现有轨迹支持联合归因，不能量化两个模块的独立因果贡献。

## 5. bfcl_149：Caller 丢失地域约束

### 用户要求与计划

用户要求查询 San Diego, CA 在 2023-03-01 的 Music 或 Theater 活动。Planner 生成两次 `Events_3_FindEvents`。

Caller 正确区分了 Music 与 Theater，日期也正确，但两次调用均将：

```json
{"city": "San Diego, CA"}
```

生成为：

```json
{"city": "San Diego"}
```

### 责任判定

**主要责任：Caller 的实体信息保留和工具参数文档遵循。置信度高。**

工具文档要求城市按 `City, State (abbr)` 格式填写，只有州信息不可用时才使用 City。本题用户明确提供 CA，因此这个错误有请求和文档双重依据，并非仅仅任意字符串差异。

Planner 没有重复写出城市约束，但也没有要求删除 CA。Caller 获得的完整请求与工具文档足以生成正确值。没有 Selector 选错工具的证据。

## 6. bfcl_29：Caller 擅自启用可选功能

### 用户要求与计划

用户要求查询 John Doe 在 New York 的定罪状态，以及其犯罪性质。Planner 输出：

```text
criminal_record.get_status
criminal_record.get_offense_nature
```

第一步调用正确。第二步实际输出：

```json
{"criminal_name": "John Doe", "optional_param": true}
```

工具文档说明该选项用于获取额外详情，默认 false；本地 gold 接受省略或 false，不接受 true。

### 责任判定

**主要责任：Caller 的可选参数启用判断。置信度高。**

Planner 没有添加额外详情任务，也未指定 true。Caller 将未明确请求的功能主动启用。这里的布尔值类型合法，问题是语义取值错误，单纯增加 JSON 类型校验无法修复。

## 7. bfcl_56：菜谱名称未通过匹配，不能认定返回对象传递失败

### 用户要求与计划

用户要求自制、健康、无麸质的意大利面菜谱，以及准备烹饪时间和营养信息。Planner 输出：

```text
recipe_search
recipe_prep_time
recipe_nutrition_info
```

搜索调用正确：

```json
{"ingredient": "spaghetti", "dietary_requirements": ["gluten_free"], "isHomemade": true}
```

后两个调用一致使用：

```json
{"recipe": "homemade gluten free spaghetti"}
```

本地 gold 对这两个参数接受的字符串集合为：

```text
spaghetti
homemade healthy spaghetti
Homemade healthy gluten free spaghetti
homemade_spaghetti
```

实际字符串不在其中，因此严格匹配失败。

### 责任判定与对先前报告的更正

**确定的失败位置：Caller 的 recipe 字符串不符合本地允许答案集合。真实任务语义是否失败，现有证据不足。**

先前总体报告将其描述为“菜谱对象在调用之间传递错误”，这个判断过强，应以本节为准。`recipe_search` 没有实际执行，没有返回菜谱名或 ID；后两个调用使用的名称彼此一致，不能证明真实返回对象被传错。

实际名称与用户请求语义接近，gold 又包含多种表述，因此应将本题单独标记为参数名称匹配敏感案例。不能把它与明确将 5 年写成 10 年的错误视为同等确定的任务理解失败，也不应为了通过该测试题将 gold 字符串硬编码进提示。

## 8. 各模块的改进位置

| 模块或环节 | 证据支持的改进方向 | 对应案例 |
|---|---|---|
| Planner | 重复使用同一工具时，子目标明确写出对象及各自约束 | `bfcl_55` |
| Caller：当前步骤绑定 | 优先遵循当前子目标中已明确的参数，生成后核对计划一致性 | `bfcl_109` |
| Caller：跨步骤约束隔离 | 避免把一个请求的条件迁移到另一个请求；检查是否漏掉尚未处理的实体 | `bfcl_55` |
| Caller：原文保留 | 保留用户明确提供的地域等限定信息，并遵循参数文档 | `bfcl_149` |
| Caller：可选参数 | 未请求的可选能力按文档默认处理或省略 | `bfcl_29`、`bfcl_55` |
| 评估分析 | 区分明确语义错误与可能同义的字符串匹配失败 | `bfcl_56` |

这 5 题均没有发现 Selector 选错工具的证据。Synthesizer 位于调用生成之后，本次 BFCL 评分检查已有调用列表，因此不是这些失败的直接来源。

以上是基于日志和当前实现的归因分析，未重新调用模型或实施修复。后续若验证改进，应在训练集和 selection 集开发，并保留独立测试集；不要将已分析的测试题作为专门调参目标。

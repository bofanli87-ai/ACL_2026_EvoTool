# g15 的 Blame、实际修复和回归

使用修复反馈后的原始 3 epochs 运行。训练触发案例与测试得失分开统计。原始 Static 和 Evolution 的 30 个测试 ID 一一配对，23/30 → 25/30，由 4 道新增成功、2 道退化构成，另外 24 道成败相同。

90 代中从归因到留存的统计如下。接受指训练小批次平均 Reward 严格提高，留存指新 Child 当代进入选后 Population。

| Blame 模块 | 归因次数 | 对应 Prompt 实际变化 | 批次接受 | 当代留存 |
|---|---:|---:|---:|---:|
| Planner | 50 | 44 | 15 | 1 |
| Caller | 39 | 39 | 13 | 2 |
| Synthesizer | 1 | 1 | 0 | 0 |
| Selector | 0 | 0 | 0 | 0 |

**触发点。** g15 的训练小批次为 bfcl_10、bfcl_110、bfcl_132。传给 Mutator 的代表轨迹对应 bfcl_110：用户要求分别计算 15、20、30 年房贷，三次 Caller 参数却都是 15 年。Blamer 给 Caller 1 分，其余三个模块 0 分。Mutator 只在 Initial Caller 后追加“Ensure that each tool call is unique and distinct based on its arguments to prevent duplicate calls.” 三题批次平均 Reward 由 0.3833 升至 0.6167。这个均值无法单独确定 bfcl_110 在变异后是否通过。轨迹中的 no_execution 是此 BFCL 接口的执行方式，定位依据是实际参数重复。

**测试影响。** 下表列出全部成败发生变化的题。已逐题确认 Static 与 g15 的 Planner 输出相同，所选工具名称和次序也相同。四个正例依据配对端到端轨迹；两个负例另有冻结原 Plan、工具序列后回滚 Caller 的三次重复干预。

| 测试题 | 成败 | Static → g15 的调用差异 | 证据与解释 |
|---|---|---|---|
| bfcl_8 | 错→对 | 第二次运动学调用从重复的速度 50、距离 600 改为 400、1000 | 正确区分两组参数 |
| bfcl_58 | 错→对 | 第二次酒店搜索从重复 Paris 改为 New York | 正确区分城市 |
| bfcl_104 | 错→对 | 第二次置信区间计算的样本量由重复 50 改为 150 | 正确区分样本量 |
| bfcl_115 | 错→对 | 第二次案件查询从重复案号 28473 改为 64725 | 正确区分案号 |
| bfcl_109 | 对→错 | 年数序列 1、5、10 变为 1、10、10 | 仍产生重复且覆盖明确参数；冻结上游、换回 Initial Caller 后 3/3 通过 |
| bfcl_149 | 对→错 | 两次活动查询均将 San Diego, CA 缩写成 San Diego | 调用本来已按活动类型区分，共享城市字段丢失州名；同样的 Caller 回滚 3/3 通过 |

**判读。** 对重复参数错误归因于 Caller 后，修改给四个同型测试案例带来了与预期一致的行为变化。两个负例分别体现明确参数失真和共享实体失真，回滚定位到 Caller 版本对本题结果的影响。现有记录不能区分模型为何在这两题改变参数，也不足以断言需要多模块 Blame。以上是分析 g15 单次变异的证据，不是所有 Blame 决策的准确率估计。

来源：归档项目 tmp/evotool_latest_audit/results/aligned_comparison_3ep 下的 evolution runlog（gen=15）、static.episodes.jsonl、evolution.episodes.jsonl 和 interventions；另见 outputs/evotool_review/mentor_report_20261101/FINAL_3EP_5CASE_INTERVENTION_RESULTS_ZH.md。

# EvoTool实验汇报
## 一、完整轨迹：g15为什么没有继续进化

### 1. 1 epoch和3 epochs比较
3 epochs多出的60代并不是完全没有变化：期间发现仍然生成并接受了一些新策略，也新增了一个留在Population中的g67。但这些新策略最后都没有超过g15，因此最终部署结果没有变化。

| 指标 | 1 epoch | 3 epochs |
|---|---:|---:|
| 总代数 | 30 | 90 |
| Initial被选作Parent | 27 | 74 |
| g4被选作Parent | 2 | 12 |
| g15被选作Parent | 1 | 3 |
| 通过训练批次门槛的Mutation | 11 | 28 |
| 通过门槛且当代留存的新策略 | 2 | 3 |
| 最终部署策略 | g15 | g15 |
| 原30题测试结果 | 25/30 | 25/30 |

所以，增加Epoch后没有提升，并不是因为后面完全没有搜索，而是后续搜索没有产生能够留存并替代g15的策略。
g15的后续积累在两个地方中断：一是分到的父代机会少；二是生成的后代即使在训练批次上变好，也不一定能进入Population并继续进化，和之前判断的原因一致。

## 二、Selection：换选择方式能否有提升

为了检查问题是不是主要出在Selection上，先在原30代设置下比较了baseline、val_acc、greedy和top-k。

| Selection方式 | 非Initial作为Parent的次数 | 原30题成功数 |
|---|---:|---:|
| baseline | 2 | 21/30 |
| val_acc | 18 | 21/30 |
| greedy | 25 | 22/30 |
| top-k | 26 | 20/30 |

换Selection以后，非Initial策略被选作Parent的次数从2次提高到18—26次，说明调整Selection确实能让进化策略得到更多利用。但原30题成绩没有随之稳定提高：greedy只多1题，top-k反而少1题。
随后又在56道新题上，用3个搜索seed比较了diversity和greedy。每个seed下两种方法使用的训练批次和训练覆盖都一致。

| 搜索seed | diversity | greedy | greedy独有成功 | diversity独有成功 |
|---|---:|---:|---:|---:|
| 42 | 45/56 | 42/56 | 2 | 5 |
| 43 | 45/56 | 45/56 | 2 | 2 |
| 44 | 34/56 | 35/56 | 4 | 3 |
| 平均 | 41.33/56 | 40.67/56 | — | — |

三个seed里，greedy相对diversity分别少3题、相同和多1题。平均只差0.67题，而且不同seed之间最多相差11题，明显大于两种Selection之间的平均差距。

目前可以得到的判断是：

- 换Selection可以明显增加进化策略作为Parent的机会。
- 但“更多利用进化策略”暂时没有转化成稳定的新题提升。
- 当前系统瓶颈主要原因不是搜索次数或Parent利用不足，而是Mutation生成的修改作用范围太大、适用条件不清楚，导致新规则容易修复一部分任务，同时干扰其他任务。系统能够产生互补改进，但缺少稳定保留和组合这些改进的机制。

## 三、矩阵反映出的Mutation和积累问题

为了看清楚不同策略到底改变了哪些题，这次先补了一个小规模的Policy × Task矩阵：选择6个有代表性的策略，在同一批30道Selection题上逐题比较。6个策略包括最终Population中的Initial、g4、g15、g67，也包括生成后被淘汰的g44和g89，共180个结果。

### 1. 六个策略看起来不同，实际行为大部分相同

30道题中，有27道题的成败在六个策略之间完全一样。真正能把这些策略区分开的只有bfcl_38、bfcl_127和bfcl_16三道题。

| 策略 | bfcl_38 | bfcl_127 | bfcl_16 | 总成功数/30 |
|---|---:|---:|---:|---:|
| Initial | 0 | 0 | 0 | 22 |
| g4 | 1 | 1 | 0 | 24 |
| g15 | 0 | 0 | 0 | 22 |
| g67 | 0 | 1 | 0 | 23 |
| g44（被淘汰） | 0 | 1 | 1 | 24 |
| g89（被淘汰） | 0 | 0 | 0 | 22 |

可以看到**多数Mutation虽然改了Prompt，但没有明显改变大部分任务上的行为。** g15和g89在这30道题上与Initial的成败完全相同；g67只多解决1题，而且这道bfcl_127已经能被g4解决。真正带来不同能力的主要是g4和g44。

这比较像当前Mutation已经进入一个局部阶段：偶尔能针对某个具体问题补上一条有效规则，但很难形成覆盖更多任务的普遍提升。继续生成更多Prompt，不一定会带来更多不同的能力，很多新策略可能只是文字上不同，实际做题表现基本一样。

### 2. 五次代表性Mutation中，真正有新增效果的并不多

把Parent和Child直接放在一起比较，结果如下：

| Parent→Child | 新增成功 | 退化 | 净提升 | 新增成功题 | 当时是否留存 |
|---|---:|---:|---:|---|---|
| Initial→g4 | 2 | 0 | +2 | bfcl_38、bfcl_127 | 是 |
| Initial→g15 | 0 | 0 | 0 | 无 | 是 |
| Initial→g67 | 1 | 0 | +1 | bfcl_127 | 是 |
| g15→g44 | 2 | 0 | +2 | bfcl_16、bfcl_127 | 否 |
| g15→g89 | 0 | 0 | 0 | 无 | 否 |

五次代表性Mutation里，g4和g44带来了比较明确的新效果；g15和g89在这批题上没有变化；g67虽然多做对1题，但这项能力Population里已经有了。所以可以说真正新增且不重复的能力并不多。
所以当前Mutation不是完全失效，而是有效产出率偏低。 它仍然能生成g4、g44这样的有效修改，但更多时候，新Prompt没有改变结果，或者只重复Population中已有的能力。从这个角度看，单纯增加Epoch，可能只会生成更多相似策略，很难持续推高最终成绩。
### 3. Population保留了多个策略，但没有真正积累更多能力

| 比较范围 | 最佳单策略成功数 | 所有策略成功题并集 | 多策略额外覆盖 |
|---|---:|---:|---:|
| 最终Population：Initial、g4、g15、g67 | 24 | 24 | 0 |
| 六个代表性候选，加入g44、g89 | 24 | 25 | 1 |

最终Population里虽然保留了Initial、g4、g15和g67四个策略，但它们的成功题并集仍然只有24题，和最佳单策略g4完全一样。也就是说，**Population在Prompt层面看起来有多样性，但在这30道题的实际能力上没有带来额外覆盖。** g15没有补上g4不会的题，g67解决的bfcl_127也已经包含在g4的成功任务中。

反而是被淘汰的g44额外解决了bfcl_16。这道题是最终Population里所有策略都没有解决的，因此g44与g4存在真实的互补性。如果把所有六个候选都考虑进去，成功题并集可以从24题增加到25题。但g44没有进入后续Population，这项新能力也就没有机会继续传下去。

这里暴露出两个问题：

1. Mutation偶尔能够产生新的、互补的能力，例如g44解决bfcl_16。
2. 当前Population Selection不一定能把这种小范围但有价值的能力留下来，最终保留的多个策略反而比较重复。

**当前瓶颈既有Mutation的问题，也有积累机制的问题。Mutation大部分时候只能产生很窄或重复的改进，已经有接近局部上限的迹象；同时，少数真正互补的Mutation又可能在Population Selection中被淘汰。** 这也解释了为什么换Selection后增加进化策略的使用次数，最终成绩仍然没有稳定提升——如果候选策略本身大多相似，而少数有独特价值的策略又没有被识别和保留，仅仅增加抽样次数并不能解决问题。
完整矩阵保存在[成功矩阵](https://github.com/bofanli87-ai/ACL_2026_EvoTool/blob/main/reports/evotool_review/policy_matrix/pilot_success.csv)，逐题结果和Parent→Child统计保存在[矩阵核验结果](https://github.com/bofanli87-ai/ACL_2026_EvoTool/blob/main/reports/evotool_review/policy_matrix/pilot_verified.json)。

## 四、两条有效Mutation能不能直接组合

已有记录中选了两条分别有效、解决任务也有互补性的Planner修改：A为g4的修改，B为g44的修改。A主要要求把参数和不同条件写清楚、拆开处理；B则是针对case number和court查询状态、庭审日期的专门规则。先对比Initial、A、B和A+B，结果如下：

| 策略 | 成功数 | 相对Initial新增成功 | 相对Initial退化 | 净提升 |
|---|---:|---:|---:|---:|
| Initial | 33 | 0 | 0 | 0 |
| A | 44 | 12 | 1 | 11 |
| B | 43 | 13 | 3 | 10 |
| A+B | 43 | 13 | 3 | 10 |

A和B单独使用时，成功任务的并集一共有49题，说明两条规则确实有互补性。但直接组合后的A+B只成功43题，丢掉了并集中6道本来能由A或B解决的题，而且没有解决并集之外的新题。

如果两条有效规则可以简单叠加，A+B应该更接近49题；实际结果没有做到。这已经说明一个问题：**Prompt里的规则不是简单做加法。分别有效的两条规则放在一起，模型的整体行为可能会重新变化，而不是自动同时获得两边的能力。**

### 1. 六道丢失题的重复实验

为了判断这6道题是不是刚好遇到一次推理波动，又对A、B和A+B各重新运行3轮，共做了54次新推理。

| 任务 | A成功/3 | B成功/3 | A+B成功/3 |
|---|---:|---:|---:|
| live_parallel_multiple_20-17-0 | 3 | 3 | 0 |
| live_parallel_multiple_23-20-0 | 3 | 0 | 0 |
| parallel_114 | 3 | 0 | 0 |
| parallel_63 | 3 | 0 | 0 |
| parallel_multiple_101 | 3 | 2 | 0 |
| parallel_multiple_156 | 3 | 2 | 0 |

结果很明显：A在18次评估中全部成功，A+B在18次评估中全部失败。A+B在每道题上的三次计划和调用也完全一致，不是这次这样错、下次换一种方式又做对。B在其中两道题上有波动，但这种波动无法解释A+B为什么连续18次都失败。

因此，在这6道题上，原来看到的组合收益丢失基本可以认为是稳定现象，而不是一次偶然失败。可以确认：**简单把B加到A后面，确实稳定破坏了A原本在这些题上的正确行为。**

### 2. 组合后到底错在什么地方

逐题看计划和调用后，A+B的错误并不是同一种：

- 有的题在Planner阶段就改错了。例如把需要的工具换成另一个工具，把输入数字32写成31，或者把`volume_traded`改成`avg_closing_price`。
- 有的题计划里已经列出了正确组合，但到了Caller阶段又重复绑定了参数，最后少掉或重复调用。
- 有的题任务意思基本没错，但参数格式变了，例如数字变成字符串，或者城市字符串少了空格，最后没有通过当前评分。

这说明问题不只是某一条规则写错，也不只发生在Planner。把两条规则放进同一个Prompt以后，模型对任务的表达方式、参数格式和下游绑定都可能跟着变化。即使B原本只针对案件查询，它被写进全局Prompt后，也会影响完全无关的并行调用、数字参数和工具选择任务。

两条规则的文字本身没有明显的正面冲突，因此这里更像是**Prompt组合后的行为干扰**：规则越加越多以后，模型的注意重点和表达方式发生变化，原来稳定的行为被带偏了。

### 3. 对Mutation上限的判断

这个结果进一步支持第三部分的猜想：当前Mutation还能找到A、B这样的局部有效规则，但“把新规则直接加进整个模块Prompt”已经接近局部上限。问题不是完全找不到新规则，而是每增加一条规则，都可能改变其他任务上的行为；规则越积越多，不一定能力越强，反而可能开始互相干扰。
因此，目前更倾向于认为：
1. **Mutation生成能力还没有完全用完。** A和B单独都能解决不少新题，说明系统仍能找到有效修改。
2. **简单拼接Prompt的积累方式可能已经到上限。** A+B稳定丢失A的收益，说明有效规则不能靠无条件叠加来积累。
3. **规则的作用范围缺少控制。** B是案件查询的专门规则，却影响了6道非案件任务，说明局部Mutation实际是以全局方式生效的。
4. **Selection很难单独解决这个问题。** 即使选中了一个局部有效策略，继续往它的Prompt里加规则，也可能破坏已有能力。

六道题的重复结果和逐题调用分析保存在[重复验证结论](https://github.com/bofanli87-ai/ACL_2026_EvoTool/blob/main/reports/evotool_review/generalization/repeat_six/FINDINGS_ZH.md)和[逐题调用报告](https://github.com/bofanli87-ai/ACL_2026_EvoTool/blob/main/reports/evotool_review/generalization/repeat_six/TRACE_REPORT_ZH.md)中。

## 五、Blame、实际修复和回归之间的关系

### 1. Blame通常能推动修改，但不代表修改最后有价值

90代中的整体情况：

| Blame指向 | 被归因次数 | Prompt实际发生修改 | 训练批次变好 | 最后留在Population |
|---|---:|---:|---:|---:|
| Planner | 50 | 44 | 15 | 1 |
| Caller | 39 | 39 | 13 | 2 |
| Synthesizer | 1 | 1 | 0 | 0 |
| Selector | 0 | 0 | 0 | 0 |

这组数字说明，Blame之后大部分时候确实会产生对应模块的Prompt修改，Planner和Caller也各有一部分修改能让当前训练批次变好。但真正进入Population的只有3个。

所以，问题不只是“Blame有没有找到一个模块”。即使模块找到了、Prompt也改了、当前训练批次也提高了，修改仍然可能只对眼前几道题有效，换到Selection题上就没有优势。**Blame更像是在告诉系统去哪里改，但它不能保证怎么改是对的，也不能保证修改不会影响其他任务。**

### 2. g15是一个很典型的“找对位置，但修改有副作用”的案例

g15由一个重复参数案例触发。原任务要求分别计算15年、20年和30年的房贷，但Caller连续三次都传了15年。Blame把问题定位到Caller，Mutator随后在Caller Prompt中加入“不同工具调用要根据参数保持唯一，避免重复调用”的规则。训练批次Reward从0.3833提高到0.6167。

这次Blame从直觉上是合理的：错误就发生在Caller参数重复，实际修改的也是Caller。修改后的测试变化也和这个判断基本对应。

| 结果 | 测试题 | 修改后的表现 |
|---|---|---|
| 修复 | bfcl_8 | 两次运动学调用不再重复，正确区分两组速度和距离 |
| 修复 | bfcl_58 | 两次酒店搜索不再都查Paris，第二次正确改为New York |
| 修复 | bfcl_104 | 两次计算不再重复样本量50，第二次正确使用150 |
| 修复 | bfcl_115 | 两次案件查询不再重复同一案号，正确区分两个案号 |
| 回归 | bfcl_109 | 原本正确的1、5、10年变成1、10、10，再次出现参数重复 |
| 回归 | bfcl_149 | 两次调用都把San Diego, CA缩成San Diego，丢掉了共享的州信息 |

前四道修复题都属于“多个调用需要使用不同参数”，正好是这条Mutation想解决的问题。这说明Blame和Mutation确实抓到了一个真实错误模式，不是碰巧涨分。

但后两道题说明，加入去重规则以后，Caller并没有学会一条稳定、通用的参数处理原则。它有时能把重复参数拆开，有时又会改坏明确给出的参数，或者在多个调用中丢失本来应该保留的共享信息。bfcl_109和bfcl_149在固定Planner和工具顺序、只换回Initial Caller后，三次都恢复成功，说明这两道回归主要跟Caller修改有关，而不是Planner一起出了问题。

因此，g15更像是：**Blame找对了模块，Mutation也修对了一类问题，但规则写得太全局，修复一个局部错误模式时改变了Caller在其他任务上的参数处理方式。**
## 数据和记录位置

- [6策略×30题成功矩阵](https://github.com/bofanli87-ai/ACL_2026_EvoTool/blob/main/reports/evotool_review/policy_matrix/pilot_success.csv)
- [矩阵逐题核验、亲子差异与Population并集](https://github.com/bofanli87-ai/ACL_2026_EvoTool/blob/main/reports/evotool_review/policy_matrix/pilot_verified.json)
- [56道新题逐题结果和组合修复、退化列表](https://github.com/bofanli87-ai/ACL_2026_EvoTool/blob/main/reports/evotool_review/generalization/final_verified.json)
- [56道新题与组合实验汇总](https://github.com/bofanli87-ai/ACL_2026_EvoTool/blob/main/reports/evotool_review/generalization/FINAL_REPORT_ZH.md)
- [6道组合丢失题重复验证结论](https://github.com/bofanli87-ai/ACL_2026_EvoTool/blob/main/reports/evotool_review/generalization/repeat_six/FINDINGS_ZH.md)
- [6道组合丢失题逐题调用报告](https://github.com/bofanli87-ai/ACL_2026_EvoTool/blob/main/reports/evotool_review/generalization/repeat_six/TRACE_REPORT_ZH.md)
- [g15的Blame触发、4道修复、2道回归及Caller回滚](https://github.com/bofanli87-ai/ACL_2026_EvoTool/blob/main/reports/evotool_review/g15_trace_20261103/BLAME_SIX_CASES_ZH.md)
- [g15完整轨迹、抽样概率和三个后代去向](https://github.com/bofanli87-ai/ACL_2026_EvoTool/blob/main/reports/evotool_review/g15_trace_20261103/REPORT_ZH.md)
- [四种Selection方式对照](https://github.com/bofanli87-ai/ACL_2026_EvoTool/blob/main/reports/evotool_review/selection_30gen/comparison.json)
- [四种Selection方式测试结果](https://github.com/bofanli87-ai/ACL_2026_EvoTool/blob/main/reports/evotool_review/selection_30gen/test_comparison.json)

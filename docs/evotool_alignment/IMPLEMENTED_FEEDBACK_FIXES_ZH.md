# Evolution 反馈链路修复（2026-10-30）

实现范围为对齐指南 T1/T2 及部分日志/预算支持，不是完整附录复现。

- Blamer 分数必须为有限的 0–1 数值（不接受布尔值）；程序执行 argmax。
  同分按 MODULES 顺序选择；primary 冲突写日志。非法分数采用规则回退并标记。
- Blamer rationale 经 loop 传入 Mutator；关闭 use_feedback 时不传 rationale。
- Mutator 校验 target_module 和字符串 revised_spec；错误目标、非法或未变化的规格作为 no-op。
- mutation_trace 保存组装的请求、解析响应、校验结果。此处是客户端截断前请求；
  截断后的实际 messages、finish_reason 等完整 API 日志仍待实现。
- 诊断采用调用实例一对一匹配，保留重复工具调用；BFCL 使用 gold_match 允许值语义。
  缺失/多余调用是症状，不能单凭此确定唯一责任模块。评分器未变更。
- 运行器支持 --generations；子进程禁用输出缓冲；逐代输出包含完成数/总数。

没有添加拒绝领域词的策略约束，没有改变 batch 接受、diversity 选择或 reward。
修复应用到所有运行，不提供旧行为开关。历史结果应保留，跨版本须披露差异。

先使用与旧 1 epoch 相同预算比较修复效果：

```powershell
.\.venv\Scripts\python.exe -u scripts\run_bfcl_aligned_comparison.py --epochs 1 --outdir results/feedback_fixed_1ep
```

另设 8-generation 预算实验，不能与旧 90 代结果混为单因素比较：

```powershell
.\.venv\Scripts\python.exe -u scripts\run_bfcl_aligned_comparison.py --generations 8 --outdir results/feedback_fixed_g8
```

测试命令：`.\.venv\Scripts\python.exe -m pytest -q`。

剩余：结构化 Plan/action、STATE 变量和依赖、真实响应写回、fallback、全模块实际请求日志、
缓存隔离、新鲜测试集与官方评分器对照。旧 30 道测试题已用于分析，后续同题结果属于诊断性比较。
离线测试证明信息链路与匹配行为，不承诺真实模型成功率提升。

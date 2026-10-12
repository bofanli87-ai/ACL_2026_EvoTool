# BFCL 静态诊断实验记录

记录日期：2026-10-12（Asia/Shanghai）

## 1. 研究问题

导师建议先判断 EvoTool 的提升主要来自 reasoning，还是来自输出格式、参数类型和接口约束修复；
并比较 Baseline、Schema、EvoTool、EvoTool+Schema 和简单 Repair 的收益是重复还是互补。
更进一步的假设是：reasoning 错误应修改 prompt，格式错误应使用 schema，确定性接口错误应修改 code/validator。

## 2. 本轮实现

- `run.py`：为 held-out 测试保存逐题 `.episodes.jsonl`，包含 plan、预测调用、gold、success、
  Caller 原始输出、解析状态以及 Repair 前后参数。
- `src/bfcl_error_analysis.py`：将失败多标签分类为 `serialization`、`planning`、`selection`、
  `schema_interface` 和 `semantic_argument`。gold 只用于离线报告，不进入模型、进化或 Repair。
- `src/schema_repair.py`：无额外 LLM、无 gold 的保守 Repair；不猜缺失值，只做可审计的无歧义
  类型转换和递归容器修复，仅在 `additionalProperties: false` 时删除未声明字段。
- `scripts/apply_bfcl_repair_offline.py`：在同一次 Baseline 输出上应用 Repair，排除模型重跑波动。
- `scripts/analyze_bfcl_conditions.py`：生成错误分布、逐题转移和核心 2×2 交互效应。
- 新增六个 `configs/bfcl_diag_*.yaml` 配置及 Repair/诊断测试；当前 `15 passed`。

BFCL 工具定义使用 JSON-Schema-like 方言，已规范化：

| BFCL 类型 | Repair 中的类型 |
|---|---|
| `float` | `number` |
| `dict` | `object` |
| `tuple` | `array` |
| `any` | 不施加类型约束 |

## 3. 实验设置

- 模型：`evotool-qwen3:8b`（Ollama），temperature 0.0；
- seed 42，train/selection/test = 90/30/30，held-out leak = 0；
- 静态 policy 为 `init`；
- 所有条件使用 `data_schema/bfcl/samples.json` 中相同的 150 条样本；Baseline 仅隐藏 schema。

## 4. 四次在线运行

| 条件 | 成功数 | 成功率 | mean reward | tokens | 时间 |
|---|---:|---:|---:|---:|---:|
| Baseline | 2/30 | 6.67% | 16.77 | 78,656 | 188.5 s |
| Schema-in-prompt | 13/30 | 43.33% | 42.43 | 91,203 | 191.9 s |
| Repair v1 在线重跑 | 8/30 | 26.67% | 30.81 | 78,642 | 190.5 s |
| Schema + Repair v1 | 13/30 | 43.33% | 42.48 | 91,101 | 191.3 s |

Repair v1 的 8/30 不是最终 Repair 结论。初版漏掉了 BFCL schema 中大量使用的 `float`；同时，
temperature=0 的独立 Ollama 运行仍可能轻微波动，因此单独重跑不能严格隔离 Repair 因果效应。

## 5. 严格配对的离线 Repair

使用修正后的 Repair 直接处理同一次 Baseline 预测：

```powershell
.\.venv\Scripts\python.exe scripts/apply_bfcl_repair_offline.py `
  --episodes results/diag_baseline.episodes.jsonl `
  --out results/diag_baseline_offline_repair.episodes.jsonl
```

结果：Repair 前 2/30，Repair 后 13/30；17 个样本发生修改，共 74 个 edit；11 个失败被修复，
6 个被修改样本仍失败。把 Repair 应用于 Schema 输出时没有产生任何 edit，成功数仍为 13/30。

Schema 与离线 Repair 的 13 个成功样本完全相同，逐题 outcome difference 为 0：

```text
bfcl_90, bfcl_98, bfcl_2, bfcl_72, bfcl_57, bfcl_60, bfcl_24,
bfcl_8, bfcl_9, bfcl_109, bfcl_27, bfcl_36, bfcl_7
```

## 6. 配对结果与错误分布

| 条件 | 两者都成功 | 仅 Baseline | 仅处理组 | 两者都失败 |
|---|---:|---:|---:|---:|
| Baseline vs Schema | 2 | 0 | 11 | 17 |
| Baseline vs 离线 Repair | 2 | 0 | 11 | 17 |
| Baseline vs Schema+离线 Repair | 2 | 0 | 11 | 17 |

| 条件（失败样本，多标签） | planning | selection | schema/interface | semantic argument |
|---|---:|---:|---:|---:|
| Baseline（28 失败） | 14 | 14 | 21 | 3 |
| Schema（17 失败） | 14 | 14 | 0 | 3 |
| 离线 Repair（17 失败） | 14 | 14 | 5 | 3 |

Schema 清除了本次测试集失败中的全部 schema/interface 标签。Repair 虽取得相同成功集合，但仍有
5 个最终失败保留 interface 子错误，因为保守 Repair 不猜缺失值，也不在 schema 未明确禁止时删字段。
Schema 剩余的 17 个失败按 primary error 分为 14 个 planning/tool-selection 和 3 个参数语义错误。

## 7. 阶段性结论

1. Schema 和严格配对 Repair 都提升 11/30（+36.67 个百分点），且无 observed regression。
2. 两者修复完全相同的样本；Schema+Repair 没有额外收益，说明静态条件下二者高度重复。
3. 这支持“此前部分 EvoTool 提升来自接口格式修复而非 reasoning 改善”的假设。
4. 尚需 EvoTool 与 EvoTool+Schema 验证 EvoTool 是否还能修复剩余 planning/semantic 错误。
5. 当前仍是单模型、单 seed、30 条 held-out 样本，不能声称普遍性。

## 8. 明日实验

```powershell
.\.venv\Scripts\python.exe run.py `
  --config configs/bfcl_diag_evotool.yaml `
  --benchmark bfcl `
  --out results/diag_evotool.json
```

```powershell
.\.venv\Scripts\python.exe run.py `
  --config configs/bfcl_diag_evotool_schema.yaml `
  --benchmark bfcl `
  --out results/diag_evotool_schema.json
```

之后运行：

```powershell
.\.venv\Scripts\python.exe scripts/analyze_bfcl_conditions.py `
  --runs `
    baseline=results/diag_baseline.episodes.jsonl `
    schema=results/diag_schema.episodes.jsonl `
    repair_offline=results/diag_baseline_offline_repair.episodes.jsonl `
    evotool=results/diag_evotool.episodes.jsonl `
    evotool_schema=results/diag_evotool_schema.episodes.jsonl `
  --json-out results/diag_full_comparison.json
```

重点分析 2×2 interaction、逐题重叠/回归、mutation 模块与接受率、prompt 样本绑定以及成本。

## 9. 关键产物校验值

| 文件 | SHA-256 |
|---|---|
| `results/diag_baseline.json` | `E125997274A5ACFD986774D30D94538CBA765732E1D794DD689E3D84448C9655` |
| `results/diag_schema.json` | `3B3D0FB9BEE821AC53F7652C9C0556F6DC5C1C89A40EB536FE7E96E665D7768F` |
| `results/diag_repair.json`（v1，仅审计） | `4D13085A52E06D488C9AC05CBFF7FDA8B9F60883458262129C6CB7B6623A9479` |
| `results/diag_schema_repair.json` | `FDD755885AF084BB6FB05942FE09A13DAB5337294693ECCEAC66B065A11864E0` |
| `results/diag_baseline.episodes.jsonl` | `C82028CEB7D0E1149E0CB40894DDD19D56EAED5FC041670960213F311950B3B8` |
| `results/diag_schema.episodes.jsonl` | `8BE2973FA25C58B8C4F6DC45113393DEE7D64C3E5771EE65739FE84A7610D49D` |
| `results/diag_baseline_offline_repair.episodes.jsonl` | `8609F029E3FE2699010ED21AF1271ACAF36D38139D9EBA29B242A7D5C028A2E6` |
| `results/diag_schema_offline_repair.episodes.jsonl` | `F665ACE751844BF75C8399F01C19B6CA7111BF29BA0C9D7B27777B52E45C7745` |
| `results/diag_static_comparison.json` | `B7F71430B0F7C0136FA4EAFD086642062752F45EA1329636DA950CF808C8F778` |

"""Offline diagnostics only. Does not call an LLM or modify original predictions.
Case-specific interventions were chosen after inspecting held-out gold, and are
NOT deployable policies or generalization measurements.
"""
import copy, csv, json, sys, hashlib
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
SRC=ROOT/'source' if (ROOT/'source').is_dir() else ROOT
OUT=ROOT/'bad_cases'
OUT.mkdir(exist_ok=True)
sys.path.insert(0,str(SRC))
from src.eval_bfcl_ast import bfcl_ast_success
from src.bfcl_error_analysis import diagnose_bfcl

def load_rows(name):
    rows=[json.loads(x) for x in (SRC/f'results/diag_{name}.episodes.jsonl').read_text(encoding='utf-8').splitlines() if x.strip()]
    assert len(rows)==30 and len({x['sample_id'] for x in rows})==30
    return {x['sample_id']:x for x in rows}
runs={n:load_rows(n) for n in ['baseline','schema','evotool','evotool_schema']}
data={x['id']:x for x in json.loads((SRC/'data_schema/bfcl/samples.json').read_text(encoding='utf-8'))}
rows=runs['evotool_schema']
for rs in runs.values():
    assert set(rs)==set(rows)
    for sid,r in rs.items():assert bfcl_ast_success(data[sid],r['predicted_calls'])==r['success']

def dedup(calls):
    seen=set();out=[]
    for c in copy.deepcopy(calls):
        key=json.dumps([c['tool'],c['args']],sort_keys=True)
        if key not in seen:out.append(c);seen.add(key)
    return out

def merge_details(calls):
    # Only manually reviewed read-query tools; never apply to arbitrary list args.
    out=[];groups={}
    for c in dedup(calls):
        if c['tool'] not in ['museum_info.get_info','sport_analysis.last_game_performance']:
            out.append(c);continue
        fixed={k:v for k,v in c['args'].items() if k!='details'}
        key=json.dumps([c['tool'],fixed],sort_keys=True)
        if key not in groups:groups[key]=c;out.append(c)
        else:
            for v in c['args'].get('details',[]):
                if v not in groups[key]['args']['details']:groups[key]['args']['details'].append(v)
    return out

def scenario(sid,mode):
    c=copy.deepcopy(rows[sid]['predicted_calls'])
    if mode=='exact_dedup':return dedup(c)
    if mode=='merge_details':return merge_details(c)
    if mode=='drop_subsumed_case_queries':
        c=dedup(c)
        return [a for a in c if not any(a is not b and a['tool']==b['tool'] and len(a['args'])<len(b['args']) and all(b['args'].get(k)==v for k,v in a['args'].items()) for b in c)]
    if mode in ['omit_unrequested_type','omit_optional','dedup_and_omit_optional']:
        if mode=='dedup_and_omit_optional':c=dedup(c)
        for a in c:
            if mode=='omit_unrequested_type' and a['tool']=='GameGuideAPI.search_guide' and a['args'].get('game')=='Battle Reign':a['args'].pop('type',None)
            if mode!='omit_unrequested_type' and a['tool']=='criminal_record.get_offense_nature':a['args'].pop('optional_param',None)
        return c
    if mode in ['replace_one_music','dedup_add_theater']:
        if mode=='replace_one_music':c[1]['args']['event_type']='Theater'
        else:
            c=dedup(c);t=copy.deepcopy(c[0]);t['args']['event_type']='Theater';c.append(t)
        return c
    if mode=='swap_gcd_equivalent':
        c[0]['args']['a'],c[0]['args']['b']=c[0]['args']['b'],c[0]['args']['a'];return c
    if mode=='recipe_name_reference_probe':
        for a in c:
            if a['tool'] in ['recipe_prep_time','recipe_nutrition_info']:a['args']['recipe']='spaghetti'
        return c
    raise ValueError(mode)

annotations={
'bfcl_145':('评测等价疑点','GCD 的 a=36,b=48 与参考值顺序相反；数学结果相同。','不适合作为 reasoning 失败的主案例；保留原严格评分。'),
'bfcl_44':('多余调用与参数问题并存','5 次调用而参考为 2 次；额外查 sculpture_id=0，纽约参数含 museum。','去重不足；逐项核对工具选择和实体规范化，不证明必须多模块修改。'),
'bfcl_55':('可选参数过度指定','Battle Reign 的查询额外指定 type=strategy；用户只对 Shadow Fall 明确要求 strategy。','Schema 合法不保证参数符合当前子任务；验证 Caller 对可选参数的处理。'),
'bfcl_104':('完全重复','sample_size=50 的正确置信区间调用重复；3 次而参考为 2 次。','检查计划粒度和重复调用约束；已有正确调用。'),
'bfcl_115':('查询覆盖冗余','两个案件的历史和当事人信息被拆为 6 次查询；完整查询已经存在。','要识别参数覆盖关系，而不仅是完全重复。'),
'bfcl_51':('查询冗余与名称匹配并存','6 次调用，参考 2 次；team=L.A. Lakers 不在参考名称集合。','合并字段后仍可能因标点命名失败，需人工判断评分合理性。'),
'bfcl_149':('重复并遗漏需求','3 次 Music 查询，缺少 Theater。','既需去重又需需求覆盖；验证携带调用参数的历史是否有帮助。'),
'bfcl_130':('可合并字段被拆开','每城市分别查询三项 details，总计 6 次；工具支持一次查询数组。','Planner 不见工具能力是候选解释；需控制提示和输入信息分别验证。'),
'bfcl_56':('名称等价或实体绑定疑点','recipe 名称不在允许字符串中；BFCL 没有实际 recipe_search 返回。','无法确认真实搜索结果引用关系；不要宣称执行依赖已验证。'),
'bfcl_23':('重复与名称差异并存','4 次调用，含 company XYZ 与 XYZ 两种 company_name。','纯去重不够；需审核名称等价和子目标冗余。'),
'bfcl_140':('重复与工具选择差异','搜索重复；选 generate_human_image，参考为 generate_image，参数契约不同。','两个工具说明存在语义重叠；先核对工具选择歧义，再做联合修复。'),
'bfcl_58':('完全重复','两个城市的酒店查询各重复一次；4 次而参考为 2 次。','优先案例：验证输入历史与确定性去重。'),
'bfcl_71':('完全重复','太阳能和风能查询各重复一次；4 次而参考为 2 次。','采集信息和计算被拆分后调用相同工具；正确调用已齐全。'),
'bfcl_29':('重复与可选参数并存','状态查询重复；optional_param=true 不被参考接受。','分别移除重复和可选参数均不足，联合修改可检验多错误共存。')}
assert set(annotations)=={s for s,r in rows.items() if not r['success']}
checks=[]
def evaluate(sid,mode,scope):
    calls=scenario(sid,mode)
    rec={'sample_id':sid,'intervention':mode,'scope':scope,'success':bfcl_ast_success(data[sid],calls),'before_calls':len(rows[sid]['predicted_calls']),'after_calls':len(calls),'calls':calls,'diagnosis':diagnose_bfcl(data[sid],calls,rows[sid]['caller_traces'])}
    checks.append(rec)
    return rec
for sid in rows:evaluate(sid,'exact_dedup','same_rule_all_30_posthoc_diagnostic')
for sid,modes in {'bfcl_130':['merge_details'],'bfcl_51':['merge_details'],'bfcl_115':['drop_subsumed_case_queries'],'bfcl_55':['omit_unrequested_type'],'bfcl_149':['replace_one_music','dedup_add_theater'],'bfcl_29':['omit_optional','dedup_and_omit_optional'],'bfcl_145':['swap_gcd_equivalent'],'bfcl_56':['recipe_name_reference_probe']}.items():
    for mode in modes:evaluate(sid,mode,'case_specific_gold_inspected_not_generalization')
assert {r['sample_id'] for r in checks if r['intervention']=='exact_dedup' and r['success'] and not rows[r['sample_id']]['success']}=={'bfcl_104','bfcl_58','bfcl_71'}
assert not [r for r in checks if r['intervention']=='exact_dedup' and not r['success'] and rows[r['sample_id']]['success']]

logs=[json.loads(x) for x in (SRC/'results/logs/bfcl__bfcl_diag_evotool_schema.runlog.jsonl').read_text(encoding='utf-8').splitlines() if x.strip()]
gens=[x for x in logs if x.get('type')=='generation']
logstats={'generations':len(gens),'parents':dict(Counter(x['parent_id'] for x in gens)),'accepted':sum(x['accepted'] for x in gens),'accepted_immediately_removed':[x['child_id'] for x in gens if x['accepted'] and x['child_id'] not in [p['id'] for p in x['population_snapshot']]],'test_ids_in_batches':sorted(set(rows)&{i for x in gens for i in x['batch_ids']}),'deployed_mutation':next(x for x in gens if x['child_id']=='g12-planner')}
assert not logstats['test_ids_in_batches']
inventory=[]; packets=[]
for sid,(cat,obs,hyp) in annotations.items():
    r=rows[sid]; tests=[x for x in checks if x['sample_id']==sid]
    inventory.append({'sample_id':sid,'category':cat,'observation':obs,'next_check':hyp,'calls':len(r['predicted_calls']),'gold_calls':len(r['gold_calls']),'baseline_success':runs['baseline'][sid]['success'],'schema_success':runs['schema'][sid]['success'],'evotool_success':runs['evotool'][sid]['success'],'schema_evo_success':False,'offline_results':'; '.join(x['intervention']+':'+str(x['success']) for x in tests)})
    packets.append({'sample_id':sid,'analysis':inventory[-1],'data':data[sid],'conditions':{n:rs[sid] for n,rs in runs.items()},'checks':tests})
(OUT/'diagnostic_results.json').write_text(json.dumps({'scope':'Post-hoc offline diagnostics; no new LLM experiments','commit':'ede2328b8e54eafa6c91e8e0c8e9d42adb238c46','checks':checks,'evolution_log_audit':logstats},ensure_ascii=False,indent=2),encoding='utf-8')
(OUT/'case_evidence.json').write_text(json.dumps(packets,ensure_ascii=False,indent=2),encoding='utf-8')
with (OUT/'case_inventory.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(inventory[0]));w.writeheader();w.writerows(inventory)
doc=['# 14 道失败题逐题证据','日期：2026-10-18。固定版本 ede2328b8e54eafa6c91e8e0c8e9d42adb238c46。','所有修改均为看过测试结果后的离线诊断，不代表新模型成绩或自动修复能力。保存的 plan 与调用列表并非一一对应：Selector 可跳过子目标，原测试文件未保存逐步 subgoal 映射。']
for pkt in packets:
    sid=pkt['sample_id'];r=rows[sid];a=pkt['analysis']
    doc += [f'## {sid} {a["category"]}',f'任务：{r["query"]}',f'观察：{a["observation"]}',f'待验证：{a["next_check"]}','### 原始计划',*['- '+s for s in r['plan']],'### 原始调用','```json',json.dumps(r['predicted_calls'],ensure_ascii=False,indent=2),'```','### 标准调用','```json',json.dumps(r['gold_calls'],ensure_ascii=False,indent=2),'```','### 离线修改结果']
    for c in pkt['checks']:
        doc += [f'- {c["intervention"]}：{c["before_calls"]} → {c["after_calls"]} 次，严格匹配 {"通过" if c["success"] else "失败"}。']
    doc+=['完整工具定义、Caller 原始输出、四组轨迹及修改后调用见 case_evidence.json。']
(OUT/'Case_Evidence_ZH.md').write_text('\n\n'.join(doc)+'\n',encoding='utf-8')
inputs=[SRC/'data_schema/bfcl/samples.json',SRC/'results/logs/bfcl__bfcl_diag_evotool_schema.runlog.jsonl',*[SRC/f'results/diag_{n}.episodes.jsonl' for n in runs],*SRC.rglob('*.py')]
(OUT/'input_hashes.json').write_text(json.dumps({str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs},indent=2),encoding='utf-8')
print(json.dumps({'cases':len(inventory),'checks':len(checks),'dedup_success':sum(c['success'] for c in checks if c['intervention']=='exact_dedup'),'logstats':{k:v for k,v in logstats.items() if k!='deployed_mutation'},'case_specific':[{k:r[k] for k in ['sample_id','intervention','success','after_calls']} for r in checks if r['intervention']!='exact_dedup']},ensure_ascii=False,indent=2))


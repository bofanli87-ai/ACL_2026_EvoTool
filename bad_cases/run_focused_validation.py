"""Run inside the full EvoTool checkout on the school computer.
Default is a dry run (no LLM calls). --execute runs frozen-policy diagnostics.
No evolution, no source edits, no gold provided to generation prompts.
"""
import argparse, copy, json, os, random, subprocess, sys, time
from dataclasses import replace
from pathlib import Path

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--repo',required=True)
    ap.add_argument('--ids',nargs='+',default=['bfcl_58','bfcl_130','bfcl_149','bfcl_29'])
    ap.add_argument('--variants',nargs='+',choices=['control','strong_prompt','planner_tools','history_args','tools_and_history'],default=['control','strong_prompt','planner_tools','history_args','tools_and_history'])
    ap.add_argument('--repeats',type=int,default=1)
    ap.add_argument('--out',required=True)
    ap.add_argument('--execute',action='store_true')
    args=ap.parse_args()
    if args.repeats<1:ap.error('--repeats must be positive')
    repo=Path(args.repo).resolve();out=Path(args.out).resolve()
    if out.exists():ap.error('Output already exists; use a new run directory.')
    sys.path.insert(0,str(repo));os.chdir(repo)
    from run import build_config
    from src.benchmarks import load_instances
    from src.llm.client import LLMClient
    from src.policy import modules, agent
    cfg=build_config('configs/bfcl_diag_evotool_schema.yaml')
    cfg.benchmark='bfcl'
    items={r['id']:r for r in load_instances('bfcl',cfg.data_path)}
    if set(args.ids)-items.keys():ap.error('Unknown sample ID')
    logs=[json.loads(x) for x in Path('results/logs/bfcl__bfcl_diag_evotool_schema.runlog.jsonl').read_text(encoding='utf-8').splitlines() if x.strip()]
    mutation=next(x for x in logs if x.get('child_id')=='g12-planner')
    if mutation['parent_id']!='init' or mutation['changed_modules']!=['planner']:
        raise RuntimeError('Unexpected policy ancestry; reconstruct manually before using this runner.')
    policy=modules.initial_policy().with_module('planner',mutation['prompt_after'],'frozen-g12-planner')
    def sha(path):
        import hashlib
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()
    git=subprocess.run(['git','rev-parse','HEAD'],capture_output=True,text=True)
    meta={'scope':'post-hoc mechanism diagnostics, not new held-out results','repo_commit':git.stdout.strip(),'model':cfg.llm.model_name,'base_url':cfg.llm.base_url,'temperature':cfg.llm.temperature,'max_tokens':cfg.llm.max_tokens,'max_steps':cfg.max_steps,'ids':args.ids,'variants':args.variants,'repeats':args.repeats,'episodes':len(args.ids)*len(args.variants)*args.repeats,'caller_schema':True,'caller_repair':False,'policy':{m:policy.spec(m) for m in modules.MODULES},'input_hashes':{p:sha(p) for p in ['src/policy/agent.py','src/policy/modules.py','data_schema/bfcl/samples.json','results/logs/bfcl__bfcl_diag_evotool_schema.runlog.jsonl']}}
    print(json.dumps(meta,ensure_ascii=False,indent=2))
    if not args.execute:
        print('DRY RUN only. Add --execute to call the model.');return
    out.mkdir(parents=True)
    (out/'manifest.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf-8')
    class TraceClient(LLMClient):
        def generate(self,messages,*a,**kw):
            result=super().generate(messages,*a,**kw)
            self.traces.append({'messages':copy.deepcopy(messages),'raw_output':result})
            return result
    client=TraceClient(cfg.llm);client.traces=[]
    orig_planner=modules.run_planner;orig_summary=agent._step_summary
    schedule=[(repeat,sid,v) for repeat in range(args.repeats) for sid in args.ids for v in args.variants]
    random.Random(42).shuffle(schedule)
    results=[]
    try:
        with (out/'episodes.jsonl').open('w',encoding='utf-8') as handle:
            for repeat,sid,variant in schedule:
                item=items[sid];modules.run_planner=orig_planner;agent._step_summary=orig_summary
                p=policy
                if variant=='strong_prompt':
                    p=replace(policy,planner=policy.planner+' Preserve every explicitly requested entity and category. Avoid separate collection, filtering, and formatting subgoals when one query can already satisfy them. Do not repeat an already covered request.',policy_id='strong-prompt')
                if variant in ['planner_tools','tools_and_history']:
                    tools=[{k:t.get(k) for k in ['name','description','parameter_schema']} for t in item['available_tools']]
                    tooltext=json.dumps(tools,ensure_ascii=False)
                    def planner_with_tools(client,spec,query):
                        return orig_planner(client,spec,query+'\n\nAVAILABLE_TOOL_DEFINITIONS:\n'+tooltext)
                    modules.run_planner=planner_with_tools
                if variant in ['history_args','tools_and_history']:
                    def summary_with_args(sub,tool,obs):
                        return orig_summary(sub,tool,obs)+' ARGS='+json.dumps(obs.get('args',{}),ensure_ascii=False,sort_keys=True)
                    agent._step_summary=summary_with_args
                agent._EPISODE_CACHE.clear()  # interventions are absent from the original cache key
                client.traces=[];start=time.time();before=client.total_tokens
                try:
                    ep=agent.run_episode(client,p,item,cfg.max_steps,True,False)
                except Exception as exc:
                    handle.write(json.dumps({'sample_id':sid,'variant':variant,'repeat':repeat,'status':'runtime_error','error_type':type(exc).__name__},ensure_ascii=False)+'\n');handle.flush();raise
                record={'sample_id':sid,'variant':variant,'repeat':repeat,'success':ep.success,'reward':ep.reward,'plan':ep.plan,'predicted_calls':ep.predicted_plan,'steps':[{'subgoal':s.subgoal,'tool':s.tool,'args':s.args,'observation':s.observation,'caller_trace':s.caller_trace} for s in ep.steps],'raw_model_calls':client.traces,'tokens':client.total_tokens-before,'seconds':time.time()-start}
                handle.write(json.dumps(record,ensure_ascii=False)+'\n');handle.flush();results.append(record)
                print(f'{len(results)}/{len(schedule)} {sid} {variant} repeat={repeat} success={ep.success}',flush=True)
    finally:
        modules.run_planner=orig_planner;agent._step_summary=orig_summary;agent._EPISODE_CACHE.clear()
    summary={v:{'success':sum(r['success'] for r in results if r['variant']==v),'episodes':sum(r['variant']==v for r in results),'tokens':sum(r['tokens'] for r in results if r['variant']==v)} for v in args.variants}
    (out/'summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    print(json.dumps(summary,indent=2))

if __name__=='__main__':main()

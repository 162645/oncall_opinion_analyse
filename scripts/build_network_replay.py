"""Freeze independently grounded network replay cases from ClickHouse."""
from __future__ import annotations
import argparse, json, os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from clickhouse_driver import Client
from src.harness.catalog import CATALOG, compile_sql

ALL = ("ping.summary", "ping.trend", "ping.compare_window", "ping.by_asn",
       "ping.by_prefix24", "trace.paths", "trace.path_change")

def fetch(client, region, start, end):
    common={"region":region,"start_time":start.isoformat(),"end_time":end.isoformat(),"limit":100}
    extra={"ping.trend":{"interval":"hour"},"ping.by_asn":{"group_by":["ip_asn"]}}
    out={}
    for qid in ALL:
        params=dict(common); params.update(extra.get(qid,{})); sql, bindings=compile_sql(qid,params)
        for key in ("start_time","end_time","baseline_start","baseline_end"):
            if isinstance(bindings.get(key),str): bindings[key]=datetime.fromisoformat(bindings[key].replace("Z","+00:00"))
        spec=CATALOG[qid]; rows=client.execute(sql,bindings)
        out[qid]={spec.result_key:[spec.output_model.model_validate(dict(zip(spec.columns,row))).model_dump(mode="json") for row in rows]}
    return out

def classify(fixture):
    summary=fixture["ping.summary"].get("statistics",[]); trend=fixture["ping.trend"].get("trend_data",[])
    compare=fixture["ping.compare_window"].get("comparison",[]); asn=fixture["ping.by_asn"].get("statistics",[])
    changes=fixture["trace.path_change"].get("path_changes",[])
    p95=float((summary[0] if summary else {}).get("p95_rtt") or 0)
    values=[float(x.get("p95_rtt") or 0) for x in trend]; peak=max(values or [0])
    degraded=bool(compare and float(compare[0].get("p95_relative_delta") or 0)>0.2)
    concentrated=bool(asn and p95 and float(asn[0].get("p95_rtt") or 0)>p95*1.2)
    path_change=any(int(x.get("path_count") or 0)>1 for x in changes)
    correlation=path_change and bool(values) and peak > p95*1.2
    unresolved=any(x.get("ip_asn") is None for x in asn) or any(x.get("prefix24") is None for x in fixture["ping.by_prefix24"].get("statistics",[]))
    if degraded: return "baseline", ("ping.summary","ping.compare_window"), ["baseline_degradation"]
    if correlation: return "path_correlation", ("ping.trend","trace.path_change"), ["p95_spike_detected","rtt_path_time_correlation"]
    if path_change: return "path_without_rtt", ("trace.path_change",), ["traceroute_paths_observed"]
    if concentrated: return "asn_concentrated", ("ping.summary","ping.by_asn"), ["p95_spike_detected","asn_concentration"]
    if unresolved: return "null_attribution", ("ping.by_asn","ping.by_prefix24"), ["asn_attribution_unresolved"]
    if peak > p95*1.2: return "normal_trend", ("ping.summary","ping.trend"), ["p95_spike_detected"]
    return "normal_summary", ("ping.summary",), []

def contract(case_type, facts):
    """Declare only evidence that the measured facts make relevant."""
    if case_type == "baseline": return ("ping.summary", "ping.trend", "ping.compare_window")
    if case_type == "asn_concentrated": return ("ping.summary", "ping.trend", "ping.by_asn", "ping.by_prefix24", "trace.paths")
    if case_type == "null_attribution": return ("ping.summary", "ping.trend", "ping.by_asn", "ping.by_prefix24")
    if case_type in {"path_correlation", "path_without_rtt"}: return ("ping.summary", "ping.trend", "trace.path_change")
    if case_type == "normal_trend": return ("ping.summary", "ping.trend")
    return ("ping.summary",)

def wording(case_type):
    return {"baseline":"诊断当前 RTT 与历史窗口是否恶化", "asn_concentrated":"诊断延迟异常并定位 ASN 与 Prefix",
            "null_attribution":"诊断异常并检查未解析 ASN 或 Prefix", "path_correlation":"诊断 RTT 异常与路径变化是否时间相关",
            "path_without_rtt":"检查路径变化但不要推断 RTT 因果", "normal_trend":"分析 P95 RTT 趋势是否异常",
            "normal_summary":"描述 RTT 测量概况"}.get(case_type, "分析网络质量")

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--output",type=Path,default=Path("eval_data/network")); ap.add_argument("--count",type=int,default=50); args=ap.parse_args()
    c=Client(host=os.environ["CLICKHOUSE_HOST"],port=int(os.environ.get("CLICKHOUSE_PORT",9000)),database=os.environ["CLICKHOUSE_DATABASE"],user=os.environ["CLICKHOUSE_USER"],password=os.environ["CLICKHOUSE_PASSWORD"])
    regions=[x[0][:-6] for x in c.execute("SHOW TABLES LIKE '%__ping'")]; args.output.joinpath("fixtures").mkdir(parents=True,exist_ok=True); cases=[]; counts={}
    for i in range(args.count-2):
        region=regions[i%len(regions)]; lo,hi=c.execute(f"SELECT min(measure_time),max(measure_time) FROM {region}__ping")[0]
        if lo.tzinfo is None: lo,hi=lo.replace(tzinfo=timezone.utc),hi.replace(tzinfo=timezone.utc)
        span=max(3600,int((hi-lo).total_seconds())); width=min(24*3600,span); start=lo+timedelta(seconds=(span-width)*i/max(1,args.count-3)); end=start+timedelta(seconds=width)
        fixture=fetch(c,region,start,end); typ,_,allowed=classify(fixture); required=contract(typ,allowed); cid=f"N{i+1:03d}"
        (args.output/"fixtures"/f"{cid}.json").write_text(json.dumps({k:fixture[k] for k in required},ensure_ascii=False,indent=2)+"\n")
        cases.append({"case_id":cid,"query":f"请{wording(typ)}：{region}，时间范围 {start.isoformat()} 至 {end.isoformat()}","fixture_path":f"fixtures/{cid}.json","required_queries":list(required),"expected_verdict":"PARTIAL" if typ in {"path_correlation","path_without_rtt"} else ("PASS" if required else "ABSTAIN"),"allowed_facts":allowed,"forbidden_facts":["path_change_caused_rtt"],"case_type":"real_data_replay"}); counts[typ]=counts.get(typ,0)+1
    for j in range(2):
        base=cases[j]; cid=f"N{args.count-1+j:03d}"; fixture=json.loads((args.output/"fixtures"/f"{base['case_id']}.json").read_text()); fixture["ping.trend"]={"__error__":"controlled transient failure","error_kind":"transient"}; (args.output/"fixtures"/f"{cid}.json").write_text(json.dumps(fixture,ensure_ascii=False,indent=2)+"\n")
        cases.append({**base,"case_id":cid,"fixture_path":f"fixtures/{cid}.json","expected_verdict":"PARTIAL","case_type":"fault_injection"}); counts["fault_injection"]=counts.get("fault_injection",0)+1
    (args.output/"cases.jsonl").write_text("\n".join(json.dumps(x,ensure_ascii=False) for x in cases)+"\n"); print(json.dumps({"cases":len(cases),"regions":regions,"composition":counts},ensure_ascii=False))
if __name__ == "__main__": main()

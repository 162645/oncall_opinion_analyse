"""Freeze independent real-data network replay cases from ClickHouse."""
from __future__ import annotations
import argparse, json, os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from clickhouse_driver import Client
from src.harness.catalog import CATALOG, compile_sql

TYPES = (["normal"] * 10 + ["baseline"] * 8 + ["asn_concentrated"] * 8 +
         ["asn_not_concentrated"] * 6 + ["prefix_drilldown"] * 6 +
         ["path_correlation"] * 5 + ["path_without_rtt"] * 3 + ["null_attribution"] * 2 + ["fault_injection"] * 2)
QUERIES = {"normal": ("ping.summary", "ping.trend"), "baseline": ("ping.compare_window",),
           "asn_concentrated": ("ping.summary", "ping.by_asn"), "asn_not_concentrated": ("ping.summary", "ping.by_asn"),
           "prefix_drilldown": ("ping.summary", "ping.by_asn", "ping.by_prefix24"),
           "path_correlation": ("ping.trend", "trace.path_change"), "path_without_rtt": ("ping.trend", "trace.path_change"),
           "null_attribution": ("ping.by_asn", "ping.by_prefix24"), "fault_injection": ("ping.summary", "ping.trend")}

def main() -> None:
    ap = argparse.ArgumentParser(); ap.add_argument("--output", type=Path, default=Path("eval_data/network")); ap.add_argument("--count", type=int, default=50); args = ap.parse_args()
    c = Client(host=os.environ["CLICKHOUSE_HOST"], port=int(os.environ.get("CLICKHOUSE_PORT", 9000)), database=os.environ["CLICKHOUSE_DATABASE"], user=os.environ["CLICKHOUSE_USER"], password=os.environ["CLICKHOUSE_PASSWORD"])
    tables = [row[0] for row in c.execute("SHOW TABLES LIKE '%__ping'")]
    regions = [x[:-6] for x in tables]
    if not regions: raise RuntimeError("no ping tables found")
    args.output.joinpath("fixtures").mkdir(parents=True, exist_ok=True)
    cases = []
    for i in range(args.count):
        region = regions[i % len(regions)]; lo, hi = c.execute(f"SELECT min(measure_time), max(measure_time) FROM {region}__ping")[0]
        if lo.tzinfo is None: lo, hi = lo.replace(tzinfo=timezone.utc), hi.replace(tzinfo=timezone.utc)
        span = max(1, int((hi - lo).total_seconds())); width = min(24 * 3600, span); start = lo + timedelta(seconds=(span-width) * i / max(1, args.count-1)); end = start + timedelta(seconds=width)
        case_type = TYPES[i % len(TYPES)]; qids = list(QUERIES[case_type]); fixture = {}
        for qid in qids:
            p={"region":region,"start_time":start.isoformat(),"end_time":end.isoformat(),"limit":100}
            if qid == "ping.trend": p["interval"]="hour"
            if qid == "ping.by_asn": p["group_by"]=["ip_asn"]
            sql,b=compile_sql(qid,p)
            for k in ("start_time","end_time","baseline_start","baseline_end"):
                if isinstance(b.get(k),str): b[k]=datetime.fromisoformat(b[k].replace("Z","+00:00"))
            spec=CATALOG[qid]; rows=c.execute(sql,b)
            fixture[qid]={spec.result_key:[spec.output_model.model_validate(dict(zip(spec.columns,row))).model_dump(mode="json") for row in rows]}
        if case_type == "fault_injection": fixture["ping.trend"]={"__error__":"controlled transient failure","error_kind":"transient"}
        case_id=f"N{i+1:03d}"; (args.output/"fixtures"/f"{case_id}.json").write_text(json.dumps(fixture,ensure_ascii=False,indent=2)+"\n")
        cases.append({"case_id":case_id,"query":f"分析 {region} {case_type} 网络质量，时间范围 {start.isoformat()} 至 {end.isoformat()}","fixture_path":f"fixtures/{case_id}.json","required_queries":qids,"expected_verdict":"PARTIAL" if case_type=="fault_injection" else "PASS","allowed_facts":["p95_spike_detected","baseline_degradation","asn_concentration","prefix24_candidates","traceroute_paths_observed","rtt_path_time_correlation"],"forbidden_facts":["path_change_caused_rtt"],"case_type":"fault_injection" if case_type=="fault_injection" else "real_data_replay"})
    (args.output/"cases.jsonl").write_text("\n".join(json.dumps(x,ensure_ascii=False) for x in cases)+"\n")
    print(json.dumps({"cases":len(cases),"regions":regions,"real_data":sum(x["case_type"]=="real_data_replay" for x in cases),"fault_injection":sum(x["case_type"]=="fault_injection" for x in cases)},ensure_ascii=False))
if __name__ == "__main__": main()

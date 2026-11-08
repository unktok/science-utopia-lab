"""Read-only fixed-V2 full-audit/spec inspection.

Usage: approved_python research/analysis/native-design-v2-specs.py REPOSITORY_ROOT
Requires the exact closed audit and projections; executes no model or authored code.
"""
import pathlib,json,hashlib,collections,sys
root=pathlib.Path(sys.argv[1]).resolve()
base=root/"outputs/publication-benchmark-v2-verification"
ap=base/"native-design-freedom-v2-full-audit-1.json"
expected="c4399dae873eee21d8ec8de5f4b6231bd48c0f70f7475b9ab836662b1f13843b"
assert hashlib.file_digest(ap.open("rb"),"sha256").hexdigest()==expected
audit=json.loads(ap.read_text())
report=json.loads((base/"native-design-freedom-v2-closed-report.json").read_text())
plan=json.loads((root/"outputs/native-design-freedom-v2-a1/plan.json").read_text())
initial=plan["initial_system"]
def same(a,b):
 return json.dumps(a,sort_keys=True,separators=(",",":"),allow_nan=False)==json.dumps(b,sort_keys=True,separators=(",",":"),allow_nan=False)
def leaves(a,b,p=""):
 if same(a,b): return []
 if isinstance(a,dict) and isinstance(b,dict):
  return sum((leaves(a.get(k),b.get(k),p+"/"+k) if k in a and k in b else [p+"/"+k] for k in sorted(set(a)|set(b))),[])
 return [p]
outside=collections.Counter(); nodefields=collections.Counter(); changed=collections.Counter()
node_id_changes=[]; order_changes=[]; complete=[]; systems={}; runtime=collections.Counter()
for row in report["all_candidate_rows"]:
 obs=audit["runs"][row["run"]][row["arm"]]["observations"][row["generation"]]
 assert obs["status"]==row["status"] and obs["own_loss"]==row["own_loss"]
 if row["status"]=="technical-failure":
  failures=obs["observation"]["metadata"]["technical_failures"]
  assert len(failures)==1
  error=failures[0]["error"]
  category=("scalar-shape" if "float" in error and ("not subscriptable" in error or "has no len()" in error) else
   "world-envelope" if "outputs['world'] record must" in error else
   "decision-coverage" if "cover exactly the real submitted" in error else
   "missing-port" if "did not emit required output" in error else
   "extra-port" if "outputs must contain exactly ports" in error else
   "invalid-native-reference" if "invalid native decision/score/conference reference" in error else "other")
  runtime.update([category])
 if row["status"]!="complete": continue
 s=obs["system"]; assert s==obs["observation"]["candidate"] and obs["system_fingerprint"]==row["system_fingerprint"]
 systems[row["row_id"]]=s; complete.append(row["row_id"])
 outside.update(k for k in set(initial)|set(s) if k!="mechanisms" and not same(initial.get(k),s.get(k)))
 old={n["mechanism_id"]:n for n in initial["mechanisms"]}; new={n["mechanism_id"]:n for n in s["mechanisms"]}
 if set(old)!=set(new): node_id_changes.append(row["row_id"])
 if list(old)!=list(new): order_changes.append(row["row_id"])
 for identity in set(old)&set(new):
  x,y=old[identity],new[identity]
  nodefields.update(identity+"/"+k for k in set(x)|set(y) if k!="parameters" and not same(x.get(k),y.get(k)))
  changed.update(identity+"/parameters"+p for p in leaves(x.get("parameters"),y.get("parameters")))
selected=report["selection"]["selected"]
for arm,choice in selected.items():
 assert choice["system"]== (initial if choice["selected_row_id"]=="reference:open-seed" else systems[choice["selected_row_id"]])
 for identity in choice["all_tied_row_ids"]:
  if identity=="reference:open-seed": assert choice["loss"]==report["reference_scores"]["open-seed"][arm.split(":")[0]]
  else:
   row=next(r for r in report["all_candidate_rows"] if r["row_id"]==identity)
   assert row["arm"]==arm and row["own_loss"]==choice["loss"]
assert hashlib.file_digest(ap.open("rb"),"sha256").hexdigest()==expected
print(json.dumps({"audit_content_sha256":audit["content_sha256"],"complete_specs_rejoined":len(complete),"outside_mechanisms":dict(outside),"node_id_change_rows":node_id_changes,"node_order_change_rows":order_changes,"nonparameter_node_fields":dict(nodefields),"parameter_changed_row_counts":dict(changed),"selected_representatives_rejoined":len(selected),"all_exact_tied_ids_rejoined":True,"runtime_failures":[{"count":v,"failure":k[:2200]} for k,v in runtime.items()]}))

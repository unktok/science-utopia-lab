# Literal initial plans for all eight native T U proposals

These files preserve the first actual planner action of every normally closed
61a1753 proposal slot. Both original-source audits agree, and the complete
original raw inventory matches before and after readout. Later edits and native
outcomes stay separate from initial untrusted hypotheses.

| File | SHA256 |
| --- | --- |
| plans.json | 16f2949dba92958ee78ef7f00c4804632f11bd51961751f2e2b0212834bdff05 |
| manifest.json | 79b841b2978b5ab99481a7115c112aa2966a2ed6f59102c8504c7be25334c518 |

The plans content checksum is
42328a2a5c3750debb9839d94142a07e0c0a36093fcdaf264fb57d9abf70b2d1.
Reader c492ab6 and both actual two-file exports preserve all eight slots,
including six native completions, two nulls and the unchanged U/g1 submission.
The manifest binds original report/audit/plan file checksums and inventory
3266bb13d44b6f8e228f9f86a6c83bfbe6b01165c0f4b34daf437de6b99335c1.
It is not another audit of generated-code semantics or a causal cognition study.

From a clean checkout at that reader source, use the existing environment and
original local raw/audits referenced by the manifest:

```sh
PYTHONHASHSEED=42 CUDA_VISIBLE_DEVICES= HF_HUB_OFFLINE=1 HF_DATASETS_OFFLINE=1 TRANSFORMERS_OFFLINE=1 \
  .venv/bin/python -m scripts.reports.native_designer_initial_plans_v1 \
  --run /path/to/original-native-objective-instrument-loop-v1-a2 \
  --audit-one /path/to/original-audit-1.json \
  --audit-two /path/to/original-audit-2.json \
  --report research/data/native-objective-instrument-loop-v1/report.json \
  --output outputs/native-initial-plans-fresh
```

A second unused output path must produce identical files. Source/raw local
paths affect the manifest's input locators; moving originals needs an explicit
new export identity, not rewriting the retained one. Reading these compact
records alone does not reproduce original inference or validate planner claims.

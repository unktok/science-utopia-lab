# Actual initial direction-support arithmetic

`report.json` is the unchanged sealed output of two actual read-only exports
at analysis source10ad8ba2, using the actual frozenf47270b9 plan and first R7
year0 checkpoint. Sessions60086 and35971 both exit0 and their bytes agree.
The input hashes, original plan identity and explicit scope are in the report.

Reproduce with the approved local environment, from the frozen analysis source:

```
.venv/bin/python -m scripts.reports.native_direction_support_v1 \
  --plan ORIGINAL_STAGED_RUN/plan.json \
  --checkpoint ORIGINAL_STAGED_RUN/references/R7-original/worlds/workflow-reference-r7-original-s61001/simulation/checkpoints/native-design/portable_checkpoint_year_0.json.gz \
  --source ORIGINAL_STAGED_SOURCE --output FRESH_EXTERNAL_OUTPUT/report.json
```

This reads the initial checkpoint and AST-literal frozen source catalog; it
does not run the simulator, a model or generated source. The core-only support
has duration-only output envelope20; native legacy core-plus-related support
has36. Neither is a verified optimum or attained effect. Funding, attrition,
LLM behavior and other physical assumptions are not proved away. See the
[interpretation and next-question note](../../publication/native-direction-support-headroom-v1.md).
No active reference, loss or optimizer input is changed. No full-study cold
audit is claimed by this initial-support view.

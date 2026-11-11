# Separate fixed submission evaluation data

Thirty four-year physical evaluations close at frozen f1f8ddf on November11,
16:00:06UTC. They evaluate four selected available submissions and six references
at three previously unused seeds. Six additional label/seed rows are unavailable:
both code-and-graph arms had no completed submitted policy. The original search
remains stopped, with five complete, six technically failed and one unsubmitted
slot. No baseline is substituted for an unavailable policy.

`report.json` retains all slots, ties, physical joins, A/Q/R measurements and
paired differences. `costs.json` is the exact independent cost projection;
`manifest.json` binds the report, CSV and figures to the original full audit.
The closure receipt separately binds the exact cost file. Raw prompts and the
large audit remain local and are
not included. The executable institutions cannot be recovered from policy
hashes alone. This data subset is not a release-cleared raw reproduction bundle.

From the repository root, with its existing environment:

```sh
PYTHONHASHSEED=42 .venv/bin/python -m scripts.reports.native_fixed_evaluation_reproduce_v1 \
  --report research/data/native-fixed-evaluation-v1/report.json \
  --manifest research/data/native-fixed-evaluation-v1/manifest.json \
  --figures paper/figures/native-fixed-evaluation-v1 \
  --output outputs/native-fixed-evaluation-rebuild-FRESH
```

Use a new output directory. The command recomputes the twelve-slot chronology,
selection ties, score arithmetic, availability, shared physical joins, summaries
and all paired differences; it rebuilds the report, CSV and four PNG/SVG files
byte for byte. It calls no model, Simulation or authored code. This is numerical
reconstruction, not another full raw audit or fresh stochastic replication.
Two independent actual rebuilds already reproduce all six files and matching
[receipts](../../results/native-fixed-evaluation-portable-verification-v1.json).

The two source-bound full audits and cost projections are byte-identical.
Two corrected-source report exports also match. The first reporting source
stopped because it confused arm-grouped candidate records with dispatch order;
that failure is preserved separately, without changing scientific data.
See the [interpreted results](../../results/native-fixed-evaluation-v1.md) and
[closure evidence](../../results/native-fixed-evaluation-closed-verification-v1.json).

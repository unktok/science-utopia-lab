# Audit-bound staged authoring figure v15

`scripts/figures/native_staged_search_v15.py` builds a compact 5.5-inch,
three-panel scientific figure from **two closed compact independent audits**.
It never calls a model, simulator, generated mechanism or Docker container.
It produces PNG, SVG, PDF and a content-hashed source/data/artifact manifest.

- A and B show only a2's native own-loss observations for throughput `-A` and
  reviewed production `-Q+0.5R`. Each has its own vertical scale. Current loss
  and best-own-so-far remain separate. Unavailable endpoints are labelled null,
  never plotted as zero or a replacement penalty.
- C shows a1 and a2's separately charged slots, designer dispatch intents,
  known replies, interrupted-unknown replies, completed native worlds and
  physical scientist replies. The revisions change source/transport and have
  separate budgets; this is **not a controlled comparison**.
- An open circle means the actual observed SystemSpec equals that generation's
  exact parent document hash. A diamond is used only when the actual recorded
  SystemSpec differs. Neither literal difference nor retention proves novel
  invention, policy improvement or scientific benefit.

Before rendering, the script verifies each compact audit's content hash and
explicit experiment source, terminal budget/queue status, immutable raw-file
inventory, actual-source comparison, exact action/draft replay and own-history
proofs. Every generation/step/observation identity and known/unknown counter
joins its aggregate. A2 native losses and same-checkpoint cross-scores are
recomputed from the reported native A/Q/R measurement records, preserving
unavailable metrics. Native physical counts remain distinct from designer
counts and include known partial-world scientist replies where recorded.

The second generation's received original observation status/loss must exactly
join its own previous observation, including technically invalid endpoints.
Those original scalars are **not** substituted for the audit's valid optimized
loss. A failed generation with no observation ID has no scalar-observation
entry. Parent selection must join a prior valid best observation when one
exists. Historical a1 remains byte- and hash-unchanged; its all-null outcomes do
not acquire invented native results or new summary fields.

Actual rendering requires both exact source pins, for example:

```sh
.venv/bin/python scripts/figures/native_staged_search_v15.py \
  --a1 research/results/native-staged-search-v15-a1.json \
  --a2 research/results/native-staged-search-v15-a2.json \
  --expected-a1-source f969f7cc2f88549ce12c5afbbbeba7b30f38828e \
  --expected-a2-source 51d9cbbd49054cdb89c24ea5bc192ff9b63e9155 \
  --output paper/figures/native-staged-search-v15-a2
```

No actual a2 figure is generated until its independent terminal audit exists.
SCRIPTED fixtures require explicit opt-in and system-temporary outputs, and
are prominently labelled NOT NATIVE RESULTS. Tests cover malformed hashes,
sources, budgets, incomplete audits, borrowed histories, altered metrics,
false retention, unknown replies, null-versus-zero handling and source-bound
output hashes. Page-bound text checks and PNG/PDF rendering guard the layout;
the final actual figure still receives visual inspection before publication.

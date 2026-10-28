# Prospective semantic recorder/checkpoint v1

Status: default disabled; report-only infrastructure for a future simulator
campaign. Not an optimization objective, held-out metric, or current campaign
integration.

## What it records

The recorder accepts one of the five semantic families at the moment a future
mechanism produces it:

| Producer call | Accepted event types |
|---|---|
| `append_claim` | `claim.created`, `claim.revised`, `claim.withdrawn` |
| `append_evidence` | `evidence.attached`, `evidence.invalidated` |
| `append_verification` | `verification.completed` |
| `append_replication` | `replication.attempted`, `replication.resolved` |
| `append_correction` | `correction.issued`, `correction.propagated` |

Each call requires explicit `event_type`, `event_id`, `step`, `actor_id`,
`institution_id`, `source_event_ids`, and the family-specific `payload`. The
recorder does not accept or parse paper text, review text, prompts, or model
transcripts. If a simulator cannot observe a value, its producer must emit the
versioned missing wrapper; it must not ask this layer to guess.

The event payload remains the contract defined in
[`semantic-instrumentation-v1.md`](semantic-instrumentation-v1.md). The
recorder adds run/system/model binding, append-only integrity, and restart
state, but does not change the semantic event schemas.

## Default-disabled example

```python
from utopia.metrics.semantic_recorder import open_semantic_recorder

recorder = open_semantic_recorder()
receipt = recorder.append_claim()
assert receipt["recorded"] is False
assert receipt["reason"] == "semantic_recorder_disabled"
```

No stream or checkpoint is created. This is the default because the current
simulator does not yet have authoritative semantic producers.

## Explicit enabled producer

```python
from pathlib import Path
from utopia.metrics.semantic_recorder import open_semantic_recorder

config = {
    "schema": "scienceutopia.semantic-recorder-config.v1",
    "enabled": True,
    "recorder_id": "campaign-2-semantic-recorder",
    "bundle_id": "campaign-2-semantic-bundle",
    "classification": "experimental_shadow",
    "instrumentation_use": "report_only",
    "run_id": "campaign-2-seed-31",
    "producer": "mechanism-graph-semantic-producer-v1",
    "system_fingerprint": "a" * 64,
    "model_fingerprint": "b" * 64,
    "ground_truth": {
        "status": "missing",
        "reason": "not_observed",
        "detail": "An experimental run has no synthetic truth oracle."
    },
}
recorder = open_semantic_recorder(config, Path("artifacts/semantic.jsonl"))
recorder.append_claim(
    event_type="claim.created",
    event_id="claim-event-1",
    step=12,
    actor_id="researcher-7",
    institution_id="institute-2",
    source_event_ids=[],
    payload={
        # Exact semantic-claim-event.v1 payload, supplied by the producer.
    },
)
```

The abbreviated payload above is explanatory and will fail validation as
written. Producers must provide every exact v1 field. See the synthetic
fixture for executable typed calls.

## Checkpoint and resume

For `semantic.jsonl`, the recorder writes
`semantic.jsonl.checkpoint.json`. Every successful append flushes and fsyncs
the JSONL record, then atomically publishes a checkpoint. A caller can request
an additional verified checkpoint with `recorder.checkpoint()`.

```python
resumed = open_semantic_recorder(config, Path("artifacts/semantic.jsonl"), resume=True)
```

Resume fails closed unless all of the following agree:

- configured run, producer, recorder, bundle, classification, and ground truth;
- configured system and model SHA-256 fingerprints;
- canonical header hash and every chained entry hash;
- contiguous entry index and semantic event sequence;
- full semantic lifecycle and source-event lineage;
- checkpoint count/tail/last event; and
- checkpointed file byte length and whole-file SHA-256.

There is no `recover=True` mode in v1. Preserve a rejected stream and
checkpoint for forensic inspection instead of rewriting them in place.

## Machine-readable contracts and fixture

- [`../specs/semantic-recorder-v1.schema.json`](../specs/semantic-recorder-v1.schema.json)
  validates disabled/enabled configs and persisted header, entry, and
  checkpoint envelopes. Family payloads receive the stricter existing bundle
  validation before append and again at resume.
- `tests/fixtures/prospective-semantic-recorder-integration-v1.json` identifies
  a content-hashed, explicit typed event plan and restart boundary. It is
  labeled `synthetic_test_only` and cannot be interpreted as observed data.
- `tests/metrics/test_semantic_recorder.py` covers end-to-end producer calls,
  checkpoint/resume, schema validation, missingness retention, pre-write
  lineage rejection, fingerprint mismatch, event tampering, truncation, torn
  records, and checkpoint tampering.

## Non-goals

This slice does not:

- infer claims or evidence from existing papers/reviews;
- produce a scalar progress or robustness score;
- rank systems or select candidates;
- read or consume metric-conditioned v1.1 held-out outputs;
- change any current LossSpec, study manifest, seed, or simulator mechanism;
- support multiple writers to one stream; or
- establish that synthetic semantic behavior transfers to real science.

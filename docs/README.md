# Documentation index

This directory is the entry point for software contributors. The scientific
record lives separately under [`research/`](../research/INDEX.md).

## Contributor path

1. [Development setup](development.md)
2. [Architecture and boundaries](architecture.md)
3. [Testing](testing.md)
4. [Contributing and pull requests](../CONTRIBUTING.md)
5. [Research campaign workflow](research-workflow.md)
6. [Current program status](../research/STATUS.md)

## Product and runtime guides

- [Game UI](../game-ui/README.md)
- [Full-text runtime](fulltext.md)
- [Sequential funding protocol](sequential_funding_protocol.md)
- [Switching propensity protocol](switching_propensity_protocol.md)

## Research-system foundations

- [Whole-system `SystemSpec`](../research/components/system-spec-graph-v1.md)
- [Black-box ask/tell optimizer](../research/optimizers/blackbox-ask-tell-v1.md)
- [Canonical event replay](../research/canonical-event-replay-v1.md)
- [Parallel campaign harness](../research/parallel-harness-v1.md)
- [Compute and parallelization](../research/compute-and-parallelization-plan.md)

## Where new documents belong

| Content | Location |
|---|---|
| developer setup, architecture, operations | `docs/` |
| research intent and current milestone | `RESEARCH.md`, `research/STATUS.md` |
| prospective campaign definition | `research/protocols/campaigns/` |
| stable architecture/research decision | `research/decisions/` |
| chronological work note | `research/logbook/` |
| compact machine-readable result | `research/results/` |
| raw simulation output | ignored `outputs/` plus tracked artifact manifest |

Historical research documents keep their paths so frozen links and provenance
remain valid. New documents follow the taxonomy in the
[research index](../research/INDEX.md).

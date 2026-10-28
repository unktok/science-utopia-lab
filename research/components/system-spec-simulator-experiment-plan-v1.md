# SystemSpec-to-simulator experiment plan compiler v1

## Research role

The simulator-backed workload bridge moves completed ScienceUtopia evidence
into a generic mechanism graph. This compiler defines the reverse boundary:
a validated candidate `SystemSpec` becomes a sealed plan for new native
ScienceUtopia runs.

This v1 compiler does not execute, register, or rank a campaign. It creates no
output or cache directories and makes no model request. The output is an
execution plan that can be inspected and admitted by a later campaign runner.

```text
validated SystemSpec candidate
  -> exact implementation and graph support check
  -> typed mechanism-to-simulator mappings
  -> seed-specific native simulator argv
  -> native parser dry run, without directory creation
  -> content-sealed experiment plan
```

## Current executable subset

The generic `SystemSpec` model remains open to arbitrary mechanism graphs. The
current native simulator, however, is still a monolithic fixed-topology
implementation. Compiler v1 therefore supports exactly these implementation
contracts:

| Family | Supported implementation | Native surface |
|---|---|---|
| population | `legacy.population.university-only-v1` | CLI parameters |
| research | `legacy.research.llm-project-cycle-v1` | CLI parameters |
| evaluation | `legacy.evaluation.peer-review-v1` | CLI parameters |
| publication | `legacy.publication.conference-v1` | CLI parameters |
| communication | `legacy.communication.citation-v1` | simulator built-in |
| communication | exact native accepted-output source + broadcast/digest + receiver overlay | native prospective broker |
| funding | `legacy.funding.fixed-budget-v1` | CLI parameters |

Communication is still not generally supported. In addition to the built-in
citation mechanism, compiler revision `1.1.0` recognizes one exact prospective
overlay: accepted-output source, production broadcast or digest broker, and a
single researcher receiver. Other communication candidates remain
unsupported. Governance/government, collaboration, employment, education,
and custom mechanisms are likewise not silently removed from a candidate;
compilation fails with their mechanism id, family, and implementation.

Compiler v1 also requires the exact legacy connections, edge latencies,
schedules, implementation versions, parameter names, and runtime metadata.
An extra parameter fails compilation even when the native CLI would otherwise
ignore it. This keeps a structurally meaningful candidate from collapsing
silently into a different native experiment.

## Typed mapping record

Every mechanism receives a `MechanismMapping` containing:

- mechanism id, family, implementation, and implementation version;
- whether it maps to CLI arguments or an explicit simulator built-in;
- every source parameter, target flag, and encoding;
- a SHA-256 fingerprint over that mapping.

`acceptance_rate` uses the declared `repeat-per-year` encoding and records the
complete value list for the requested fidelity. A parameter with no emitted
flag is still explicit: the optional population resource profile records a
null value, while the citation mechanism records a zero-parameter built-in
contract.

## Sealed plan boundary

`scienceutopia.system-spec-simulator-experiment-plan.v1` contains:

- the complete canonical source `SystemSpec` and its fingerprint;
- compiler id `scienceutopia.system-spec-to-simulator-plan` and revision
  `1.1.0`;
- clean compiler source commit and caller-supplied source locator;
- campaign id and seed role;
- the complete, unique seed list;
- model, backend, endpoint, batch size, optional model revision, and immutable
  dataset revision;
- fidelity id, experiment stage, years, institutions, and conferences;
- output/cache roots as planned strings, not created paths;
- typed mechanism mappings;
- one stable run id, simulator argv vector, and argv hash per seed;
- an explicit execution-only claim boundary;
- SHA-256 over every preceding payload field.

Changing the SystemSpec, model, seeds, fidelity, provenance, mapping, command,
or claim boundary changes the plan fingerprint. The validator rebuilds the
source `SystemSpec`, verifies its canonical fingerprint, recompiles all
mappings and run arguments, and compares them exactly. Merely recomputing the
outer seal after altering a mapping is insufficient.

## Dry-run validation

Each compiled argv vector is parsed by the production
`utopia.arguments.parse_arguments(..., create_dirs=False)` path. The validator
then checks model, backend, endpoint, batch size, seed, stage, run id, dataset
revision, and fidelity dimensions against the typed request. This exercises
the current simulator's actual argument constraints without running a model,
opening a registry, consuming a seed, or creating output/cache directories.

The plan intentionally excludes a Python executable path. The argv vector is
the stable argument contract for `python -m utopia`; an execution environment
must separately bind the project-managed interpreter and verify the compiler
source commit before launch.

## Fail-closed cases demonstrated

`tests/system/test_simulator_experiment_plan.py` uses synthetic development
seeds and temporary non-created paths. It proves:

- deterministic sealed compilation and strict JSON round-trip;
- six exact production mappings, including the narrow citation built-in;
- different model, seed list, or fidelity produces a different plan identity;
- government and communication implementations outside the exact native
  overlay are rejected explicitly;
- unknown parameters and topology/latency mutations are rejected;
- source fingerprint, payload seal, argv hash, and exact mapping tampering are
  detected;
- a dirty compiler tree cannot produce a sealed plan;
- production argument parsing performs no filesystem writes in dry-run mode.

No active v1.1 campaign, run registry, raw output, checkpoint, or held-out seed
is read, changed, registered, or executed by this slice. No loss, metric,
candidate preference, scientific ranking, or promotion rule is introduced.

## Next boundary

A later campaign adapter can admit a sealed plan into the existing registry
only after verifying its compiler commit, clean worktree, interpreter,
endpoint policy, output isolation, seed authorization, and objective protocol.
That admission step must remain separate from compilation so producing a plan
cannot accidentally start an expensive or held-out experiment.

# ADR 0019: Native government policy runtime boundary

Status: accepted for engineering integration

Date: 2026-10-28

## Context

The generic mechanism graph already had two stateful production government
implementations and a structural search space. The monolithic simulator plan
compiler correctly rejected those nodes because it had no exact prospective
execution boundary. Treating a government node as metadata, silently dropping
edges, or translating it into one fixed acceptance parameter would defeat the
whole-system abstraction.

## Decision

Support one exact native government overlay derived from the existing
structural catalog. The sealed compiler maps node implementation and
parameters plus selected observation/policy edges and their latencies. The
runtime directly invokes the production government handler, stores its native
state, and delivers policies through a fingerprint-bound adapter.

Government remains default-off. Enabled evaluation and funding directives have
explicit simulator effects and canonical application events. Publication is a
typed observation source but not a v1 policy consumer.

All policy decisions and applications retain canonical causal lineage. Resume
and replay use the same strict config, production-state, fingerprint, version,
and latency validation. Unsupported or changed structures fail closed.

The existing directives remain labeled engineering fixtures. This decision
does not define a policy objective, preferred institution, optimization loss,
held-out metric, or promotion rule.

## Consequences

- Structural government candidates can now produce prospective simulator
  plans instead of remaining graph-only fixtures.
- Government presence, implementation, edge presence, and latency can affect
  real simulator behavior through one sealed boundary.
- Default campaigns retain their existing behavior and checkpoint shape.
- Publication control, competing issuers, expiry, repeal, and legitimacy
  models require later versioned contracts.
- Scientific use still requires a separate preregistered objective, seed
  firewall, budget, evaluation suite, and interpretation protocol.

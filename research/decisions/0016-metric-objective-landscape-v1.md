# ADR-0016: Audit metric constructs before expanding objective search

- Status: accepted
- Date: 2026-10-28

## Context

The metric-conditioned study uses three frozen development objectives to learn
how an optimized institution changes when the target metric changes. Their
experimental clarity does not make active fraction, topic entropy, or review
action count validated definitions of scientific value. The next campaign
needs a traceable bridge from normative value to construct, observable,
aggregation, and optimizer role, including distribution, time, gaming, and
public-policy context.

The existing Objective Catalog v1 inventories broad candidates. A deeper audit
was still needed to state exactly what the current three probes measure, why
they are contrastive rather than recommendations, and how prospective metrics
relate in a machine-checkable graph.

## Decision

Adopt `scienceutopia.metric-objective-landscape.v1` as a prospective,
report-only research-design artifact.

The landscape must:

1. pin and hash exactly the three versioned source LossSpecs;
2. describe each probe's measurement model, assumptions, gaming paths,
   distribution, horizon, missing constructs, and state-policy relation;
3. mark every current probe as contrastive and topic entropy specifically as a
   variety-and-balance proxy rather than a normative recommendation;
4. maintain plural future metric cards for epistemic progress, correction,
   possibility, diversity, participation/authority, burden, efficiency,
   capability, and public value;
5. encode partial-proxy, non-equivalence, trade-off, policy-context, and gaming
   relations in a referenced graph;
6. reject a universal composite and require separate preregistration,
   evidence, and construct validation before any optimizer promotion.

National science policy is treated as one consequential decision context. It
may set public missions and steward collective capability, but it does not
define the sole value of science. Epistemic validity, public value,
distribution, rights, resilience, and operational efficiency remain distinct.

## Consequences

- The active v1.1 study is unchanged and no runtime campaign state is read.
- The existing LossSpec registry and evaluation split are unchanged.
- Current results can still be interpreted as metric-induced institutional
  differences without overclaiming construct validity.
- Future objective work gains explicit data requirements and adversarial tests.
- Important constructs may remain diagnostics or audits rather than objectives.
- A future composite, if used, is a declared temporary policy choice and not a
  discovered universal optimum.

## Evidence

- [`../objectives/landscape/metric-objective-landscape-v1.md`](../objectives/landscape/metric-objective-landscape-v1.md)
- [`../objectives/catalog/objective-catalog-v1.md`](../objectives/catalog/objective-catalog-v1.md)
- pinned `t46/ai-scientist-survey` commit
  `02b437b854e73f1bd8a274399e56167ee05a4400`; exact files and sections are in
  the machine-readable citation ledger.


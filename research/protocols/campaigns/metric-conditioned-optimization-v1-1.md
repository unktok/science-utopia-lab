# Metric-Conditioned Optimization Study v1.1 amendment

Status: preregistered; freeze only after the repair and artifact-adoption tests
pass on one clean source commit.

This amendment inherits the complete scientific protocol in
`metric-conditioned-optimization-v1.md`. Unless explicitly changed below, the
three LossSpecs, fixed-topology eight-parameter design space, adaptive random
search algorithm and seed, five-suggestion budget, three optimization seeds,
five held-out seeds, common evaluator, report-only policy, analyses, stopping
rules, and simultaneous winner freeze are byte-for-byte unchanged.

## Reason for the new version

Frozen v1 exhausted both attempts for design `d61de1ee4e74b`, seed 607 after a
valid zero-active-author year passed an empty query list into RAG. V1 remains
immutable with eight complete runs and one terminal technical failure. Its
held-out seeds were never consumed.

V1.1 changes two engineering boundaries only:

1. empty retrieval batches return an explicit empty result without invoking
   the embedding or matrix-multiplication paths; and
2. identical initial design-seed trajectories may be adopted across LossSpec
   arms through a content-addressed, read-only provenance relation.

The zero-query repair does not assign a loss or penalty. It permits the
simulator to record the scientifically meaningful zero-submission trajectory,
which the frozen LossSpec then evaluates normally.

## Evidence isolation

No v1 artifact is an optimization observation in v1.1. All v1.1 physical
artifacts must be produced from the single source commit frozen for v1.1.
Cross-version adoption is forbidden.

The participation/review arm is the canonical physical producer for the first
three byte-identical suggestions. After its nine initial physical runs are
terminal and valid, the topic-diversity and review-burden arms may adopt those
artifacts only if the adoption API proves all of the following:

- target is planned at attempt zero;
- source is a terminal, technically valid, independently executed run;
- source commit, normalized producer command, design JSON, fidelity, seed,
  model/backend, dataset identity, and scientific configuration agree;
- an immutable bundle receipt enumerates and hashes every admitted raw file;
- the bundle contains no symlink and still verifies byte-for-byte;
- the logical-to-physical link records source attempt/scheduler provenance;
- arm-specific derived evaluations are written only under the logical arm;
- executed and adopted logical runs are reported separately.

Adoption is common-random-numbers reuse, not three independent replications.
The optimization budget remains 45 logical runs. Under successful initial
adoption, the expected producer budget is 27 physical simulations: nine common
initial trajectories plus eighteen arm-specific adaptive trajectories.

If any identity or bundle check fails, do not copy, link, rewrite, or mark the
target complete. Execute that logical target normally from the same pinned
commit instead.

## Execution order

1. Freeze and tag the tested repair/adoption source commit; create a clean,
   detached experiment worktree from it.
2. Initialize all three v1.1 campaigns and verify byte-identical first three
   suggestions and zero held-out rows.
3. Execute the participation/review arm's nine initial physical runs.
4. Seal and verify their bundle receipts; adopt them into the other two arms;
   independently evaluate each logical arm under its own LossSpec.
5. Generate and execute suggestions four and five independently for each arm,
   observing all three optimization seeds after each suggestion.
6. Audit 45 terminal logical runs, physical/adopted lineage, failures,
   runtimes, clean source provenance, and the held-out firewall.
7. Simultaneously freeze all three winner fingerprints. Do not create the
   held-out registry during the optimization-stage goal.

## Completion gate

Optimization v1.1 is complete only when every arm has exactly five observed
suggestions, all 45 logical runs are terminal with explicit execution or
adoption provenance, no protected seed appears in an optimization registry,
all bundle receipts verify, and one immutable winner fingerprint per arm is
sealed in the same study-level freeze.

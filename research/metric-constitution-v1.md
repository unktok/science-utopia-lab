# Metric Constitution v1

Status: draft for implementation and empirical revision  
Scope: ScienceUtopia institutional-design experiments  
Machine-readable contract: [`specs/metric-constitution-v1.schema.json`](specs/metric-constitution-v1.schema.json)  
Minimal instance: [`specs/example-metric-constitution-v1.json`](specs/example-metric-constitution-v1.json)

## 1. Purpose and constitutional stance

This constitution defines what an optimization run is allowed to optimize, what it must preserve, how evidence is attributed, and which comparisons are not legitimate. It is an experiment contract, not a declaration that scientific value has been reduced to one number.

ScienceUtopia must not treat “national benefit,” publication count, citations, novelty, acceptance rate, or any other observable as a universal welfare function. A government is one legitimate stakeholder and mission-setter, but not the sole utility-bearing subject. Researchers, affected communities, publics, research institutions, infrastructure providers, the international knowledge commons, future generations, and the environment may each have standing. Their interests may conflict and must remain visible.

The constitution therefore adopts five default rules:

1. Hard constraints are non-compensable: gains elsewhere cannot purchase permission to violate them.
2. Capabilities needed for future inquiry, criticism, correction, and recovery are protected before commitment-specific performance is optimized.
3. Objectives are attached to explicit commitments, stakeholders, time horizons, and validity domains. They are not silently promoted to universal scientific value.
4. Evaluators, decision policies, allocators, appeals, and correction mechanisms are versioned and governed separately.
5. Results are reported as a constrained, distribution-aware vector. Scalarization is exceptional, local, declared, and temporary.

“Unknown,” “not yet measurable,” and “failed” are distinct states. Missing measurement is never interpreted as constraint satisfaction.

## 2. The four-layer objective architecture

The layers are ordered. A later layer cannot override an earlier one.

### Layer 1 — Constitutional hard constraints

Hard constraints protect rights, epistemic integrity, safety, and legitimate process. Examples include prohibitions on fabrication or coercion, minimum due-process requirements, unacceptable concentrated harm, and minimum integrity or evaluation coverage.

Every constraint declares:

- the normative claim and protected stakeholders or slices;
- an observable metric or an explicit measurement gap;
- threshold, evaluation scope, uncertainty policy, and failure action;
- why the constraint is non-compensable;
- whether current evidence can establish `pass`, `fail`, or only `unknown`.

Honest error must not be conflated with deception. A negative or incorrect finding can remain epistemically valuable if provenance, uncertainty, and correction are intact. Conversely, a high-impact or highly cited output does not compensate for fabrication.

### Layer 2 — Capability preservation

The system must preserve the capacity to produce, challenge, reproduce, correct, and redirect knowledge in the future. Relevant capabilities include independent challenge capacity, methodological and topic diversity, retained expertise, correction and rollback capacity, evaluation capacity, infrastructure, exploration reserves, and researcher sustainability.

A capability may be represented as a floor, reserve, stress-test requirement, or recovery-time objective. Capability loss can be slow, path-dependent, and hard to observe; each declaration therefore names its time horizon, recovery or rollback expectation, and stress scenarios. Short-run efficiency cannot silently consume long-run capability.

### Layer 3 — Commitment-specific objective vectors

Optimization occurs within named commitments. Supported commitment types include exploratory inquiry, confirmatory work, formal/software verification, public missions, commons maintenance, and capability building. Each commitment declares owners, intended beneficiaries, burden bearers, validity scenarios, expiry or review conditions, and a vector of objectives.

A mission objective is a political and institutional commitment, not ground truth about the value of science. A commitment can use lexicographic ordering, Pareto comparison, or epsilon constraints, but must retain the underlying vector and stakeholder distributions. Its weights, if any, do not automatically transfer to another commitment, jurisdiction, or time period.

### Layer 4 — Objective-and-evaluator governance

Metrics and evaluators change behavior and distribute authority. They therefore require governance rather than being treated as neutral instruments. The constitution records who may propose, approve, audit, appeal, revise, or retire them; how conflicts of interest are disclosed; which decisions an evaluator may inform; and how invalidated results propagate to downstream decisions.

Evaluation, decision, allocation, appeal, and correction are distinct functions. One actor or model may perform more than one function only when the overlap is disclosed and specifically authorized. Appeal must have an independent route. Corrections must update affected downstream artifacts and decisions where practicable.

## 3. Stakeholder standing and distributional slices

Each stakeholder entry specifies its standing: beneficiary, burden bearer, voice, proposer, approver, appellant, auditor, or metric subject. A protected stakeholder cannot disappear merely because its outcomes are difficult to measure.

Aggregate means must be accompanied by declared slices where distributional effects could matter. Candidate slicing dimensions include career stage, institution and resource level, geography, topic, agent type, demographic attributes, generation, and exposure to a mission's benefits or harms. The relevant dimensions are context-specific; the constitution does not require identity attributes where collecting them would be unsafe or illegitimate.

For every decision-active metric, the reporting layer must state:

- which slices were evaluated;
- sample support, missingness, and uncertainty per slice;
- whether aggregation masks a threshold breach or sign reversal;
- which stakeholders bear costs and which receive benefits;
- whether future generations, the global knowledge commons, or environmental effects are represented directly, by proxy, or not at all.

If a protected slice lacks adequate support, its state is `unknown`; it is not pooled away by default.

## 4. Evaluation unit and lineage

The default evaluation unit is:

`subject × claim × artifact version × autonomy slice × evaluator relation/version × decision-policy version`

Decision-active observations must preserve, at minimum:

- `subject_id` and `claim_id`;
- `artifact_id` and immutable `artifact_version`;
- `run_id` and `autonomy_slice`;
- `evaluator_id`, `evaluator_version`, and evaluator relation;
- `decision_policy_id` and `decision_policy_version`;
- constitution ID/version and metric ID/version;
- timestamps and parent/supersession links where applicable.

Evaluator relation is substantively important, not metadata decoration. The permitted vocabulary includes `self`, `same_producer`, `external`, `independent`, `instrument`, and `formal_kernel`. Self- or same-producer evaluation may be useful diagnostically but cannot be silently presented as independent validation.

Goal custody is also recorded across `generate`, `select`, `revise`, `stop`, and `release`. This permits analysis of autonomy and authority even when two systems produce similar artifacts.

Historical runs retain the exact constitution, metric, evaluator, and decision-policy versions used. A newer version never rewrites the meaning of an old result.

## 5. Metric contract

Every registered metric has a versioned card in the machine-readable constitution. A metric entry declares:

- the construct it claims to represent and its role (`constraint`, `objective`, `diagnostic`, `shadow`, or `governance`);
- the observable, formula, unit, data sources, time horizons, and applicable stakeholder slices;
- evaluator and uncertainty model;
- validity status and evidence;
- authorized and prohibited uses;
- known proxy risks and plausible gaming strategies;
- shadow or counter-metrics;
- owner, review trigger, and expiry.

The measurement chain is explicit:

`value claim → construct → observable → metric → evaluator → decision policy → allocation/action`

Evidence for one link does not validate the whole chain. Predictive validity is not causal validity; construct validity does not prove that optimization improves public value; a stable formula does not imply a stable behavioral response.

The current harness metrics—topic entropy, lexical novelty, conditional retention, survival equity, burden, integrity checks, evaluation coverage, and activity—remain provisional diagnostics or engineering constraints unless stronger validation is supplied. They must not be relabeled as truth, social value, reproducibility, or welfare.

## 6. Proxy validity and Goodhart auditing

Any metric used for selection, ranking, funding, release, or stopping becomes a target and must receive stronger scrutiny than a descriptive diagnostic. A decision-active metric needs:

1. a validity claim bounded by population, scenario, and time;
2. at least one shadow or counter-metric when feasible;
3. a gaming hypothesis and manipulation test;
4. subgroup and distributional checks;
5. a review cadence and event-triggered reauthorization;
6. a response plan: warn, quarantine, suspend optimization, recalibrate, retire, or roll back.

The audit registry can cover proxy–construct drift, gaming elasticity, target-substitution lag, metric half-life, evaluator-error correlation, holdout degradation, subgroup harm, decision concentration, allocation diversity, rule-authority concentration, and recovery time after a metric is withdrawn.

Goodhart risk is a property of a metric-in-use, not just a formula. The same observable can be a low-risk diagnostic and a high-risk allocation target. Audit intensity therefore depends on decision power, optimization pressure, observability to agents, and reversibility of harm.

## 7. Aggregation boundary

The default report is a constrained vector with uncertainty and distributions, not a single score. Reports must preserve:

- every hard-constraint state and measurement gap;
- capability floors, reserves, stress-test results, and recovery indicators;
- the commitment-specific objective vector;
- stakeholder-slice distributions and missingness;
- time-horizon-specific results;
- seed/run distributions rather than only a pooled mean;
- shadow metrics, evaluator disagreement, and Goodhart audit findings.

Permitted aggregation methods are Pareto comparison, epsilon constraints, lexicographic ordering, scenario dominance, and declared transient scalarization. Transient scalarization may be used inside a search procedure for candidate acquisition only if the full vector is retained, weights and provenance are logged, sensitivity is reported, and the scalar expires with the run. It must not be named or reported as “scientific value,” “social welfare,” or “national interest.”

The following compensation is prohibited by default:

- a hard-constraint violation offset by any benefit;
- severe harm to a protected slice offset by average gains elsewhere;
- destruction of future corrective capacity offset by short-run throughput;
- missing evidence converted to a favorable score;
- a state mission score treated as the utility of all stakeholders.

Cross-stakeholder or cross-time compensation requires an explicit, contestable authorization in the relevant commitment, and never applies to constitutional hard constraints.

## 8. Run lifecycle

For each experiment:

1. Validate the design and constitution schemas; freeze their versions and hashes.
2. Declare commitment, stakeholder standing, slices, time horizons, and evaluator versions before looking at comparative results.
3. Execute simulations and retain event-level lineage.
4. Evaluate hard constraints. `fail` makes the candidate infeasible; `unknown` triggers the declared uncertainty policy.
5. Evaluate capability preservation, including relevant stress or recovery tests.
6. Compare feasible candidates on the commitment-specific vector and stakeholder distributions.
7. Run scheduled and trigger-based proxy/Goodhart audits.
8. Apply the versioned decision policy, preserving evaluator disagreement and appeal paths.
9. Publish a report that includes limitations, unmeasured constructs, and the exact constitutional snapshot.

Optimization code may propose candidates; it does not have authority to redefine the constitution during a run.

## 9. Minimal implementation boundary

The JSON Schema verifies document shape, required governance declarations, enums, and many local invariants. It cannot establish referential integrity between IDs, prove that a metric measures its construct, determine independence in fact, or evaluate normative legitimacy. Those require a semantic validator, audit evidence, and institutional review.

The minimal example is deliberately modest. It treats harness integrity as a hard constraint, researcher participation as one capability proxy, and sustainable exploration as an exploratory commitment. It marks topic entropy and survival as provisional rather than claiming that either is scientific value. The example is sufficient to exercise validation, lineage, governance, and aggregation boundaries; it is not a validated objective set for substantive policy conclusions.

## 10. Change control and acceptance criteria

A constitution revision requires a new semantic version and a change record identifying proposers, approvers, affected stakeholders, evidence, migration implications, and rollback conditions. Metric or evaluator changes likewise create new versions. A run can only claim compliance with v1 when:

- all four layers are present;
- stakeholder standing and required slices are declared;
- decision-active evidence is lineage-addressable;
- validity and Goodhart obligations are assigned;
- prohibited aggregation and compensation boundaries are explicit;
- unknown and not-yet-measurable states remain visible;
- the machine-readable instance validates against the v1 schema.

The constitution is intended to be revised through measured failures and stakeholder contestation. Its purpose is not to freeze one account of good science, but to make optimization assumptions legible, bounded, auditable, and reversible.

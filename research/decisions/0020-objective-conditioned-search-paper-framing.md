# Decision 0020: Make objective-conditioned institutional search the paper's center

Date: 2026-10-31

Status: accepted

## Decision

The working paper will be organized around **objective-conditioned black-box
optimization of scientific institutions**, not around another set of fixed
institutional comparisons and not primarily around optimization
infrastructure.

The central empirical map is:

```text
declared objective
    -> sequential search trajectory
    -> frozen SystemSpec
    -> common held-out cross-objective profile
```

The optimization objective is the experimental intervention. The scientific
system is the dependent design object. Technical validity, held-out evaluation
metrics, and any later decision policy remain separate contracts.

## Why this distinction is necessary

The original Suto paper varies investigator-chosen strategies and institutional
conditions and studies their downstream effects. Repeating that pattern with a
few new acceptance, funding, or review settings would use the simulator but
would not establish the intended research program.

Science Utopia Lab instead asks which institution a search procedure discovers
under a declared objective, how the search path changes when that objective
changes, and what trade-offs appear when the resulting systems are evaluated
under common held-out criteria.

| Dimension | Fixed intervention study | Objective-conditioned search |
|---|---|---|
| Intervention | institution chosen before execution | optimization objective |
| Variable produced by the experiment | simulated outcomes | search path and institution |
| Feedback | within simulated world | within-world feedback plus optimizer ask/tell |
| Main result | effect of condition A versus B | objective -> path -> system -> held-out profile |

## Questions the paper should answer

1. Does changing the objective alter the observed search path?
2. Does it alter the frozen institutional design?
3. Do objective-conditioned designs exchange rank under cross-objective
   held-out scoring?
4. In the next experiment, which black-box method reaches better systems per
   simulation budget?
5. Once the runtime supports it, how does the answer change when mechanism
   graph structure rather than eight fixed-topology parameters is searched?

## Claim boundary after v1.1

The completed experiment supports these claims:

- a real Qwen3-8B simulator can participate in a persistent, result-dependent
  black-box loop;
- with simulator, parameter space, optimizer, budget, and seeds held fixed,
  changing the loss can change the frozen design;
- the two distinct frozen designs exhibit descriptive loss-dependent rank
  reversal on the common held-out split;
- technical failures can remain invalid observations without fabricated
  numeric penalties.

It does not yet support these claims:

- that every objective induces a distinct institution;
- that adaptive random search is more sample-efficient than a non-adaptive or
  alternative optimizer;
- that the observed paths or rank reversal are stable under replication;
- that whole mechanism structure has been optimized;
- that any discovered design is a desirable real science policy.

Three objective labels produced only two distinct designs. The topic and burden
arms had only two valid candidates each; their later adaptive proposals were
technically invalid. All nine paired held-out loss intervals include zero.
These facts belong in the main interpretation, not only in a limitations
paragraph.

## Manuscript consequences

- Retitle the paper around objective-conditioned black-box optimization.
- Put an explicit Suto-versus-Lab comparison in the introduction.
- State the objective -> path -> system -> held-out profile map before software
  architecture.
- Move the first engineering loop and game observatory to appendices so they
  support rather than dominate the empirical argument.
- Define the three LossSpecs in the study section.
- Analyze the actual sparsity and invalid regions of each optimization path.
- Treat repeated objective labels that selected the same fingerprint as one
  distinct design when interpreting institutional diversity.
- State explicitly that optimizer effectiveness has not been tested.

## Next evidence-producing experiment

The next optimization experiment should use:

- multiple optimizer seeds;
- a larger valid candidate budget;
- equal-budget random and Sobol baselines, followed by Bayesian and/or
  evolutionary search where the mixed space permits;
- incumbent-loss-versus-evaluation curves;
- parameter or mechanism trajectory visualizations with parent-observation
  lineage;
- design-collapsed held-out analysis;
- a broader, constitution-backed objective family;
- a separate simulator-backed structural campaign once the generic mechanism
  graph runtime is sealed.

This decision changes paper framing and future experimental design. It does not
retroactively alter any frozen protocol, LossSpec, run, winner, or held-out
result.

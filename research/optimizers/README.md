# Optimizer methods

This directory describes how candidate designs are proposed. The method is
separate from both the parameter/design space and the loss being optimized.

Implemented candidate generation:

- random sampling
- Sobol sampling

Not yet implemented as closed-loop methods:

- literal grid enumeration
- Bayesian optimization
- evolutionary or population-based search
- multi-objective/Pareto search
- surrogate-gradient or differentiable optimization

The first milestone is a common `suggest`, `observe`, `state`, and `budget`
interface, not commitment to a single optimizer family.

# Closed planning pilot: optimization incumbent and generated output

These are read-only projections of the already closed14-world planning pilot,
not additional simulations or a replacement for its original audit/selection.
The two actual CLI exports at analysis source
`a61ab4ab6e296b1636e3ad89ad12831a10e11f19` agree on all five files. The
scientific source remains `8cd61578b94d86dd0cf2ff3b0e581d9a2698fc0f`.

- `report.json`: both complete three-slot histories, all reference/own ties,
  original own-only selection and exact losses.
- `paths.csv`: K (best measured reference or own policy) and O (best completed
  own submission) at0,1,2,3 consumed own slots.
- `manifest.json`: original input hashes and four exported file hashes.
- [PNG/SVG figures](../../../paper/figures/native-planning-incumbents-v1/):
  the five-file bundle's two plots are stored separately here in the repository.

T has K=O=-18 after the first own submission. U has
K=O=-13.333333333333332. Both trajectories are flat; generated improvement over
the best measured reference is zero. T retains four tied references and three
tied own policies; U retains one tied reference and three tied own policies.
Before own proposals O is missing, not zero. Including known references in K
does not mean their development cost is zero or that the designer invented them.

The original [data and five mechanism readouts](../native-planning-objective-loop-v1/README.md)
remain authoritative for the closed study. The projection consumes two closed
reports; it does not reexecute a raw audit, change the original selections,
show an independent optimization replication or evaluate unused seeds.
The [verification record](../../results/native-optimization-incumbents-verification-v1.json)
binds the actual exports, test scope, visual inspection and future read-only
continuations separately.

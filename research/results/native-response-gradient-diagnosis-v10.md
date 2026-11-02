# Posthoc v9 gradient diagnosis for v10 method development

No fresh model/native/container calls. All old raw bytes remain unchanged.

| temperature | center gradient | calibration loss RMSE | memory backward contribution |
|---:|---:|---:|---:|
| 1 | -0.2409215939 | 0.5271664749 | 0 |
| 0.2 | -0.0942579723 | 0.3297384961 | -2.7756e-17 |
| 0.05 | 0.01155722212 | 0.01521551529 | 0 |
| 0.01 | 1.148890401e-15 | 1.15620127e-05 | 0 |

Only one of 18 raw review responses has a substantial fitted slope: at theta0.5 its fitted raw score is3.8333333333 and slope1.6666666667. The other17 slopes are approximately2.28e-15 numerical fitting residuals, retained rather than zero-imputed.

At temperature0.01 the individual integer-parse relaxation is nearly flat; the affected paper remains near score3 below the3.25 selection threshold, so the admission gate is also nearly flat. Their product, not recurrent-memory differentiation, suppresses the center gradient. At0.05 the gradient is positive, while at0.2 and1 it is negative. The smooth objective charges publication cost even for fractional acceptance of papers whose score is below that cost; publication-cost and accepted-score utility derivatives compete. Thus a larger gradient need not point in the native-improving direction.

Selecting temperature by calibration loss-value RMSE rewards a nearly hard, locally flat representation. This does not validate the fitted response slope: the varying review is observed as3.5,3.5,4.5 at the three calibration points. A single affine fit moves its crossing earlier; the old unused0.65 failure is not repaired by this temperature diagnosis.

Prospective method recommendation: fix a continuation schedule and step/trust rule before any new model calls; report all stages and gradient signs, retain native reevaluation as the authority, and compare with an equal-budget black-box method using the same historical development data. Do not select a temperature retrospectively by favorable native/unused outcomes.

Actual native source: `fb2d1b6f07aadba39148bd5871dac2fd0595b618`. Operator SHA-256: `2c7e56037ef184a02da01836b07dd8b00caa5969fbd996930f8ff0724ae5ca8a`.
Analysis source: `650d27ef105e15533178557aadc279073952fe4f`. 101 old files checked before/after.

All temperature curves and mixed parser/institution sweeps are offline representation ablations, not native samples or held-out evaluation.

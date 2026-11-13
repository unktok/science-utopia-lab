# Free-design frames exceed the nominal reserved context budget

This is a partial live diagnostic, not a closed U/literal generation or an
isolated causal contrast between presentations. The unchanged writer11716
remains active at scientific source30e3f5fa. Do not adjust its frozen prompt,
model options, loss, budget or failed slots during the experiment.

The [two-frame snapshot](../results/native-parent-presentation-free-frame-capacity-v1.json)
retains exact completed-journal and request-wire hashes for U/literal:g0:

| Completed action | Requested context/output | Reported input/output | Termination and validity |
| --- | --- | --- | --- |
| Step0 | 40960 /8192 | 37658 /8192 | `length`; incomplete output rejected |
| Step8 | 40960 /8192 | 43200 /941 | `stop`; tool-call JSON shape rejected |

Both received HTTP200 and final envelopes, but neither action is valid. The
first has a known length-limited output, not a successful plan or unknown
transport. The second is complete as a provider reply, not valid as a tool
action. These charged actions are not silently repaired or refilled.

The actual wire sizes159602/178049 bytes are within the declared200000-byte
bound. Byte bounds alone do not reserve tokens. The existing
`capacity_observation` diagnostic correctly records `false` because each
reported input plus8192 exceeds the requested40960. The prior28/28 directed
readiness pass therefore does not establish enough room for these free-design
frames. This is additional evidence beyond the different first T/control
empty-marker source mistake; do not merge them into one alleged root cause.

The later reported input count itself exceeds requested `num_ctx`. This does
not establish which tokens, if any, were dropped or that the requested option
is the effective backend limit. No truncation was requested. Nor does the
first output reaching8192 establish context exhaustion as its sole cause;
the declared output limit alone can terminate a long reasoning response.
Inspect actual backend option semantics before concluding that increasing
`num_ctx` would fix it. A larger context/output reservation or lossless removal
of duplicated presentation content would be a separate prospective condition,
not a repair to this live experiment. No such follow-up is dispatched here.

The generation is still pending at this snapshot. Retain completed rows,
partial/unknown costs and final native outcomes separately when it closes.
No scientific gain, loss penalty, new world or publication-readiness claim is
introduced by this diagnostic.

The existing bounded-context regression file subsequently passes10 checks in
23.40s (`outputs/native-parent-free-frame-context-regressions-v1-a1/pytest.xml`).
This includes the already implemented false/unknown/true capacity observations;
it does not prove the actual backend honors a requested context limit.
At the later direct read, the U/literal worker has `submitted:true` after
1172.5243s inside the worker and14 actions. Its native evaluation is still
pending. The two invalid actions therefore did not prevent eventual submission;
do not describe them as a failed entire generation or as its proven sole cause.

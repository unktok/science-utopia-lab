# V34 rejected-history robustness and observed-key diagnostics

While immutable V33 runs, reproduce its throughput G1 host TypeError from the
two actual saved steps under original2a52318: exact transitions agree, then the
next prompt fails with "string indices must be integers, not 'str'". No new
model/world calls or raw-file writes. Separate V34 replay preserves both exact
transitions and rejected action but successfully rebuilds the next prompt
(107151 UTF8 prompt bytes/103013 wire-message bytes). This is a source-change
engineering comparison, NOT a reconstructed original terminal response or
evidence of sufficient measured model token capacity.

SCRIPTED rejected-history tests first fail10/pass2 before the fix, including
string/null/scalar/list/missing-dict operands. Combined field-feedback/history
scope then passes112 in8.86s; JUnit focused-development.xml SHA
a07c650211a4e2119e39103a6f12f41c34417dc77cf60253f773273f28cc2af3.
Preserve last action/error/raw response; only compact earlier-action summaries
become type-safe. Add bounded actual-key diagnostics to atomic field failures;
no selected policy/value, source repair, new veto or extra calls.

Separately, the test-only corrected V33 goldens full suite17018 passes2838/
six skips in1462.98s. JUnit full-53f2499.xml SHA
066f8367967a0aa21b7749ab9f61cff7ac8fe4c4a9d57fb599b63d8dec543722.
Runtime/scripts at53f2499 are byte-identical to actual frozen2a52318. The latter's
original2836-pass/two-golden-failure result remains preserved, not relabelled.

Expanded changed-code/accounting scope58933 passes122/one skip in16.54s,
JUnit expanded-development.xml SHA
90d9797937d6941040c9744528f65808c6b8e55c79129f3d54b42988c2dd9fbf.

All376 former V33 focused checks plus both new modules/accounting pass420/
one skip in67.83s (81328), focused-complete-development.xml SHA
4778d62f54776f6dea2c0456eee43ab22a1aaf0412ea0cca73be9be659549284.
The wider optimization-only suite7008 runs independently; no full-source pass
is inferred before its actual exit.

The separate read-only component diagnostic also replays the already-closed
V31's original c62 native worlds, exact author steps/transport and terminal
definitions without new calls or file changes (development21762 exits0). It
explicitly excludes full queue/UI audit claims; its identity is
4d038a72ce35602c65c2c633af99689567315f577d450fc5500a5c39353a7c66.
The V33 missing-terminal source-exception path still requires actual closure.

Read-only actual V33 G0 comparison finds all97 full scientist wire rows equal
across throughput world native-adaptive-30ea229ef1133fba6dfa9389-s42 and
efficiency world native-adaptive-6bb2aca16a6c6bbfc677a7af-s42. Both raw wire files
have SHA370b51d6371fd0aabaec86d5b5a0d59924f68d2c61c51a76a745e942a12a3e47.
Unlike the earlier94/97 cross-clock result, this is actual same-source97/97
input invariance with independent execution clocks. It is not institutional
invention, a candidate loss improvement or a cross-source causal comparison.

At the above development entries V33 remains live; no actual V34 inference or
new functional institution is claimed. Follow the prospective V34 protocol and
keep the unchanged original goal active, rather than handing off at engineering
gates.

## Forward closure and actual V34 continuation

V33 subsequently exits0 at00:52:11.310706Z, four slots consumed. Both unmodified
original-source full audits fail on its missing throughput G1 terminal journal.
Both separately identified component diagnostics exit0/cmp0, content
7f91d563da14137d4a155f9d810ba7e6e6d0704d57a367a57369b458076af85c.
The source exception reproduces exactly; the efficiency G1 Python edit fails
in its actual native world with KeyError features. See the closed V33 result;
neither failure is refunded or called a successful institutional invention.

Only after that terminal writer, freeze75da492bcccf7117d89cd0be97bc1c1b2645cdd6
in experiment-native-field-feedback-v34-a1 with matching protocol tag. Source
proof33861 verifies254 blobs. Exact frozen source/focused4042 again verifies254
and passes420/one skip in67.91s, JUnit focused-75da492.xml SHA
2ca121473feb9f22b600d942462ec14c21e359205994b5a2b345abf1bd301090.
Fresh independent actual readiness52284/PID62529 runs the declared same V30
request/provider, max24 controls. It has no native worlds and is not yet a
passing certificate or free-design success. Preserve the frozen source; wait
for its actual terminal status and subsequent loaded40960 gate, then continue
the original-world feedback pilot if eligible. The original goal stays active.

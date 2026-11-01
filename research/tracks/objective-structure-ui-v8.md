# Objective-conditioned native structure UI v8

Status: implementation, byte-exact terminal a2 audit export, and actual-data
browser QA complete.

`game-ui-v2/objective-structure.html` is a local, read-only NOCTILUCA view over
`scienceutopia.native-objective-structure-audit.v8`. It does not start a model,
simulator, optimization campaign, native worker, or adoption.

## Research boundary

The view treats the LossSpec as the fixed condition and the native institution
as the changed object. It keeps the two illustrative development objectives,
every observed candidate path, exact first-best ties, null technical states,
and same-checkpoint cross-scores visible together. Cross-scores retain their
own raw units; an unavailable other-objective score remains `null` with the
audited evaluator reason and is never converted into a penalty.

This is development engineering evidence. Held-out metrics are not defined or
measured, and no promotion policy is defined or applied. The UI does not claim
convergence, causal institutional benefit, scientific value, or a universally
best system. It distinguishes fixed Qwen3:8B researcher weights from the
external, self-reported Codex specialist who authored institution source.

## Fail-closed transport

The actual channel accepts only classification
`actual-native-qwen-objective-structure-development-v8`. A local exporter
copies the independently audited report byte-for-byte and emits a receipt with
the exact file SHA-256 and audit `content_sha256`. The browser verifies the raw
response bytes against that receipt before rendering, then validates the
source commit, campaign accounting, two exact arms, row/loss/selection binding,
candidate SystemSpec shape, literal graph-diff counts, and selected cross-score
matrix. Missing or non-JSON actual artifacts show `WAITING FOR AUDITED EXPORT`;
they do not fall back to a fixture.

Selection is bound to the exact audited observation/suggestion pair. A system
fingerprint remains a structural label only: independent native worlds can
produce the same SystemSpec with different stochastic losses. The UI therefore
does not select, mark ties, choose the initial station, or resolve the selected
cross-score row by fingerprint alone.

The scripted fixture is constructed only for interface development and opens
only with `?fixture=objective-v8`. It is conspicuously labelled
`LABELLED UI FIXTURE` and is rejected by the actual evidence parser.

## Visual model

- The dual-line switchyard shows all objective-conditioned path stations.
- The blueprint stage renders the selected candidate's real SystemSpec nodes
  and connections, highlighting exact added nodes and wires.
- The change ledger and source bay expose node, edge, Python source-body,
  protocol/configuration, and schedule differences versus the generation
  parent rather than substituting labels for structure.
- The signal exchange shows the selected representatives in each raw loss
  coordinate and explicitly marks unavailable cells.
- The failure dock separates generation failure, technical world failure, and
  missing cross-objective measurement.

## Reproduction

After a terminal actual audit has been committed:

```sh
cd game-ui-v2
node scripts/export-objective-structure.mjs \
  ../research/results/native-objective-structure-v8-a2.json
npm test
npm run build
node scripts/verify-objective-structure-browser.mjs \
  --mode=actual \
  --output=screenshots/objective-structure-v8-actual-qa
```

The exporter performs no inference and rejects non-terminal, non-actual, or
misclassified evidence. The browser harness starts only a loopback Vite server
and a clean headless Chrome profile. It rejects every non-GET HTTP request,
page/console exception, HTTP error, horizontal overflow, truth-channel mismatch,
or report/receipt byte-hash mismatch. It writes four captures and a checksummed
browser-QA receipt, then stops both owned processes and moves its temporary
Chrome profile to Trash.

The capture helper is local developer tooling for this macOS machine: Node22+
(built-in WebSocket) and Google Chrome at the standard `/Applications` location
are required. These requirements do not change the browser UI's runtime or
imply a portable cross-platform capture harness.

## Actual a2 receipt

The independently audited terminal report is exported byte-for-byte at
`game-ui-v2/public/data/native-objective-structure-v8-a2.json` with:

- source commit `425ec10396b17df85efdff20bb063b20c33886e5`;
- file SHA-256 `fd25c21dfa4e2e39c37888402513d2f031e9ae1091b74ea44c65ec5ae2e5f945`;
- audit content SHA-256 `e932c88a73fe7fa9e3b70b487d798a1504994e3ae6841c26ff335070cbb2ffff`;
- raw inventory SHA-256 `09ebc9ab788855b20fa954107454d7e4ff3679163a134b82f304ff4907b2b1a9`;
- eight complete physical worlds, 734 physical Qwen3:8B replies, and no
  recorded technical failures.

The throughput development path is `[-9, -9, -10, -10]`; the illustrative net
reviewed utility path is `[0, 0, 0.4833333333333335,
0.4833333333333335]`. The exact throughput representative has matrix row
`[-10, 2.666666666666668]`; the exact utility representative has `[0, 0]`.
These are raw, objective-conditioned development observations—not held-out,
causal, convergence, promotion, or generalized-benefit results.

Actual local browser QA verifies all eight stations are present and defaults to
the exact generation-1 throughput representative rather than the first row
sharing its system fingerprint. The selected blueprint renders 17 actual nodes
and 24 actual edges. Desktop overview, graph, cross-score, and 390×844 mobile
captures pass with zero page/console errors, HTTP failures, non-GET requests,
or horizontal overflow. The checksummed receipt and PNGs are under
`game-ui-v2/screenshots/objective-structure-v8-actual-qa/`.

Fixture QA at the implementation commit:

- 184 Vitest checks pass, including exact-row selection, repeated-fingerprint,
  tie-ordering, and truth-boundary wording checks;
- TypeScript and the Vite production build pass;
- desktop overview, graph, cross-score, and 390×844 mobile captures render;
- the mobile document has `scrollWidth === innerWidth === 390`;
- the browser reports zero page exceptions, console errors, and HTTP failures;
- the missing-actual route displays waiting state with evidence and fatal
  panels hidden.

The fixture screenshots live under `game-ui-v2/screenshots/` and must not be
used as actual experiment figures.

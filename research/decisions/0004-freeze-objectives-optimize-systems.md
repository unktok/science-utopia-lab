# ADR-0004: 目的を固定し、科学システム側を探索する

- Status: Accepted
- Date: 2026-10-25

## Context

この研究で optimizer が変更する対象は科学システムであり、観測後に都合のよい目的へ変更することではない。従来の harness report は参加状況や資金分布を診断できたが、それらをそのまま最適化目的とみなすと、測りやすい値を事後的に目的へ昇格させる危険があった。

また、Metric Constitution が要求する `low-resource-researchers` slice は、現行 artifact だけでは outcome より前に決まる membership と reviewer action を結合できない。run 終了時の資金下位層を使えば値は作れるが、それは outcome-conditioned selection となり、制度比較を歪める。

## Decision

1. 一つの optimization campaign 内では Metric Constitution と objective evaluator を固定し、design `θ` だけを変更する。
2. evaluator は hard constraints、capability constraints、未集約の objective vector を versioned artifact として出力する。
3. v1 は technical integrity、参加継続率、topic entropy、review burden を評価する。活動量や資金残高は診断値であり、自動的に目的へ含めない。
4. required slice の証拠がなければ `unknown` を保持し、aggregate の値で上書きしない。
5. aggregate で既知の threshold failure がある場合、その failure は slice の `unknown` より優先して制約違反とする。
6. Constitution が定める最低 run 数を満たし、必要な制約がすべて `pass` になるまで design の選択・順位付けを承認しない。
7. evaluator output には evaluator version、implementation hash、run manifest hash、scientific config hash、source commit を記録する。

## Consequences

研究の流れは次のように固定される。

```text
system design θ
  -> stochastic simulation trajectory
  -> frozen objective evaluator
  -> constraints + objective vector
```

現行 baseline 2 seed は aggregate objective を測定できるが、protected slice が `unknown` で、最低 5 run にも達していない。そのため `authorized_for_ranking` は `false` である。残りの smoke runs は感度と実装検証には利用できるが、このまま最適制度を主張する証拠にはしない。

次の measurement-complete revision では、outcome より前に定義された resource band と review-action event を記録する。この境界は evaluator 1.1 と `study-v1-smoke.json` で実装した。v0 artifact は evaluator 1.0 の履歴として保持し、異なる evaluator version で再ランキングしない。

## Validation

- optimization tests: 26 passed
- full suite: 600 passed, 6 skipped, 6 known upstream failures
- actual baseline report: evaluator errors 0、ranking authorization false

## Evidence

- `research/specs/example-metric-constitution-v1.json`
- `utopia/optimization/objective_evaluator.py`
- `tests/optimization/test_objective_evaluator.py`
- `research/logbook/2026-10-25.md`

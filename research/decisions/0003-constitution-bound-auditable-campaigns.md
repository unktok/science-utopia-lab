# ADR-0003: 実験campaignをMetric Constitutionと申請conservationへ拘束する

- Status: accepted
- Date: 2026-10-24

## Context

最初のharness runでは、資金申請の初回生成対象26件に対してsemantic retryが多数発生し、最終評価・保存は25件だった。既存のtransport retry統計とrun attempt registryだけでは、この差が正当な`submit=false`、validation failure、重複、または説明不能な脱落のどれかを判別できなかった。

同時に、制度探索を開始する前に、何を制約・能力・目的・診断とするかをrunへ固定しなければ、結果を見た後で評価規則を選ぶ余地が残る。study specificationがdesign spaceだけをhashしても、目的と評価器の変更を別campaignとして識別できない。

## Decision

1. 各資金申請に年内で決定的なtrace IDを与え、`target → generation attempt → validation → evaluation → decision → allocation`をprompt-free JSONLへ記録する。
2. `submit=false`、semantic validationの全retry失敗、重複などを理由付き終端として記録する。説明不能な段階間attritionはintegrity failureにする。
3. harnessはprocess exitとnative manifestだけでなく、integrity reportとfunding application trace summaryも成功条件にする。
4. 各studyはschema-validかつ参照整合なMetric Constitutionを必須とする。その内容hashをstudy revisionへ含め、完全なconstitutionをstudy snapshotへ保存する。
5. Metric Constitutionはhard constraints、capability preservation、commitment-specific vector、evaluator governanceの四層を保持し、global scalarizationと`unknown=pass`を禁止する。

## Consequences

- retry costをharness attempt、request error、semantic invalid attemptへ分解できる。
- 評価前の脱落が制度効果へ混入した場合、candidateを成功runとして扱わない。
- constitution、metric、evaluator、decision policyの変更は新しいstudy revisionを生成する。
- 旧revision `eadef0bb5a` の実行結果はそのまま保存し、新constitutionを持つrevision `6fcbf8bae1`とは混合しない。
- traceは識別子、段階、結果、理由だけを保存し、prompt、proposal本文、model messageは保存しない。

## Validation

- funding validation / sequential / trace tests: 76 passed
- Metric Constitution / harness / trace targeted tests: 17 passed
- full suite: 591 passed, 6 skipped, 6 known upstream fixture failures
- new study plan: 5 designs × 2 exploration seeds = 10 planned runs under revision `6fcbf8bae1`

## Evidence

- [Metric Constitution v1](../metric-constitution-v1.md)
- [Harness](../harness.md)
- [First harness validation](../runs/2026-10-24-harness-baseline-seed101.md)


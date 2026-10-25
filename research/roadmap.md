# 研究ロードマップ

日付はコミットメントではなく、前段階の検証を通過したことを次段階の開始条件とする。

## Phase 0 — 再現可能なローカル基盤（進行中）

成果物:

- Qwen3-8B / Ollama による macOS 実行経路
- ベースライン run、manifest、数値レポート
- 研究憲章、ログ、実験テンプレート
- upstream と研究 fork の分離

完了ゲート:

- 同一設定の再実行と checkpoint が動く
- 設定・出力・コード revision がrun単位で追跡できる
- 既知の環境差と未解決テストが記録される

## Phase 1 — 測定と最適化 harness

成果物:

- 設計変数 registry
- objective / constraint の metric cards
- seed を束ねる run registry
- random と Sobol の探索 baseline
- runtime、分散、failure rate の測定

完了ゲート:

- 一つのコマンドで design -> replicate runs -> report が生成される
- 5〜8変数の小規模探索を再現できる
- 未使用 seed で候補を再評価できる

## Phase 2 — Evaluation System API

成果物:

- `LegacyPeerReviewEvaluation`
- 型付き機構 interface と contract tests
- 少なくとも一つの代替評価機構
- 現行挙動との regression comparison

完了ゲート:

- simulator 本体を分岐せず評価機構を交換できる
- decision provenance と resource effect を追跡できる

## Phase 3 — 多目的ブラックボックス制度探索

成果物:

- Bayesian / evolutionary / multi-fidelity baseline
- Pareto front と robustness report
- Goodhart / adversarial stress suite
- 最初の研究報告または論文草稿

完了ゲート:

- random search と同予算で比較できる
- 選ばれた制度が未使用 seed と環境 shift で検証される
- 改善だけでなく代償と失敗範囲を説明できる

## Phase 4 — 微分可能な評価機構

成果物:

- 連続緩和された評価・配分機構
- differentiable surrogate
- gradient / ES / black-box の比較
- gradient fidelity 診断

完了ゲート:

- surrogate 上だけでなく真の simulator 上で改善を確認する
- 勾配近似が壊れる条件を特定する

## Phase 5 — 科学システム構造探索

成果物:

- mechanism graph schema
- publication / funding / governance の分離
- 構造とパラメータの共同探索
- 複雑さと性能の trade-off

## Parallel Track — Game vertical slice

Phase 1 の canonical event schema を利用し、read-only replay viewer を作る。その後、checkpoint から制度を変更して branch できる interactive prototype へ進む。研究 core とUIの二重実装は禁止する。

## 直近の次の3項目

1. **完了:** v1で最大のstress caseだったbaseline seed 113をv2で1本だけfull実行し、funding conservation・objective・reliability gateをend-to-end検証した。
2. **進行中:** 参加継続率のceiling effectに対し、4年・10人のlongitudinal fidelityとfloor/ceiling gateを事前定義した。baseline seed 113で測定可能性を検証する。
3. longer-horizon gate通過後にv2 baselineの反復を揃え、候補designを同じseed束で比較し、slice分布を保持したPareto/lexicographic analysisへ進む。


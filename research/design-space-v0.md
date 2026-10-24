# Design Space v0 — 評価・資金制度の小規模探索

## 位置づけ

v0 は、最良の科学制度を結論するための探索空間ではない。現行 simulator で実際に変更できる変数を使い、design validation、複数seed実行、測定、optimizer比較、held-out評価が正しく機能するかを確かめるための最初の benchmark である。

機械可読な定義は [`specs/design-space-v0.json`](specs/design-space-v0.json)、有効な候補例は [`specs/example-design-v0.json`](specs/example-design-v0.json) に置く。

## 設計変数

| ID | 型・範囲 | 現行実装への写像 | 制度的な意味 |
|---|---|---|---|
| `acceptance_rate` | continuous `[0.10, 0.50]` | 各年同値の `--acceptance_rate_schedule` | 評価後に通過させる割合 |
| `reviews_per_paper` | integer `[1, 5]` | `--reviews_per_paper` | 一成果あたりの評価量 |
| `reviewer_capacity` | integer `[1, 8]` | `--reviewer_capacity` | 一評価者が一年に負える上限 |
| `reviewer_matching` | `random \| topic` | `--reviewer_matching` | 評価者を無作為または専門適合で選ぶ |
| `review_policy` | `persona \| standardized` | `--review_policy` | 評価者固有文脈を使うか、共通規則を使うか |
| `funding_budget_slots_frac` | continuous `[0.10, 0.50]` | `--funding_budget_mode fixed --funding_budget_slots_frac` | 初期研究者数に対する年次資金枠 |
| `funding_application_cost` | integer `[0, 20]` | `--funding_application_cost` | 資金申請が消費する資源 |
| `resubmission_cost` | continuous `[0, 20]` | `--resubmission_cost` | 却下後に再評価を受ける費用 |

`acceptance_tiebreak=seeded`、`acceptance_mode=rate`、`funding_budget_mode=fixed` は比較可能性のためv0では固定する。構造探索ではなく、既存構造内の混合変数探索である。

## 固定 context と fidelity

共通 context:

- Qwen3-8B / Ollama
- `university_only` population
- 一機関5研究者
- RAGはCPU
- resource ledger と funding application log を有効化
- 同じ dataset revision と開始年

予定する fidelity:

| Level | 機関 | 研究者 | 年 | 会議 | 用途 |
|---|---:|---:|---:|---:|---|
| smoke | 2 | 10 | 1 | 1 | schema、失敗、最低限の活動確認 |
| screen | 4 | 20 | 2 | 多数候補の粗い比較 |
| confirm | 12 | 60 | 5 | 選択済み候補の長期・未知seed評価 |

実行時間を測定してから規模を再決定する。fidelity間の順位相関が低い場合、smoke結果による早期打ち切りは行わない。

## v0 の暫定signal portfolio

単一の重み付き和は定義しない。次はoptimizer pipelineを検証する暫定signalであり、科学的価値の最終目的ではない。Science of Science調査を受け、noveltyとresource equalityは無条件の単調最大化から外す。

1. topic breadth AUC — provisional maximize / diagnostic
2. submission novelty distribution — observe as portfolio, not monotonic
3. active researcher retention — maximize subject to activity and autonomy diagnostics
4. resource distribution — minimum floor + diagnostic, not equality maximization
5. review burden — minimize subject to evaluation coverage

採択数・採択率・review score は診断値に留める。これらを直接最大化すると、制度変数自身で容易に操作できるためである。定義と弱点は[Metric Cards v0](metric-cards-v0.md)に記録する。

目的アーキテクチャの正式な判断は[ADR-0002](decisions/0002-objective-architecture.md)、根拠は[Science of Science調査](literature/science-of-science-objectives.md)と[`ai-scientist-survey`調査](literature/ai-scientist-survey-objectives.md)を参照する。

## 必須制約

- simulation integrity checks がすべて通る。
- resource ledger がreconcileする。
- LLM transport error と未解決responseがない。
- 各投稿に少なくとも1件の有効なreviewがある。
- 年次活動が完全に停止した候補は infeasible とする。

活動量などの数値thresholdは、恣意的に置かず初期Sobol sampleからcalibrationする。

## 探索・評価の分離

- **Exploration seeds:** 空間の探索とoptimizer fittingに使用
- **Selection seeds:** Pareto候補の絞り込みに使用
- **Confirmation seeds:** 最終候補を一度だけ評価

同じ応答cacheを異なる制度間で共有すると、制度が変えたpromptや状態に不正な対応を再利用しうる。cacheはscientific binding単位で分離し、同一design・同一seedのfailure recoveryにのみ使う。

## v0 で主張できないこと

- 高いnoveltyやdiversityが真に高品質な科学であること
- Qwen3-8B内で良い制度が、人間社会または別モデルでも良いこと
- 1〜2年fidelityの順位が長期結果を保存すること
- simulatorで未表現の政治・倫理・教育・実験設備などを含む制度最適性


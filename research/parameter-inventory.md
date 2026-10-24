# 現行パラメータ棚卸し

2026-10-24 時点のCLIとglobal configを、制度設計上の役割で分類した。単に変更可能であることと、optimizerへ渡すべきことは同じではない。

## v0 で最適化する変数

| Parameter | Current interface | Classification |
|---|---|---|
| acceptance rate | `--acceptance_rate_schedule` | evaluation threshold/capacity |
| reviews per paper | `--reviews_per_paper` | evaluation effort |
| reviewer capacity | `--reviewer_capacity` | evaluator labor constraint |
| reviewer matching | `--reviewer_matching` | assessor selection |
| review policy | `--review_policy` | assessment rule |
| funding slots | `--funding_budget_slots_frac` | resource capacity |
| application cost | `--funding_application_cost` | access/friction cost |
| resubmission cost | `--resubmission_cost` | feedback/retry cost |

## v0 では固定する制度変数

| Parameter | Current interface | v0 decision |
|---|---|---|
| acceptance mode | `--acceptance_mode` | `rate`; `fixed_slots`は人口・成長実験で後に扱う |
| acceptance tie-break | `--acceptance_tiebreak` | `seeded`; submission order由来の偏りを避ける |
| score representation | `--review_score_mode` | `float`への変更はreview-policy効果と交絡するため初期値を固定 |
| funding budget mode | `--funding_budget_mode` | `fixed`; 申請数にbudgetが追随する内生性を切る |
| funding allocation amount | `--funding_allocation_mode` | `fixed` |
| panel size | `--funding_panel_max_apps` | 固定; scaleとprompt-contextの問題として別実験にする |
| weighted allocation | `--weighted_funding_assignment` | off; allocation semanticsの別機構候補 |
| resubmission enabled | `--disable_resubmission` | enabled; v0ではcostだけを動かす |

## 将来の制度・構造探索へ送る変数

| Area | Parameters / implementation | Reason deferred |
|---|---|---|
| publication output | `--papers_per_project`, `--production_cost_mode`, `--project_production_cost` | 評価以前のproduction mechanismを変える |
| funding conservatism | `--funding_intervention`, novelty penalty config | 現状はbinary toggleとglobal configが分離している |
| citation incentive | `--citation_intervention`, `lambda_citation` config | 長期horizonが必要 |
| population influx | `--annual_influx_rate` | 現状は0または特定の0.1 scheduleのみ |
| researcher composition | `--strategy_mix` | 制度よりpopulation/contextに近い |
| collaboration | `--collaboration_mode`, `--collaboration_network_growth_mode` | network mechanismとして独立抽象化する |
| industry funding | `--industry_funding_mode` | university-only v0では非該当 |
| initial resources | `--initial_funding` | environment robustness軸として層別化する |
| evaluator identity | 現状はreviewer agentsとpromptへ埋め込み | Evaluation System APIで構造化が必要 |
| evaluation presence | 現状はphase 3/4が必須 | mechanism graph化後に有無を探索する |
| publication/government | 未実装 | 新しいmechanism primitiveが必要 |

## 環境・fidelityとして扱う変数

- `--num_years`
- `--num_institutions`
- `--researchers_per_institution`
- `--num_conferences`
- `--start_year`
- dataset revision
- model、model revision、prompt version

これらは制度候補 `θ` へ混ぜず、fidelityまたはrobustness context `c` として記録する。

## 実行上の変数であり、科学的設計ではないもの

- API backend、endpoint
- batch size、retry count、timeout
- RAG device、tensor parallel、GPU memory utilization
- cache/output/log directory
- checkpoint resume、start phase
- debug、verbose、W&B

これらが結果へ影響しないことは検証対象だが、制度optimizerの探索変数にはしない。backendやmodelが結果を変える場合は、制度ではなくmeasurement environmentのshiftとして報告する。

## global configに残る未露出パラメータ

conference annual cost、paper production threshold/cost、funding rates、citation candidate count、exploration quantilesなどは `SIMULATION_CONFIG` に存在する。実験ごとにglobal mutable configを書き換える方式はprovenanceと並列実行に弱いため、探索対象へ追加する前に明示的なtyped configurationへ移す。


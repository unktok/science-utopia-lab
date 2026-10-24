# Metric Cards v0

> **Status:** pipeline validation用の暫定proxy。Science of Science調査後、これらを科学的価値の最終目的とは扱わない。各directionはharnessを検証するための仮置きであり、Metric Constitution v1で置換または制約化する。

## MC-01 Topic Breadth AUC

- **Role:** provisional breadth signal; harnessではmaximize、科学的価値としては診断
- **Question:** 研究コミュニティが一部のtopicへ収束せず、複数方向を探索しているか。
- **Definition:** 各年の `topic_entropy_normalized` を時間について台形積分し、観測期間で割る。1年runではその年の値。
- **Source:** `ecosystem_year.parquet`
- **Replication:** seedごとに算出し、seed分布を比較する。
- **Known gaming:** 無意味にtopic labelを分散させても上がる。深さ、正確性、成果量を保証しない。
- **Checks:** `occupied_directions`、submission activity、方向選択fallback率を併記する。

## MC-02 Submission Novelty Median

- **Role:** diagnostic portfolio signal; 単調最大化しない
- **Question:** 制度下で生まれる研究案が、埋め込み空間上で既存・過去方向からどれだけ離れるか。
- **Definition:** accepted/rejectedを問わず、全新規投稿の `novelty_score` のseed内中央値。年別値も保存する。
- **Source:** `paper.parquet`
- **Replication:** seedが単位。投稿を独立replicateとして扱わない。
- **Known gaming:** embedding距離は科学的価値ではない。無関係・支離滅裂な研究も高得点になりうる。embedding model依存。
- **Checks:** review score、distance bucket、topic breadth、将来citationを診断として見る。

## MC-03 Active Researcher Retention

- **Role:** provisional sustainability signal; activity / autonomy条件付き
- **Question:** 制度が研究参加を持続可能にしているか。
- **Definition:** 最終年のactive founder researchers / 初期founder researchers。influxを導入した場合はcohort別生存へ変更する。
- **Source:** `agent_year.parquet` または checkpoint agent state
- **Known gaming:** 全員を低生産性のまま温存しても高い。研究成果を保証しない。
- **Checks:** submissions per active researcher、resource balance、attrition reasonを併記する。

## MC-04 Resource Equity AUC

- **Role:** distribution diagnostic / minimum-floor候補; 完全平等を単調最大化しない
- **Question:** 研究資源が少数へ過度に集中していないか。
- **Definition:** 各年の `1 - funding_gini` を時間平均する。
- **Source:** `ecosystem_year.parquet` と resource ledger
- **Known gaming:** 全員を等しく貧しくしても最大になる。必要な差や成果との関係を無視する。
- **Checks:** total resources、下位10% balance、zero-resource count、成果効率を併記する。

## MC-05 Review Burden

- **Role:** provisional cost objective; evaluation coverageとerror detectionを制約にしてminimize
- **Question:** 評価制度が研究コミュニティへどれだけの査読負担を課すか。
- **Definition:** total valid reviews / active researcher-year。補助値として reviews / submission と最大reviewer loadを保存する。
- **Source:** checkpoints、review assignment audit、`release` summary
- **Known gaming:** reviewをゼロに近づければ低下するが、評価品質も失われる。
- **Checks:** 各投稿1review以上をhard constraintとし、review disagreement、decision stabilityを診断する。

## Constraints

### MC-C01 Integrity

- 全年の `integrity_checks.json` がpass。
- resource ledgerがreconcile。
- non-finite resource、重複paper、未来citation、self-loopがない。

### MC-C02 Valid evaluation coverage

- 各submissionに少なくとも1件のvalid review。
- parser fallback、validation fallback、transport failureを別々に記録する。
- fallback率thresholdは初期calibration後に固定する。

### MC-C03 Minimum activity

- 少なくとも一つのsubmissionと一つのdecisionがある。
- screen/confirmでは年次activity floorを初期sampleに基づき追加する。

## Diagnostics, not objectives

- acceptance rate / accepted paper count
- mean and variance of review scores
- reviewer disagreement and maximum load
- citation edges, citation Gini, self-citation
- accepted-paper novelty
- total resource stock and resource consumption by category
- wall-clock、LLM call count、retry、parse fallback

## Major measurement gap

現行系には、仮説の真偽、実験の再現成功、社会的有用性といった外部ground truthがない。したがって、v0 objectivesのPareto改善を「科学の改善」と呼んではならない。Phase 1中に、hidden truthを持つsynthetic task、再現イベント、またはoutcome verifierの導入可能性を別研究課題として設計する。

また、国家の科学政策で使われる生産性、引用、特許、重点分野、経済効果などは候補observableであって、社会全体の効用そのものではない。[科学政策としての目的設定](science-policy-frame.md)に従い、stakeholder valueからmetricまでの翻訳と、研究の自律性などhard constraintの扱いを分離する。


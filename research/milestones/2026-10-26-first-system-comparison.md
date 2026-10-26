# Milestone 1 — 再現可能な制度比較基盤と最初の5-seed比較

**期間:** 2026-10-24〜2026-10-26

**到達点:** ScienceUtopiaをローカルで再実行する段階から、目的と制約を固定し、
二つの科学制度を同一の5 worldsで監査可能に比較する段階まで進んだ。

## Executive summary

このマイルストーンでは、ScienceUtopiaを「LLMエージェントのデモ」から
「科学制度を設計変数として比較・最適化する研究基盤」へ移行する最初の一巡を
完了した。

主な成果は次の四つである。

1. Apple Silicon上でQwen3-8Bを使う再現可能なローカル実行経路を構築した。
2. 科学システムの良さを単一スコアへ早期に圧縮せず、hard constraints、
   capability preservation、未集約objective vector、評価器統治からなる
   Metric Constitutionを実装した。
3. 複数seed、checkpoint、retry、provenance、integrity、funding reliability、
   protected sliceを扱う制度比較harnessを構築した。
4. 資金配分枠30%のbaselineと50%の候補を、同じ5 exploration seedsで比較した。

最初の比較では、候補制度は平均で全体参加率を0.08、初期低資源層の参加率を
0.16高め、active researcher-stepあたりの査読負担を全体で0.122、低資源層で
0.208減らした。一方、各worldでgrant incomeが160、資金配分が8件増えた。
したがって観測されたのは、追加資源と引き換えに参加継続を改善する
**resource-for-continuity trade-off**であり、無条件の制度優位ではない。

baseline seed 107では低資源層参加率が固定capability floor 0.5を下回る0.4と
なった。このrunは技術的失敗ではなくbaseline制度の帰結だが、事前規則では
全5 runのfeasibilityを正式比較の条件にしたため、formal comparisonは
`incomplete`である。seedの除外、再試行、閾値変更は行わず、5組すべてを
diagnostic evidenceとして保存した。

## 1. 出発点と研究目的

出発点は、論文の公開実装をローカルで動かすことだった。しかし研究目的は再現に
留まらず、ScienceUtopia全体を確率的な制度関数として扱うことへ拡張した。

```text
制度design θ + 環境context c + world randomness ω
                         ↓
             simulation trajectory τ
                         ↓
      constraints + multi-objective measurements M(τ)
```

この枠組みで最適化する対象は指標ではなく制度側である。目的と評価器はcampaign中
に固定し、変更するのは資金、査読、公開、評価、統治などの制度designとする。

長期的な研究線は次の五つに整理した。

- 数値パラメータを対象とするブラックボックス制度最適化
- 査読を一instanceとする交換可能なEvaluation System
- publication、funding、government等を含む科学システム構造探索
- 連続緩和・代理モデル・勾配を用いる微分可能な制度設計
- 同じevent/stateを観察・操作するScienceUtopiaゲーム

## 2. 構築した研究基盤

### 2.1 ローカルQwen3-8B実行

- OllamaのOpenAI互換APIをbackendとして追加した。
- Qwen3-8BのLLM推論をApple SiliconのMetal GPUで実行した。
- unified memoryの安定性を優先し、RAGとembeddingはCPUへ分離した。
- structured output、response cache、checkpoint resumeを実モデルで検証した。
- 最小の有用なworldを2機関、10研究者、1 conferenceと特定した。

これにより、CUDA/vLLMを要求する元経路とは別に、ローカル環境で小規模な制度実験を
繰り返せるようになった。

### 2.2 Seed-replicated experiment harness

制度designと独立worldを機械的に展開し、以下を一つのrun identityへ接続した。

- study specificationとdesign-space revision
- exploration / selection / confirmationの分離seed集合
- SQLite run registryと決定的run ID
- attempt別log、失敗、wall time
- checkpoint resume
- native manifest、integrity report、objective evaluation
- model、dataset、embedding、source commit、source-file hash

process exit 0だけでは完了とせず、manifest、resource ledger、funding traceの整合まで
成功条件にした。探索中の一時的失敗と最終run状態も分離して保存する。

### 2.3 Metric Constitution

国家の単一効用や論文採択数をそのまま目的にせず、次の四層を導入した。

1. **Constitutional hard constraints** — integrity、監査可能性、資源保存など
2. **Capability preservation** — 科学活動へ参加し続けられる最低能力
3. **Commitment-specific objective vector** — 参加、負担、topic breadth等
4. **Objective/evaluator governance** — 定義、version、producer、変更管理

採択数は制度自身が直接操作できるためprimary objectiveにしなかった。topic entropyも
科学的価値とは同一視せず、portfolio diagnosticとして保持した。科学的真理、再現性、
社会的有用性のground truthが現行シミュレータにないことも明示的なmeasurement gapと
して残した。

### 2.4 Protected-slice measurement

平均値が制度の分布的な害を隠さないよう、world開始前に研究者をlower/upper resource
bandへ固定した。終了時の資源分位から対象者を逆算するoutcome-conditioned selectionは
採用していない。

`agent_year`と`review_action`をagent IDで結合し、以下をaggregateと初期低資源層の
双方で測定可能にした。

- active researcher fraction
- review burden per active researcher-step
- supportとevent-count reconciliation

### 2.5 Funding reliabilityとtrace conservation

初期runでは、past paperを持たない研究者にも不正なpaper index例を示すpromptが原因で、
semantic-invalid retryとterminal dropが多発した。これを修正し、資金申請の各段階を
trace IDで接続した。

```text
target → generation → validation → submission
       → evaluation → decision → allocation → resource application
```

semantic invalid、sanitization、request error、agent decline、terminal dropを分離し、
versioned reliability policyを制度比較のadmissibility gateとして導入した。これは
目的指標ではなく、壊れたLLM pipelineを制度効果として最適化しないための境界である。

### 2.6 Longitudinal fidelity

1年smokeでは参加率が全seedで1.0となり、制度間差を測れなかった。低資源研究者が
awardなしでexit境界へ達する最短時点から、4年fidelityを結果を見る前に選んだ。

事前指定したbaseline seed 113では、active researchersが10 → 10 → 10 → 8へ変化し、
最終参加率はaggregate 0.8、低資源層0.6だった。これにより、4年fidelityが参加継続を
観測できることを確認した。

### 2.7 Global reviewer assignment

最初のlongitudinal replicationでは、総reviewer capacityが足りているにもかかわらず、
greedyな割当順序が一部paperのeligible reviewerを先に使い切る問題が発生した。

これをdeterministic capacitated min-cost flowへ置き換えた。新しい割当は、COI、著者除外、
capacity、topic preference、seeded tie-breakを維持しながら、全paperへ最低1 reviewを
与え、その上でtarget review数を最大化する。修正後はbaseline/candidateの全10 runを
同じclean source commitから再実行した。

## 3. 実験プログラムの進展

| 段階 | 目的 | 主な結果 |
|---|---|---|
| 1年local baseline | Qwen3-8B経路の実行確認 | 2機関・10研究者のworldを完走 |
| constitution-bound runs | 設定・目的・traceの接続 | runからdecision/allocationまで監査可能化 |
| 1年baseline 5 seeds | seed分散とprotected sliceの確認 | 参加率ceilingとfunding生成不良を発見 |
| funding reliability probe | prompt修正とgate検証 | semantic invalid / dropを0に削減 |
| 4年baseline pilot | 参加継続を測れるfidelityの校正 | aggregate 0.8、低資源層0.6 |
| repaired baseline 5 seeds | baseline分布の確定 | 5/5完走、1 capability violation |
| funding-capacity candidate 5 seeds | 最初の制度比較 | 5/5完走、全candidate runs feasible |

重要なのは、途中で見つかった失敗を隠さず、新しいrevisionとして再実行したことである。
目的、候補、seed、閾値を観測後に変更していない。

## 4. 最初の制度比較

### 4.1 Research question

4年の小規模ScienceUtopia worldで、年間固定資金枠を初期研究者数の30%から50%へ
増やすと、参加継続は改善するか。その際、査読負担、topic breadth、投入資源はどう
変化するか。

### 4.2 Frozen design

| 項目 | Baseline | Candidate |
|---|---:|---:|
| `funding_budget_slots_frac` | 0.3 | 0.5 |
| その他の制度変数 | 固定 | baselineと同一 |
| Fidelity | 4年、2機関、10研究者、1 conference | 同一 |
| Model/backend | Qwen3-8B / Ollama | 同一 |
| Exploration seeds | 101, 103, 107, 109, 113 | 同一 |

候補は残りbaseline結果を見る前に固定した。scalar welfare scoreは作らず、aggregate、
protected slice、review burden、topic entropyを未集約で比較した。

### 4.3 Execution integrity

- baseline 5 / 5、candidate 5 / 5完走
- 全10 runがfirst harness attempt
- native integrityとresource reconciliationを全runでpass
- funding reliabilityを全runでpass
- aggregate / protected-slice measurementsに欠落なし
- 全runがclean source commit `c9667d7`を使用
- dataset、ordered documents、model、embedding、evaluator、Constitutionをseedごとに照合
- designとexecution argsの差が資金枠だけであることを機械検証

### 4.4 Paired results

全deltaはcandidate minus baselineである。95% intervalはseed 20261025、10,000回の
paired percentile bootstrapであり、5 simulator worldsに対する記述的区間である。

| Metric | Baseline mean | Candidate mean | Mean paired delta | 95% interval | 改善 / 同値 / 悪化 |
|---|---:|---:|---:|---:|---:|
| aggregate participation | 0.800 | 0.880 | +0.080 | [+0.040, +0.100] | 4 / 1 / 0 |
| low-resource participation | 0.600 | 0.760 | +0.160 | [+0.080, +0.200] | 4 / 1 / 0 |
| aggregate review burden | 2.351 | 2.229 | −0.122 | [−0.197, −0.047] | 4 / 1 / 0 |
| low-resource review burden | 2.674 | 2.466 | −0.208 | [−0.349, −0.067] | 4 / 1 / 0 |
| topic entropy | 1.779 | 1.766 | −0.012 | [−0.165, +0.162] | mixed |

査読負担は「低い方が改善」で符号を読んでいる。参加率と査読負担は同じ4 worldsで
改善し、seed 113では同値だった。topic entropyは1 positive、2 zero、2 negativeで、
一方向の制度効果は見えない。

### 4.5 Resource and activity shadows

| Diagnostic | Baseline mean | Candidate mean | Mean paired delta |
|---|---:|---:|---:|
| grant income | 240 | 400 | +160 |
| funding allocations | 12 | 20 | +8 |
| final total resources | 783 | 941 | +158 |
| submitted applications | 103.4 | 102.6 | −0.8 |
| papers | 18.0 | 17.6 | −0.4 |
| reviews | 88.2 | 86.0 | −2.2 |
| acceptances | 9.8 | 9.6 | −0.2 |
| wall time, seconds | 5,067.8 | 5,303.1 | +235.3 |

資金枠の増加は毎年2件、4年間で8件の追加配分に相当する。参加継続の改善には明確な
資源増が伴うため、候補をPareto-dominantとは呼べない。papersやacceptancesは目的では
なく、活動量のshadow diagnosticである。

### 4.6 Formal status

baseline seed 107ではaggregate participation 0.7に対し、低資源層が0.4となった。
Metric Constitutionのcapability floor 0.5を下回るため、このrunは`infeasible`である。

これはintegrity、measurement、funding pipelineの失敗ではなく、baseline制度のもとで
低資源研究者が維持されなかったという観測結果である。しかし事前decision ruleは
「両designに5 admissible runsがあること」を正式比較の条件にした。このため、

- five-pair diagnostic vector: **complete**
- formal comparison / ranking authorization: **incomplete / false**

となる。この緊張は重要な方法論的成果である。capability violationを比較対象から外す
admissibility failureとするのか、制度の悪いoutcomeとして分布に含めるのかを、次の
confirmation protocolで事前に定義する必要がある。

## 5. 現時点で得られた研究上の知見

### 5.1 実証的知見

この小規模な4年worldと5 seedsの範囲では、広い固定資金枠は研究参加、とくに初期
低資源研究者の参加継続を改善する方向を示した。生存する研究者一人あたりの査読負担も
低下した。ただし追加grantが必要で、topic breadthの方向は安定しない。

### 5.2 測定上の知見

- 1年runは参加継続の制度差を測れず、fidelity選択自体が研究設計の一部である。
- aggregateだけでは低資源層の脱落や負担集中を判断できない。
- acceptanceやpaper countは操作されやすく、制度目的としてそのまま使えない。
- LLM生成pipelineの不良は制度効果から分離したengineering gateが必要である。
- capability thresholdには「最低条件」と「outcome」の二つの役割があり、比較規則を
  慎重に設計しなければならない。

### 5.3 システム設計上の知見

- greedyな局所処理は、制度パラメータとは無関係なsimulation artifactを生みうる。
- provenanceはcommitだけでなく、source-file、dataset、ordered corpus、embedding、
  evaluatorまで比較しなければならない。
- objective definitionと制度探索を同時に動かすと、結果に合わせた目的変更になる。
- 技術的feasibility、制度的capability、目的上のperformanceは別々に記録すべきである。

## 6. まだ主張できないこと

このマイルストーンは次を示していない。

- 資金枠50%が現実の科学政策として望ましいこと
- candidateが統計的に有意または普遍的に優れていること
- 論文数、査読score、topic entropyが科学的価値を十分に表すこと
- Qwen3-8B以外、別dataset、別population、長期horizonでも効果が維持されること
- 現在の候補が8変数design space内の最適制度であること
- 査読方式、公開方式、統治構造そのものを探索できること
- simulatorが現実の科学システムを妥当に同定していること

現段階の成果は「最良制度の発見」ではなく、監査可能な最初の制度比較と、その比較が
露呈させた資源trade-offおよび方法論的課題である。

## 7. 研究計画に対する現在地

| 研究線 | 現在地 |
|---|---|
| 再現可能なローカル基盤 | 小規模Qwen3-8B campaignについて達成 |
| 測定・seed-replicated harness | 最初のpaired comparisonまで達成 |
| ブラックボックス最適化 | design-spaceとsamplerはあるがoptimizer比較は未着手 |
| Evaluation System API | 抽象モデルのみ。legacy査読のinterface抽出は未着手 |
| 多目的・制約付き探索 | objective vectorは実装。Pareto探索は未着手 |
| 微分可能な制度 | 研究計画のみ |
| 科学システム構造探索 | 機構グラフ構想のみ |
| ゲーム | UX・技術境界の構想のみ |

## 8. 再現性と検証

- paired analysis: `utopia.optimization.paired_comparison`
- optimization tests: 38 passed
- offline non-integration suite: 613 passed、2 skipped、7 deselected
- 既知の7 failures: prospective logging fixture 6件、year-zero switching resume 1件
- paired JSONは再生成時に同一SHA-256
- comparison report commit: `dcc0a56`
- GitHub issue #10: completed and closed

既知failureは今回の比較器による回帰ではないが、未解決事項として維持する。

## 9. 成果物マップ

### 研究の定義

- [研究憲章](../charter.md)
- [科学政策としての目的設定](../science-policy-frame.md)
- [科学システムの抽象モデル](../system-model.md)
- [最適化研究計画](../optimization.md)
- [ロードマップ](../roadmap.md)

### 測定と実験契約

- [Metric Constitution](../metric-constitution-v1.md)
- [Metric Cards](../metric-cards-v0.md)
- [Design Space](../design-space-v0.md)
- [Harness](../harness.md)
- [Funding reliability](../funding-reliability.md)
- [Longitudinal fidelity](../longitudinal-fidelity.md)

### 最初の制度比較

- [事前protocolと結果](../first-system-comparison.md)
- [詳細run note](../runs/2026-10-26-first-paired-system-comparison.md)
- [機械可読paired report](../results/first-paired-system-comparison-v1.json)
- [日次log](../logbook/2026-10-26.md)

## 10. 次のマイルストーン

次の自然な区切りは「未使用seedによる最初の確認比較」である。

1. capability violationを制度outcomeとしてどう扱うかを事前登録する。
2. 候補、目的、閾値を変更せず、未使用confirmation seeds
   `401, 409, 419, 421, 431`でbaselineとcandidateを実行する。
3. explorationの効果方向が再現するか、追加資源とのtrade-offが維持されるか確認する。
4. confirmation結果に基づいて候補を保持・棄却し、その後に複数designを扱う
   random/Sobol baselineとblack-box optimizer比較へ進む。

この確認を終えるまでは、観測済みseedに合わせた閾値変更、候補微調整、目的の追加を
同じcomparison系列へ混ぜない。

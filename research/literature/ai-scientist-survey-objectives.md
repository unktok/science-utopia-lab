# `ai-scientist-survey` から見た ScienceUtopia の目的関数と評価設計

> **Historical interpretation; not current user requirements.**
> 本文の「単一scoreで最適化すべきでない」「不許容状態の制約」等は当時の解釈であり、
> 現在の実験に採用する要件ではない。ユーザーは明示した目的に基づく最適化を求め、
> 途中で追加された規範的vetoを不要としている。surveyの議論とプロジェクトの実験契約を
> 混同しない。元の本文・出典は保持する。
> 正本：[研究目的](../../RESEARCH.md)、[投稿ゴール](../publication/submission-goal.md)。

作成日: 2026-10-24
調査対象: `t46/ai-scientist-survey`
固定commit: [`02b437b854e73f1bd8a274399e56167ee05a4400`](https://github.com/t46/ai-scientist-survey/tree/02b437b854e73f1bd8a274399e56167ee05a4400)
位置づけ: ScienceUtopia の目的関数を確定する文書ではなく、既存の議論から設計要件・指標候補・未解決点を抽出した調査ノート。

## 要約

`ai-scientist-survey` の蓄積から得られる中心的な帰結は、ScienceUtopia を単一の「科学的生産性」scoreで最適化すべきではない、ということである。ただし、これは最適化を諦めるという意味ではない。最適化問題を次の四層へ分けるべきだという意味である。

1. **不許容状態を制約として除外する。** 捏造、assurance deception、訂正不能、異議・退出不能な評価支配などを、他の便益との交換可能な損失にしない。
2. **誤り訂正と将来の目的変更に必要な能力を保存する。** claim–evidence対応、negative result、独立なchallenge、versioning、rollback、異議申立て、探索branchの保持を測る。
3. **用途別の複数目的をPareto問題として扱う。** 探索、検証、速度、公平、資源、負担、長期optionなどを早期に固定weightへ潰さない。
4. **目的・指標・評価器を変更する制度自体を評価対象にする。** Goodhart効果の不存在ではなく、proxy支配の集中、乖離検出、置換遅延、回復時間、変更権限の集中を測る。

現在の `Metric Cards v0` は、最初のsimulation harnessを成立させる目的には妥当だが、topic breadth、embedding novelty、retention、resource equity、review burdenはいずれも科学的価値そのものではない。v1以降では、これらを制度アウトカムの一部として残しつつ、**検証・訂正・独立性・探索option・権限・長期状態遷移**を観測できるevent schemaを追加する必要がある。

## 1. 既存議論から抽出した原則

### 1.1 「科学全体の一つのloss」ではなく、制約付き多目的最適化として定式化する

既存ノートは、真理性、発見速度、再現性、探索多様性、社会的有用性、安全、自由、公平、効率、長期記憶を同時最大化できない価値として列挙し、問いを「単一目的関数は何か」から「何を拒否し、何を最低限保存し、どのcommitmentで何を優先し、誰がそれを改訂するか」へ変更している [S1]。

これはScienceUtopiaに次の構造を要求する。

```text
feasibility / constitutional constraints
    ↓
capability-preservation constraints
    ↓
domain- and commitment-specific objective vector
    ↓
Pareto / dominance / scenario comparison
    ↓
objective-and-evaluator governance metrics
```

したがって、最終的に微分可能なsurrogateを置く場合でも、全価値を一つのscalarへ恒久的に同一化しない。学習時の一時的なscalarizationと、制度上の価値の同一化は別物として扱う。weight、適用domain、期限、protected party、変更権限をrun manifestへ含める必要がある。

### 1.2 誤りを罰することと、欺瞞・訂正不能を禁止することを分ける

既存議論は、未知を扱う科学には正直な誤り、再現失敗、negative resultが不可避であり、false resultをゼロ化する制度は探索を保守化させうるとする。一方、実施していない検証の表示、失敗の意図的隠蔽、provenanceの捏造、訂正済み状態の不伝播は別の問題としている [S1]。

ScienceUtopiaへの含意は明確である。

- `wrong hypothesis` や `failed replication` 自体を大きな負報酬にしない。
- `unreported failure`、`claim stronger than evidence`、`fake evaluation`、`correction not propagated` を別eventとして記録する。
- 「真であること」だけでなく、「誤りが発見され、依存する判断が更新されること」を制度性能に含める。
- 現行simulatorにground truthがない間は、真理性を推定できたかのようなobjective名を使わない。

### 1.3 評価単位はsystemでもpaperでもなく、型付きclaim–version–evaluator関係である

AI Scientistのrubricを16事例へ試行した結果、既存調査はsystem単位の採点を廃止し、次の積を評価単位としている [S2]。

```text
assessment subject
× target claim
× autonomy slice
× evaluator relation
× artifact version
```

同じsystem内に、強く検証された成果、自己評価だけの最適化、人間が与えたagenda、非公開run、単なるinfrastructureが共存するためである。単一の`oracle strength`や`evidence maturity`も廃止され、formal proof、実行test、物理測定、expert review、model judge、producer test、external check、independent rerunが型として分離されている [S2]。

ScienceUtopiaでは、agent、paper、review scoreだけでなく、少なくとも次のIDをevent logへ導入すべきである。

- `claim_id`, `artifact_version`, `run_id`
- `evaluator_id`, `evaluator_type`, `evaluator_version`
- `evaluator_relation`: self / same-producer / external / independent / instrument / formal kernel
- `target_of_evaluation`, `decision_enabled`, `known_unchecked_scope`
- `goal_custody`: generate / select / revise / stop / release の権限主体

これがないと、評価systemを最適化したのか、評価器への適応を最適化したのかを区別できない。

### 1.4 評価と意思決定を分離する

既存の機能分解は、evidence validity、method validity、reproducibility、novelty、importance、safety、social valueをtyped evaluationとして返し、それらをpublish / fund / defer / replicate / reject / investigateへ変換するdecision policyを別に置く [S3]。また、研究評価を20機能へ分け、問いの選択、来歴、全試行、claim–evidence、独立検証、訂正、資源配分、評価器監査、異議申立てを区別している [S3]。

この分離は「評価システム自体を自由に設計する」という本プロジェクトの中心に直接対応する。

- evaluatorは観測・診断を返すmodule。
- decision policyは評価を制度行為へ写像するmodule。
- allocatorは資源を実際に移動するmodule。
- appeal / audit / correctionはdecision後にも作用するmodule。

これらを同じclassやpromptへ閉じ込めず、交換・ablation可能なinterfaceにするべきである。

### 1.5 自律性、成果、verificationは別軸で測る

73件の横断分析では、system-bearing full-text 26件のgoal originはhuman 16、shared 10、system 0だった一方、implementationやhypothesis generationのagent shareは高かった。また、empirical full-text 40件の独立judgeは14件、明示的なindependent end-to-end replicationは確認できず、run数、cost、trace、environmentの報告も弱かった [S4]。

ここから、ScienceUtopiaで「自律性が高い」ことを成功指標にしてはいけない。少なくとも次を分ける。

- agenda autonomy
- execution autonomy
- evaluation independence
- release / resource authority
- independently verified outcome
- human labor and intervention denominator

自律性を目的にする場合も、「何の権限をどこまで移したか」というdesign variableであり、scientific qualityの代理にはしない。

### 1.6 生成量・topic entropy・embedding noveltyと、実効的な探索可能性は異なる

科学的可能性空間の議論は、AIがideaを大量生成しても、共通corpus、model lineage、tool interface、benchmark、evaluatorへ収束すれば、実効的なoption breadthは狭まりうるとする [S5]。可能性の形成を次の七層へ分けている。

1. unresolved salience
2. representational availability
3. world access and material affordance
4. generative plurality
5. question and frame constitution
6. pursuit and resource allocation
7. constraint and public commitment

この観点では、現在の `topic_entropy_normalized` とembedding noveltyはL3–L4の表面の一部しか測らない。v1以降の探索指標候補は次になる。

- model / corpus / evaluator lineageの独立性
- non-overlapping world interactionまたはsimulation oracle
- 新しいdiscriminating testの生成
- 新しいrepresentation / measurement relation
- branch survivalとdormant branchの再開
- later evidenceによるreopening capacity
- data-rich領域へのattention concentration

ただし、これらも単一の`possibility score`へ合成しない。未解決trace、representation、world access、lineage、dormant branch、constraint capacityは、異なる失敗を防ぐreserveとして扱う [S5]。

### 1.7 Science of Scienceが示すのは、signalの時間構造と内生性である

repo内のScience of Science配分調査は、重要な欠落として次を挙げる [S6]。

- 新規な研究のsignalは遅れて現れ、短いcitation windowでは不利になりうる。
- 高リスク研究を使命とする制度でも、新規性の高い提案が低評価になりうる。
- 評価対象の知的frontierから遠い提案は低く採点されうる。
- 過去の実験容易性、data availability、既存attentionが将来の研究配分を規定しうる。
- 明示的な悪意やgamingがなくても、産出量による選択だけで方法の質が劣化しうる。
- 一件ずつのrankingは、portfolio全体の相関・多様性・option valueを表現しない。

したがって、短期runで上がるmetricだけを最適化すると、将来価値が遅れて現れるbranchを系統的に切る可能性がある。必要なのは単純なlong-run rewardだけではなく、次の観測である。

- signal latency curve
- early-stop false-negative rate
- branch extinction / reopening rate
- allocation path dependence
- metricに利用したsignalが資源配分によって自己成就した程度
- exploration reserveを除いた場合のcounterfactual loss

特に、citationや後続資源は制度が与えた可視性・資金・継続能力の結果でもある。予測精度が高いことを、対象の内在的価値を識別した証拠と直ちにみなさない。

### 1.8 査読・助成審査の「成功」は一つのoutcomeではない

助成金審査の調査では、審査scoreの予測妥当性、資金獲得の因果効果、審査後の交渉・改稿による改善を別estimandとしている。scoreと後続成果の関連は制度・分野・outcomeにより正、null、弱い関連へ分かれ、出版・引用・特許だけでは再現、訂正、再利用、社会利用を測れない [S7]。

査読改革についても、reviewer attention、request、author implementation、published manuscript、post-publication correctionの各遷移を分けるべきだとされる。二重委員会での採否不一致はdecision consistencyを測るがtruth validityを直接測らない。改革の有望な原則は、専門性の適応的追加、二値採否から複数signalへの分解、事前評価と出版後検証の接続、不確実性の表示である [S8]。

ScienceUtopiaへの含意は、acceptance rateや平均review scoreをobjectiveにしないという現行判断を支持するだけではない。次を別々に測る必要がある。

- reviewer agreement / calibration
- decision stability under reassignment
- error / limitation detection
- requested changeの実装率
- revised artifactの改善
- post-decision verification / correction
- reject後のrevision、resubmission、別経路での成功
- burden、delay、資源機会費用

### 1.9 国家の科学政策目標は正当なobjective候補だが、科学全体のground truthではない

repo内のgovernance議論は、研究評価が「何を良い研究と数えるか」だけでなく、どの問いを研究し、誰の便益・負担・危険を数え、何へ公的資源と実行権限を与えるかを決める制度問題だとする。一方で、epistemic truth、agenda priority、deployment permission、constitutional authorityを同じ判断へ束ねない。科学者・AI evaluatorの認識能力を政策目的の正当性へ変換してはならず、政治的多数や国家authorityを経験的claimの真偽を決める権限へ変換してもならない [S9]。

この区別から、国家の科学政策目標は次のように扱うべきである。

- **国家missionは一つのcommitment-specific objectiveである。** 例えば特定課題の解決、国家能力、期限、安全保障、public infrastructureは正当な目的候補だが、基礎探索や他社会の価値を含む普遍的な`scientific value`ではない。
- **公費・公的強制・退出困難性はgovernance要件を強める。** mission owner、payer、受益者、loss bearer、excluded alternative、decision rule、理由、異議、expiryを記録する [S9]。
- **政府が宣言した目標と公共的価値は同一ではない。** affected non-users、将来世代、研究参加者、maintainer、資源を得なかった代替案にもstandingがありうる。政策目標はこれらの入力を受けるversioned proposalであって、固定された外部真値ではない。
- **事実判断と目的判断を分ける。** 政府がagendaと資源配分を決めても、claimの妥当性は独立した証拠・批判・再現へ開く。逆に、専門家が証拠を評価できても、国家priority、許容損失、配備、補償を単独で決める根拠にはならない。

国家指標をそのままouter lossへ入れると、少なくとも次の失敗が起こりうる。

- publication、patent、citation、GDP、mission milestoneなど測りやすい政策proxyへの過適応。
- official categoryに翻訳できないneed、異論、minority loss、undone scienceの不可視化。
- electoral cycleや短いKPI windowによる長期branchの打ち切り。
- 国家がagenda、evaluator、allocator、成功判定を同時に持つ自己認証。
- national aggregate gainによる地域・集団・将来世代への損失の相殺。
- providerのmodel、cloud、workflow、evaluationへの依存を「国家主導」と誤認すること。

Research Frame Constitutionの議論は、public mission portfolioには強いresource couplingがある一方、official category、mission、security、electoral cycleがframeを閉じうるとする。そのため、Top Nだけでなくreserved alternative、contrarian、replication、infrastructure、maintenance、watchlistへ可逆的配分を残し、authorizationを期限付きにし、新しいaffected groupやresource changeでreopenする設計を提案している [S10]。

また、公共資源配分者に関する議論は、公共性を名称ではなく実効的な条件として扱う。公共allocatorにもprovider captureとpolitical mission narrowingがありうるため、providerから独立したrule governance、appeal、conflict disclosure、vendor-independent rerun、全試行分母、allocation後outcomeが必要である。拘束すべきなのは一つの価値判断ではなく、object/version/use、最低証拠、actual action、correction response、appeal、expiry、exportであり、科学的価値次元とadmissible候補間のportfolio判断はpluralに残す [S11]。

国家とprivate providerの共同基盤では、missionを国家が所有していても、problem intake、prioritization、engineering、agent memory、workflow、telemetryをproviderが握れば、operating layerが事実上のconstitutionになりうる。repo内のDOE事例監査は、public counter-capacityを所有名義でなく、provider撤退後もmissionを`continue / fork / repair`できる能力として扱い、provider substitution、mission continuity、workflow portability、researcher exit/voice、verification plurality、affected-party powerを一つのscoreへ平均しない [S12]。

したがってScienceUtopiaでは、国家政策との関係を次のvectorとして実装・評価するのがよい。

| policy-facing dimension | 問い |
|---|---|
| mission attainment | 宣言された対象outcomeを、どの期限・不確実性で達成したか |
| epistemic independence | mission ownerから独立した検証・反証がdecisionを変えられるか |
| public-value distribution | 便益・費用・risk・機会費用は誰に分布したか |
| agenda plurality | official frame外の代替・少数説・基盤研究が生存・再開できるか |
| standing and contestability | payer、研究者、affected non-user、将来利益がreason・appeal・stopへ接続されるか |
| public counter-capacity | providerやmetricの撤退・失敗後もcontinue / fork / repairできるか |
| temporal robustness | electoral・KPI windowを越えて長期optionとmemoryが残るか |
| policy learning | failure、externality、value changeからmission・metric・allocationを改訂できるか |

このvectorを「国益score」へ再圧縮しない。国家missionを含むrunでは、少なくとも `mission_spec_version`、`mission_authority`、`public_value_hypothesis`、`protected_parties`、`excluded_alternatives`、`expiry`、`appeal_route`、`independent_evaluator`、`provider_dependency` をmanifestへ記録する。

## 2. 現在のMetric Cards v0への評価

| 現行metric | 残す理由 | 主な不足・gaming | v1で併記すべき候補 |
|---|---|---|---|
| Topic Breadth AUC | 収束・agenda concentrationの粗いsignal | label entropyはlineage、world access、test diversityを測らない | lineage diversity、branch survival、data-rich concentration、reopening |
| Submission Novelty Median | 既存方向からの距離を低コストに測れる | incoherenceや表面的な言い換えでも上がる。遅い価値を測らない | discriminating-test novelty、representation novelty、later validation、novelty latency |
| Active Researcher Retention | 制度の参加持続性を捉える | 生産性・自由・退出可能性・強制的残留を区別しない | voluntary exit、blocked exit、cohort survival、role diversity、option preservation |
| Resource Equity AUC | 集中と累積優位を可視化する | 均等な貧困、費用差、必要な集中を区別しない | minimum capability floor、resource-to-opportunity conversion、concentration persistence、mobility |
| Review Burden | 評価capacityの希少性を扱う | review削減だけで改善する。質・効果・遅延を捉えない | burden per detected issue、decision change、verification throughput、queue latency |

v0のmetricは削除せず、**制度状態を観測する低コストproxy**として位置づけ直す。`primary objective`という表記は、外部ground truthを導入するまでは「v0 optimization objective」であって「scientific value objective」ではないことをmanifestにも残す。

## 3. 目的関数アーキテクチャ案

### 3.1 Hard constraints / constitutional exclusions

初期simulationで直接観測可能なものから始める。

- 実行していないreviewをvalid reviewとして扱わない。
- unresolved parse / transport failureを科学的判断へ変換しない。
- artifact / evaluator / decision versionを欠いた状態で資源移動しない。
- correction後の旧versionをactive canonical stateとして残さない。
- appeal不能、単一evaluatorへの全面依存、全探索branch消滅を少なくともflagする。
- integrity failureを他の高scoreで相殺しない。

### 3.2 Capability-preservation metrics

- `claim_evidence_coverage`
- `negative_space_retention`
- `independent_challenge_capacity`
- `correction_propagation_rate`
- `rollback_success_rate`
- `objective_evaluator_version_reproducibility`
- `appeal_resolution_coverage`
- `protected_exploration_capacity`

これらは「良い科学」を直接最大化するobjectiveではなく、制度が自らの誤りを後から修正できるoptionを守るconstraintまたはsecondary objectiveである。

### 3.3 Commitment-specific objective portfolios

同じ制度でもcommitmentを分ける。

| commitment | 目的候補 | 避けるべき短絡 |
|---|---|---|
| exploratory science | effective option breadth、information gain、branch survival | novelty distance = value |
| confirmatory science | calibration、independent replication、error detection、correction latency | acceptance = validity |
| formal / software | correctness、execution、robustness、security | test pass = scientific importance |
| mission science | target outcome、time、safety、externality、public value | mission score = universal value |
| research commons | access、reuse、preservation、substitution、governance plurality | openness count = usable commons |

### 3.4 Meta-objectives for the objective system

目的関数それ自体の健全性を次で測る。

- `proxy_concentration`
- `target_substitution_lag`
- `metric_half_life_without_reauthorization`
- `gaming_elasticity`
- `evaluator_error_correlation`
- `allocation_diversity`
- `recovery_time_after_proxy_failure`
- `rule_authority_concentration`

ここは本研究の独自性が最も出る可能性がある。ScienceUtopia内のagentが明示されたmetricへ適応する条件を作り、reward強度、metric公開範囲、evaluator rotation、sealed evaluator、appeal、metric sunsetを操作すれば、Goodhart化を制度levelで実験できる。

## 4. 最適化方法への示唆

### 4.1 最初はPareto + feasibility + stress test

単一のglobal optimumを探す前に、次を行う。

1. hard constraint違反を除外する。
2. Pareto dominatedな制度を除外する。
3. scenario別にfrontierを比較する。
4. 未知seed、別model、別population、長期runで順位反転を調べる。
5. evaluator、metric、agent policyを変えたstress testを行う。
6. 僅差ならreversibilityとoption preservationを優先する候補も残す。

### 4.2 微分可能化の対象を明示する

微分可能な評価systemを作る場合、区別すべき対象は少なくとも三つある。

- `surrogate evaluator`: claimやartifactからtyped evaluationを予測する。
- `decision policy`: typed evaluationから採否・再現要求・資源配分を出す。
- `outer institutional objective`: simulation trajectory全体を評価する。

end-to-end gradientを流すと、surrogateのblind spotを制度が利用する可能性がある。したがって、sealed / orthogonal evaluator、外部ground-truth task、evaluator rotation、adversarial test、held-out institution regimeを併用し、train evaluator scoreと外部outcomeの乖離を主結果として保存する。

### 4.3 介入効果と予測能力を分ける

制度Aが「良い将来成果を高scoreにする」ことと、「制度Aを導入すると良い成果が増える」ことは違う。optimizer比較では次を別estimandにする。

- evaluator predictive validity
- allocation treatment effect
- feedback / revision mediation
- selection effect
- downstream resource amplification
- long-run correction and reuse

可能なら同じproposalやpaperを複数制度へcounterfactualに通すpaired design、境界近傍randomization、shadow evaluationを導入する。

## 5. 先に追加すべきログとschema

指標確定より先に、後から別の指標を計算できる観測基盤を作る価値が高い。

### Minimum event types

- `objective_declared`, `objective_revised`, `metric_reauthorized`, `metric_expired`
- `claim_created`, `claim_revised`, `claim_withdrawn`
- `evidence_attached`, `evidence_invalidated`
- `evaluation_issued`, `evaluation_challenged`, `evaluation_overturned`
- `decision_made`, `decision_appealed`, `decision_reversed`
- `resource_allocated`, `resource_withdrawn`
- `branch_suspended`, `branch_reopened`, `branch_extinct`
- `replication_attempted`, `replication_succeeded`, `replication_failed`
- `correction_issued`, `correction_propagated`, `dependent_decision_updated`

### Minimum common fields

- actor / institution / role / authority
- object / claim / version / parent relation
- evaluator / evaluator type / evaluator version / independence relation
- stated objective / metric version / decision policy version
- time / resource / compute / human-or-agent labor
- observed evidence / unobserved scope / uncertainty
- action / recipient / affected party / appeal route
- counterfactual or matched comparison key where available
- mission / policy specification、public authority、payer、beneficiary、loss bearer
- protected party、excluded alternative、standing / appeal / expiry
- provider dependency、export / substitution / succession state

このevent logは分析とゲームUIの双方に使える。ゲーム上の「査読」「資金」「訂正」「論争」「研究branch」の表示が、そのまま研究用trajectoryの観測面になる。

## 6. 未解決点

1. **ground truthをどう入れるか。** synthetic truth、formal task、simulated world、physical experiment、expert judgmentはそれぞれ別の対象しか保証しない。
2. **社会的価値を誰が定めるか。** utilityを固定すると政治を隠し、毎run変更可能にするとcaptureと不安定性が増える。
3. **長期価値を短いsimulationでどう扱うか。** signal latencyとsleeper branchを表現しないと早期選抜が常に有利になる。
4. **lineage independenceをどう測るか。** model名の違いだけでは、共通data、training、tool、evaluator依存を捉えない。
5. **world accessをどうsimulationへ導入するか。** text生成だけではmaterial answerabilityを測れない。
6. **人間の役割を固定すべきか。** human-in-the-loopの有無ではなく、problem framing、override、release、correction、appealの権限を変数化する必要がある。
7. **制度がagent policyを変える内生性をどう同定するか。** outcome差は選抜だけでなく、agentが制度signalへ適応した結果でもある。
8. **評価負担と検証価値をどう交換するか。** review件数ではなく、検出・改善・訂正に寄与した限界効果が必要である。
9. **metric自身を最適化対象に含めると誰がouter objectiveを決めるか。** 無限後退を避けるconstitutional boundaryが必要になる。
10. **現実妥当性。** Qwen3-8B agent社会でのfrontierが、人間科学または別model社会へ外挿できる保証はない。
11. **国家目標と公共的価値のずれをどう観測するか。** policy documentへの一致、民主的正統性、社会的便益、少数者のrights、認識的妥当性は別の構成概念である。
12. **国家間の競争をどう扱うか。** 一国の能力・速度を最大化する制度が、公開性、国際的commons、安全、他国への外部性を悪化させうる。

## 7. 本プロジェクトでの暫定的な採用判断

### すぐ採用する

- v0の複数目的・Pareto方針を維持する。
- acceptance、accepted count、review scoreを診断値に留める。
- objective、metric、evaluator、decision policyへversion IDを付ける。
- 国家missionを一つのscenario / commitmentとして実装し、universal scientific objectiveと呼ばない。
- mission attainment、epistemic validity、public-value distribution、counter-capacityを別々に記録する。
- evaluator independenceとdecision transitionをevent logに追加する。
- seedだけでなくmetric / evaluator perturbationで制度をstress testする。
- negative result、failed run、rejected branch、correctionを分母から消さない。

### 観測基盤を作ってから採用する

- correction propagation、independent verification、branch reopening。
- effective option breadth、lineage diversity、world-access diversity。
- gaming elasticity、target-substitution lag、metric half-life。
- downstream outcomeとlongitudinal reuse。

### 現時点では採用しない

- 全metricの固定加重和を「科学の価値」と呼ぶこと。
- citation、acceptance、publication、LLM judge scoreの単独最大化。
- systemまたはinstitution全体への一つのquality grade。
- 自律性や生成量をscientific qualityの代理とすること。
- publication、citation、patent、GDP、national competitiveness、mission milestoneなど、単一の国家指標を科学全体のouter lossとして直接最大化すること。

## 8. 根拠となるrepo内資料

以下はすべて固定commit `02b437b854e73f1bd8a274399e56167ee05a4400` で確認した。repo内文書には統合ノート、探索的rubric、一次資料カードが混在するため、同じ証拠強度とはみなしていない。

- **[S1] 単一目的関数なしに「望ましい科学制度」を設計する方法**
  [`research/2026-09-10-scientific-value-constitution-method.md`](https://github.com/t46/ai-scientist-survey/blob/02b437b854e73f1bd8a274399e56167ee05a4400/research/2026-09-10-scientific-value-constitution-method.md#L9-L280)
  単一尺度の拒否、四層constitution、proxy sovereignty、Goodhart、Pareto、reversibility。

- **[S2] 「研究」を評価するrubric v0.3**
  [`research/research-conceptual-foundations-2026-08-29/rubric-v0.3-synthesis.md`](https://github.com/t46/ai-scientist-survey/blob/02b437b854e73f1bd8a274399e56167ee05a4400/research/research-conceptual-foundations-2026-08-29/rubric-v0.3-synthesis.md#L5-L164)
  system rankingの廃止、claim-level evaluation、typed verifier、human laborとlongitudinal ledger。

- **[S3] AIネイティブな研究評価システム：必要機能の分解**
  [`research/2026-09-09-research-evaluation-function-decomposition.md`](https://github.com/t46/ai-scientist-survey/blob/02b437b854e73f1bd8a274399e56167ee05a4400/research/2026-09-09-research-evaluation-function-decomposition.md#L28-L218)
  F01–F20、評価とdecisionの分離、evaluation independence、correction-native infrastructure。

- **[S4] AI Scientist引用圏73件の横断構造分析**
  [`research/2026-08-23-ai-scientist-cross-sectional-analysis.md`](https://github.com/t46/ai-scientist-survey/blob/02b437b854e73f1bd8a274399e56167ee05a4400/research/2026-08-23-ai-scientist-cross-sectional-analysis.md#L51-L226)
  autonomy / verification / judge independence / run・cost・trace分母の実証的な監査。

- **[S5] 問いの前に何が起きるか――科学的可能性空間の制度的構成とAI時代**
  [`research/2026-10-07-before-the-question-scientific-possibility-space.md`](https://github.com/t46/ai-scientist-survey/blob/02b437b854e73f1bd8a274399e56167ee05a4400/research/2026-10-07-before-the-question-scientific-possibility-space.md#L11-L275)
  七層model、生成量とeffective option breadthの区別、Possibility Portfolio。

- **[S6] 第8章「探究はどう配分されるか」とScience of Scienceの配分研究**
  [`research/2023-intellectual-reconstruction/manuscript-driven-external-research/57-publication-revision-2026-09-28/SCIENCE-OF-SCIENCE-ALLOCATION-SURVEY-2026-10-07.md`](https://github.com/t46/ai-scientist-survey/blob/02b437b854e73f1bd8a274399e56167ee05a4400/research/2023-intellectual-reconstruction/manuscript-driven-external-research/57-publication-revision-2026-09-28/SCIENCE-OF-SCIENCE-ALLOCATION-SURVEY-2026-10-07.md#L11-L205)
  信号遅延、新規性bias、探索不足、累積優位、data-rich領域への集中、配分の内生性。

- **[S7] 助成金審査の予測妥当性：採択後アウトカムに対する混合証拠**
  [`research/2026-09-09-grant-review-predictive-validity-evidence-card.md`](https://github.com/t46/ai-scientist-survey/blob/02b437b854e73f1bd8a274399e56167ee05a4400/research/2026-09-09-grant-review-predictive-validity-evidence-card.md#L5-L50)
  predictive validity、funding treatment effect、outcome measurementの分離。

- **[S8] 査読改革の深掘り分析**
  [`research/2026-09-09-peer-review-reform-deep-analysis.md`](https://github.com/t46/ai-scientist-survey/blob/02b437b854e73f1bd8a274399e56167ee05a4400/research/2026-09-09-peer-review-reform-deep-analysis.md#L291-L325)
  専門性、複数signal、事前・事後評価の接続、不確実性、代理指標gaming。

- **[S9] 科学的価値を誰が変えられるのか**
  [`research/2026-09-10-scientific-value-constitution-standing-amendment-and-ai-succession.md`](https://github.com/t46/ai-scientist-survey/blob/02b437b854e73f1bd8a274399e56167ee05a4400/research/2026-09-10-scientific-value-constitution-standing-amendment-and-ai-succession.md#L3-L103)
  epistemic / agenda / deployment / constitutional judgment、public funds、standing、authority、appealの分離。

- **[S10] 誰が問いを設定するのか――Research Frame Constitution**
  [`research/2026-10-05-who-sets-the-question-research-frame-constitution.md`](https://github.com/t46/ai-scientist-survey/blob/02b437b854e73f1bd8a274399e56167ee05a4400/research/2026-10-05-who-sets-the-question-research-frame-constitution.md#L93-L137)
  public mission portfolio、reserved alternatives、reopening、lineage-adjusted plurality。

- **[S11] 最初に誰の行動を変えるのか**
  [`research/2026-09-11-first-acceptor-binding-plurality-and-public-payer.md`](https://github.com/t46/ai-scientist-survey/blob/02b437b854e73f1bd8a274399e56167ee05a4400/research/2026-09-11-first-acceptor-binding-plurality-and-public-payer.md#L11-L110)
  public/shared allocator、用途別判断、binding conversion、公共性と独立検証の費用負担。文書冒頭に後続反証比較による限定・一部撤回が明記されているため、単一acceptor一般則としては採用しない。

- **[S12] 国家missionとprivate operating constitution――DOE Genesis co-production audit**
  [`research/2026-10-05-doe-genesis-state-provider-coproduction-audit.md`](https://github.com/t46/ai-scientist-survey/blob/02b437b854e73f1bd8a274399e56167ee05a4400/research/2026-10-05-doe-genesis-state-provider-coproduction-audit.md#L7-L145)
  state–provider co-production、public counter-capacity、provider substitution、mission continuityとauthority vector。

## 9. 調査上の限界

- このノートは `ai-scientist-survey` の既存資産を再統合したもので、新しい外部文献サーベイや一次資料の独立再読ではない。
- repo内には非公開discussion memo、bounded synthesis、exploratory rubric、一次資料evidence cardが共存する。提案の存在と効果の実証を区別した。
- Science of Scienceの知見の多くは出版記録、引用、新規性proxy、特定分野の観察研究に依存する。ScienceUtopiaへ移植する際は、simulation内で観測可能になったからといって構成概念妥当性が自動的に得られるわけではない。
- ここで列挙したmetric候補は、実装可能性、識別可能性、計算費用、seed分散をまだ評価していない。次段階ではevent schemaを先に設計し、小規模runで欠損率と安定性を測ってからMetric Cards v1へ昇格させる。

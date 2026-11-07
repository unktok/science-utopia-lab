# ScienceUtopia の制度最適化における目的関数候補

> **Historical design memo; not the active optimization contract.**
> 下記の2026-10-24本文にある「制約付き多目的」「採択数を目的にしない」等は、
> その後のユーザー方針で採用されていない。現在は宣言したLossSpecで候補を順位付けし、
> 評価指標・技術的失敗・任意の採用方針を分ける。文献上の注意を隠れたvetoとして
> 復活させない。元の本文は研究史として保持し、出典・測定上の論点だけを参考にする。
> 正本：[研究目的](../../RESEARCH.md)、[投稿ゴール](../publication/submission-goal.md)。

**Status:** literature-informed design memo v0.1  
**Date:** 2026-10-24  
**Scope:** Science of Science、metascience、研究評価、国家科学技術政策の議論を、ScienceUtopia の制度最適化へ接続するための非網羅的な研究メモ。

## 要旨

ScienceUtopia を一つの確率的関数として最適化することは可能である。しかし、最適化すべき対象を、論文数、引用数、採択数、平均新規性などの単一指標で表すべきではない。既存研究と政策文書から得られる中心的な含意は次の通りである。

1. **観測しやすい研究出力と、科学的価値は異なる。** 論文数・引用数・journal 指標は活動や影響の一側面であり、真理性、再現性、社会的便益を直接には測らない。
2. **新規性と disruption は、それだけでは善ではない。** 科学には既存知識を発展・統合・検証する仕事も必要であり、極端な意味距離は無関係さや incoherence でも上げられる。
3. **再現可能性と replicability は別の構成概念である。** 同じデータとコードで再計算できることと、新しいデータで同じ科学的主張を支持できることを分ける必要がある。
4. **多様性は entropy だけでは足りない。** 少なくとも variety、balance、disparity を分け、研究内容、方法、主体、機関、資源配分の各層で測る必要がある。
5. **効率は成果数／費用ではなく、検証済み知識や option value を含む。** 集中的な大型配分には逓減収益がありうる一方、大型設備や共同研究が不可欠な領域もある。
6. **公平性は平均的な資源平等ではない。** 機会、手続、誤差、成果、便益、負担を主体・機関・career stage・topic ごとに分解しなければならない。
7. **研究者の持続可能性は科学システムの生産能力である。** retention だけでは不十分で、仕事量、資源の不安定性、独立までの時間、退出、回復可能性を見る必要がある。
8. **指標は観測器であると同時に介入である。** 最適化対象になった指標は、エージェントの行動を変え、測ろうとした対象を変形する。これは simulator 内で明示的に研究すべき現象である。
9. **国家科学政策の目的は重要だが、国家を唯一の効用主体にはしない。** 経済競争力、mission 達成、危機対応能力と同時に、研究の自律性、国際的知識 commons、被影響者、将来世代、人類全体の利益を別々に保持する。

したがって v1 では、**制約付き多目的最適化**を採用し、目的ベクトル、最低条件、分布指標、時間軸、未知 seed での頑健性を別々に保存するのが妥当である。単一 scalar は探索アルゴリズム内部で一時的に使ってもよいが、研究上の結論や制度順位として固定しない。

---

## 1. 何を最適化するのか

制度設計を `theta`、環境・外生条件を `c`、確率性を `omega`、軌跡を `tau` とすると、

\[
\tau = F(\theta, c, \omega), \qquad y = M(\tau)
\]

である。ここで難しいのは `F` より `M` である。測定 `M` は中立な読み出しではなく、次の選択を含む。

- 誰にとっての価値を測るか。
- 研究活動、研究出力、知識状態、社会的 outcome のどの層を見るか。
- 何年後まで見るか。
- 平均、下位分位、上位 tail、格差、最悪条件のどれを重視するか。
- 不確実性、欠測、検閲、field 差をどう扱うか。
- 指標を資源配分へ接続した時に、行動がどう変わるか。

[Fortunato et al. (2018)](https://doi.org/10.1126/science.aao0185) は Science of Science を、資金、協働、論文、引用、移動、career などの大規模データから科学活動の機構を理解し、政策設計へつなぐ研究領域として整理している。ただし、そこで観測される規則性は、そのまま規範的な目的関数にはならない。「何が起きているか」と「何を望むか」を分ける必要がある。

### 1.1 四つの評価対象

ScienceUtopia では少なくとも次を混同しない。

| 層 | 例 | 注意 |
|---|---|---|
| activity / input | 資金、研究時間、査読数、compute | 多いこと自体は成果ではない |
| output | 論文、dataset、software、replication | 件数は質や有用性を保証しない |
| epistemic state | 真偽、calibration、再現性、誤り訂正 | 現行 simulator には ground truth が乏しい |
| social / public outcome | 健康、環境、政策、能力、安全 | simulator 外の因果連鎖が必要 |

既存の v0 metric cards は主に activity、output、内部状態を測っている。これらを「科学の改善」と呼ぶには、hidden truth、replication event、outcome verifier、または外部 outcome model の追加が必要である。

---

## 2. 領域別の既存議論と目的関数候補

## 2.1 Bibliometrics：活動と影響の診断であり、価値の代用品ではない

[Leiden Manifesto](https://doi.org/10.1038/520429a) は、定量評価を専門家判断の補助とし、研究 mission に合わせ、field 差を考慮し、データと分析を透明にし、指標の制度効果を定期的に精査することを求める。[DORA](https://sfdora.org/read/) は journal impact factor を個別論文・研究者の質の代替として使わないこと、研究内容と多様な output を評価することを推奨する。DORA の[定量指標ガイダンス](https://doi.org/10.5281/zenodo.10979644)も、citation、h-index、field-normalized indicator、altmetrics を文脈依存の指標として扱う。

したがって ScienceUtopia では、以下を原則とする。

- publication count、accepted count、citation count、acceptance rate は **診断** とし、primary objective にしない。
- citation を使う場合、件数だけでなく、field、年、citation window、自己引用、citation network の集中、negative citation の扱いを固定する。
- 上位 journal や採択ラベルを transferable な品質 token にしない。
- simulation 内の review score を「真の質」と呼ばず、特定 evaluator の judgement として version 付きで記録する。

**候補指標:** field-year 正規化 citation、知識 diffusion の到達範囲、citation concentration、knowledge lineage coverage。ただしすべて lagging diagnostic である。

## 2.2 Novelty と disruption：探索価値はあるが単調最大化しない

[Uzzi et al. (2013)](https://doi.org/10.1126/science.1240474) は、17.9 million papers の分析から、高 impact 研究は非常に conventional な基盤と、一部の atypical combination を同時に持つ傾向を示した。これは「距離が遠いほど良い」ではなく、**conventionality と atypicality の組合せ**が重要であることを示唆する。

[Wu, Wang & Evans (2019)](https://doi.org/10.1038/s41586-019-0941-9) は、小チームが disruption、大チームが既存方向の development を担う傾向を報告し、両者が科学 ecosystem に必要だと論じる。[Park, Leahey & Funk (2023)](https://doi.org/10.1038/s41586-022-05543-x) は CD index により disruption の長期低下を報告したが、CD index には citation inflation や reference practices への感度があるとの批判もある（[Petersen, Arroyave & Pammolli, 2024](https://doi.org/10.1162/qss_a_00333)）。よって disruption は妥当性が確定した objective ではない。

**ScienceUtopia での候補:** 

- 既存知識との semantic distance の中央値だけでなく、distribution と上位 tail。
- conventional core と atypical combination の同時存在。
- novelty の後続 uptake、独立再発見、replication、長期 survival。
- disruptive contribution と consolidating contribution の portfolio 比率。
- incoherent novelty を除くための evidence quality / internal coherence floor。

**設計判断:** `Submission Novelty Median` は最大化対象から、quality・coherence 制約付きの探索指標へ格下げする。最適点は高い端ではなく、領域と mission に応じた portfolio として探索する。

## 2.3 Reproducibility、replicability、真理性、訂正

[National Academies (2019)](https://doi.org/10.17226/25303) は、reproducibility を同じデータ・コード・計算手順から同じ結果を得ること、replicability を新しいデータを使う独立研究で一貫した結果を得ること、と区別する。この二つを一つの「再現性」に潰してはならない。

大規模な replication project は、成功率が手続・領域・判定方法に依存することを示す。[Open Science Collaboration (2015)](https://doi.org/10.1126/science.aac4716) は心理学100研究を対象とし、[Camerer et al. (2018)](https://doi.org/10.1038/s41562-018-0399-z) は Nature / Science 掲載の社会科学実験21件を対象とした。[Errington et al. (2021)](https://doi.org/10.7554/eLife.71601) は cancer biology で、計画した193実験のうち完了できたものが50件に留まり、方法記述、data、reagent、materials の不足自体が測定対象になることを示した。単純な「replicated / failed」だけでは、再現を試せたか、効果量と不確実性がどう変わったかを失う。

**hidden truth を導入した場合の候補:** 

- claim の calibration（Brier score、log score）。
- false discovery / false omission、confidence-weighted error。
- 独立 replication の効果量一致と uncertainty overlap。
- 誤りの発見までの時間、訂正の伝播時間、撤回後の stale reliance。
- reproducible artifact coverage：data、code、method、seed、environment の再実行可能率。
- replication portfolio coverage：重要度・不確実性・下流依存に応じて検証資源が配分された割合。

**重要:** replication failure は常に元研究の不正や低品質を意味しない。異質性、文脈、sampling variation、元効果の過大推定、replication design の失敗を分離する。

## 2.4 研究多様性：variety、balance、disparity、coherence

[Stirling (2007)](https://doi.org/10.1098/rsif.2007.0213) は diversity を次の三成分に分ける。

- **variety:** 何種類あるか。
- **balance:** 各種類がどれほど均等に存在するか。
- **disparity:** 種類同士がどれほど異なるか。

Shannon entropy は主に variety と balance を反映するが、topic 間の距離を表す disparity を持たない。近接した細分 topic を多数作れば高くなるため、`topic_entropy_normalized` だけでは epistemic diversity を測れない。[Rafols & Meyer (2010)](https://doi.org/10.1007/s11192-009-0041-y) は diversity と network coherence を分け、異なる知識領域を参照していることと、それらを構造的に統合できていることを区別する。

また diversity には、topic だけでなく主体と制度の分布がある。[Hofstra et al. (2020)](https://doi.org/10.1073/pnas.1915378117) は、米国の約120万件の博士論文と career data から、underrepresented group が高い novelty を生みながら、その novelty の uptake と career return が低いという diversity–innovation paradox を報告した。新規性の総量だけを見ると、誰の新規性が無視されたかを見落とす。

**候補指標:** 

- Rao–Stirling 型 topic diversity：topic share と topic distance の組合せ。
- method、evidence type、theory lineage、team size、institution の diversity。
- minority hypothesis survival、abandoned branch 数、再探索可能な branch の option value。
- knowledge integration coherence。
- agent group 別の novelty 生成、評価、採択、資金、uptake、career return の差。

## 2.5 効率：固定予算下の情報価値と遅延

[Fortin & Currie (2013)](https://doi.org/10.1371/journal.pone.0065263) は Canadian NSERC の研究者について、資金と publication/citation impact の関係は弱く、多くの場合 funding に対する impact が逓減したと報告した。これはすべての領域で少額分散が最適という証拠ではないが、資源集中を当然視せず、marginal return を測る根拠になる。

効率の分母は grant 額だけでなく、研究時間、compute、review、application effort、設備占有、失敗からの回復を含む。分子は paper count ではなく、制度の目的に応じて次を使う。

- 検証済み claim または uncertainty reduction / resource。
- idea から公開、検証、訂正までの latency。
- independent lines of inquiry / total budget。
- reuse 可能な data、software、negative result の生成。
- reviewer / applicant burden と decision quality の Pareto 関係。
- funding level に対する marginal epistemic return curve。

大型設備・長期基盤・大規模 team は一件あたり費用が高くても、代替不能な capability を形成しうる。したがって cost efficiency と capability / option value を別目的にする。

## 2.6 公平性：配分だけでなく、機会・手続・承認・便益

[Ginther et al. (2011)](https://doi.org/10.1126/science.1196783) は NIH R01 で Black applicants が観測可能な背景等を調整後も White applicants より award probability が10 percentage points低いと報告した。[Hoppe et al. (2019)](https://doi.org/10.1126/sciadv.aaw7238) は topic choice が funding gap の一部と関係し、個人属性だけでなく、制度がどの topic を重視するかが分布的結果を作ることを示した。[Tomkins, Zhang & Heavlin (2017)](https://doi.org/10.1073/pnas.1707323114) の controlled experiment では、single-blind reviewers が著名著者・上位機関・企業の論文をより推薦する傾向が示された。

公平性を `1 - Gini` だけで最大化すると、全員を等しく貧しくする制度が最適になる。また、必要資源が異なる研究を同額にするのが公平とは限らない。

**候補指標:** 

- **機会:** application / participation / facility access / review assignment の到達率。
- **手続:** 同等の latent quality と evidence に対する score・decision 差、appeal 成功、説明可能性。
- **配分:** career stage、institution、topic、初期資源別の funding share と下位分位。
- **承認:** novelty や成果が等しい場合の uptake、citation、reputation、career return 差。
- **便益と負担:** public outcome、review burden、failure risk、externality の group 別分布。
- **mobility:** 低資源状態から独立研究者・decision role へ移れる確率。

現行 simulator に現実の race / gender を安易に割り当てたり、名前から推定したりしない。まず institution、career stage、resource endowment、topic を使い、因果機構を検証する synthetic protected attribute は明示的な実験条件として導入する。

## 2.7 研究者と研究能力の持続可能性

[Wellcome (2020)](https://wellcome.org/insights/reports/what-researchers-think-about-research-culture) の4,000人超の survey では、研究 career に security を感じる回答は29%、competition が不親切・攻撃的な環境を作るとの回答は78%であった。survey は因果推論ではないが、研究文化、雇用安定性、mental health、management、metric pressure を scientific capacity の一部として測る必要を示す。[UNESCO Recommendation on Science and Scientific Researchers (2017)](https://www.unesco.org/en/legal-affairs/recommendation-science-and-scientific-researchers) も、公正な career prospects、研究者 pool の再生産、自律性と自由を科学政策の条件としている。

**候補指標:** 

- cohort 別 retention / attrition hazard と退出理由。
- funding runway、resource volatility、無資源期間。
- research、application、review、administration の workload distribution。
- early-career agent が独立資源を得るまでの時間。
- mentor access、collaboration access、career mobility。
- shock 後に researcher population と capability が回復するまでの時間。
- 最大 workload、下位 resource quantile、burnout-risk latent state。

LLM agent の文章上の「幸福」や「stress」を、そのまま人間の well-being 指標として扱わない。制度状態から計算する workload、資源不安定性、退出、裁量などを先に測り、心理状態を導入する場合は明示的な agent model として検証する。

## 2.8 Goodhart、Campbell、metric gaming

Campbell は、定量的な社会指標が意思決定に強く使われるほど、腐敗圧力を受け、測ろうとした過程を歪めると論じた（[Campbell, 1979](https://doi.org/10.1016/0149-7189(79)90048-X)）。研究制度では実際に、publication count を funding formula に接続すると output が増える一方、増加が低 impact journal に偏る現象が観測されている（[Butler, 2003](https://doi.org/10.3152/147154403781776780)）。[Fire & Guestrin (2019)](https://doi.org/10.1093/gigascience/giz053) は120 million超の papers を分析し、publication、citation、h-index 等の指標が coauthorship、self-citation、reference inflation、field 差により意味を失いうると指摘した。

ScienceUtopia の optimizer は、人間制度より高速に metric の穴を探索する可能性がある。したがって gaming はノイズではなく primary research object とする。

**候補指標:** 

- proxy–ground-truth correlation の optimization 前後差。
- reward を強めた時の gaming elasticity。
- 同じ metric / evaluator が資金・採択・career を支配する decision concentration。
- metric version の half-life、失効後も使われる stale-decision rate。
- evaluator 間 disagreement と correlated blind spot。
- holdout metric、adversarial metric、human-coded sample 上の degradation。
- proxy failure 発見から rule change / resource correction までの recovery time。

**運用原則:** decision-active metric には target、production、uncertainty、interpretation、authorized use、incentive footprint、owner、version、expiry、appeal、revision trigger を記録する。

---

## 3. 国家科学政策として見る場合

研究システムの目的を問うことは、国家が科学政策で何を目指すかを問うことに近い。ただし国家の効用を唯一の上位目的にすると、学問の自由、国際協力、少数者・他国・将来世代への便益と損害が消える。

### 3.1 国家レベルで現れる目的群

| 目的群 | 例 | ScienceUtopia での候補 |
|---|---|---|
| epistemic commons | 信頼できる知識、公開、保存、訂正 | verified claims、reproducible artifacts、correction lag |
| mission achievement | 気候、健康、防災などの具体的問題 | mission-specific milestone、outcome、期限、被影響者別効果 |
| economic / innovation | 生産性、技術移転、新産業 | usable invention、diffusion、complementary capability。paper/patent countはproxy |
| capacity / resilience | 人材、設備、危機対応、absorptive capacity | capability coverage、mobilization time、shock recovery、portfolio diversity |
| security / strategic autonomy | 重要技術・供給・情報の安全 | dependency、single point of failure、dual-use risk。閉鎖性とのtrade-off |
| equity / territorial cohesion | 地域、機関、主体間の参加と便益 | access、resource floor、regional capability、burden/benefit distribution |
| democratic legitimacy | accountable priority-setting、参加、contestability | stakeholder coverage、appeal、rule revision、公開理由 |
| scientific freedom | 問いの自律性、異論、長期基礎研究 | investigator-led share、minority hypothesis survival、topic capture |
| global / intergenerational value | 国境を越える知識と将来便益 | international spillover、future option、externalized harm |

[OECD Frascati Manual (2015)](https://doi.org/10.1787/9789264239012-en) は R&D 支出と人材という input を比較可能にするが、それ自体は社会的 outcome を測らない。[OECD/Eurostat Oslo Manual (2018)](https://doi.org/10.1787/9789264304604-en) は innovation を novelty だけでなく、実装され利用可能になった product/process として捉え、経済・社会・環境への正負の outcome を別に測る必要を示す。GERD、研究者数、papers、patents は national science system の状態記述には有用だが、最終効用ではない。

Mission-oriented policy は、広い challenge を測定可能な期限付き mission に翻訳し、複数主体・領域・政策手段を束ねる（[Mazzucato / European Commission, 2018](https://research-and-innovation.ec.europa.eu/knowledge-publications-tools-and-data/publications/all-publications/mission-oriented-research-innovation-eu-problem-solving-approach-fuel-innovation-led-growth_en)）。[OECD STI Outlook 2023](https://doi.org/10.1787/0b55736e-en) は directionality だけでなく、legitimacy、flexibility、stakeholder involvement、policy mix、evaluability、reflexivity を mission の要素とする。したがって mission score を一つ置くだけでは不十分であり、mission が誰により設定され、誰が便益・損害を受け、途中でどう改訂されるかをモデル化する必要がある。

科学能力と resilience も output の副産物ではない。[OECD science policy guidance](https://www.oecd.org/en/topics/science-policy.html) は、危機前から scientific capacity、network、science–policy–public interface を構築する必要を指摘する。広い研究 portfolio と人材・設備の spare capacity は短期効率を下げても、未知の shock に対する option value を持つ。

同時に、[UNESCO 2017 Recommendation](https://www.unesco.org/en/legal-affairs/recommendation-science-and-scientific-researchers) は public accountability と研究の自律性を両立させ、国家目標だけでなく、人類、将来世代、環境、国際社会への責任を含める。[UNESCO Open Science Recommendation (2021)](https://www.unesco.org/en/legal-affairs/recommendation-open-science) は collective benefit、equity、diversity、inclusion を掲げる。ゆえに国家は funder・rule setter・beneficiary の一つであって、唯一の welfare function ではない。

### 3.2 国家指標の Goodhart 化

R&D/GDP、paper share、citation share、patent count、university rank を政策 target にすると、次が起こりうる。

- input 増加が outcome 改善と同一視される。
- 国内 share を高めるため国際協力や小分野を犠牲にする。
- 短い citation window に有利な field へ資源が偏る。
- patent / paper の分割、低価値 output の増産、classification 操作が起きる。
- mission 指標に現れない basic research、maintenance、negative result が失われる。
- national benefit を上げるため、他国・少数者・将来世代へ cost を外部化する。

従って national dashboard は、**投入、能力、活動、知識 outcome、社会 outcome、分配、外部性**を別々に表示し、国別 league table の総合点を作らない。

### 3.3 Multi-principal welfare

ScienceUtopia では目的の owner を少なくとも次に分ける。

- researchers / research communities
- funders and governments
- mission beneficiaries and affected communities
- firms and infrastructure providers
- non-participating citizens
- other countries and the international knowledge commons
- future generations and the environment

各制度について `benefit_to[p]`、`burden_to[p]`、`voice_of[p]`、`exit_or_appeal[p]` を記録する。総和が正でも一主体へ重大な損害を集中させる制度を「最適」としない。権利・安全・minimum capability は constraint、残りを Pareto objective として扱う。

---

## 4. 推奨する目的ベクトル v1

現段階では次の九群を保持する。すべてを直ちに primary objective にするという意味ではない。

| ID | 構成概念 | 方向 | v1 operationalization | 現在の測定可能性 |
|---|---|---:|---|---|
| O1 | epistemic reliability | max | hidden truth 上の calibration、replication consistency、error rate | **未実装**：truth / replication が必要 |
| O2 | correction capacity | max | error detection、correction propagation、recovery time | **未実装**：claim lineage が必要 |
| O3 | useful exploration | portfolio | novelty × coherence、独立探索、minority branch survival | semantic novelty は可、coherence は要追加 |
| O4 | epistemic diversity | max/floor | variety–balance–disparity、method / lineage diversity | topic は可、distance taxonomy 要改善 |
| O5 | resource efficiency | max | verified knowledge / cost、latency、marginal return | cost は一部可、verified outcome は未実装 |
| O6 | equitable opportunity | max/floor | group 条件付き access、decision、resource、recognition、mobility | institution/resource/topicで一部可 |
| O7 | researcher sustainability | max/floor | cohort survival、workload、runway、independence time | retention/review burden は一部可 |
| O8 | resilience / capability | max | shock recovery、capability coverage、dependency、option reserve | scenario と capability model が必要 |
| O9 | mission / public value | context-specific | mission outcome、benefit/burden、externality、legitimacy | **未実装**：mission/outcome model が必要 |

### 4.1 Hard constraints の候補

- integrity / ledger reconciliation。
- deliberate fabrication や assurance deception を許さない。
- minimum evaluation / evidence coverage。
- agent ごとの minimum resource floor と最大 workload。
- protected group / institution / topic に対する重大な disparate harm の上限。
- academic freedom / minority branch / appeal route の最低水準。
- mission-specific safety と externality ceiling。

### 4.2 Diagnostics に留める指標

- acceptance rate、accepted count、mean review score。
- raw paper / citation / patent count。
- semantic novelty 単独。
- journal / venue prestige。
- total resources 単独。
- R&D/GDP に相当する input share。

---

## 5. 単一スカラー化を研究上の最終目的にしない理由

### 5.1 価値の重みは simulator からは導出できない

truth、speed、freedom、equity、mission outcome、safety の重みは規範的選択である。観測データから一意に学習できない。重みを隠して一つの loss にすると、政治的判断が技術的係数に見える。

### 5.2 尺度と時間軸が異なる

review burden は即時、publication は年単位、replication と citation は数年、社会 outcome と capability はさらに長い。標準化して足すと、window と scaling の選択が結論を支配する。

### 5.3 平均は分布的損害を消す

総便益が増えても、early-career、特定 institution、minority topic、将来世代へ損害が集中しうる。平均 score には、誰が得て誰が失ったかが残らない。

### 5.4 固定 scalar は攻略対象になる

複数指標でも固定 weight で和を取れば、新しい単一 proxy になる。optimizer は人間が想定しなかった相互作用や measurement error を利用できる。

### 5.5 非代償的な価値がある

integrity、重大な safety、minimum livelihood、appeal、研究の自由などは、paper 数や平均 novelty の増加で相殺できない。constraint または veto として扱うべきである。

### 5.6 一つの最適点より frontier が情報を持つ

Pareto frontier は、review burden を一単位下げるために diversity や reliability をどれほど失うかを示す。研究上重要なのは一位の制度より、trade-off surface と、制度が優位になる条件である。

### 推奨運用

- primary report は objective vector、Pareto front、制約違反を示す。
- optimizer の都合で scalar acquisition function を使う場合、weight を複数 sample し、全 metric を保存する。
- epsilon-constraint、lexicographic safety、Pareto Bayesian optimization を比較する。
- mean だけでなく median、下位10%、上位負担、Gini、group gap、worst-case / CVaR を保存する。
- 探索用 seed と confirmation / stress-test seed を分ける。
- 選択された制度は、metric に使わなかった shadow outcome と human-coded sample で再評価する。

---

## 6. 測定可能性と時間軸

### 6.1 時間 horizon を明示する

| Horizon | 主な観測 | 主な危険 |
|---|---|---|
| within-year | workload、資源、submission、decision、fallback | proxy が早いが epistemic outcome は見えない |
| 1–3 years | retention、topic portfolio、resubmission、初期 replication | cohort censoring、seed noise |
| 3–10 years | citation / uptake、career mobility、correction、field shift | model drift、simulation cost |
| shock / event time | mobilization、degradation、recovery | scenario choice 依存 |
| intergenerational | capability、externality、knowledge preservation | 強いモデル仮定が必要 |

一つの早期 proxy で長期 objective を置き換えず、`leading indicator -> intermediate outcome -> confirmatory outcome` の chain を記録する。右側 censoring を無視して最近の研究を不利にしない。

### 6.2 Metric card に必須の項目

各 metric は最低限、次を持つ。

```text
construct / normative rationale
unit and population
formula and estimator
data provenance and version
time horizon and citation/observation window
uncertainty, missingness, censoring
field / cohort normalization
subgroup and distributional slices
authorized decision use
known gaming and causal ambiguity
shadow metrics and falsification checks
owner, revision trigger, expiry
```

### 6.3 分布的影響の標準出力

各 objective について、可能な限り以下を出す。

- 全体 mean / median と seed interval。
- institution、career stage、initial resource、topic、agent type 別。
- bottom 10%、top 10%、zero-access / zero-resource population。
- within-group と between-group inequality。
- transition matrix：誰がどの状態からどこへ移動したか。
- benefit、burden、voice、appeal の主体別台帳。

---

## 7. 現行 metric cards への具体的提案

### MC-01 Topic Breadth AUC

維持するが、`topic_entropy_normalized` 単独から次へ拡張する。

- variety：occupied directions。
- balance：normalized entropy / concentration。
- disparity：topic embedding / taxonomy distance を使う Rao–Stirling 型指標。
- survival：minority direction が何年維持されたか。
- coherence：異分野要素が実際に統合されたか。

### MC-02 Submission Novelty Median

単調最大化をやめる。`novelty distribution × coherence / evidence quality` とし、conventionality と atypicality を併記する。accepted novelty は evaluator の selection effect、all-submission novelty は agent behavior として分ける。

### MC-03 Active Researcher Retention

単純 retention から cohort survival へ変更する。退出を一律に失敗とせず、resource starvation、overload、voluntary mobility、performance rule など理由別に記録する。workload と output floor を同時に見る。

### MC-04 Resource Equity AUC

`1 - Gini` 単独をやめ、resource floor、zero-resource rate、career-stage mobility、need-adjusted allocation、institution/topic 別 gap、total stock を併記する。完全平等を最大化せず、最低条件と分布的診断にする。

### MC-05 Review Burden

review 数だけでなく、application、review、revision、appeal の時間 cost と最大負担を含める。evaluation quality、decision stability、error、coverage を制約とし、burden をゼロへ最適化できないようにする。

### 新設候補

- **MC-06 Epistemic Reliability**：hidden truth / replication 導入後。
- **MC-07 Correction and Recovery**：誤り発見・訂正・依存更新の時間。
- **MC-08 Capability and Resilience**：shock 下の performance と回復。
- **MC-09 Metric Integrity**：proxy drift、gaming elasticity、holdout degradation。
- **MC-10 Public / Mission Value**：mission ごとの outcome と分布。汎用 score にはしない。

---

## 8. 最初の実験として現実的な構成

現行 simulator だけで真理性や社会的便益を測ったふりをしない。最初の black-box optimization は次の構成が妥当である。

### Primary objective vector

1. Rao–Stirling 型 topic diversity。
2. quality floor 付き novelty portfolio。
3. cohort researcher survival / sustainable workload。
4. resource floor と opportunity equity。
5. evaluation burden。

### Constraints

- integrity checks。
- minimum activity と evaluation coverage。
- maximum parse / transport fallback。
- maximum workload と minimum resource floor。

### Diagnostics / shadow metrics

- acceptance rate、paper count、review score。
- total resource、Gini、citation / uptake。
- metric-specific gaming signal。
- subgroup gaps と transition matrix。

### 並行して実装すべき measurement primitives

1. `claim` と evidence lineage。
2. hidden truth を持つ synthetic research task。
3. replication / reproduction event。
4. correction、retraction、downstream dependency update。
5. capability inventory と shock scenarios。
6. mission、beneficiary、externality、stakeholder voice。
7. decision-active metric registry と expiry。

これらが入った段階で、epistemic reliability、correction、resilience、public value を primary objective に昇格させる。

---

## 9. `ai-scientist-survey` 内の既存議論との接続

ローカルの `ai-scientist-survey` には、本メモと直接接続する先行整理がある。

- `/Users/shiro/unktok/dev/ai-scientist-survey/research/2026-09-10-scientific-value-constitution-method.md`：科学制度を単一目的関数にせず、不許容条件、最低限保存する能力、用途別目的、目的変更手続の四層で扱う。特に proxy sovereignty、metric expiry、allocation diversity、recovery time が本研究に有用。
- `/Users/shiro/unktok/dev/ai-scientist-survey/data/metric-constitution-prior-art-2026-10-05/README.md`：Leiden、DORA、metrology、program evaluation の prior art を比較し、測定の provenance だけでなく decision authorization と incentive footprint を結びつける必要を整理している。
- `/Users/shiro/unktok/dev/ai-scientist-survey/data/decision-active-metric-license-prototype-2026-10-05/README.md`：target、production、interpretation、decision、governance、reflexivity、time の contract を持つ metric prototype。
- `/Users/shiro/unktok/dev/ai-scientist-survey/data/reflexive-portfolio-capture-2026-10-05/README.md`：指標への局所適応と、科学 portfolio 全体の capture を区別し、完全な因果 chain を観測しなければ aggregate capture を主張できないとする。

これらから、ScienceUtopia の metric は単なる分析 column ではなく、**versioned、use-bounded、expiring institutional object** として実装するのが自然である。また、simulator は metric gaming を再現できるため、制度最適化だけでなく「測定制度が研究 portfolio をどう変えるか」を実験できる。

---

## 10. 参考文献・一次資料

### Science of Science / bibliometrics

- Fortunato, S. et al. (2018). “Science of science.” *Science*, 359, eaao0185. [doi:10.1126/science.aao0185](https://doi.org/10.1126/science.aao0185)
- Hicks, D., Wouters, P., Waltman, L., de Rijcke, S., & Rafols, I. (2015). “Bibliometrics: The Leiden Manifesto for research metrics.” *Nature*, 520, 429–431. [doi:10.1038/520429a](https://doi.org/10.1038/520429a)
- DORA (2012). “San Francisco Declaration on Research Assessment.” [Official declaration](https://sfdora.org/read/)
- DORA (2024). *Guidance on the responsible use of quantitative indicators in research assessment*. [doi:10.5281/zenodo.10979644](https://doi.org/10.5281/zenodo.10979644)

### Novelty、disruption、多様性

- Uzzi, B., Mukherjee, S., Stringer, M., & Jones, B. (2013). “Atypical combinations and scientific impact.” *Science*, 342, 468–472. [doi:10.1126/science.1240474](https://doi.org/10.1126/science.1240474)
- Wu, L., Wang, D., & Evans, J. A. (2019). “Large teams develop and small teams disrupt science and technology.” *Nature*, 566, 378–382. [doi:10.1038/s41586-019-0941-9](https://doi.org/10.1038/s41586-019-0941-9)
- Park, M., Leahey, E., & Funk, R. J. (2023). “Papers and patents are becoming less disruptive over time.” *Nature*, 613, 138–144. [doi:10.1038/s41586-022-05543-x](https://doi.org/10.1038/s41586-022-05543-x)
- Petersen, A. M., Arroyave, F., & Pammolli, F. (2024). “The disruption index is biased by citation inflation.” *Quantitative Science Studies*, 5, 936–953. [doi:10.1162/qss_a_00333](https://doi.org/10.1162/qss_a_00333)
- Stirling, A. (2007). “A general framework for analysing diversity in science, technology and society.” *Journal of the Royal Society Interface*, 4, 707–719. [doi:10.1098/rsif.2007.0213](https://doi.org/10.1098/rsif.2007.0213)
- Rafols, I., & Meyer, M. (2010). “Diversity and network coherence as indicators of interdisciplinarity.” *Scientometrics*, 82, 263–287. [doi:10.1007/s11192-009-0041-y](https://doi.org/10.1007/s11192-009-0041-y)
- Hofstra, B. et al. (2020). “The diversity–innovation paradox in science.” *PNAS*, 117, 9284–9291. [doi:10.1073/pnas.1915378117](https://doi.org/10.1073/pnas.1915378117)

### Reproducibility / replicability

- National Academies of Sciences, Engineering, and Medicine (2019). *Reproducibility and Replicability in Science*. [doi:10.17226/25303](https://doi.org/10.17226/25303)
- Open Science Collaboration (2015). “Estimating the reproducibility of psychological science.” *Science*, 349, aac4716. [doi:10.1126/science.aac4716](https://doi.org/10.1126/science.aac4716)
- Camerer, C. F. et al. (2018). “Evaluating the replicability of social science experiments in Nature and Science between 2010 and 2015.” *Nature Human Behaviour*, 2, 637–644. [doi:10.1038/s41562-018-0399-z](https://doi.org/10.1038/s41562-018-0399-z)
- Errington, T. M. et al. (2021). “Investigating the replicability of preclinical cancer biology.” *eLife*, 10, e71601. [doi:10.7554/eLife.71601](https://doi.org/10.7554/eLife.71601)

### Efficiency、公平性、持続可能性

- Fortin, J.-M., & Currie, D. J. (2013). “Big Science vs. Little Science: How Scientific Impact Scales with Funding.” *PLOS ONE*, 8, e65263. [doi:10.1371/journal.pone.0065263](https://doi.org/10.1371/journal.pone.0065263)
- Ginther, D. K. et al. (2011). “Race, ethnicity, and NIH research awards.” *Science*, 333, 1015–1019. [doi:10.1126/science.1196783](https://doi.org/10.1126/science.1196783)
- Hoppe, T. A. et al. (2019). “Topic choice contributes to the lower rate of NIH awards to African-American/black scientists.” *Science Advances*, 5, eaaw7238. [doi:10.1126/sciadv.aaw7238](https://doi.org/10.1126/sciadv.aaw7238)
- Tomkins, A., Zhang, M., & Heavlin, W. D. (2017). “Reviewer bias in single- versus double-blind peer review.” *PNAS*, 114, 12708–12713. [doi:10.1073/pnas.1707323114](https://doi.org/10.1073/pnas.1707323114)
- Wellcome (2020). *What researchers think about the culture they work in*. [Official report](https://wellcome.org/insights/reports/what-researchers-think-about-research-culture)

### Goodhart / indicator effects

- Campbell, D. T. (1979). “Assessing the impact of planned social change.” *Evaluation and Program Planning*, 2, 67–90. [doi:10.1016/0149-7189(79)90048-X](https://doi.org/10.1016/0149-7189(79)90048-X)
- Butler, L. (2003). “Modifying publication practices in response to funding formulas.” *Research Evaluation*, 12, 39–46. [doi:10.3152/147154403781776780](https://doi.org/10.3152/147154403781776780)
- Fire, M., & Guestrin, C. (2019). “Over-optimization of academic publishing metrics: observing Goodhart’s Law in action.” *GigaScience*, 8, giz053. [doi:10.1093/gigascience/giz053](https://doi.org/10.1093/gigascience/giz053)

### 国家科学政策・公共価値

- OECD (2015). *Frascati Manual 2015: Guidelines for Collecting and Reporting Data on Research and Experimental Development*. [doi:10.1787/9789264239012-en](https://doi.org/10.1787/9789264239012-en)
- OECD/Eurostat (2018). *Oslo Manual 2018: Guidelines for Collecting, Reporting and Using Data on Innovation*. [doi:10.1787/9789264304604-en](https://doi.org/10.1787/9789264304604-en)
- Mazzucato, M. / European Commission (2018). *Mission-Oriented Research & Innovation in the European Union*. [Official publication](https://research-and-innovation.ec.europa.eu/knowledge-publications-tools-and-data/publications/all-publications/mission-oriented-research-innovation-eu-problem-solving-approach-fuel-innovation-led-growth_en)
- OECD (2023). *Science, Technology and Innovation Outlook 2023*. [doi:10.1787/0b55736e-en](https://doi.org/10.1787/0b55736e-en)
- OECD (2025). *Science, Technology and Innovation Outlook 2025: How science systems need to adapt to support transformative change*. [Official chapter](https://www.oecd.org/en/publications/oecd-science-technology-and-innovation-outlook-2025_5fe57b90-en/full-report/how-science-systems-need-to-adapt-to-support-transformative-change_5e31f189.html)
- National Science Board / NCSES (2026). *The State of U.S. Science and Engineering 2026*. [Official indicators report](https://ncses.nsf.gov/pubs/nsbsep20261)
- UNESCO (2017). *Recommendation on Science and Scientific Researchers*. [Official recommendation](https://www.unesco.org/en/legal-affairs/recommendation-science-and-scientific-researchers)
- UNESCO (2021). *Recommendation on Open Science*. [Official recommendation](https://www.unesco.org/en/legal-affairs/recommendation-open-science)

## Evidence boundary

このメモは目的関数設計のための purposive review であり、systematic review や effect-size meta-analysis ではない。引用した研究の多くは特定分野・国・時期の observational study であり、ScienceUtopia 内で同じ因果効果が再現される保証はない。ここでの利用目的は、単一 proxy の危険を減らし、測定すべき構成概念、反証条件、分布、時間軸を明示することである。

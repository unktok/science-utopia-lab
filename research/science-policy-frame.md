# 科学政策としての目的設定

## なぜ同じ問題なのか

ScienceUtopia全体の目的関数を決めることは、国家、大学、研究コミュニティ、市民が「良い科学システムとは何か」を定義することに近い。研究費配分、評価制度、人材政策、publication、重点領域は、いずれも科学システムの状態遷移へ介入する政策である。

したがって、この研究は単なるhyperparameter optimizationではなく、計算可能な科学政策・制度設計の実験でもある。

## ただし「国家の効用」を唯一の目的にしない

国家の政策指標は重要な観察対象だが、そのまま唯一の目的関数にはしない。

- 論文数、特許、引用、ランキングは測りやすいが、代理指標として攻略される。
- 重点分野への集中は短期的成果を増やしても、探索の多様性と長期的option valueを失わせうる。
- 経済・安全保障上の価値と、公開性、国際協力、基礎研究の自律性は衝突しうる。
- 平均的な生産性の向上が、若手、少数分野、小規模機関の退出を伴う場合がある。
- 現在の政策主体が価値を認識できない未知の研究を、目的関数が排除しうる。

国家は一つのstakeholderであり、科学者、研究機関、市民、将来世代、国際的な知識commonsも別のstakeholderとして扱う。

## 目的の階層

目的関数を一つの数へ直結させず、少なくとも次の階層を区別する。

### 1. Epistemic value

- 信頼できる知識の増加
- 誤りの発見と訂正
- 新規性、説明力、再現性
- 問題・方法・分野の多様性

### 2. Scientific capacity

- 人材、技能、設備、データ、institutional memory
- 次世代研究者の参入と育成
- 長期研究を継続できる余力
- shockや失敗に対するresilience

### 3. Public and mission value

- 健康、環境、教育、経済などへの公共的寄与
- 社会的課題へ応答する能力
- 緊急時のmission遂行と平時の探索余地

### 4. Distribution and legitimacy

- 資源・参加機会・発言力の分布
- 地域、機関、分野、career stage間の公平性
- decision provenance、説明可能性、contestability
- 市民と研究者から見た制度の正統性

### 5. Constitutional constraints

- 研究の自律性と学問の自由
- 不正、利益相反、差別への防御
- 公開性、privacy、安全保障の境界
- 取り返しのつかない集中やlock-inの回避

最後の層は、他の成果と交換可能な小さなpenaltyではなく、hard constraintまたはlexicographic priorityとして扱う場合がある。

## シミュレーションでの表現

```text
stakeholder values
      ↓
goal hierarchy ── constitutional constraints
      ↓
measurable constructs
      ↓
simulation metrics + uncertainty
      ↓
multi-objective / constrained optimization
      ↓
policy alternatives and trade-offs
```

「社会的価値」から「citation count」へ直接落とさない。value -> construct -> observable -> metricという翻訳過程をmetric cardで明示し、各段階の仮定を監査する。

## 分析の単位

結果は「この制度が最適」で終えず、次の形で議論する。

- どのstakeholderにとって何が改善したか
- どの環境条件・時間幅で成り立つか
- 誰が費用とriskを負担したか
- どの価値間にtrade-offが現れたか
- 制度が指標を攻略した可能性はないか
- 現実の政策判断へ移す前に何が未表現か

## 研究への含意

Science of Science、科学技術政策、economics of science、responsible research and innovationの議論を、objective evaluatorの設計根拠として使う。一方、既存の国家指標は「候補metric」と「歴史的に採用された価値判断」の両方として研究し、正解としては扱わない。


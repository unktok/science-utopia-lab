# 最適化研究計画

> 歴史的な初期計画。現在の方針は[設計見直し](search-design-review.md)と
> [研究憲章](charter.md)を参照。以下の公平性・参加率・複雑さ等の制約や段階順は
> 新規実験のデフォルトではない。実験で宣言したLossSpecだけで最適化し、
> 微分可能化や大規模seed比較を自由な制度設計の前提にしない。

## 問題設定

制度設計 `θ` に対し、複数 seed と環境条件でシミュレーションし、軌跡 `τ` を得る。

\[
\min_{\theta \in \Theta} \; \mathbb{E}_{c,\omega}[L(M(F(\theta,c,\omega)))]
\]

ただし、初期段階では単一損失へ固定せず、目的ベクトルと制約を保持する。

一つの optimization campaign 内では目的、制約、evaluator を固定し、変化させるのは科学システム design `θ` だけとする。目的定義を変更する場合は別 revision とし、変更前後の結果を同じ探索系列として順位付けしない。

```text
maximize: epistemic progress, robustness, diversity, useful novelty
minimize: resource waste, delay, inequality, reviewer burden, lock-in
subject to: budget, capacity, participation, safety, minimum field coverage
```

## 指標候補

### Epistemic outcomes

- 新規性と既存知識からの距離
- 正確性・再現可能性の proxy
- 独立に発見された知見の一致
- 分野・方法・仮説の多様性
- 長期的に残る知識と誤りの訂正速度

### System performance

- 資源あたりの有用成果
- idea から公開・検証までの遅延
- reviewer / evaluator burden
- 失敗研究から得られた情報の再利用
- shock、能力分布、LLM変更に対する頑健性

### Distribution and participation

- 研究者・機関・分野間の資源分布
- entrant の生存、mobility、参加機会
- 少数派仮説が検討される確率
- prestige と成果の自己強化、集中度、lock-in

すべて simulator 内 proxy である。観測値の定義、測定誤差、攻略可能性を metric card として別途管理する。

## ブラックボックス最適化の段階

### Stage A — 感度とノイズ床

- 同一 `θ` を複数 seed で反復し、実行時間・分散・失敗率を測る。
- Latin hypercube / Sobol で低次元空間を被覆する。
- 単変量感度と相互作用を可視化する。

### Stage B — 低次元の逐次探索

- random / quasi-random を必須 baseline とする。
- Bayesian optimization、TPE、CMA-ES を同一予算で比較する。
- 早期年を低 fidelity、長期 run を高 fidelity とする multi-fidelity を試す。

### Stage C — 多目的・制約付き探索

- Pareto front と hypervolume を報告する。
- 最低公平性、最低多様性などを制約として扱う。
- optimizer が作った極端な制度を simulation invariant と adversarial scenario で検査する。

### Stage D — 構造探索

- 機構グラフの primitive を列挙する。
- categorical / graph / program search を使い、数値と構造を共同探索する。
- 複雑さ penalty と解釈可能性を目的または制約に加える。

## 微分可能化の研究線

「シミュレータ全体が厳密に微分可能」であることを最初から要求しない。次の順に勾配の有用性を検証する。

1. **微分可能な局所機構**  
   評価集約や資金配分のみを連続関数にし、固定された軌跡上で学習する。
2. **離散選択の緩和**  
   soft threshold、Gumbel-Softmax、straight-through estimator を用いる。
3. **軌跡の代理モデル**  
   `θ -> outcomes` の differentiable surrogate を simulation data から学習する。
4. **方策勾配 / evolution strategies**  
   pathwise gradient が得られない部分を score-function estimator や ES で扱う。
5. **hybrid optimization**  
   surrogate gradient で候補を作り、真の simulator で評価・補正する。

重要な検証は、近似目的上の改善ではなく、未使用 seed の真の simulator 上で改善が転移するかである。勾配方向と有限差分、局所順位相関、out-of-distribution 条件での失敗も測る。

## 実験統計

- 独立単位は seed / world。
- 探索、選択、最終評価の seed を分離する。
- optimizer 間比較は同じ初期 design と計算予算を使う。
- best-so-far curve、regret、hypervolume、wall-clock、failure rate を報告する。
- 選択後推論の楽観バイアスを避けるため、選ばれた制度を新規 seed で再評価する。
- 一つのモデルに overfit しないよう、可能になった段階で model / prompt / dataset shift を行う。

## 最初の具体的課題

最初は「構造を固定した5〜8個の制度パラメータ」と「3〜5個の未集約指標」に限定する。現行査読と funding のうち、挙動が明確で実行時に変更可能なパラメータを registry 化し、random/Sobol baseline を作る。ここで測定、cache、run registry、失敗回復を固めてから、評価機構の交換へ進む。

## 現在の実装境界

evaluator 1.0で評価したv0 artifactは、aggregateの参加継続率、topic entropy、review burdenとtechnical integrityを計算できるが、protected resource sliceは`unknown`のまま凍結する。measurement-complete v1では、outcomeより前に固定したresource bandとreview-action eventを記録し、evaluator 1.1でslice-level objectiveを計算する。`study-v1-smoke.json`はdesignごとに最低5 exploration seedsを使い、v0とv1を同じ探索系列として順位付けしない。


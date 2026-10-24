# 科学システムの抽象モデル

## 基本表現

科学システムを、状態を持つ型付き機構グラフとして表す。

- **Agents**: 研究者、査読者、編集者、資金配分者、政府、市民、企業、AI
- **Artifacts**: 仮説、研究計画、論文、データ、コード、査読、資金申請、政策
- **State**: 知識、資源、評判、能力、ネットワーク、公開記録、時間
- **Mechanisms**: 評価、公開、資金、雇用、教育、協働、情報流通、統治
- **Channels**: artifact、score、decision、feedback、resource、signal、constraint
- **Observables**: 科学的成果、効率、公平性、頑健性、参加者の状態

各機構は概念上、次の契約を持つ。

```text
Mechanism
  input_schema
  state_schema
  parameters
  eligibility(state, event)
  transition(inputs, state, rng) -> outputs, next_state, audit
  differentiable_view?       # 任意の連続緩和または代理
  validation_invariants
```

この契約により、「査読」は simulator 全体へ埋め込まれた固定フェーズではなく、交換可能な一機構になる。

## Evaluation System

評価システムを次の5段階へ分解する。

1. **Evidence formation**: 何を評価対象として提示できるか
2. **Assessor selection**: 誰または何が評価するか
3. **Assessment**: スコア、順位、議論、予測などをどう生成するか
4. **Aggregation / decision**: 個々の評価をどう集約し、何を決定するか
5. **Consequences / feedback**: 公開、資源、評判、改善機会へどう作用するか

現在の peer review + acceptance threshold は一つの instance にすぎない。比較候補には以下を含める。

- 二重盲検・単盲検・公開査読
- threshold、定員制、順位制、部分抽選
- 継続的な事後評価と更新可能な公開
- prediction market または将来再現性の予測
- 独立パネル、群衆、AI、人間とAIの混成
- 多段階評価、appeal、再提出、条件付き採択
- 評価を持たず、公開後の利用や再現だけで信号を作る制度

## システム構造の自由度

最終的な設計変数は数値だけではない。

- **Parametric**: 採択率、panel size、予算、遅延、重み
- **Categorical**: reviewer policy、集約規則、公開方式
- **Topological**: 機構の有無、順序、接続、feedback loop
- **Programmatic**: 条件分岐、時間変化、適応的ルール
- **Learned**: neural policy、scoring model、resource allocator

初期実装では型付き設定と registry を使い、後に構造探索へ拡張する。任意コード生成から始めると比較可能性、安全性、監査可能性を失うため、まず有限個の型付き primitive の合成として表現する。

## 現行コードからの移行方針

1. 現行イベントと状態遷移を観測し、暗黙の依存関係を列挙する。
2. 現行の査読・採択挙動を `LegacyPeerReviewEvaluation` として固定する。
3. 入出力 schema と不変条件を contract test にする。
4. 第二の単純な instance（例: score + lottery）を実装し、交換可能性を証明する。
5. publication と funding を別機構へ切り離す。
6. 機構グラフの設定、検証、可視化を追加する。

## 必須の不変条件

- 資源の生成・移動・消滅は ledger で説明できる。
- decision の根拠と入力 artifact を追跡できる。
- 同一設定、同一 seed、同一応答 cache から同じ状態遷移を再生できる。
- 制度が情報へアクセスできる時点を明示し、未来情報の漏洩を防ぐ。
- agent identity や institution による不当な自己評価・利益相反を設定可能かつ監査可能にする。


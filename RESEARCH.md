# Science Utopia Lab

このリポジトリは、ScienceUtopia を単に再実行するための fork ではない。科学の制度設計を、シミュレーション・最適化・機構設計・インタラクティブなゲームを通じて研究するための実験基盤である。

## 研究の中心命題

科学システムを、研究者だけでなく、評価、公開、資金配分、政府、情報流通などの機構を含む設計可能なシステムとして扱う。その設計空間を探索し、どの制度がどの条件で、どのような科学的・社会的帰結を生むかを調べる。

現時点の研究トラックは次の4つである。

1. **ScienceUtopia 全体のブラックボックス最適化**  
   シミュレータを確率的な関数とみなし、制度パラメータや構造を入力、科学的成果や公平性などを出力として最適化する。
2. **評価システムの抽象化と機構探索**  
   現在の査読・採択を一つの具体例に格下げし、「研究成果を評価し、その後の状態へ作用する機構」自体を交換・合成・探索できるようにする。
3. **微分可能な科学制度**  
   離散的で非微分可能な制度やシミュレーションを、緩和、代理モデル、学習可能な機構で近似し、勾配に基づく制度設計がどこまで可能か検証する。
4. **ScienceUtopia をゲームにする**  
   エージェントと制度が動いていることを理解・操作できるピクセルアート調のゲーム体験を作り、可視化、教育、仮説形成、人間参加型実験へつなげる。

## ノート体系

- [研究憲章](research/charter.md): 目的、問い、原則、成功条件
- [科学政策としての目的設定](research/science-policy-frame.md): stakeholder、公共価値、能力、自律性
- [科学システムの抽象モデル](research/system-model.md): 機構、状態、インターフェース、設計空間
- [最適化研究計画](research/optimization.md): 目的関数、ブラックボックス最適化、微分可能化
- [Design Space v0](research/design-space-v0.md): 最初の8変数とfidelity
- [Metric Cards v0](research/metric-cards-v0.md): 指標の定義、集約、攻略リスク
- [Metric Constitution v1](research/metric-constitution-v1.md): 制約、能力、commitment、評価器統治の実験契約
- [現行パラメータ棚卸し](research/parameter-inventory.md): 採用、固定、延期、実行設定の分類
- [複数seed実験harness](research/harness.md): 計画、registry、再試行、基本集計
- [ゲーム構想](research/game.md): 研究基盤とゲーム体験の接続
- [ロードマップ](research/roadmap.md): 段階、成果物、ゲート
- [Milestone 1 総括](research/milestones/2026-10-26-first-system-comparison.md):
  ローカル基盤から最初の5-seed制度比較までの成果、限界、次段階
- [実験テンプレート](research/protocols/experiment-template.md): 実験前後に必ず残す項目
- [意思決定ログ](research/decisions/): 長期的に効く設計判断
- [Science of Science 調査](research/literature/science-of-science-objectives.md): 外部文献に基づく目的関数候補
- [`ai-scientist-survey` 調査](research/literature/ai-scientist-survey-objectives.md): 既存内部議論との接続
- [日次ログ](research/logbook/): 作業、観察、疑問、次の一手
- [実行記録](research/runs/): 再現可能なベースラインと実験結果

## 記録の原則

- 実験は、可能な限り実行前に仮説、操作変数、固定条件、評価指標、停止条件を記録する。
- 独立な seed / world を反復単位とし、エージェントや年を独立標本として扱わない。
- 生の生成物は `outputs/` に置き、Git には設定、要約、manifest、ハッシュ、解析コードを残す。
- 「最適値」だけでなく、Pareto front、失敗条件、感度、分布、制度が機能する範囲を報告する。
- 指標の改善を科学そのものの改善と同一視しない。Goodhart 化、代理指標の攻略、モデル固有の癖を常に検査する。
- 上流 ScienceUtopia との差分、モデル、データ revision、実行環境、推論 backend を記録する。

## 現在地

2026-10-26時点で、Qwen3-8Bのローカル実行、seed反復harness、Metric
Constitution、protected-slice measurement、funding reliability、4年fidelity、
global reviewer assignmentを実装し、最初のpaired制度比較まで完了した。

資金配分枠を30%から50%へ増やした候補をbaselineと同じ5 seedsで比較した結果、
aggregate参加率は平均+0.08、初期低資源層は+0.16、査読負担はaggregate
−0.122、低資源層−0.208だった。一方で各worldのgrant incomeは+160であり、
これは無条件の優位ではなくresource-for-continuity trade-offである。

baseline seed 107が固定capability floorを下回ったため、事前規則上のformal
comparisonは`incomplete`であり、結果は5-pair diagnostic evidenceとして保持する。
次はcapability violationの扱いを事前登録し、未使用confirmation seedsで同じ二制度を
再評価する。全体の経緯、成果、限界は
[Milestone 1 総括](research/milestones/2026-10-26-first-system-comparison.md)を参照する。


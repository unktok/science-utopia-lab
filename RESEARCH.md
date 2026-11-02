# Science Utopia Lab

このリポジトリは、ScienceUtopia を単に再実行するための fork ではない。科学の制度設計を、シミュレーション・最適化・機構設計・インタラクティブなゲームを通じて研究するための実験基盤である。

## 研究の中心命題

科学システムを、研究者だけでなく、評価、公開、資金配分、政府、情報流通などの機構を含む設計可能なシステムとして扱う。その設計空間を探索し、どの制度がどの条件で、どのような科学的・社会的帰結を生むかを調べる。

元の研究者世界も単純すぎるため、最終的な設計空間の上限にはしない。その世界を
包含する一つのinstanceとして再現でき、さらにactor、成果物、制度の実装と関係、
過程を拡張できることを目指す。「小規模で試す」は人数・期間を小さくする意味で、
研究活動をもっと簡単な数値世界に置き換える意味ではない。

現時点の研究トラックは次の4つである。

1. **科学システム全体の抽象化**
   評価、公開、資金、統治、情報流通などを任意に構成できる`SystemSpec`として表す。各機構は存在しても存在しなくてもよく、査読制度は多数ある具体例の一つにすぎない。
2. **ScienceUtopia 全体のブラックボックス最適化**
   シミュレータを確率的な関数とみなし、`SystemSpec`のパラメータ・機構選択・接続構造を入力、科学的・社会的帰結を出力として最適化する。
3. **利用できる勾配・勾配推定による制度最適化**
   適切な部分の微分可能表現に加え、離散的な世界の期待損失を尤度比などで勾配推定する。世界全体や固定LLMの微分可能化を必須にせず、ブラックボックス評価と組み合わせる。
4. **ScienceUtopia をゲームにする**  
   エージェントと制度が動いていることを理解・操作できるピクセルアート調のゲーム体験を作り、可視化、教育、仮説形成、人間参加型実験へつなげる。

## ノート体系

- [研究INDEX](research/INDEX.md): loss、metrics、optimizer、protocol、resultの入口
- [プロジェクト全体図](research/program-map.md): 目的、中心実験、依存関係、並列トラックの現在地
- [現在地](research/STATUS.md): 実装済み、未統合、未着手の一覧
- [閉ループ最適化contract](research/objectives/losses/closed-loop-v1.md):
  optimization lossとheld-out evaluation metricsの分離
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
- [Milestone 2 confirmation比較](research/milestones/2026-10-27-confirmation-comparison.md):
  未使用seedによる最初の候補の確認、棄却判断、次campaignへの境界
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

## 現在地（2026-11-02、v13の自由な制度設計＋内部最適化が完走）

[v13の有限ゴール](research/milestones/2026-11-02-nested-free-institution-v13.md)は、
自由な制度コード・構成の生成と、その制度が宣言した分布内の期待損失勾配更新を
同じ元の研究者世界でつなぐこと。2目的それぞれについて、G0の2候補→1回の更新→
更新後1候補→自己履歴を受けた自由なG1再設計1候補を実行した。
合計8世界・592件の新しいQwen応答で打ち止めとし、人数・期間・seed数は増やしていない。

採択数lossは`[-7,-7,-6,-10]`、明示的な査読生産proxyは`[-17,-12.5,-10,-18]`。
両方で内部更新直後の1候補は以前の最良値を下回り、後の自由なコード再設計が
観測最良値を改善した。査読側は自己履歴の評価点から査読者を選ぶ制度になった。
これは目的関数が生むインセンティブの観察であり、研究の質・一般化・勾配手法の
優位性・発明者自身の改善を立証したものではない。

元世界の実際の査読タスクを生成コードが割り当てる接続口と、完全な変更前研究計画を
含む由来証明も追加した。全129 rawを変えず独立再計測し、227 source blob、
40コード実行、16計画変更、16配分イベント、28査読を照合した。
英語の既存サイバーパンクUIで経路・コード・配線・作用を実データから閲覧できる。
ローカル編集/分岐は実行・採用の権限と分離している。
[結果と限界](research/results/native-nested-search-v13-a1.md)、
[最新STATUS](research/STATUS.md)、[全体のゴール対応表](research/program-map.md)を参照。

## 前段階の現在地 — v8の目的条件付き構造探索（履歴）

[今回のゴール](research/milestones/2026-11-02-objective-structure-and-response-v8.md)は、
少数規模のまま、制度コード・機構の追加削除・配線・活動プロセスを実際に変え、
異なる目的関数でどんなシステムと探索パスが生まれるかを比較すること。
2目的×2世代×2候補の8世界・734件の実Qwen応答まで完走・独立監査した。
人数・期間・seed数は増やしていない。
全候補の同じ指標群での相互評価は開発データの再利用であり、held-outではない。

構造の記述・元世界での作用・再開、独立監査、英語の比較UIを実装・検証した。
採択数lossは`[-9,-9,-10,-10]`へ改善し、もう一方は`[0,0,.4833,.4833]`で
以前の候補が最良のままだった。実際に制度コード・ノード・配線が変わり、
16〜18ノードの異なる構造を実行した。全候補・同点・相互評価を保存し、
132個のrawファイルを変えずに監査した。[結果と限界](research/results/native-objective-structure-v8-a2.md)。
英語UIへの実データ接続・画面検証、37ページの原稿更新・PDF全ページ確認まで完了した。
[sourceと成果物の検証記録](research/results/objective-structure-v8-verification.json)も保存した。
並行した微分側は元世界の7つの6年試行で、応答の
変化・整数parser・制度の再帰実行を結ぶ局所表現を検証した。ただしこちらは
スクリプト応答の実装QAで、Qwenへの忠実性ではない。有限区間の損失変化を
よく再現しても、勾配から選んだ候補は同点だった。条件付き勾配、応答近似の
勾配、世界全体のpathwise微分を同じものとは扱わない。
[最新STATUS](research/STATUS.md)を実行状況の正本とする。

## 前段階の現在地 — v7の通常実装残件を完了（履歴）

[固定した非スケール実装残件表](research/milestones/2026-11-02-non-scale-implementation-closure-v7.md)
を正本とする。v6の区切りを「スケール前の通常実装がすべて終わった」とは扱わない。
元の研究者世界を保ち、次の経路を実装・結合テストした。

- 任意の型・役割の永続actor、科学成果物、独自状態を定義し、自由コードから
  本物の研究者入力・研究計画・資源へ作用する。新しい型付きアクションも登録できる。
- 依存関係を明示したプロセス、条件分岐、boundedな活動反復、状態に基づく停止。
  ラップしたコード・LLM・Tensorも導入・コールド再開時に検証する。
- 実測lossを次の自由コード／配線／探索語彙の生成へ渡し、連続値と離散構造を
  black-box／score／hybridで探索し、設計戦略の分布も更新できる。
- attention・routing・メモリ操作・明示noiseによるsamplingのbackward、
  制度へのprojection、元世界での再実行、局所的な忠実性の失敗検出。

元の6年間の研究世界を使う小規模テストに加え、実Qwenの統合pilot、独立監査、
英語ゲームUIへの実データ接続、31ページの原稿・PDF検証まで完了した。
実pilotは4つのreset世界・342応答で、実測lossを受けた自由コードの改訂と
探索分布更新まで実行した。lossは`[-1.2,-0.2,-0.8,-0.2]`で最良値は更新しなかった。
[結果と限界](research/results/native-open-integrated-v7-a2.md)、
[source別の検証記録](research/results/non-scale-closure-v7-verification.json)を参照。
テスト応答と実Qwen、条件付き表現の勾配と世界全体の微分を混同しない。
新actorは任意の制度主体であり、自動的に新しいLLM研究者になるわけではない。
設計戦略更新の機能は、設計者自身の改善の成功を意味しない。

## 前段階の現在地 — v6（履歴）

[非スケール統合 v6 の完了条件](research/milestones/2026-11-01-non-scale-completion-v6.md)、
[全体目標との対応表](research/program-map.md)、[最新STATUS](research/STATUS.md)
を現在地の正本とする。元の研究者世界を保ち、研究計画・実論文をtypedな入出力として
開く基盤、任意コード/protocol/配線の分布勾配、lossを見た同一社会の制度改訂、
英語ゲームUIからの正確な導入確認を小規模で統合・実行した。単体テスト、実Qwen実行、
独立監査、目的関数上の改善、科学的有用性を同じ「完了」にまとめない。

元の世界全体やLLMの入力応答を通るpathwise微分、新しいactor/研究活動の意味論、
設計者自身の再帰的改善は未達である。スケールアップをこれらの代わりにはしない。
lossに書かれていない公平性・参加率・品質の制約も追加しない。

## 前段階の現在地 — v5（履歴）

[全体目標・実装・実証・未達の対応表](research/milestones/2026-11-01-objective-conditioned-design-v5.md)
と[最新STATUS](research/STATUS.md)を現在地の正本とする。スケールアップではなく、
元の研究者世界を包含するまま、明示lossに基づくコード・protocol・配線の再設計を
実際の結果と閉じることを優先する。暗黙のfairness/参加率/品質gateは追加しない。

自由なコードとグラフを記述するAPI、実測結果を受けた再提案、同じ社会の永続的な
制度移行、英語ピクセルアートの編集・実行・結果表示基盤は実装済み。ただし
ローカルQwenによる広い制度生成は、v5の3試行でも候補の実行まで到達せず失敗した。
設計者と研究者を分けたCodex設計者／Qwen研究者の別pilotは、5世界・285応答で完了。
実損失は`[-1,-3,-3]`と`[.70,.45,.45]`で、新しい2機構/protocolへの改訂も実行した。
後者は同点で、構造上の改善は示していない。全97 raw filesの不変性まで独立監査した。
[今回の結果](research/results/native-external-objectives-v5-a1.md)を参照。
これをQwenによる発明や、科学的に有効な新制度の発見と混同しない。
任意制度から本物の研究者・台帳へ資源移転を適用する別capabilityも実装・QAしたが、
これは新しいlive-Qwen最適化結果ではない。

微分側は新しい元世界2回の損失から実際の確率勾配更新まで実行・監査したが、
同じ制度を2回抽選したため比較上の改善は示せていない。条件付きsoft制度、元世界
損失による分布勾配、忠実性検証に失敗した応答近似を区別する。任意Pythonや
研究者の入力応答を含む世界全体のpathwise backpropagationは未達である。
ゲームUIはv4を維持し、今回は新しい画面やプレイ実証を追加したとは扱わない。

## 以前の現在地（2026-10-31、履歴）

固定topologyのQwen3-8B版では、目的関数ごとの閉ループ探索と共通held-out比較まで
完了した。別の小規模数値backendでは、新しい機構をASTプログラムとして生成し、
node/edge、遅延、処理順序を変更して実行するところまで進んだ。そのworld全体の
連続緩和に対するbackpropagationも実行・数値差分検証済みである。

Qwenが生成したSignalBoost規則と初期研究者特徴を凍結し、production/burdenの
2目的、6人、3期、2development worldsで探索・離散評価・再現確認・game表示を
完了した。ただし、この数値worldは手法検証であり、元の研究者世界の拡張を
達成した証拠としては扱わない。
[今回の結果](research/results/generative-program-world-v1.md)と
[最新の能力表](research/STATUS.md)を参照する。

NativeScienceKernelでは元のSimulationを一般グラフから呼び、新しいPython/LLM
制度と新protocolを実際の研究者入力・出版状態へ接続する経路を追加した。
元の6年実行との互換性、接続・遅延、査読除去と実装置換、checkpoint/replayをQAした。
新actorの永続化は拡張できるが、その行動まで自動的に実装されるわけではない。
任意の研究過程の置換と世界全体の微分可能化は未完である。
[設計と制限](research/components/native-science-kernel-v1.md)に範囲を記録する。

## 基礎実験の履歴（2026-10-27以降）

2026-10-27時点で、Qwen3-8Bのローカル実行、seed反復harness、Metric
Constitution、protected-slice measurement、funding reliability、4年fidelity、
global reviewer assignmentを実装し、最初の候補のuntouched-seed confirmation
まで完了した。

資金配分枠を30%から50%へ増やした候補をbaselineと同じ5 seedsで比較した結果、
aggregate参加率は平均+0.08、初期低資源層は+0.16、査読負担はaggregate
−0.122、低資源層−0.208だった。一方で各worldのgrant incomeは+160であり、
これは無条件の優位ではなくresource-for-continuity trade-offである。

その後、capability failureを制度のoutcomeとして保持する規則を事前登録し、未使用の
confirmation seeds 401, 409, 419, 421, 431で同じ比較を行った。候補は全5 seedで
capability floorを満たし、平均参加率は全体+0.06、低資源層+0.12だった。しかし
seed 431では低資源層参加率が0.8から0.6へ低下し、「負のprotected-slice pairを
許さない」という固定gateに違反した。したがって候補は`not_confirmed`であり、平均値で
この害を相殺しない。詳細は
[Milestone 2](research/milestones/2026-10-27-confirmation-comparison.md)を参照する。

これまでの二条件は手作業で選んだ二つのdesign pointの反復評価であり、design
spaceの探索ではなかった。その後、optimizerが直接参照するversioned lossと、
候補凍結後にheld-out worldsで報告するevaluation metricsを分離し、
`suggest → simulate → observe → suggest`の最初の閉ループをQwen3-8Bで完成させた。
固定トポロジー上の8変数を`SystemSpec`へ持ち上げ、2つの初期候補と、低lossの
観測に依存する1つの適応候補を各3 seedsで評価した。適応候補は親候補と完全に同点で、
改善は主張しない。この同点はone-year smoke fidelityのengineering lossが異なる
制度を区別できない場合があることを示した。
過去campaignのprotected-slice vetoは歴史的promotion policyとして保存するが、
新しいoptimizerの既定constraintにはしない。

whole-system `SystemSpec`のtyped graph、validator、legacy compilerと、
不透明な`SystemSpec`を扱うblack-box `ask/tell`境界を実装した。optimizerは
simulator内部や勾配を必要とせず、現行8変数を制限版SystemSpecとして提案し、
観測lossに依存した次候補を生成できる。実シミュレーションcampaignとの永続的な
controller接続とversioned `LossSpec`も動作している。optimization seeds 503, 509,
521で9 runsが完了し、held-out seeds 523, 541, 547は未使用のまま保存されている。
これはengineering demonstrationであり、科学政策上の制度順位ではない。次の中心課題は、
目的とheld-out metricsの科学的妥当性、一般graph executor、構造探索、微分可能な緩和を
設計することである。

並行してcanonical replayから生成した状態だけを描画するpixel-art風game UIの
最初のvertical sliceを実装した。ローカルOllamaのworkers 1/2/4 benchmarkでは、
4 workersは安定動作したがthroughputは1.016倍に留まったため、単一endpointを
4倍速とは見積もらない。


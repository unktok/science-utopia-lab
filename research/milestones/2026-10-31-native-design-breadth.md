# 元の研究世界を包含する設計ラボ — 現状と次の実装ゲート

更新: 2026-10-31。Decision 0025/0026を現在の実装へ対応させる。

## 一つの研究対象、二つの独立した軸

目的は、宣言した目的関数をよく実現する**科学システムそのもの**を探すこと。
既存制度の少数候補を評価するだけでも、元より単純な数値世界を最適化するだけでもない。
元の研究者・研究方向・実際の文献検索・投稿・査読・出版・資金・履歴を最小の実例とし、
それを包含して自由度を増やす。元の世界が十分リアルだという主張ではない。

- 動かす対象: パラメータ → 規則/実装コード → 機構・成果物/通信形式 → 配線・順序 → 研究活動/世界のモデル。
- 探索方法: ブラックボックス、勾配推定、微分可能な局所計算/代理モデル、将来のhybrid。

構造探索と微分可能化は同義でも排他でもない。どの自由度をどの方法で探すかを明示する。
制度比較中に世界の科学的法則を都合よく変えることは、別実験として区別する。

## 当初の希望ごとの実装と未完部分

| 希望 | 現在実行できる範囲 | 残る最初のゲート |
|---|---|---|
| 目的を変えると別の制度になる | 固定8パラメータで3 LossSpecの探索・共通held-out比較を完了。native任意source/graphにも同じLossSpec境界と永続campaignを接続 | 広いsource/graph探索で異なるlossごとの探索経路を少数候補で実行。回数拡大は後 |
| 出来合いの制度を抽象化し、新制度を作る | Pythonコード/JSON状態/schemaを直接記述・生成し隔離実行。native紙IDに基づく新producer/consumerを組み合わせ可能。外側LLM patch proposerもある | 新しい制度のLLM生成・修正がnative世界で最後まで動く実証。今回のlive共同編集例は人間が書いたアルゴリズムであり発見ではない |
| 配線・規則・順序も設計する | 原子的patchでsource、ports、artifact types、nodes、edges、delays、schedulesを同時変更し、完成したgraphを検証。native接続/遅延の因果効果はQA済み | native年間枠の前提を外す一般event実行器と、未知protocolの受け手を含む意味的検証。任意の並びが有効とは主張しない |
| 元の研究者世界で閉ループ最適化 | baseline → 実行 → 実際のloss → 次patch → 次の実行。pending/観測/親系譜を永続化。実機2候補pilotは別resultで報告 | 一回の追加提案から、複数の適応的source/構造改訂へ。改善や科学的価値は別の評価課題 |
| 微分による最適化 | 数値backendで全体autogradは実装済みだが別世界のmethod test。native側は実際のlossから連続設計分布のscore-function勾配を推定し更新、再開できる | nativeの一部をtensor演算へ移し、有限差分等で局所勾配検証 → 不透明LLM/検索/離散選択と推定勾配を接続。**元の世界全体のbackpropagationは未実装** |
| 科学活動自体を豊かにする | 任意schemaの成果物・履歴/参照、新機構から研究者promptへ因果的な入力、新actorの永続化codec | 仮説→実験/解析→データ/ソフトウェア→検証/訂正の少なくとも一連鎖を実際の研究者行動・資源・履歴へ接続。名前付きartifactを置くだけでは未達 |
| 楽しいゲームとして操作/観測する | 既存city、replay、分岐比較、数値backend viewerあり。native側は同じcandidate fingerprintの設計差分・loss経路・canonical replayをexport可能 | native新role/protocolの都市表現とsource adapter、プレイヤーpatchを隔離branchで評価する接続。exportだけではUI完成ではない |
| 研究システムの自己改善 | opt-in自己構成観測 → 世界内機構からpatch → 未採点journal → 別のnative世界で評価、という最初のbridgeをQA。親の稼働世界は変更しない | 観測結果を内部designerの記憶へ返す → checkpointを明示移行して同じ社会を継続 → designer/探索戦略自体も改訂。再帰的改善や自律的発見はまだ主張しない |

## 実行入口と証拠の区別

`scripts/run_native_design_loop.py` の `--proposer example|llm|endogenous` は
同じSystemSpec patchとnative evaluatorへ接続する。`endogenous` は提案を本当に出す
初期SystemSpecを `--system` で指定する。`scripts/run_native_gradient_loop.py` は
明示した数値JSON座標の分布をnative lossで更新する。詳細とコマンドは
[native設計ループ](../components/native-design-loops-v1.md)。

テストのscripted transport/corpus、実際のlocal Qwen/corpus実行、native autograd、
LLMが新しいsourceを発見したことは別々に記録する。今回の実機pilotの目的関数は
負の採択件数という**工学用のgameableな例**であり、科学の良さの定義ではない。
all-acceptを禁止せず、勝手なfairness/promotion制約も追加しない。

## 次の小規模実装の順序

1. native共同編集pilotを完走し、実際の履歴からlossと系譜を再計算して記録。
2. 同じ元世界上でLLMによるsource/protocol共同設計とnative勾配推定を各一周実行。
   失敗も残し、toy成功で置き換えない。
3. 新しい研究活動の一連鎖と、そこへ介入できるnative game adapterを接続する。
4. 局所tensor化/勾配推定を同じ世界へ積み上げる。全面的な自動微分と偽称しない。
5. 内部designerへの評価フィードバックと明示的なstate migrationを実装する。
   改善手続き自体の改訂はその上の別ゲートとして扱う。

これはseed/populationを増やす計画ではなく、欠けている能力を小規模に接続する計画。
実行中のcommit-pinned worktreeは変更せず、機能開発と実験を隔離する。

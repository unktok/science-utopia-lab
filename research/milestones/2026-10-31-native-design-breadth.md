# 元の研究世界を包含する設計ラボ — 現状と次の実装ゲート

更新: 2026-10-31。Decision 0025/0026を現在の実装へ対応させる。

追記（Decision 0027）: 中心は制度・実装・protocol・配線・進行の設計自由度を増やすこと。
仮説/実験活動をこちらが列挙して実装することは、その前提条件ではない。LLMの重みと
研究者personaは固定し、制度側を最適化する。微分可能化のために元世界を歪めない。
ゲームはまず実行と設計が見えるgame-like UIも許容する。

新しい到達点: 同じ機構のhard/soft表現をnative graphへ接続し、実際のnative traceで
参照・分岐・記憶・tensor間通信を微分できる。制度7座標を更新した後、同じ固定Qwenの
元世界を再実行し、工学用loss 0→-3を確認・監査した。全世界の微分ではなく、opaqueな
研究者反応はtrace fitでは条件付き入力になる。新しいnative UIもPC/mobileで確認済み。
下表の以前の状態に対する更新として[実機結果](../results/native-trace-relaxation-v1.md)を参照。

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
| 出来合いの制度を抽象化し、新制度を作る | 自由なPython/LLM/型付きprotocolに加えID指定の構成編集を実装。Qwen生成のPeer Observerは元世界で実行済みだが条件が発火せずmessage0。配線はgeneric host attachment | 効果が生じる制度のsource/構成を実際の結果から反復改訂する。モデル生成sourceの実行と、有用な新制度発見を区別する |
| 配線・規則・順序も設計する | 原子的patchでsource、ports、artifact types、nodes、edges、delays、schedulesを同時変更し、完成したgraphを検証。native接続/遅延の因果効果はQA済み | native年間枠の前提を外す一般event実行器と、未知protocolの受け手を含む意味的検証。任意の並びが有効とは主張しない |
| 元の研究者世界で閉ループ最適化 | baseline → 実行 → 実際のloss → 次patch → 次の実行。pending/観測/親系譜を永続化。実機2候補pilotは別resultで報告 | 一回の追加提案から、複数の適応的source/構造改訂へ。改善や科学的価値は別の評価課題 |
| 微分による最適化 | 同じ制度のhard/soft表現を元世界へ接続。実際のtrace上で7座標のautogradを検証し、更新制度を固定Qwenの元世界で再評価してloss0→-3。機構間tensor通信・記憶の勾配もQA | 固定LLMの入力→応答やopaqueな後続世界への影響を勾配に含め、条件付き近似のずれを測る。**元の世界全体のbackpropagationは未実装** |
| 科学活動自体も豊かにできる | 任意schemaの成果物・履歴/参照、新機構から研究者promptへの因果的入力、新actorの永続化codec | 追加の拡張候補であり制度生成の前提ではない。研究活動の例を固定catalogとして列挙するより、自由な規則・protocol・実装を生成できる幅を優先 |
| ゲームまたはgame-like UI | 既存city/replayに加えnative.htmlが元世界の実行された構成・コード・配線・研究者・loss・勾配範囲を表示。PC/mobileの操作・hash検証を確認済み | 自由に編集した設計を隔離branchで実行し、完了後にUIへ返す。現在は実記録の読み取り・観測UIでありプレイ可能な制度運営ゲームではない |
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

1. 完了: native共同編集とhard/soft制度fit→再実行の経路を、実際の履歴から監査して記録。
2. 次: inertだったLLM sourceを含め、source/protocol/配線の設計と実測結果による改訂の自由度を広げる。
   失敗も残し、toyや便利な制度catalogで置き換えない。
3. 次: UIから編集した任意設計を隔離実行へ渡し、実際の結果を同じUIに返す。
4. 継続: 固定LLMの反応経路を含む局所tensor化/勾配推定を、元世界を歪めず積み上げる。
   条件付きtrace fitと全世界の微分を区別する。
5. 後続: 内部designerへの評価フィードバックと明示的なstate migrationを実装する。
   改善手続き自体の改訂はその上の別ゲートとして扱う。

これはseed/populationを増やす計画ではなく、欠けている能力を小規模に接続する計画。
実行中のcommit-pinned worktreeは変更せず、機能開発と実験を隔離する。

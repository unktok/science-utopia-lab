# Native feedback comparison V1: closed development pilot

2026-11-07。固定Qwen3-8B研究者・承認済みローカル35B設計者で、元の研究者
lifecycleを保った二年・五研究者・seed42の比較を完了した。
[事前protocol](../protocols/campaigns/native-feedback-comparison-v1-a1.md) ·
[全候補JSON](native-feedback-comparison-v1-a1.json) · [現状](../STATUS.md)

## 結果

最小化する目的はT=-A、E=-Q+0.5R。Aは採択decision数、Qは採択decisionごとの
**元の査読overall_scoreの平均**の総和（査読なしは0）、Rは個別review数。
制度自身が書くfinal_scoreをQとして採点しない。両方とも科学の質そのものではない。

| 提案群 | 世代 | T | E | 状態 |
| --- | ---: | ---: | ---: | --- |
| 共通初期制度 | — | 0 | 12 | 完走 |
| throughput / loss-feedback | 0 | 0 | 12 | 完走 |
| throughput / loss-feedback | 1 | null | null | scalar値にlenを適用 |
| throughput / technical-only | 0 | 0 | 12 | 完走 |
| throughput / technical-only | 1 | null | null | world出力のpayload envelope不正 |
| efficiency / technical-only | 0 | -7 | -11.833333333333336 | 完走 |
| efficiency / technical-only | 1 | null | null | scalar値を添字参照 |
| efficiency / loss-feedback | 0 | null | null | required decisions出力なし |
| efficiency / loss-feedback | 1 | 0 | 12 | 完走 |

全8slotを消費し、4完走／4実行失敗。全案が提出を終えており、今回のnullは提出・
JSON・transport失敗ではない。失敗の補充、hostによる生成科学コードの修理、
baselineへの置換はしていない。表の群名は候補の採用条件ではない。
全候補を損失だけで選ぶと、**両目的ともefficiency-control G0が最良**となる。

## 何が改善したか／していないか

最良案のA/Q/Rは7/22.333333333333336/21。初期系は0/0/24。
元のreview後のworld.selectionを、対象recordを全てacceptするコードへ変更した。
graph・schedule・process契約の変更はない。表示final_score=10も書くが、Qは
元の査読記録から独立に計算されるため、その値の上書きによる直接の得点ではない。
一方、empty-input分岐は架空IDを作るため、今回通った軌跡で全入力の正しさは示せない。

これは目的条件付きの**初回提案**の観測改善であり、測定feedbackから学んだ改善ではない。
世代1の測定上積み、feedbackの優位性、目的ごとの異なる勝者、新しい配線・機構の
発明、設計者自身の改善、科学の質の改善は示していない。
全採択は単純で既知のルールであり、これ自体を新アルゴリズム発明とは呼ばない。

共通初期制度は19nodeの開発用open_native_systemで、補助協働processとtensor
routingを含む。未変更の原quota制度ではない。弱い初期系への勝利だけで自由設計の
価値を結論しない。legacy原制度・手作業all-accept等・parameter-only・free-code・
free-graphを同一条件で比べ、選択後の未使用条件で確認するのが次の研究課題。
対照群も目的定義・自分の設計履歴・技術状態は受け取るが、損失・測定・選択parent等は
受け取らない。二群のG0は別々の設計者callで、同一乱数proposalではない。

## 失敗解析と前向き修正

throughput-feedback G0は負係数を逆に読み、全rejectを生成した。hostの符号逆転ではない。
係数から厳密に導く増減方向の表示を別sourceで修正し、111 focused testsを通した。
required出力の空listについても、既存runtimeのcardinalityと説明文の不一致を修正し、
105 focused testsを通した。どちらも凍結2e375c2には後付けせず、失敗を残した。
前向き修正はモデル遵守の保証ではなく、新生成前には新sourceで校正が必要。
[算術表示の記録](../logbook/2026-11-07-affine-direction-context.md) ·
[出力契約の記録](../logbook/2026-11-07-required-output-context.md)

## 時間・物理費用

- run:05:08:38.465743–06:01:45.235840 UTC、53m06.77s、exit0、budget-complete-with-failures。
- 物理world directory9（baseline含む完走5／部分失敗4）。
- scientist response553／wire request553（baseline97＋候補456）。
- designer response102（各群18/28/28/28）。校正28responseは別枠。
- 記録された制度コード実行53（baseline8＋候補45、部分失敗を含む）。role load18は別枠。
- 校正28/28技術合格、exact-copy26/28は診断、cold replay合格。

slot数と呼出し数は別。研究者・年は独立sampleではない。model-call時間の合計を
wall-timeへ加算しない。equal slot budgetをequal computeと呼ばない。

## 原source監査・生成物

凍結source: `2e375c22793210d3496450a99ca96a86f0f7aecc`。
source/helper/protocol/lossの271blob、実作者journal、checkpoint測定、コード実行、
物理cacheとwire、writer/progress、校正のcold replayを検査。
raw inventoryは前後不変。監査による新モデル呼出し・生成コード実行は0。

- full audit content SHA256: `f3741b407f1fb262961bc86e279206263e72da59b686b93407c9d30d3f569c0c`。
- compact summary content SHA256: `928cc83f57d2fc6376097d5f4b5af866e94d39d0d4a7478ed76df6e58331ffbc`。
- raw: `outputs/native-feedback-comparison-v1-a1/`（Git対象外）。
- full audit: `outputs/native-feedback-comparison-v1-a1-audit.json`（Git対象外）。
- [自動表](../../paper/generated/feedback-comparison-v1/results.tex)、
  [全cross-score図](../../paper/figures/feedback-comparison-v1-a1-r2/feedback-comparison.png)、
  [探索経路](../../paper/figures/feedback-comparison-v1-a1-r2/search-paths.png)、
  [図manifest](../../paper/figures/feedback-comparison-v1-a1-r2/manifest.json)。

図の線はその群のbest-so-far、点は完走候補。nullを通る線は候補完走の意味ではない。
同じcheckpointのcross-scoreは追加の独立実験ではない。
原source監査は凍結worktreeで実行し、前向き修正後のmainで再解釈しない。

# Top-conferenceに向けた研究計画

2026-11-07。投稿・採択を保証する計画ではなく、研究上の問いと必要な証拠を決める。
[全体の目的](../../RESEARCH.md)と、一本目の論文の主張は区別する。

## 一本目の中心

仮題：**Objective-Conditioned Design of Scientific Institutions**。

固定された研究者モデルの下で、科学を運営する制度のコード・構成・接続を
探索する。目的、設計自由度、探索法の違いが、発見される制度・経路・帰結を
どう変えるかを調べる。元世界の介入条件を再比較するだけでも、LLMを学習する
話でも、コード提出インターフェースの修理履歴でもない。

提案する貢献は次の三つ。ただし現時点で全て実証済みとは扱わない。

1. 科学システムの実行可能な設計空間：数値、制度アルゴリズム、機構、配線・過程を分離する。
2. 目的条件付きの探索・比較：固定研究者世界、共通初期条件、明示した費用で方法を比べる。
3. 発見された制度の解析：目的間の帰結、proxy攻略、情報・資源・行動への実際の作用を説明する。

既存のLR、black-box、LLMプログラム探索を、新しい最適化理論の発明とは主張しない。
全世界の微分可能性は不要。再帰的自己改善とゲーム体験全体も一本目の必須主張にしない。

## 現時点での査読者の疑問

| 疑問 | 必要な答え | 現在の証拠／不足 |
| --- | --- | --- |
| 元のScienceUtopiaと何が違うか | 固定介入の分析から、目的を受けて制度を検索する問題への差分 | APIは実装済み。比較実験で価値を示す必要がある |
| LLMでコードを作るだけでは既存では | 先行のプログラム／mechanism探索との差、全体構成と長期feedbackの価値 | 関連研究の初期整理済み。最初の発明と主張しない |
| parameter-onlyで十分では | 同じ世界・目的・予算で自由度の対照比較 | 過去の別source結果を並べるだけでは不足 |
| feedbackは役立つか | loss由来の情報漏れを防いだno-feedback対照 | own-historyは動作するが、現在の有効性の証明には不足 |
| 代理指標を攻略しただけでは | 実装作用と最適化／外側評価の区別、重み感度と失敗例 | V13の好意的査読者選択、V45の表示score作用は解析対象 |
| seedや研究者モデル固有では | 選択後の未使用条件で評価、独立単位と不確実性の明示 | 初期parameter研究をfree-codeの頑健性と混ぜない |
| 勾配に価値があるか | 条件付き分布・同じoracle予算・対象を限定した比較 | V10/V13は優位性を示していない。主張する場合だけ追加検証 |

## 証拠の扱い

[機械可読の棚卸し](../results/publication-evidence-inventory-v1.json)と
[再生成コード](../../scripts/reports/publication_evidence.py)は最初の実装成果。
V10/V12/V13/V45のsource/schema/content hashを検証し、全loss経路、失敗null、
同点、過去観測、著者由来、物理費用、事後cross-scoreを分離して抽出する。
これは既存4研究のprojectionであり、新しいraw auditや全プロジェクトの網羅的調査ではない。

- V13の外部設計者による観測改善を消さず、ローカルLLMの能力とも同一視しない。
- V45の効率arm失敗と、別arm候補の事後効率最小値を付け替えない。
- sourceが同じでもworld、seed、初期観測、oracle能力、予算が一致するとは限らない。
- 異なるsourceの記述的な順位付けは可能だが、それを方法の因果比較としない。
- 失敗率、null、同点、採用されなかった改訂も表示する。望んだ差を強制しない。

## 次の実験の順序

**P0：今回着手・実装済み**：出典固定の証拠棚卸しと、
[比較contract](benchmark-contract-v1.md)を作る。研究者worldもモデルも追加実行しない。

**P1：実装・検証済み**：既存NativeAdaptiveDesignCampaignへloss-feedbackの
有無を比較できる入口を接続する。単にscoresを消すだけでは、incumbent選択、
候補順、parent、strategy更新から正解が漏れる。最初にこの対照のテストを作る。
技術的なエラーfeedbackは両群に残し、科学的損失feedbackと区別する。
制御実装と[有限比較protocol](../protocols/campaigns/native-feedback-comparison-v1-a1.md)
を作成。固定source2e375c2で28技術校正・冷再生後、有限pilotと原source監査まで完了。
条件変更・失敗補充はせず、[全結果](../results/native-feedback-comparison-v1-a1.md)を保持した。

**P2：少数規模の統合比較完了**：同一source・共通初期系・二目的・二探索法の
最小比較を回し、全候補、null、費用、探索経路、cross-scoreと作用を保存する。
4完走／4実行失敗。両目的ともcontrolの初回全採択案が最良で、G1の上積みはない。
この段階の単一seedを統計的な優位性とは呼ばない。

**P3：自由度と一般化**：parameter-only／自由コード固定graph／自由graphを
同じ条件で比較する。選択を固定してから未使用seed・条件を評価する。
現在のopen-system初期系は未変更の原制度ではないため、legacy原制度と
明らかな手作業ルールも対照に含め、弱い初期系だけに勝つ比較にしない。
効果が出ない場合、予算追加で良い結果を探すのでなく、事前に定めた解析を行う。
現在は[有限V2 study](../protocols/campaigns/native-design-freedom-v2.md)を固定b6654adで実行中。
S1の強い8基準は完走・二回監査済み。V2のrun00実校正28項目とcold replayを通過し、
fresh基準9件は終了、探索3/120slotまで進行。全探索・選択後評価の結果はまだ未確定。

**P4：原稿を組み直し中**：開発経緯を主文から外し、図とclaim/evidence対応で構成する。
基盤、比較、制度機構の知見を主文へ。失敗履歴・API・source検証は付録へ。
[主張中心の章立て](../../paper/submission-outline.md)を次稿の正本とする。
現在の長いworking draftやNeurIPS形式は、投稿準備完了を意味しない。
[短い新稿](../../paper/submission.tex)は方法・比較中心の構成を実装済みで、
監査から自動生成した全候補表・探索経路と実作用の解析を入れた。旧長稿は保存する。
S1の実測・print用グラフ・V2の前向きprotocol、固定record選択の代数的解析と
再現の限界を追加した10ページの版も作成・全ページQA済み。V2部分結果は入れていない。

## V2が閉じた後の解析

原source checkoutの`analyze_native_design_benchmark.py`で全campaign・実校正・
role load・physical cache/checkpoint・選択・未使用評価をread-only監査する。
別のfresh outputへ二度保存し、入力不変と監査一致を確認する。稼働中を完了扱いしない。

後段の`python -m scripts.reports.native_design_benchmark`はその閉じたauditとplanを
source/schema/hashで束縛して、120slot、三controller履歴、各五world seedのpaired差、
null・共有physical job・別horizon・全費用をprojectionする。これは新raw auditではない。
同じ制度を19labelで呼んでも追加の独立標本にしない。各参照との比較を全て残し、
評価結果を見て都合の良い基準だけを選ばない。欠測対を0へ埋めず、available条件付き平均と
不足数を分ける。四年の単一seed診断を五seed・二年の標本に足さない。

`python -m scripts.figures.native_design_benchmark`はそのreportから全三履歴の
best-including-initial経路と全完走点・null表示を印刷用に作図する。重なった経路を
jitterせず、方法優位のbandを捏造しない。SCRIPTED QAの図には明示watermarkを入れる。
実結果はまだ未生成であり、解析コードのテストは実験結果ではない。

## 会議の方針：確認できた事項と判断を分ける

2026-11-07時点、第一候補の方向はNeurIPS/ICMLの通常研究論文。
科学システム設計という問題設定・実用的な比較の貢献を重視する。
これは適合性についての研究側の判断であり、採択可能性の予測ではない。

- [NeurIPS2026 reviewer guidance](https://neurips.cc/Conferences/2026/ReviewerGuidelines)
  は技術的裏付け、明瞭さ、重要性、新規性を評価し、新規性は新アルゴリズムだけに
  限らない。Concept & Feasibility/Negative Resultsも重要性・新規性の基準が高い。
  不十分な実験の逃げ道にはしない。2027の規則・締切は確認後に固定する。
- [ICML2027 official page](https://icml.cc/Conferences/2027)ではCFPと投稿締切は
  まだ今後掲示とされている。推測の日付を計画上の確定締切にしない。
- [ICLR2027 CFP](https://iclr.cc/Conferences/2027/CallForPapers)の論文締切は
  2026-09-25AoEで、今回の確認日には既に過ぎている。今から同cycleへ出す計画にしない。

投稿先が決まったら、その年のページ数、匿名化、重複投稿、著者資格、AI利用、
コード・データ公開方針を公式情報で再確認する。勝手に投稿・著者追加・外部連絡はしない。

## 初期関連研究

[初期文献メモ](related-work.md)を参照。この初期調査はabstract/公式解説中心であり、
唯一性を証明する網羅調査ではない。原論文全文、関連する自動機構設計・LLM社会
シミュレーション研究との比較を追加してから、新規性の最終表現を決める。
[対象を絞った本文比較](method-section-comparison.md)は、汎用的なLLMコード探索や
LLM＋勾配の組合せを新規性として売らないための具体的な差分を記録している。

## スケール前の終了条件と、未達をどう扱うか

比較contractを実装し、元世界で小さな比較を一度通し、どの指標にどの制度が選ばれたか、
何が変更され実行されたかを説明できること。これが統合の終了条件であり、必ず改善や
異なる勝者を出すことではない。論文の主張を支える反復と独立評価は、その後に別途必要。
外部有料モデル・新マシン・人間参加研究・追加の共有権限が必要なら事前確認する。

# Top-conferenceに向けた研究計画

2026-11-08立案、11月12日に入口情報を更新。以下の段階・不足は立案時の記録を含む。
現行の終了条件は[publication-ready v3](publication-ready-v3.md)、
実験の稼働・完了状況は[STATUS](../STATUS.md)を正本とする。
投稿・採択を保証する計画ではなく、研究上の問いと必要な証拠を決める。
[全体の目的](../../RESEARCH.md)と、一本目の論文の主張は区別する。

原稿方針の更新：研究内容を先にページ数で削らず、
[統合原稿](../../paper/integrated.tex)を全体の正本とする。
最新の確認済みPDFは[59ページ版](../../paper/README.md)であり、
[対応するビルド記録](../../paper/integrated-objective-evaluation-build-v1.json)を持つ。
構造・勾配・目的別parameter・UIを含め、科学的に残す内容と重複した開発記録を
[編集／証拠対応表](../../paper/integrated-content-map.md)で区別した。
投稿先確定後に焦点と正式規則に沿った投稿版を切り出す。旧12ページ稿と過去の
投稿判断は別scopeで保存し、統合だけで重要性・優位性が実証されたとは扱わない。

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

## 立案時の査読者の疑問

以下は比較設計時の問いと当時の不足。[最終照合](submission-decision-v2.md)が
完了V2による回答と、なお解消しない研究上の限界をまとめる。

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
現在は[有限V2 study](../protocols/campaigns/native-design-freedom-v2.md)を固定b6654adで完了。
S1の強い8基準は完走・二回監査済み。V2は全3runで各28項目の実校正とcold replayを
通過し、fresh基準9件と有限探索120slotが終了した。選択を固定し、19logical label／
15exact policyの90物理評価も全件正常終了し、明示的順序補正adapterによる二回の
全体監査は同一bytesで一致した。未修正の凍結CLIの成功とは扱わない。
[閉鎖・projection記録](../results/native-design-freedom-v2-closed-analysis-v1.json)と
[STATUS](../STATUS.md)を参照。探索・未使用評価・監査を追加の独立反復として混ぜない。

**P4：V2原稿・最終資料・投稿判断を完了**：開発経緯を主文から外し、図とclaim/evidence対応で構成する。
基盤、比較、制度機構の知見を主文へ。失敗履歴・API・source検証は付録へ。
[主張中心の章立て](../../paper/submission-outline.md)を次稿の正本とする。
現在の長いworking draftやNeurIPS形式は、投稿準備完了を意味しない。
[現行V2稿](../../paper/submission-v2.tex)は120試行、90評価、全履歴の経路、共通T/C/E、
64完走仕様の変更、失敗内訳、実際のrecord→研究者入力→行動経路と費用を記載した。
12ページ全てを120dpiで再renderし個別目視確認済み。
[build記録](../../paper/submission-build-v3.json)と[compact証拠](../results/native-design-freedom-v2-paper-evidence-v1.json)
で出典・数値・図表を固定する。旧11ページのV1/S1稿と旧長稿は変更せず残す。
実装自由度と実際の構造発明は区別する。数値／source以外のgraph変更は観測されず、
手法優位は示されていない。数値再構築資料、paired図の確認、権利・匿名化の
限定点検、模擬査読、補足分析と[最終投稿判断](submission-decision-v2.md)まで完了。
即時本会議投稿は非推奨で、top-conference-readyとはしない。
良い結果を得るための追加実験を自動で始めない。

## V2が閉じた後の解析

凍結b6654adの監査入口には、sorted JSONで失われたplan/selection辞書順を再構成できない
分析側の不具合がある。[明示的な順序補正adapter](../../scripts/audit_native_design_benchmark_order.py)
をcleanな分析checkoutから直接起動し、原sourceの監査関数と依存をcleanな凍結checkout
から読み込む。[実行手順と検証範囲](../../docs/research-workflow.md#audit-before-reporting-the-v2-study)
に従い、元の全campaign・実校正・role load・physical cache/checkpoint・選択・未使用評価の
監査guardは保持する。順序補正は同じ値・hash・リストを復元するだけで、原データや
選択を変更しない。実writerの正常終了後に別のfresh outputへ二度保存し、入力不変と
監査一致を確認する。稼働中のcomponent checkや未修正のCLIを全体監査成功としない。

後段の`python -m scripts.reports.native_design_benchmark`はその閉じたauditとplanを
source/schema/hashで束縛して、120slot、三controller履歴、各五world seedのpaired差、
null・共有physical job・別horizon・全費用をprojectionする。これは新raw auditではない。
同じ制度を19labelで呼んでも追加の独立標本にしない。各参照との比較を全て残し、
評価結果を見て都合の良い基準だけを選ばない。欠測対を0へ埋めず、available条件付き平均と
不足数を分ける。四年の単一seed診断を五seed・二年の標本に足さない。

`python -m scripts.figures.native_design_benchmark`はそのreportから全三履歴の
best-including-initial経路と全完走点・null表示を印刷用に作図する。重なった経路を
jitterせず、方法優位のbandを捏造しない。SCRIPTED QAの図には明示watermarkを入れる。
実結果は閉監査から生成済みであり、別の解析コードのテストとは区別する。

`python -m scripts.figures.native_design_evaluation`は同じclosed reportから、
各参照制度に対する選択policyのseed別paired差を全て作図する。二つの探索目的を
別panelとし、数値・固定graph code・code/graph・technical-only・uniform numericを
同じ順で残す。全9参照、二年五seedと四年単一seedを別figureにする。
欠測は数値軸の外へ表示し、有効なpairの平均は期待性能や信頼区間と呼ばない。
同じphysical jobは明示し、追加の独立標本と数えない。plot-data JSONとfigure hashを
保存し、元reportのphysical score・job ID・共有・seed順序と差分を再照合する。
他目的でのcross-scoreは入力reportに残る。この図は各arm自身の目的での比較である。
初期previewはSCRIPTED QAのwatermark付きで、実測結果として原稿へ入れない。

これに加え`python -m scripts.figures.native_design_cross_objective`は、全9参照と全10
選択armを共通T/C/Eの三列へ並べる。Eは診断であり、Eのsearchを追加しない。
二年は五seedのraw lossとavailable-score平均、四年は単一seedの別図とし、数値を
目的間で正規化・合算・順位化しない。nullは軸外、各cellのn/Nを表示する。P番号は
同じexact policy／physical jobの共有であり追加反復ではない。初期系の選択は星印で
明示し、生成失敗を成功した制度発明へ付け替えない。全同点IDとraw job/seed値は
plot-dataに残す。全三目的のpair blockと実physical scoreを再照合する。方式labelは
許可された自由度であり、実際にgraphが変わったという主張ではない。最初の描画QAは
明示的SCRIPTEDで、実結果・不確実性・期待性能を示す図ではない。

費用は閉監査後に`python -m scripts.reports.native_token_costs`で研究者のcommitted／
partial応答を、`python -m scripts.reports.native_auxiliary_costs`で設計step・校正・
明示的なrole loadを別集計する。後者はauthorの監査proofを元stepファイルへ、
校正を元certificateへ結び直す。既知・未報告・無効値の件数、POST記録と応答不明を
分ける。native countとtransport別名、重なる時間、同じphysical jobの別labelを足して
総費用を水増しせず、モデル読み込みの未報告値を0としない。モデルserverのcache、
retrieval・container・host・coding agent・過去開発の全computeが測れたとはしない。

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

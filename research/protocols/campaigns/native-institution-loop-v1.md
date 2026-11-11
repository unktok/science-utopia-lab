# 目的条件付きnative制度最適化の有限pilot

2026年11月11日。前段の8件は履歴再提示の設計診断であり、新しい損失を測らなかった。
今回は**実案→元の研究者世界でのloss→次の案**を閉じる新しいprospective campaign。
重要な知見が得られるかを調べるpilotで、終了をpublication-readyと同義にしない。

## 世界と目的

原Simulation、研究者Qwen3-8B、五研究者、四年、SciEvo2016〜2019の固定corpus、
既存の固定model digest/image/測定器を使用。設計役は承認済みlocal35B。
元の研究生産・計画起源・会計を固定した明示routing-v2 domain。
LLMの学習、研究完了条件や測定式の書換え、追加の規範的採用条件はない。

最小化T=`-A`とE=`-Q+0.5R`を固定する。Qは元査読値で、任意のfinal_scoreを使わない。
Cは既存の診断cross-scoreのみ。目的に合わせてよい制度が異なることを調べ、
複雑な機構・新しい配線・異なる勝者・参照超えを合否条件にしない。
過去の測定は新しい実測値へ付け替えず、同sourceのfresh世界だけを選択へ使う。

## 比較と予算

数値直接提出、固定graphの任意code、任意code/機構/配線の三設計域×T/E×2generationで12候補。
順序は三設計域の各T/EでG0、G1はその固定順を一つ左へ回す。
各候補の評価はdevelopment seed61001の四年world一つ。初回案へ参照lossは見せず、
次回案は自armの実結果・技術的失敗を受け取る。別arm、参照解コード、held-outは提示しない。
新inline順序情報とread-only詳細APIは明示し、元の任意file比較と混同しない。

共通editorは最大16action/8192出力/40960context/thinking off/1200秒。
numericは既存の最大2明示応答によるliteral提出で1200秒。
connect10秒/read900秒、retries0。interface予算が異なるend-to-end比較であり、
純粋な表現力差や純粋なoptimizer差を識別したとは主張しない。

強い参照8worldは同development seedで次を固定する。

- M1初期制度、元legacy制度。
- 元の査読を維持した全accept。
- 査読なしの全accept／全reject。
- typed routingで先頭の適格査読者1人／2人を割当てた全accept。
- 同じ1人割当ての全reject。

1人と2人は同じproducer/sourceでcountのみ異なるnested assignment。
元の乱数による査読者選択と同じとは限らず、2人routingを元制度と等価なshamとは呼ばない。
snapshot85/producer87/review90を明示し、helperは候補を修正しない。
同じ新権限の参照を与えて比較するが、equal-authority monolith対照はこのpilotに含まない。
graph構文の必要性は本pilotでは検証しない。

8参照＋最大12候補＋最大33未使用評価で**最大53 native world**。
研究者HTTPはworld当たり1024試行上限、768出力token、並列1、既存の通信・parse条件。
populationやhorizonを増やしたスケール実験ではなく、前回未使用の権限での小規模作用・探索検証。
worldごとの元のresponse cache／portable checkpoint／入力・コード記録を保持する。

## Readinessと停止

開始前に新source/新inline条件でeditorと二目的numericの実readinessを行う。
その後、各proposalの直前にも各interfaceのfresh readinessを実施し、24時間age制限を維持。
editorは初回＋8proposalで9session、各最大40 chat POST。
numericは初回＋4proposalで5session、各二目的×最大2 chat POST。
productionはeditor最大128、numeric最大8 chat POST。空prompt loadとmetadata GETは別計上。
各readiness／proposalは1200秒、設計者と研究者推論は同じlockで直列化する。

readiness失敗・完了不明・元source変更・参照失敗はcampaignを止める。
返却された無効候補や既知の実行失敗は当該候補枠を消費し、損失はnull。
提案の修復・補充・基準へのfallbackはない。run全体の再dispatchも拒否する。
停止後はrawを保持して診断し、同じtrialを新しい実行に差し替えない。

## 選択固定後の評価

全探索終了後、各armの初期制度と全2案から、assigned lossのみで最小を選ぶ。
全tieを保持し、物理実行は事前固定の到着順の先頭。参照を自動案へ採用しない。
選択JSONを保存してからseed62001/62011/62017を評価する。
初期化前にprojectの指定raw rootsの全response journalでdev/評価seed使用を確認する。
新seed使用を全世界・全machineについて保証するものではない。

5参照（legacy、元査読全accept、査読なし全accept、routing1/2全accept）＋6選択ラベルで
最大11policy×3seed=33world。同一policyは共有し、同じphysical世界を独立標本として数えない。
選択後評価から探索へのfeedbackなし。失敗補充や有意になるまでの追加seedは行わない。

## 解釈と次段階

全候補のT/E/C・raw A/Q/R、schema/実行失敗、source／数値／機構／配線のliteral変更、
review task数・identity・年ごとのpublication／再投稿、実際の研究者入力と費用を報告する。
runtime proofと選択・authoringを別にreplayし、原sourceで二回監査する。
既存の部分selector probeの結果を、この新worldの測定や完全な候補有効性へ代用しない。

結果の方向にかかわらずpilotを閉じる。重要性・一般化が弱いままなら本会議readyとしない。
次の主実験はpilotの作用と変動に基づいて別に凍結する。必要なら元世界を包含した
独立検証可能な研究課題を拡張するが、T/Eの測定や過去の成否を遡及変更しない。
新しい課金、外部モデル、公開投稿、資源調達は導入しない。

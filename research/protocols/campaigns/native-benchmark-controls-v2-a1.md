# Native strong-control pilot V2 A1

Prospective protocol,2026-11-07。S1 of the [submission goal](../../publication/submission-goal.md)。
Source/model/corpus/imageはprepare時のclean commitとplanへ固定する。

目的：弱いopen seedへの勝利だけで自由な制度探索を評価しないため、明白な基準を
元の研究者世界で測る。手作業ルールは発明とは呼ばず、探索結果を補修する材料にしない。

## 固定条件と予算

- 元のlifecycle、五研究者、二年、seed42、四年public corpus、Qwen3-8B固定。
- 8制度×1seed＝最大8物理world。順序はlegacy、open-seed、open-rank-rate、
  open-accept-all、open-reject-all、open-score-3、open-score-4、open-no-review-accept-all。
- 全採択／全却下／score閾値は原review記録から判断し、正しい既存paper IDを使う。
  空cycleは既存empty_cycle sentinel。rank-rateは既存公開sourceで、原制度との
  等価性を仮定しない。legacyは未変更native graph。
- no-review全採択だけはreview nodeを明示的に除去し、その依存と観測辺を
  costsへ配線し直す。他はopen seedからselection source／parameterのみ変更。
- 失敗はnull、消費slotを補充しない。runの再dispatchを禁止し、途中中断を
  自動再試行しない。新しい修正は別source・別protocolで実施。
- 設計者呼出し0。手作業コードなのでLLM設計者の校正証明を流用も要求もしない。
  sandbox技術検査を行い、scientist role loadとcontext確認を各worldへ記録する。
- 研究者は既存factoryのmax_tokens768、thinking=false、SDK retry0、HTTP120s。
  domainの既存max_retries2は残し、物理wireを全て保存する。無制限retryではない。

## 目的と解析

T=-A、従来E=-Q+0.5R、および**選別production loss C=4A-Q+0.1R**を
dispatch前に固定し、同じforward測定から相互採点する。Qは元review平均の総和。
Cはpublication一件にdebit4、review一件に費用0.1を明示的に置くengineering proxy。
単一論文の採択効果は4-scoreだが、longitudinalな研究行動・費用も変わりうる。
既に開発結果を見た後の設計であり、現実の科学価値や確認的仮説とは呼ばない。
4という値はnative1–5 reviewer scale内の宣言したtrade-offで、望む勝者を見て
後から調整しない。公平性・新規性・採用のvetoは追加しない。

全8制度・null・同点・A/Q/R・active/resources・費用・コード作用・reviewなしの
raw recordを保存。順位は各lossだけで定める。独立評価や方式の優位性をこの
単一seed pilotから主張しない。後続の自由度比較の初期評価と同一とはみなさない。

## 保存と監査

plan、writer start/end、各slotのstart/observation/cross-score、SystemSpec、
wire、response cache、コードcontext、年checkpoint、source/helper/protocol hash。
分析は原sourceからread-only、測定をcheckpointから再計算し、all attemptsを照合。
原制度の合法なzero-code実行も正しく監査する。model/world/codeを監査で再実行しない。

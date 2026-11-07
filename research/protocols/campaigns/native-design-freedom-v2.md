# Matched objective / design-freedom study V2

Prospective research protocol,2026-11-07。Implementation/testing pending; not yet dispatched.
S2–S4 of the [submission goal](../../publication/submission-goal.md)。
Runtime source、image、model/backend、corpus、完全なplanは実装・検査後に固定する。
S1の途中経過や過去V1から生成候補を取り込まない。正の結果を終了条件にしない。

## 問い

元の研究者worldで、目的の違いと制度の自由度が選ばれるシステム・経路・帰結を
どう変えるか。自由なコードや構造が、明白な手作業制度やnumeric tuningに
何を付け加えるか。既存LRやLLMコード進化の理論的新規性は主張しない。

## 固定した目的

主探索はT=-A、C=4A-Q+0.1R。従来E=-Q+0.5Rも全候補の診断cross-scoreとして
保存するが、Eを主目的として新しいsearch armを追加しない。
Qは採択decisionごとの元review overall_score平均の総和、査読なしは0。
Cはnative1–5 review scale上のdebit4／review費用0.1という宣言したtrade-off。
過去開発を見た探索的な目的選択であり、科学の真の良さや確認的仮説とはしない。
重みを結果を見て変更しない。公平性、新規性、改善必須のvetoは設けない。

## 世界と設計の境界

- fixed Qwen3-8B researchers、五研究者、二年、development world seed42、四年public corpus。
- fresh open_native_systemを全armの共通初期系とする。元のlegacyそのものと偽らない。
- 研究者の重み、retrieval/corpus、世界のbasic adapters、測定・LossSpecは検索対象外。
- 原制度・rank/rate・全採択／全却下・閾値3/4・reviewなし全採択／全却下は手作業対照で別評価。
  S1の異なるsource実測を新studyのfresh同条件観測として流用しない。
- 三つの入れ子の設計空間。初期anchorに対して毎回検査し、歴代parentから少しずつ
  制限外へ抜けることを認めない。
  - parameters：既存tensor閾値二つ、bias、memory_cost、router閾値、process countの
    明示した六座標。範囲・integerはplan内のdesign_spaceで固定。
  - code-fixed-graph：上の座標＋既存三つのPython source（process delegateを含む）。
    schema、port、node、edge、schedule、initial state等は固定。source再整形もsource変更。
  - code-and-graph：有効なSystemSpecのコード・node・配線・processを変更可能。
    world seedは変更不可。世界の重みや測定関数を書き換える経路ではない。
- 自由度は出来合いのルールメニューではなく、実験の比較領域。技術・表現の制限は
  明示し、科学的劣等性や未知アルゴリズムであるかを判定する門にはしない。
- domain逸脱は提出されたliteralを保存してnull、worldへは送らずslot消費。
  hostによる投影・修理・候補補充なし。domain検査と実world validityは別々に報告。

## 提案方式・反復・有限予算

各主目的につき五群：LLM parameters、LLM code-fixed-graph、LLM code-and-graph、
LLM technical-only code-and-graph、uniform-random parameters。
最初の三群は同一local35B designer、同一16action/8192output-token/40960context
profile、10s connect/900s read、temperature0.6・reasoning off。
technical-onlyは既存V1の情報遮断を再利用し、固定初期親・自分の設計と例外classだけ。
他のLLM群はloss-selected incumbent・測定feedbackを受け、技術エラーは同じclassだけ。
この比較は親選択を含むadaptive packageの比較で、scalar表示だけの効果ではない。
random群は六座標の独立一様提案、designer呼出し0。同oracle予算≠同総compute。

三つのfresh search run。controller seedは42/1031/2063、各群四世代。
world development seedは全て42であり、三runを別々のworld環境seedとは呼ばない。
LLM sourceのsampling probabilityは未知で、完全な独立性やcommon-random-number
proposalを仮定しない。各runは別session・別履歴で、他群・他runの結果を渡さない。
順序はplanで事前固定・回転し、後から良さそうな群を優先しない。

- 2目的×5群×3run×4世代＝**120 candidate slots**。
- fresh共通初期系1world＋手作業対照8world＝**9 reference slots**。
  reviewなし全却下も明示し、無活動・低費用ルールへの勝利を隠さない。
- searchとreferenceは最大**129物理world**。同一候補の別slotも別physical評価とし、
  成功分だけを残さず、物理／論理費用をそれぞれ数える。
- LLM candidateは96、author POST最大1536。各run開始時のfresh校正は≤40 POST、
  計≤120 POST。各校正が失敗・staleならその後の生成は停止し、隠れたrefreshをしない。
  日数超過等で再校正が必要なら、未実行slot・予算を保持した別明示recordとして扱う。
- 校正は原source/model/backend/profileでcold replayし、exact-copyは診断に留める。
  技術校正はfree-design成功や科学的理解の保証ではない。
- 各proposal前designer role load、各world前scientist role load/context確認。
  一つのlocal endpointの実推論は直列。実行中sourceは一切変更しない。
- 全群共通で二年worldは最大512 scientist HTTP attempts、四年評価は1024。
  literal wireへ記録したattemptを数え、上限後はdispatchしない。domainが例外を
  捕捉して年末checkpointを作っても、予算超過worldは測定成功でなくtechnical null。
  output768token、HTTP120s・既存domain再試行を含む物理費用も別途記録する。
- 失敗、同点、無変更、良くならない改訂も四世代を消費する。失敗slotの補充なし。
  pendingを隠れて再dispatchしない。writer状態と応答不明はそのまま残す。

## 選択固定と独立評価

各群×主目的について、三runの全完走候補＋共通初期系から当該lossだけで一候補を
選ぶ。全同点IDを保存し、実評価対象は事前固定した順序で最初の同点候補とする。
初期系が選ばれても、failed trialが成功に置換されたとは扱わず、探索改善なしと報告。
別途、全群・referenceをまたいだpooled loss-only最良も表示し、群labelをvetoにしない。
各run内bestと初期値からの経路も全て残し、best runだけで方式を評価しない。

選択manifestをhash固定するまで評価用seedをモデルへ渡さない。
評価seed案31001/31013/31019/31033/31039は、dispatch前の使用履歴点検を経てplanに
固定する。既に使用済みと分かった場合はdispatch前に理由付きで再選定し、その後は
変更しない。historical held-out reserved seedsは流用しない。
評価時は選択した制度の初期state seedだけを明示的にworld seedへ差し替え、policyと
seedを分離したfingerprintを保存する。これは再設計ではなく宣言した評価条件変更。
design原本は不変、評価結果をproposerへ戻さない。

選択10制度＋手作業reference9制度＝最大19対象（同一policyは同一評価を明示共有）。
各五seed・二年に加え、31001の四年条件も各対象1回測る。最大114評価world。
二年／四年の同seedは独立標本として足さない。search129＋評価114＝最大243world。
S1の8worldとそのソフトウェアQAは別会計。費用・時間の上限見積りをdispatch時に記す。

## 解析と研究判断

全loss経路、cross-score、validity率、raw A/Q/R、active/resources、world数、
author/scientist呼出・token・秒、load/container、候補source差分と実作用を表示。
invalidを巨大lossへ変換しない。完走候補に条件付けた損失と失敗率は別々に報告し、
欠測のない期待性能と偽らない。評価失敗もnull、paired比較では利用可能な組と欠測数を
併記。五world seedは小標本なので全値・平均・差・ばらつきを優先し、有意差を乱発しない。

選別だけが変わったか、新node／配線／processが実行されたか、実際の研究者入力・
行動へ届いたかをreceiptとraw recordで追う。表示scoreを評価scoreと混同しない。
proxy攻略、零活動、単純基準への敗北も知見候補だが、それだけで重要性を保証しない。
重要な差がなければ、予算追加で勝者を探さず、問いとworldの限界を検討する。
最終的な投稿準備完了は、このprotocol完了だけでなく、先行研究、重要性、再現資料、
主張の裏付け、原稿・付録・規則・匿名化の点検を通ってから判断する。

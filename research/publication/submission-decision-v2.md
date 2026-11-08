# V2最終棚卸しと投稿判断

2026-11-08。有限の投稿判断パッケージについての結論。
研究プログラム全体の完成、採択可能性、第三者の査読、公開許可ではない。

## 結論

**実験・解析・原稿・再現資料を揃えた投稿判断の区切りは完了した。
ただし、この版を今すぐtop conference本会議へ投稿することは推奨しない。**

「top conferenceに提出できる研究にする」というユーザーの最終的な希望は、
まだ達成したとは言えない。実行基盤や慎重な監査があることと、重要な研究上の
貢献を実証したことは別である。現版は共同研究者による内容検討のためのworking
paperとして提示できるが、正式な投稿用ファイル・公開資料ではない。

改善や方式の勝利を必須にしたためではない。現時点では、既存のプログラム／制度
探索と単純なproxyの代数的性質を超えて、何が重要かつ一般的に分かったかの裏付けが
弱い。否定結果としても、その原因・成立範囲を十分に分離できていない。
これを文章・図の追加やseed数の増加だけで解決したとは扱わない。

## 当初の五要件との照合

[元の終了条件](submission-goal.md)を縮めず、以下の範囲と残る限界を明記する。
「完了」は有限の実行・解析・資料の状態であり、仮説が支持されたという意味ではない。

| 要件 | 完了した実行・資料 | 残る限界／投稿上の判断 |
| --- | --- | --- |
| 1. 原制度・手作業の同条件比較 | V2の同じ凍結sourceでlegacy、editable seed、rank/rate、全採択／全却下、score3/4、reviewなし採択／却下の9参照をfresh実行。選択後条件でも全参照を評価 | 弱い初期系への改善を、強い基準への優位性としない。別sourceのS1は補助資料でありV2へ足さない |
| 2. 自由度・予算・失敗・情報境界 | numeric、固定graph code、code/graph、technical-only、uniform numericの5群。二目的×三履歴×四世代、全120枠を保持。64完走、25生成null、31実行null。初期系からの領域検査、16action等を固定し、補充なし | 同じ候補枠は同じ総computeではない。全24 LLM numeric生成失敗対全24 uniform完走のため、自由度そのものと設計者／提示interfaceの効果が交絡。許可された構造自由度の有効性は未実証 |
| 3. 複数目的・経路・相互採点・機構 | T=-A、C=4A-Q+0.1Rを固定して探索。E=-Q+0.5Rは診断のみ。全経路、全候補T/C/E、欠測・同点、64仕様の差分、失敗class、実consumer→record→prompt→行動を解析 | 全完走案は既存numeric/sourceの変更で、宣言graph/node/wiring/state/schedule変更なし。20案のprocess countは変化。観測経路は因果的な損失改善の分離実験ではない |
| 4. 選択後評価と不確実性 | Nov7 22:38:35UTCに全同点・代表選択を固定し、最初の評価は22:39:08UTC以降。19ラベル／15exact policyの90物理評価すべて正常終了。未使用5seed二年、別の単一seed四年。全値・paired差・物理共有を表示 | 三探索履歴は同じ開発world seed42。5seedは小標本、四年を追加の独立反復にしない。固定seedでもfresh LLM応答は完全には結合されない。期待性能・手法優位性は主張しない |
| 5. 先行研究・主張・再現・倫理・費用・原稿・点検 | 本文比較、主張／証拠対応、12ページ原稿と全ページ目視、別の著者名除去版、数値再構築と22図一致、13path紙面再ビルド、全試行費用／outside metrics補足、権利・会議規則点検、三観点の自己批評を完了 | 独立査読ではない。35B由来・変換手順、fresh-machine推論再現、正式cycle書式／checklist、著者責任、完全な匿名化／公開権利は未解決。投稿可能と認定しない |

## 数値として言えること

- developmentのT最良-7は単純な全採択に並ぶが、超えない。
  Cのcode選択2.1はeditable初期2.4を下回るが、reviewなし却下0を超えない。
- 未使用二年条件のT実行可能code/control/uniform選択は平均採択6.2で、
  全採択／score3と同水準。初期系を選んだLLM numericを発明成功に数えない。
- Cのcode選択は平均A=Q=0、R=19.2でC=1.92。初期2.58より小さいが、
  reviewなし却下0より良くない。低いproxyは、より良い科学を意味しない。
- 同じdevelopment C=2.1でもA0/Q0/R21とA1/Q4/R21という異なる挙動がある。
  authored final_scoreと元査読のQは異なる。実際の3件の翌年resubmission入力／
  空のresubmission応答まで追跡したが、score0の単独の因果効果とは言わない。
- 完走development64件と評価90件は全てfinal_active_authors=5。
  resourcesのraw値も保存したが、福祉・生涯参加・科学的真実の改善とは解釈しない。

目的別に制度を選び直して実行・評価する閉ループは動作した。
**feedback優位、勾配優位、有効な新構造の自動発明、発明者自身の学習、
科学の質の向上は、このV2からは示されていない。**
これらは未実証の主張であり、候補を落とす隠れたvetoではない。

## 費用・検証・再現の到達点

| 項目 | 実測／確認した範囲 | 含まないもの |
| --- | --- | --- |
| 実験writer | 正常終了、78958.697204秒＝約21時間56分 | 開発を含む全プロジェクト時間、GPU時間 |
| 全研究者応答usage | 16043応答、total17021423 tokens。cached promptは内数 | FLOPs、電力、金額、全システムのcompute |
| search設計者 | 1387要求、1385 final信号、host call19681.867535932688秒。失敗も計上 | final信号を候補提出成功とすること、load等との重複加算 |
| source/raw監査 | 明示的order-only adapterで全体監査2回exit0・完全一致。凍結source278、raw7038ファイル | 未修正の凍結CLIが通ったという主張、追加の独立world |
| 数値再現 | exact集計archiveから120枠・90評価を再結合、462 loss再計算で残差0、22 PNG一致 | raw監査・fresh inference・第三者replication |
| 補足分析 | 全cross-score、30履歴／方法cell、10集約行、90物理評価、38 outside metric summary、5図／4CSV | 未記録のper-trial end-to-end wall timeの推測 |
| 紙面再現 | identified／author-redactedの13path subsetをcached/offlineで再build。12ページのrender／text一致 | cacheなしclean-machine試験、完全な匿名化／rights clearance |

原監査の辞書順復元不具合は隠さず、値・hash・選択を変えないadapterを別sourceに固定した。
歴史的な失敗記録・旧原稿・旧QA receiptは変更しない。
最後の照合記録は[final audit receipt](../results/native-design-v2-final-decision-verification-v1.json)。
197件の統合QAはソフトウェア検証であって197件の科学的反復ではない。

## 資料への入口

- [12ページ原稿の入口](../../paper/README.md)と[LaTeX](../../paper/submission-v2.tex)。
  PDFはrepoの`output/pdf/science-utopia-lab-objective-design-v2-draft.pdf`。
- [全候補・費用・outside metricsの図表](supplemental-analysis-v2.md)。
- [実数値からの再構築](../data/native-design-v2/README.md)、
  [紙面subset再構築](../../docs/paper-rebuild-bundle.md)、
  [raw監査を含むworkflow](../../docs/research-workflow.md)。
- [近接研究の本文比較](method-section-comparison.md)、
  [自己批評](mock-review-v2.md)、[権利・会議規則の点検](release-and-venue-review-v2.md)。

## 長期目標は別途残る

[全体図](../program-map.md)の六目標を、この一稿の完成と同一視しない。
自由code・構成・配線・過程、black-boxと条件付き勾配、canonical evidenceを読む
英語game UIは実装されている。しかし、役立つ構造発明、勾配の実用上の利点、
改善手続き／設計者の自己改善、完成したゲーム体験は未達／未実証である。
全世界ADは本来の目標を満たすための必須条件ではない。

## 次に進むなら

新しい大規模実験より先に、**固定rule空間では表現できない情報経路の変更が、
何を変えるか**という具体的な識別可能な問いを定める。
同じ世界で、変更可能な箇所／固定箇所、実consumer、比較する初期制度、損失と
外側評価、生成interface、少数の対照介入、有限予算、反証条件を先に書く。
新構造を手作業で指定した対照は、自動発明の結果と呼ばない。
numericの生成不履行は別の有限interface診断で原因を分け、V2の失敗を再ラベルしない。

これは次の研究設計の推奨であり、実行済みの結果ではない。
現goalを延々と延長してseedを足したり、勝つ目的へ切り替えたりしない。
今回の区切りに未終了のwriter／モデル実験はなく、無人稼働も宣言しない。
新たな科学的実証を行う場合は別の明示的goalとprospective protocolへ切り分ける。

実投稿・共有upload／push・著者決定・有料サービス・新資源は未実施。
対象cycleの規則、著者責任、公開可能範囲は実行前にユーザーと確認する。

# スケールアップ前の最終監査

2026年11月9日。[九項目の終了台帳](../pre-scale-completion.md)に対する実施結果。
この有限ゴールの実装・接続・小規模実行・解析・UI・原稿・再現記録は完了した。
研究プログラム全体、最適制度の発見、top conferenceへの採択可能性を完了扱いしない。

| 要件 | 完了の根拠 | 証拠の限界 |
| --- | --- | --- |
| 提出・期限・中断・再生 | 元sourceのliteral数値提出2件、次62388a7の数値2件とstaged28件、cold replay。[監査](pre-scale-search-closed-verification-v1.json)。後続envelope助言は[別source検証](pre-scale-output-envelope-verification-v1.json) | 自由生成の完全信頼性は示さない。今回5件の実行失敗を保持し、修正で過去を書き換えない |
| 目的・測定・比較contract | 固定T/E、診断C、明示したdesign domain、参照、seed、予算、選択、別成分費用。[凍結protocol](../protocols/campaigns/pre-scale-search-v1.md) | loss／validity／評価／任意採用方針を区別。隠れた公平性・新規性vetoなし |
| 元世界の情報機構 | M0/M1/M2/M3・3seed・4年の12世界と2回全監査、実入力・selector再生・費用・全成分・図・数値再生成。[実結果](pre-scale-information-v1.md) | 情報が入力に到達することと科学的に有効なことは別。token量も一律に揃えた比較ではない |
| 自由制度の閉ループ | 数値／source／graph／uniformの全16枠、固定選択、27物理評価、2回全監査、全試行解析。[実結果](pre-scale-search-v1.md) | 8source変更、配線・schedule変更0。生成sourceは固定ルール選択ではないが、今回新しいtopologyが発明されたとはしない |
| 利用可能な勾配の接続 | 現M1で2draw→推定・更新→fresh native forward／無勾配対照を実装。連続・離散のcheckpoint/source/model/design一致を検証。[現native試験](../../tests/optimization/test_pre_scale_native_connections.py)、[最終559件検証](pre-scale-quiet-regression-verification-v1.json) | 実native lifecycle/Docker、研究者HTTPとcorpusはscripted。世界全体autogradや新Qwen勾配優位を主張しない。過去のlive勾配研究は独立に保持 |
| 継続社会への制度導入 | 現M3 checkpointから制度変更、研究者・論文・資源・memory・RNG・pending配送queueを保持し、cold再構築から年6まで継続。同じ[接続試験](../../tests/optimization/test_pre_scale_native_connections.py) | reset比較とsame-society導入は別。発明者自身の再帰的自己改善ではない |
| 検証可能な活動の拡張 | native archive独立計算によるcount assertion、検証、前件を保持する訂正、次年の実入力、時計非依存。[native claim tests](../../tests/system/test_native_claim_verification.py)、559件検証 | 科学論文の真偽や新知識の検証器ではない。元世界を包含する最小拡張 |
| 実記録の英語UI | 8arm実export二回一致、原コード・port・配線・年次・失敗。実Chromeで[NEXT EXECUTION](pre-scale-actual-foundry-browser-v1.json)、[失敗表示](pre-scale-actual-foundry-failure-browser-v1.json)、[閉鎖進捗](pre-scale-closed-observatory-browser-v1.json)、PC/mobileと0write/queue確認 | 開発記録と未使用seed評価は別。空間配置・spriteは模式表現。ライブ操作型の完成ゲームやuser studyとはしない |
| 解析・原稿・再現・整理 | 全49物理世界、全16枠・36論理行・96 paired比較、未知値・費用・source差を保持。132 cross-scoreと図/CSVを独立再生成。最終44p/19図/17表・全ページQA・別build本文一致。[PDF検証](../../paper/integrated-pre-scale-build-v3.json)、[全データとコマンド](../data/pre-scale-search-v1/README.md) | 数値再生成、元raw/source全監査、fresh inferenceは別。上流35B変換手順・全プロジェクトcompute・redistributionは未確認 |

## 閉鎖・検証の集計

- M12世界＋O/E49物理世界＝61実世界。元の70world上限を超えておらず、70回実行したわけではない。
- O/E49の内訳：6参照、16候補（11完走・5部分失敗）、27評価（全完走）。
  36評価ラベル行は27jobを共有し、独立な36世界とはしない。
- 検証は静穏時に旧source438/438、最新runtime559/559。追加の原稿・report関連73/73も別scopeでpass。
  これらを独立試験件数として合算せず、過去の437pass/1failも保持する。
- MとO/Eの各全監査は2回一致。O/Eのchainは11:35:12UTC、全科学stage exit0。
  M元writerの取得不能なexit statusは依然unknownであり、0へ書き換えない。
- 追跡した成果はローカルGitで統合する。実験worktree/source・rawは変更しない。
  リモートpush、公開、追加モデル、課金、スケールアップはこのゴールに含めない。

## 残るのは「省略した実装」ではなく次の研究選択

現小規模の境界で宣言した工程は閉じた。一方で、以下の成立は保証されず、
単にseed数やGPUを増やせば解決するとも限らない。

1. 非自明な新制度・新配線をローカル設計者が発明し、強い手作業ルールを安定して上回るか。
2. 勾配推定が同費用のブラックボックス法より有効になる設計分布・問題条件は何か。
3. 研究者・仮説・証拠・実験・再現の意味を拡張した世界で、最適化結果はどう変わるか。
4. 制度の改善だけでなく、発明・改訂手続き自体が改善するのか。
5. 人間にとって有益な科学の目的・指標と、実際に操作して楽しいゲーム体験をどう検証するか。

これらを実証済みへ昇格させず、次の有限研究計画で問い・対照・予算を決める。
今回の結果を良く見せるための追加再試行や、未承認の大規模化は行わない。

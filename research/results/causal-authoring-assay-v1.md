# 制度設計8セッションと保存入力上の実行結果

2026年11月11日。**8件すべてが最終提出・静的検証・cold replayを完了した。
ただし実行可能な制度が8件できたわけではない。** 保存入力での部分実行は、
1候補が例外、1候補が空decisionとなった。新しい世界のlossは測っていない。
[全枠のデータと再構成](../data/causal-authoring-assay-v1/README.md)。

## 比較条件

[事前protocol](../protocols/campaigns/causal-authoring-assay-v1.md)のT/E×初回／実履歴あり×
順序説明fileあり／なしの8枠を、clean `a2fb13c`で全て実行した。
既存local35B設計者、16 action、出力8192、context40960、1200秒／session。
旧実験のrequestと測定は歴史資料として保持し、新sourceの損失へ付け替えていない。
説明条件でrequest-bound decode seedも変わるため、共通乱数の効果推定ではない。

両条件のfresh readinessは各29件が通過。完全コピー差は各2件、原文を残した診断であり、
実interpreterの検証は通過した。8提出は2回の元source cold auditで同一バイトとなった。
未知の完了、長さ上限による終了、失敗枠の補充、生成コードのhost修復は0。
途中で5 actionがrejectedとなったが、同じ16 action枠内で全sessionがfinishした。

## 何を変更し、何が動いたか

7件は採否コード、E／初回／説明なしは既存ルーターの4数値を変更した。
全8件でnode、connection、scheduleの変更はない。
数値案はbias=-20、memory_cost=0.1、thresholdsの2値=10であり、
選択コードを書き換えた案へ読み替えない。

[別protocolの部分実行](../protocols/campaigns/causal-authoring-record-probe-v1.md)では、
元open-seed実世界から保存した4年分のselection入力を使った。
元コード4回の結果完全一致後、8候補×4入力をnetworkless/read-only Dockerで実行した。
入力の論文数は2、7、9、11。各frameは元のstate・入力を固定し、候補stateを年越しさせない。

| 目的 | 履歴 | 説明file | 変更 | 保存入力上のselection出力 |
| --- | --- | --- | --- | --- |
| T | 初回 | なし | コード | 全29論文にaccept |
| T | 初回 | あり | コード | 全29論文にaccept |
| E | 初回 | あり | コード | 4入力ともKeyError: world |
| E | 初回 | なし | ルーター数値 | 未変更selectorは全29論文にreject。変更した上流は未実行 |
| T | 実履歴 | あり | コード | 論文がある4入力全てにempty_cycle。identity被覆失敗 |
| T | 実履歴 | なし | コード | 全29論文にaccept |
| E | 実履歴 | なし | コード | 各入力1論文にaccept、残り25論文にreject |
| E | 実履歴 | あり | コード | 全29論文にaccept |

32部分実行のうち28回は関数が完了し、24回は全paper identityを被覆した。
これは**6つのselectorが固定入力で被覆した**という結果であり、6制度の有効性判定ではない。
特に数値案は上流を固定しているため、制度全体の反実仮想出力を測れていない。
native receiverへの適用、実査読task、研究者の次期行動、A/Q/R、lossは未測定である。
この4入力を新しい4独立seedや動的worldとして数えない。

## 設計者の説明と実装の隔たり

説明あり4件のいずれも`reference/causal-design.json`を読まなかった。
capability詳細fileの読取もなかった。したがって「説明を理解したが効果がなかった」
とは結論しない。本比較で与えたのは任意fileへのアクセスである。

E初回のplanは、後段の採否を厳しくすると査読へ入る論文が減る、と説明した。
現graphの査読90→採否130という年内順序とは合わない。翌年への採否の影響とは分ける。
E実履歴／説明なし案はfinal_scoreを最低10へ上げたが、EのQは元の査読値を使い、
そのfinal_scoreはQを増やすconsumerではない。説明どおりのloss改善とは扱えない。
一方、E実履歴／説明あり案の最終codeには、ここから直接review件数を制御できないと
認めるコメントもある。初回planだけで全過程の理解を断定しない。

例外案はworld入力階層を誤り、空decision案はtensor messageのpayloadを一段外して読んだ。
これらは受信・保存時のコード書換えではなく、実際に生成されたsourceの問題として保持する。
静的なPython／graph検証を、任意プログラムの実入力上の正しさの保証にはできない。

## 時間と費用

開始から最後のchat応答まで1861.22秒、約31.0分。
authoringは110 chat POST、入力2,225,666／出力23,017 token。
readinessは58 chat POST、入力618,249／出力3,574 token。
これらはbackendの各応答に報告された全prompt数で、cache差引後の計算量ではない。
最大実測入力23,419＋出力予約8192はcontext40960以内、length終了0。

これとは別に空promptのloadが10回あり、空load完了は確認したがtoken countsは全10回で未報告。
0 tokenを観測したとは記録しない。protocolの208 POST上限はchat枠であり、loadを含む全HTTP数ではない。
本assay／部分probeの研究者LLM呼出と新native worldは0。software QAのscripted世界は別集計である。

## 実行条件を変えずに整備した次回用の経路

実装identityのみだったsnapshot／review-routingに、実validatorと一致する詳細ABI cardを追加した。
さらに`causal_design_context=true, causal_design_presentation=inline`で、計画前から
現在graphの順序情報を表示できるようにした。省略時は元のfile方式を保持する。
式や解コード、最適制度、追加実験oracleは与えない。strategy bindingとresumeにも固定する。
この新表示を今回の8件へ遡及適用しておらず、モデルの提案品質向上はまだ未検証。
新sourceの実モデル実行にはfresh readinessが必要である。

clean f98f725のAPI/native整合性78件、clean3156365のinline／履歴／editor統合158件がpass。
保存入力probeの37件と完全literal exportの3件もpass。
exportは当初、数値変更をsource-onlyで表せないため出力前に停止した。
guardを外さず、数値も含む完全patchを出す方式へ変更し、全candidate fingerprintを再構成した。
最終clean22f1ac8では13module／217件が57.30秒でpass。
[source別検証記録](causal-authoring-assay-verification-v1.json)にhashと範囲を保持した。

## 次に進む研究

今回閉じたのは有限の設計・動作診断であり、top conferenceの主結果ではない。
同じ任意file比較を補充し続けず、次は新API／計画時表示を明記した有限の閉ループへ進む。
候補全体をnative worldで実行したlossと、部分入力の例外・被覆を別のfeedbackとして保持する。
数値だけの制度族、同じ情報・操作を持つcode、機構・配線を変更できる制度を比べ、
新しいtyped review-work権限は手作業参照にも与える。graphの生成や複雑さ自体を成功条件にしない。
現時点で次のlive worldや追加の実モデル探索は開始していない。

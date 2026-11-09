# スケールアップ前の数値提出と情報機構の検証

2026年11月9日。前日のdraftから、数値専用提出Dと手作業機構Mを実行する有限scopeを分離する。
ユーザーのスケールアップ前の作業一式の依頼に基づく、小規模ローカル検証。
O/E、勾配、継続社会、検証可能な活動は別の明示したscopeで実行し、ここへ暗黙に加算しない。

## 固定する対象

研究者はQwen3-8B、設計者は承認済み`qwen3.6:35b-mlx-64k`。モデルdigest、SciEvo四年corpus、Docker imageは既存のoperator bindingと実backendで一致を確認する。
実行source、実測backend、runtime全Python hashとこのprotocol hashを、推論前にplan.jsonへ保存する。
source固定はclean実験worktreeで行い、開発worktreeは別にする。

科学worldは元のSimulation、五研究者、四年、2016〜2019のcorpus、max_tokens768。
研究者LLMや文献を小さい数値モデルへ置き換えない。初期資源・project期間の法則は変更しない。
以前のopen-source例が直接行っていたproject変更は、今回の全M条件から除く。
元の研究計画を適用するnative activity bridgeは残し、制度からのamendmentは出さない。

lossはT=-A、E=-Q+0.5R、C=4A-Q+0.1R。T/Eは次段階の目的候補、Mでは同じ観測を三式で読む。
Qは元reviewの採択decision平均総和であり、作成したdossierやfinal_scoreをQに加算しない。
測定、技術的な実行可否、目的の損失、将来の採用方針を分ける。

## 数値提出D

二sessionをT/Eそれぞれのrequestで行い、最大二回／session、合計最大四回の生成POST。
六つの座標と、それを実際に読む固定実装を渡し、数値を直接JSONで指定させる。
sourceやgraphの編集toolはこの経路では提示しない。これは一般editorと異なるinterfaceであり、数値空間の内在的な優位性の証明ではない。
最後の座標は、今回無作用にした旧sourceの反復回数ではなく、dossier producerが実際に読むmax_recordsとする。
型・範囲・六値・rationaleをliteralに検査する。clip、暗黙の型変換、host修理はしない。
全current値をモデルが明示した場合のみretentionとし、生成失敗を初期制度へ置換しない。

一sessionのwall上限1200秒、connect10秒／read900秒、context40960、output8192、temperature0.6、thinking off。
親プロセスが自分のHTTP worker groupを期限で止める。read timeoutをwall上限と同一視しない。
中断後のserver側停止は未確認として保存し、同じ要求を再送しない。
完全なraw要求bytesはdispatch前のintentに保存する。HTTP200だけで成功とせず、done=true、done_reason=stopと完全なliteral JSONを検査する。
semanticな値の誤りは、元の二回の枠内でモデルに明示的に修正させられる。未知のtransport応答は再試行しない。
role loadは別途最大一POSTで記録する。

二sessionとも有効なliteral提出とcold replayができた場合、そのsource/model/backend/settings限定のnumeric certificateを作る。
general code/graphの適合性や、制度の有効性を証明するcertificateではない。
source変更後は再利用しない。

## 情報機構M

同じproducerはpublication後の記録を読み、author_id、paper_id、title、topic、採否、review履歴を限定数まとめる。
追加の研究者LLM呼出はなく、次期の既存の研究者入力へ接続する。

| 条件 | 作用 |
| --- | --- |
| M0 | 同じproducerを実行するがreceiverへの接続なし |
| M1 | 研究者自身の履歴を渡す。year1終了後に届き、最初の方向選択への入力はyear2 |
| M2 | 社会全体の履歴を、同じschema・max_records・recipientで渡す |
| M3 | M1と同じproducerに一年latencyを加える。最初の方向選択への入力はyear3 |

M2は完全な無作用placeboではなく、非個別化した情報の対照。
M0もproducerを残すので、生成・実行費用だけでM1との差を説明しない。
message内容の実際の長さ・件数も報告し、完全なtoken数一致とは扱わない。

development seedは41001、41011、41017、四条件で最大12world。
順序はseed昇順、その中でM0→M1→M2→M3。条件・順序・文面・lossを実行後に変更しない。
各worldはfresh実行であり、別条件の研究者応答を使い回さない。seed一致を完全な反実仮想ペアとはしない。
worldごとに最大1024の研究者HTTP試行を宣言し、全wireとコード実行context、年次checkpoint、最終測定を保存する。
技術的失敗はnullの観測として残してこのsourceを停止し、失敗した枠を補充しない。
効果が出ないことでは停止せず、正常なら12worldを完遂する。

## 出力と解釈

実際のcontext到達年、receiver、paperの時点、project amendmentなし、全T/E/Cとraw A/Q/R、資源・活動、応答とコードの費用を確認する。
scripted corpus／HTTPと実Dockerの試験で、M0の非到達、M1/M2のyear2、M3のyear3到達を事前に確認する。
この技術試験を実Qwenの科学実験と呼ばない。
三seedの全観測とpaired差を示し、重要な効果・一般化・科学的真実の改善を予め仮定しない。
新しい制度を発明した例ではなく、後続の探索に先立つ手作業の機構対照である。

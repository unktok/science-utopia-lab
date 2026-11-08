# 次段階の研究計画と既存データ分析

2026年11月8日。ユーザーは追加分析だけでなく研究全体の検討を求め、その方針で徹底的に進めるよう依頼した。
今回のgoalは研究質問、既存データ分析、有限の未実行実験案、分析とscale判断の作成。
新しいモデル推論、生成制度の実行、科学world、外部公開は対象外とした。

## 作業とsource

先行turnの全体案とINDEX／STATUSだけの変更を、mainの`eb41499`へ記録。
その後、`research/objective-landscape-planning-20261108`の独立worktreeで開発した。
元実験source `b6654ad`、凍結report、raw、旧稿、統合原稿とPDFは変更しない。

新分析は、既存のarchive loaderとexact-selection checkerを再利用し、64完走候補、9参照score、全120枠の状態を確認した。
元のreport contentは`75f64370d673699553f69c480c93b90c07c2babba70b4f924cbc54438ab9d732`。
9参照のA/Q/Rは独立なT/C/Eの代数的反転であり、新しいraw測定の読取とは分ける。
図のanalysis上のtie toleranceは、凍結済みのexact selectionや数値を変更しない。

分析コードの最初のsourceは`090b1c8`。
最初の試験は11pass／1failで、欠測metricのnegative fixtureが片方のreport projectionだけを変更したため、目的の欠測guardより先に整合性guardへ到達した。
production guardを緩めず、両projectionを一致させたfixtureで修正した。
figureのSVG IDも固定し、同じdataからPNG／SVGが同一bytesになる試験を追加した。
この段階の53試験は11.43秒で全pass。
続いてnumeric finish診断と保存時間成分を追加し、新分析14試験は1.46秒で全pass。

初期renderはworktreeのGit対象外`outputs/native-design-objective-landscape-initial-090b1c8`と
`outputs/native-design-objective-landscape-initial-fed54fe`に保存した。
最終の数値・図はanalysis source `0cf53668984ec3d62d772f9d70d905411207e246`からclean状態で生成し、`2f7d282`で記録した。
analysis contentは`0efa6194154fe186ce58cc12f5fd459f995c288403af3e14b78686b593c7a4a5`。
最終図は同じPNG hashの初回を目視確認済み。再現照合と最終試験の結果は別verification receiptに保存する。

## 分析から計画へ反映したこと

- Cの単純な参照制度への非優位を、モデルサイズだけの問題にしない。目的の係数と観測したQ/A、R/Aの関係を先に読む。
- Eの事後的な良い二観測を、E目的の探索成功や未使用評価済みの優位性にしない。
- 同じ制度fingerprintでQが約1/3違う二組と、浮動小数点の微小差の一組を区別する。
- 数値24候補には47回のfinish試行があり、43回がdomain超過、4回が数値範囲外。提出意思の不在だけで説明しない。
- 小規模protocolは提出診断、機構比較、目的別探索、選択固定後評価を分ける。最大70worldと20設計者sessionは検討用上限で、起動していない。
- 最適化の勝利を仮定しない一方、pilotの不成功を重要な否定結果へ自動的に格上げしない。

## 読解した資料と利用範囲

元論文、既存のmethod比較、objective catalog／landscape、native domain／process／feedbackのcontractを参照した。
一次文献はScienceUtopia、SGA、GPTSwarm、ParmasとSugiyama、Leiden Manifestoの該当箇所を再確認した。
FortunatoほかのScience公式サイトは403のため、著者原稿のPMC版の要旨と冒頭の該当範囲を使用した。全文精読や新規性の網羅調査ではない。

ai-scientist-surveyはread-onlyで使用し、先にAGENTSとTOPIC-MAPの該当分野を確認した。
snapshot commitは`02b437b854e73f1bd8a274399e56167ee05a4400`。
以下の非公開資料は冒頭と該当する機構・機能の範囲のみを読み、全文・原文・生データを本repoや原稿へコピーしていない。

| survey内path | SHA256 |
| --- | --- |
| `research/2026-09-10-science-institution-dynamics-mechanism-atlas.md` | `8f9a7ca0658aed3f09b016fea6a0f18375edecee5c2f36e1c004cc9593804b91` |
| `research/2026-09-09-research-evaluation-function-decomposition.md` | `109b0c330f90e8f71258e943c7c847b455a3727654df81abad53c607fd93f5c4` |
| `research/2026-09-10-research-reproductive-currency-and-allocation-game.md` | `542df149845067d54f8cc86e172a7be6132191567439b314bc76e31df94defe2` |

これらは計画の着想であり、独立した実証や原稿の優先権の根拠ではない。
survey側への変更や新規raw取得・保存・公開はしていない。

## 実行しなかったこと

実験writer・モデルserver・生成制度を新規起動せず、GPUや新モデルを調達せず、push／upload／投稿を行っていない。
計画の文書化にはwrite-pageスキルを用い、既存repoの文書構造を保った。
protocolは候補であり、source、seed具体値、参照、loss、期限等の実行前凍結は残る。

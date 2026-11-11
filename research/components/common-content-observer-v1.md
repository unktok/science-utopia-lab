# 科学制度から切り離した固定条件の内容採点

制度によって査読者や採否が変わると、同じ測定式でもQの観測条件が変わる。
`CommonContentObserver`は、元の研究者世界の成果を固定条件で追加採点する任意の測定器である。
進行中671436aのT/E、設計条件、raw、選択には適用しない。

## 入力と採点対象

入力は実際のnative archiveに保存されたtitle、abstract、topicsの全文。
paper ID、著者、所属、制度名、採否、元の査読値、設計者の説明、探索損失はpromptへ渡さない。
文字列は原文を保持し、入力上限を超えた場合は短縮せず失敗する。
内容中の指示はdataとして扱うよう指示するが、LLMのprompt injection耐性を保証するものではない。

固定rubricは、abstractが裏付ける研究貢献と方法の具体性を1〜5で採点する。
これは固定モデルの意見であり、実験の再現、科学的真偽、実社会の価値の検証ではない。
同じ重みの複数criticを使えても、誤りの独立性や人間の査読との一致は仮定しない。

## 損失と外側評価への接続

完了した元Simulationから、採択decisionごとの論文内容を取り出す。
各内容について固定criticの平均sを求め、次の二列を追加する。

- `native.common_content_score_sum` は採択decision全体のsの和。
- `native.common_content_utility_sum` は採択decision全体のs−3の和。

3はこの測定版の明示的な中心値であり、普遍的な科学の良さの閾値ではない。
採択のない世界は空の和として0。1 criticでも採点不能なら、当該内容を使う和はunavailableとなる。
同じ内容が複数decisionに現れた場合、元のA/Qと同様にdecisionを数え、採点の物理実行だけを共有する。

この二列を選択に使う場合は、新しいLossSpec、係数、世界、探索予算、参照、seed役割を
新campaignとして固定する。例えば中心化utilityを使うことと、元の非中心化Qを使うことの差には、
採点器の変更だけでなく出力数への誘因の変更も含まれる。単に「独立化の効果」とは呼べない。
外側評価だけに使う場合は、選択を固定してから実行し、探索へ返さない。
採点値を採用vetoや隠れた公平性制約にはしない。

`evaluate_native_suggestion(..., measurement_adapter=observer.measure)`が接続点である。
adapterはtrustedな測定コードで、候補JSONからPython関数を受け取る経路ではない。
元のrun ID、system fingerprint、A/Q/R等の全測定値は変更できない。
測定の技術的失敗で損失が得られなくても、既に完了したnative worldのcheckpointとrun証拠を保持する。
既定のadapterなしの実験は、元の測定経路を使い続ける。

## 固定条件と費用の記録

契約はsource、adapter hash、model digest、backend version、rubric、critic数、POST上限、
40960 context、512出力token、temperature0.6、connect10秒／read120秒を固定する。
localhostの既存モデルだけを使い、新しいモデルを取得する処理はない。
実モデルを使う前に、clean sourceと実際のmodel/backendを確認する。

cacheは論文内容と意味を持つ採点条件に基づく。source IDや予算などの運用識別子は証拠へbindするが、
それだけでdecode seedやpromptを変えない。別制度で同じ内容が出ても、同じ物理採点結果を共有する。
したがって未使用world seedは、未使用論文や独立したcritic応答を意味しない。
論文自体への一般化を調べるなら、別の内容単位の分割が必要になる。

POST前の正確なUTF8、受信直後のHTTP原文、完了状態、literal score、使用量、時間を別journalへ保存する。
HTTP200だけでは完了にせず、doneとstop、モデル名、score/rationaleの型を検査する。
既知の不正な応答は欠測として固定し、同じdrawを補充しない。
timeout、非final、結果の欠落では、次の物理推論を止める。受信結果の修復や切出しはしない。
同じ推論lockを使い、別のモデル要求と重ねない。

`observer.audit()`は原文から状態・採点・costを再構築し、物理attemptを数える。
cache利用を新しい応答として数えず、未報告token数はunknownのまま保持する。
このcomponent費用を科学者・設計者・readinessへ合算して重複計上しない。

## 検証と研究上の位置

scripted採点器を使う元Simulationの接続、損失計算、低い予算での欠測、未知完了での停止、
内容だけのprompt、運用IDに依存しない入力、cold replayを検証する。
scripted scoreを実際の品質評価や改善として報告しない。
clean af294b7で45 pass／3 skip、同じ3件を実Dockerで再確認して3 pass。
さらに元62388a7の44完了checkpointから263採択decision／76内容を読出し、
全文の要求1449〜3232 bytesが全件上限内となった。二回の準備出力が一致する。
[保持資料と再生成](../data/common-content-observer-v1/README.md)。
実モデルでの互換性、rubricの挙動、閉鎖済み成果への採点、目的別の新しい探索は、まだ実行していない。
現pilotの全結果を閉じて解釈した後、必要な科学的対照と有限予算を決める。

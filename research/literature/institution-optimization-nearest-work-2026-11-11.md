# 制度最適化の近接研究と主張の境界

2026年11月11日に一次公開資料を再確認した。網羅的なsystematic reviewではない。
HTMLの確認節とabstractだけの確認を分け、未読の実験設定を推測しない。

| 一次資料と今回読んだ範囲 | 既に存在する内容 | この研究で別に必要な証拠 |
| --- | --- | --- |
| [SciUtopia v1](https://arxiv.org/html/2610.01257v1)、§2.1–2.2とabstract | 時間で制限した実文献の選択、研究者の持続state、査読、採否、資金、再投稿。再投稿が査読負担を増す知見も既存 | loss条件付きで実行可能な制度を設計・選択すること。既存の介入や再投稿効果の再確認だけにしない |
| [GPTSwarm v3](https://arxiv.org/html/2402.16823v3)、§2.1–2.4 | DAGによるagent合成、node promptの改良、graph分布の期待効用に対するREINFORCE | graphやscore-functionの発明を主張しない。制度が実際に持つ観測・操作・時点と持続する帰結を検証する |
| [ADAS v2](https://arxiv.org/html/2408.08435v2)、§2–3 | code空間、評価とarchiveに基づくmeta-agent設計、reflectionと有限の実行エラー修正 | 一般code探索自体は新しくない。本文は制度の作用と目的の関係へ置く。修復を許す方法と比べる場合、修復予算も揃える |
| [SGA v1](https://arxiv.org/html/2405.09783v1)、abstract | LLMの離散仮説と、微分可能なsimulationによる連続内側最適化 | この組合せを新原理にしない。現在のnative研究者世界への勾配利用の実証は別に必要 |
| [AMD-LLM v1](https://arxiv.org/html/2502.12203v1)、abstract／導入 | 制度codeの生成と進化、問題別fixingでの設計要件充足 | 自分たちのno-host-repairを優位性にしない。lossとは別の制約を黙って追加しないという実験上の選択である |
| [LLM Economist v1](https://arxiv.org/html/2507.15815v1)、§1–2 | 労働者と税率plannerの二層in-context適応、持続的な社会の政策最適化 | 固定重みLLMの社会で制度を最適化するというだけでは新規性にならない。科学制度という対象差だけでも不足 |
| [AFlow](https://arxiv.org/html/2410.10762v1)、§1 | code workflow、既定operator、MCTSと実行feedback | 新たなoptimizerを主張する場合は対応する強い探索対照が必要。今の2世代pilotをその比較の代わりにしない |
| [ADAPT for Science](https://arxiv.org/abs/2610.30851)、abstractのみ | 科学設計の探索先と探索手続きの共適応、未使用topologyでの比較を報告 | 手続き自身の改良まで主張する場合の近接研究。今回の制度探索を設計者の自己改善へ言い換えない |
| [Mining the Design Space of Multi-Agent Workflows](https://arxiv.org/abs/2610.31709)、abstractのみ | 全探索経路の保存と、未使用search上でのworkflow原則の検証を報告 | trajectoryを残し分析するだけでは新規性にならない。発見した制度上の関係を独立な設計履歴で検証する |
| [The AI Scientific Community](https://arxiv.org/abs/2603.21344)、abstractのみ | virtual lab swarm、情報流やfitness等の概念設計。実装は開発中と明記 | 自由な科学共同体というvision自体を最初と主張しない。実行と目的別帰結で差を示す |

上の「必要」は自分たちの研究設計上の判断であり、各論文の著者が述べた要件ではない。
最後の三件は2026年の近接資料として追加した候補であり、全手法・コード・全実験の比較を済ませていない。
OpenReviewのfacility-location論文候補は今回ページを取得できなかったため、その内容や採択を根拠にしない。

## いま主結果として採用しないもの

次は実装上は必要でも、それだけで主会議の中心的貢献にしない。

- 汎用code、graph、black-box、LR、pathwise部品を同じrepoへ集約したこと。
- 全raw、null、費用を残したことや、校正／QAを多数通したこと。
- 一つの開発seedで初期制度より損失が下がったこと。
- 新nodeやwireが生成されたこと、または生成されなかったこと。
- 本来後続の制度から、既に行われた処理を変更できないことの確認。

これらは主張を支える基盤／分析であり、削除するという意味ではない。
中心は目的・作用権限・制度・持続的な帰結の関係について、既存研究以上の答えを出すこと。
その候補を今の有限native pilotで調べるが、重要性が足りなければ結果を閉じて問いを改める。

## 測定側の次の識別課題

以下は文献の要約ではなく、現在の測定実装からの自分たちの導出である。
`measure_native_world`のQは、採択された各decisionについて実査読scoreの平均を足す。
制度がreviewerを変えると、RだけでなくQを測るpanelそのものも変わる。
任意の`final_score`を排除しても、Qが制度から独立した科学的品質になるわけではない。

このため次を区別する。

1. **目的内の達成**：宣言したT/Eが改善するか。制度の複雑さや規範的条件を後から課さない。
2. **測定者の変化**：reviewer集合、paper集合、採否、再投稿、年次を分け、何がQの差を生んだかを見る。
3. **独立な外側観測**：必要なら、選択後に固定したblind observerで同一artifactを同一条件で評価する。
   これは追加の診断であって現T/Eの新しい合否条件ではない。同じLLMの意見は科学的真偽でもない。
4. **独立検証可能な科学活動**：真偽・発見の改善を問うには、検証器と研究課題を原worldへ足す別研究が必要。
   元の研究者世界を簡単な数値世界へ置き換えず、現在のpilotへ遡及適用しない。

blind observerを導入する場合は、artifact ID／年／タイトル／abstract等の対象範囲、固定panel、
raw prompt、cacheの共有単位、有限呼出数、未使用評価の扱いを実行前に別protocolへ固定する。
制度名、探索loss、設計者の説明、採択済みというlabelをobserverへ与えない。
同じartifactの再観測を独立標本として増やさず、欠測を補充・0埋めしない。
現段階ではこの追加観測をdispatchしていない。

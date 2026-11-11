# 元の制度の実行順序

`initial-system.json`は、閉鎖済み62388a7実験のopen-seed参照が実行したSystemSpecの同一バイトである。
`operational-order.json`は、そのschedule、port、wireから派生した読み取り専用の説明である。
費用80、査読90、採否sender130、およびその間の明示的な割当機構を置ける時点を記録する。
コード本文の意味を推論せず、損失や新しい科学的成果も作らない。

既存の承認済みproject interpreterで、freshな出力先へ再生成できる。

```text
.venv/bin/python -m scripts.reports.native_causal_design_v1 --system research/data/native-causal-design-v1/initial-system.json --output <fresh-output.json>
```

元file、独立した二出力、retained fileからの出力が同一バイトであることを確認した。
この派生物は元実験の全監査を再実行したものではない。raw応答やcacheは含めない。
[研究計画](../../publication/institution-causal-design-plan.md)と[接続検証の結果](../../results/institution-causal-design-v1.md)を参照。

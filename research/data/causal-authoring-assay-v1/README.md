# 制度設計診断の保持データ

[解釈と全8枠の結果](../../results/causal-authoring-assay-v1.md)。
assay sourceはa2fb13c、部分Docker probe sourceはbda0406。

- `audit.json`: 元sourceで2回同一バイトとなったcold audit。全8枠とchat単位のcostを保持。
- `policies.json`: 全8モデルplan、finish、read回数、実際のselector source、完全literal patch。
  [初期SystemSpec](../native-causal-design-v1/initial-system.json)へpatchを適用すると各candidate fingerprintを再構成できる。
  1件の数値変更も保持しており、source変更7件と混同しない。
- `fixed-record-probe.json`: 4保存入力×8候補の例外・出力・paper被覆。
  native world実行でも、新candidate lossでもない。
- `costs.json`: 設計、readiness、空loadの分離。未報告load token countsは不明。
- `manifest.json`: 各file hash、元plan・両cold audit・probe planの識別。

`scripts.reports.causal_authoring_assay_v1`で同じ原source audit2件とraw assay／probeから再生成する。
このディレクトリはcompactな結果・候補の復元資料であり、raw HTTP全体を含む公開fresh-inference bundleではない。
元request、HTTP、途中のrejected action、container入力・出力は独立experiment worktreeのignored outputsへ保持している。

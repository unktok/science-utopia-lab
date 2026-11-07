# S1 strong-rule controls: all eight completed and audited

2026-11-07。[submission goal](../publication/submission-goal.md)のS1。
[protocol](../protocols/campaigns/native-benchmark-controls-v2-a1.md) ·
[compact data](native-benchmark-controls-v2-a1.json) ·
[figure](../../paper/figures/native-controls-v2-a1/strong-controls.png)

全8worldを元の研究者lifecycle・固定Qwen3-8B・五人・二年・development seed42で実行。
07:49:17.234630–08:26:40.560637UTC、37m23.326s、exit0。
八制度とも完走、失敗・slot補充なし。**全て開発者の基準制度で、自動発明ではない。**

## 結果

T=-A、E=-Q+0.5R、C=4A-Q+0.1R。Qは元review平均の総和、科学的真理の指標ではない。

| 基準制度 | A | Q | R | T | E | C |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 未変更legacy制度 | 2 | 6 | 18 | -2 | 3 | 3.8 |
| editable open seed | 0 | 0 | 24 | 0 | 12 | 2.4 |
| open＋rank/rate source | 2 | 6.666667 | 21 | -2 | 3.833333 | 3.433333 |
| open＋全採択 | 7 | 22.333333 | 21 | -7 | -11.833333 | 7.766667 |
| open＋全却下 | 0 | 0 | 24 | 0 | 12 | 2.4 |
| open＋score閾値3 | 7 | 22.333333 | 21 | -7 | -11.833333 | 7.766667 |
| open＋score閾値4 | 0 | 0 | 24 | 0 | 12 | 2.4 |
| open＋reviewなし全採択 | 7 | 0 | 0 | -7 | 0 | 28 |

表示のみ丸め、exact floatと全同点はJSONに残す。目的間で尺度を平均しない。
同じforward測定のcross-scoreであり、追加の独立標本ではない。
Tの最小は全採択／閾値3／reviewなし全採択、Eは全採択／閾値3、Cはseed／
全却下／閾値4の全同点。異なる目的が異なる順位を与えるが、最適化方式の比較ではない。

## 何を意味するか

- 元のlegacy制度は実際に2件を採択する。弱いopen seedの0件を、原制度の能力として
  語らない。open seedは追加の協働processとtensor選択を持つ別の具体例である。
- V1のLLM最良案と同じ観測損失に、単純な全採択ルールでも到達した。ただしV1とは
  sourceが異なり、同値の数値だけで同条件の方式比較や厳密な実装等価性は証明しない。
  次の本試験には手作業対照をfresh同sourceで組み込む。
- reviewなしでも採択数だけなら同点になる。Qは0となるため、E/Cでは同じ帰結ではない。
  reviewなしの全7採択はraw accepted_unreviewed_decisionsにも残っている。
- Cは宣言した採択debitを含むため、全却下が最良群に入る。これを科学の改善と
  呼ばず、不都合な候補のvetoにも使わない。次の本試験にはreviewなし全却下も明示して、
  自由graphだけが容易なゼロ活動対照と競争しない比較を避ける。
- 原制度とopen rank/rateでは、selection以外のopen processも異なる。両者の差を
  selection sourceだけの因果効果やコード移植の厳密等価性と呼ばない。

この単一seedの基準比較は、研究として必要な対照を揃える段階である。
自由コード／構造探索の追加価値、feedback効果、期待改善、未使用条件への一般化は未実証。

## 費用・監査

物理8world、scientist応答726／wire726、制度コード実行56。designer応答0。
explicit scientist role loadは各world1回で、生成応答と別会計。
local DockerのソフトウェアQAは研究worldやモデル反復として加算しない。

原source `2aa02c3cb4610cde4797744386da67fe851383b0`で二回read-only監査し、
full reportがbyte-identical。265 source/helper/protocol/loss files、年checkpoint測定、
code/source/context、response/wire、role/context、writer/progressを検査。
raw inventory前後不変。監査時の新モデル呼出し・コード実行は0。

- full audit content SHA256: `3a344dcbc71c8300d0844696d44b807d3a5ba0eeca14301b1d50c60dd4656ac1`
- full audit file SHA256: `8540825985998fe97ef8258e8896a1436a1d6797271646b50612a53ecad68d85`
- compact content SHA256: `7d94f5db85648d5feb211039949cea1947239d35ae08d97fa9ebf3035bb01aa5`
- raw: `outputs/native-benchmark-controls-v2-a1/`（Git外）
- audits: `outputs/native-benchmark-controls-v2-a1-audit{,-a2}.json`（Git外）

[report generator](../../scripts/reports/native_control_summary.py)でcompact JSONと図を
再生成できる。図は別尺度・全同点を表示し、PNGを目視確認した。
前向きな本試験コードは別worktreeで開発し、終了済みS1を改変していない。

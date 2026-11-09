# 全体のゴールと証拠の対応

2026-11-09更新。目的は「自由に設計できる科学制度を、利用できる評価・勾配で最適化する」こと。
[研究目的](../RESEARCH.md) · [直近状態](STATUS.md) · [優先順位](roadmap.md)

現在は[スケールアップ前の終了条件](pre-scale-completion.md)を進めている。
情報経路の12世界比較は解析まで完了し、目的別の数値／code／graph／uniform探索を
実行中である。選択後評価は探索終了後に行う。過去のV2の完了を、この新しい区切りの完了とは扱わない。

## 一本の研究経路

```text
明示した目的関数                 固定した研究者モデル・コーパス・世界条件
       ↓                                           ↓
制度の設計空間 → 提案器 → 技術検査 → 元の研究世界で実行 → 不変の測定記録
                   ↑                                      ↓
                   └──── 損失に基づく探索状態更新 ← canonical loss
                                                          ↓
                                  評価・解析・原稿・同じ記録を読むゲームUI
```

目的を変えること、制度を変えること、探索法を変えることは別の操作。
技術的失敗はnullとして残す。目的ラベルは候補採用のvetoではない。

## 六つの目標

| 元の目標 | 実装・実証済みの範囲 | 残る研究上の問題 |
| --- | --- | --- |
| 目的別に科学システムを最適化 | LossSpec、ask/tell、own-history再設計、履歴bank。過去V2の120枠・選択後90評価まで完了。現在は情報機構の12世界比較が閉じ、新しいT/E探索を実行中 | 現在の探索・選択後評価・解析は未完。強い基準への上積み／feedback優位は未実証 |
| 出来合いでない制度を作る | sandboxed Python、typed ports/state、生成IR。外部設計者のV13で実作用と観測改善 | ローカル設計者の信頼性、コード変更と機構上の新規性の区別 |
| 構成・関係・プロセスを自由にする | SystemSpec、node/edge/protocol編集、actor/artifact、guard/repetition。V12で新機構の実作用 | パラメータ探索を超える価値の対照比較、信頼境界・世界の単純化の明示 |
| 勾配を利用する | 条件付きLR/LOO/control variate、tensor/局所表現、V10の実経路比較。現在のM1にも2draw→更新→fresh native forwardと無勾配対照を接続し、scripted研究者・corpusと実Dockerで確認 | live研究者に対する勾配の優位性・費用効率、世界全体ADは未証明 |
| 継続・再帰的な改善 | 評価→own-history→再設計、same-society adoption。現在の遅延情報M3でも、制度変更後の研究者・論文・資源・memory・待機中情報・RNG保持と継続をscripted QAで確認 | live研究者での制度導入効果、改善手続き・設計者自身の改善は未実証 |
| ゲーム的体験 | 英語pixel/cyberpunk UI、canonical replay、Foundryと経路の表示。実M/O/E記録の時点付き観測画面も実装・ブラウザ確認済み | 現在の探索／評価の最終exportは未完。経営ゲームとしての体験、人間参加型研究は長期課題 |

## 証拠への入口

- [現在の情報機構比較](results/pre-scale-information-v1.md)：M0/M1/M2/M3×3seed、
  元の研究者世界で12/12完走。実入力・全監査・selector再生・費用・図・数値再構築まで完了。
- [現在のT/E有限protocol](protocols/campaigns/pre-scale-search-v1.md)：
  16提案枠・6参照、選択固定後の3未使用seed評価。新sourceで数値2件・staged28件の提出確認後に実行。
  全失敗・null・同点を保持し、改善が出るまでの補充はしない。
- [現在の接続QA](../tests/optimization/test_pre_scale_native_connections.py)：
  勾配更新後のforwardと、遅延情報を保持する継続社会への導入を元simulatorで検証。
  [ソフトウェア検証の出典と限界](results/pre-scale-regression-verification-v2.json)に
  広域437pass/1failと同sourceの単独2passを分けて保持し、静穏時の最終広域確認は未完。
- [検証可能な活動の実装](../utopia/system/native_claim_verification.py)と
  [元世界への接続テスト](../tests/system/test_native_claim_verification.py)：
  実際のnative記録から独立に件数を計算し、誤った主張と訂正を両方残して研究者入力へ接続。
  科学論文の真偽判定や新しい研究課題の自動発見ではない。
- [S1強い基準比較](results/native-benchmark-controls-v2-a1.md)：手作業8制度すべて完走。
  自動発明の結果でなく、弱いseedへの改善を単純基準への優位性と混同しないための対照。
- [V2 protocol](protocols/campaigns/native-design-freedom-v2.md)：二目的・五群・三履歴・四世代と
  選択後評価を固定。全件終了・二回監査・解析／再現資料／原稿を完了。
  [最終棚卸し](publication/submission-decision-v2.md)は、実装と観測された知見を区別する。
- [V1](results/native-feedback-comparison-v1-a1.md)：ローカル35B、二目的・二群・二世代。
  全8案提出、4完走／4実行失敗。両目的ともcontrol G0の全採択案が最良、世代1の上積みなし。
- [V45](results/native-warmstart-v45-a1.json)：ローカル設計者、二案提出、一評価完走／一失敗。
- [V13](results/native-nested-search-v13-a1.md)：外部設計者、自由制度＋条件付き更新、観測改善とproxy攻略。
- [V12](results/native-objective-redesign-v12-a1.md)：新しい機構と配線の実作用、改善しなかった改訂も保存。
- [V10](results/native-method-paths-v10-a1.md)：共通履歴を課金した勾配／black-box経路。優位性は示していない。
- [Parameter/held-out研究](../paper/figures/metric-conditioned/README.md)：初期の制限された探索空間。自由制度の実証と混ぜない。
- [英語UI](../game-ui-v2/README.md)：同じ証拠を見るインターフェース。

## いま動いているもの

V1、V45、V2のwriterは終了済み。現在のM比較も閉じているが、別の凍結sourceで
T/E探索→選択固定→評価→全監査を行う直列writerは動いている。
別プロセスは実記録を読むUI用の観測だけを行い、追加の科学推論を起動しない。
勾配・継続社会・検証活動の接続実装はQA済みであり、それぞれが別のlive実験を
永続的に走らせているわけではない。時点付きの状態と出典は[STATUS](STATUS.md)、
残る終了条件は[現在の台帳](pre-scale-completion.md)に分ける。記録ファイルだけで
プロセスの生存を主張せず、原稿とUIの最終反映まで今回のゴールは完了としない。

## 全体像と一本目の論文を分ける

六つの目標は研究プログラム全体の射程であり、全てを一論文の貢献としない。
最初の論文の中心は、目的条件付きの自由な制度最適化と、その方法・自由度・
発見された機構の比較。勾配は利用可能な場合の方法、ゲームは証拠の観察層。
再帰的自己改善と現実政策への一般化は、現時点では長期課題である。

[以前の全体図](program-map-history-through-v45.md)も原文のまま保持する。

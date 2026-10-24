# ADR-0001: 研究 fork を `unktok/science-utopia-lab` に置く

- Status: accepted
- Date: 2026-10-24

## Context

上流 ScienceUtopia をmacOS上で動かす変更ができ、次の段階として制度最適化、評価機構の抽象化、微分可能化、ゲーム化を継続的に研究する。これは単発の個人再現ではなく、metascience とAI研究基盤にまたがる長期プロジェクトである。

## Decision

- 研究 fork は private repository `unktok/science-utopia-lab` とする。
- `origin` は研究 fork、`upstream` は `Ahren09/ScienceUtopia` とする。
- simulator code、研究ノート、実験 harness、ゲームとの共有 schema を一つの repository で開始する。
- 大きいデータ、model cache、生出力はGitへ入れず、manifest、要約、hash、解析コードを保存する。
- ゲームが独立して配布・運用される段階になった場合のみ、別 repository への分離を再検討する。

## Why `unktok` rather than `t46`

`t46` は個人研究・公開成果の置き場所として自然だが、この研究は科学制度設計という組織的な metascience 方針と、既存のAI研究基盤へ接続する。所有と継続性の観点から `unktok` を選ぶ。個人論文や公開用 artifact が成立した場合は、必要に応じて別途公開 repository または archival release を作る。

## Consequences

- 上流追従と研究固有変更を明示的に分ける必要がある。
- private の間も、論文・データ・model のライセンスと出典を維持する。
- 一つの repository が過度に大きくなった場合、event schema を境界にゲーム client を分離できるよう設計する。


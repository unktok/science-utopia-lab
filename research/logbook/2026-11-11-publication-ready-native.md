# 投稿準備ゴールの再開とnative閉ループ

ユーザーはtop conferenceへpublication-readyになるまでの自律継続を依頼。
新しいgoal toolをactiveにし、[研究目標](../publication/publication-ready-v3.md)と
[次の有限protocol](../protocols/campaigns/native-institution-loop-v1.md)を作成した。
以前のQAや有限パッケージの完了を、主会議readyの達成へ付け替えない。

近接研究SciUtopia/GPTSwarm/ADAS/SGAの一次abstractを再確認。
graph最適化、codeによるagent設計、LLMとsimulationの離散／連続最適化は既存研究。
それ自体の再発明でなく、科学制度の目的・利用できる操作・継続する帰結を切り分ける。
abstract確認は各論文の全手法・全実験の詳細比較を終えたという意味ではない。

新しい開発branchは`research/publication-ready-native-v1`。先行experiment checkoutは触らない。
初期制度・legacy・強い単純ルールに加え、typed routingの1/2人review基準を実装した。
候補に与える権限は手作業参照にも与える。2人routingは元の乱数割当てとの等価shamではない。
任意の候補sourceを修復するhelperではなく、明示的なdeveloper基準として扱う。

T/E×3設計域×2generationの12案、参照8、選択後最大33で最大53worldを固定。
fresh source・inline条件で初回readinessを行い、各proposal前にもfresh校正する。
これにより参照worldを待つ間に古い証明書を使う問題を避け、24時間guardは変更しない。
全失敗・null・費用を保持し、参照失敗や未知の完了では止まる。補充なし。

純粋なorchestration8件がpass（5.56秒）。新しい実モデル・native worldはまだ未dispatch。
seed61001/62001/62011/62017の使用確認と、実Simulation/Dockerのscripted接続検証を進める。
外部モデル・費用・公開投稿・pushなし。

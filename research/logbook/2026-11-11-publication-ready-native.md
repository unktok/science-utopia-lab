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

clean4851aceで56件pass／39.90秒。3raw rootsのseed scanを含むa1 planをprepareしたが、
モデルdispatch前の最終確認で、再利用numeric校正器の内側lockとcampaign共通lockが
別pathである点を修正。共通lockを校正全体で保持するようにし、競合取得拒否の回帰を追加。
a1はprepared-onlyとして保持し、変更したsourceを新しいa2 checkout/planへ固定する。
古いplanのsourceや失敗記録を変更せず、まだモデル生成・科学worldは0。

## 新sourceの初回readinessで停止した不具合

a2/clean234044fの56件は40.07秒でpassし、3roots合計1014 response journalに
dev/held-out seedの使用がないことを確認した。plan file SHA256は
`626679045f77e48126ba2a3b543be828bc10e89d34aa6387bea5cb69abeee87a`。
08:04:22UTCにPID35444で実readinessを開始したが、08:05:45UTCに停止。
16 typed controlsのHTTP応答は全て完了し、次のsequence-planの送信前に
`inline causal context requires bounded authoring profile`が発生した。
科学world、候補生成、数値校正への後続呼出は0。a2は停止のまま保持する。
terminal file SHA256=`ab2666a72846bb5154ac0b90b12f2fb4890e35fd7f87462e08c384a336eaa2ed`。

原因は、実production plannerのv45表示を検証した一方、校正器のplan分岐が
profileをbuild_promptへ渡さず、planning_conversationも旧schemaのkeyを読んでいたこと。
新たなreadonly表示に対するこちらの接続バグであり、生成案やモデルの誤答ではない。
両分岐を直し、実campaign requestをそのままscripted backendの全校正とcold replayへ通す回帰を追加。
file/inline/旧既定を区別する17件が14.19秒でpass。
copy taskのSYSTEMは維持し、loss最適化とcopyを混ぜず、旧証明書・停止成否を変更しない。
修正sourceを新a3へ固定して再開する。新source校正の費用もa2の16応答と分けて保持する。

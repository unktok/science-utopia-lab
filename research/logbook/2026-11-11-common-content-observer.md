# 固定内容採点器の実装と継続中の制度探索

前goal turnは47頁統合稿とbuild/evidence bindingをmainへ統合したprogress。
このturnはsession52939／48610の生存をpollし、同じwriterで実験を継続した。
科学source671436a／解析source d11e431は変更していない。

10:14UTCにE数値G1は−11.166666666666668でcompleteし、G0と同じ損失。
10:19UTCにはT固定graph G1が実行失敗となり、8/12枠終了、E固定graph G1の校正へ進む。
失敗lossはnullのまま。未使用評価はまだ未開始。これらは進行中stateの観測で、閉鎖後のfull audit前。

固定content observerを別開発sourceに追加した。元Simulationを置き換えず、完了後の
trusted measurement adapterで新しい測定列を追加する。既存のA/Q/Rとidentityの上書きは拒否する。
中心化3は明示した候補尺度で、現T/Eを変更せず、truthやpublication-readyとも言わない。
write-page skillとwriting_qualityを読み、repoのcomponentノートへ契約と限界を記録した。
LLM採点の新呼出、world、PDFの変更、外部公開は0。

最初の15 unit checksはpass。次のnative接続の実行ではfixture import不足と
CPU/offline環境の設定漏れで20 pass/4 setup error。guardを弱めずimportと起動環境を修正。
その後23 pass/1 failは、scripted native fixtureが12 POST上限を超えて測定不能となったもの。
24へした中間fixtureでも同様で、両JUnitは保持する。
最終testは低予算12で測定不能を確認する場合と、fixtureの4著者×6年×3critic=72の有限上限で
接続を確認する場合の両方を保持する。実験予算や停止条件の延長ではない。
native/budget testsは25 pass/4.41秒、raw HTTP保存とcold status/cost検査等は28 pass/4.49秒。

追加調査として、モデル一覧のlocalhost GETは通常sandboxで拒否されたため、read-onlyの
明示escalationで取得。推論・load・downloadはしていない。現在の35B-mlxと8Bのほかに
35B-A3B Q6の既存aliasがあるが、モデルを切り替えていない。
現在はthink-offの固定protocolであり、今の失敗がthinking設定のせいだったとは断定しない。

clean af294b7のfinal QAは45 pass/3 skip/7.63秒。同じ既存3 Docker caseを
権限付きで再確認し3 pass/20.85秒。元のskipもJUnitも変更していない。
source/HEADは両検査と実入力準備の前後で不変。
busy inference lockでintentすら作らないこと、observer完了不明で次のseedのworldを
作らないことも検証した。実LLMは呼んでいない。

af294b7のstaging scriptは、元62388a7 readerで44完了checkpointを読み、全hash／spec／年／Aを
旧full auditへjoin。5途中worldは保持してskipし、263採択decisionを取り出した。
76種類のcontentがあり、3criticの全要求は1449〜3232 UTF8 bytes、全件上限内。
必要な物理POST上限は228だが、新採点は0で、token容量やモデル互換性の証明ではない。
二回のcontents／contract／staging JSONはすべてcmp一致。
summary content SHA256=`ef8043a0fc464338e90999d4b1ce7fec239766751ddb368050ae01c3b938f935`。
原文付きcontentsはignored outputsにだけ保持し、content hash／wire hashと数のsummaryをGitへ保持。
1859 raw全体のfull auditを反復したという意味ではなく、旧監査にbindしたcheckpoint読出しの検査。

進行中pilotは10:32:53UTCにE固定graph G1が−11.166666666666668でcomplete。
初回の出力envelope失敗に対し、モデル自身が固定されたG1で有効な案を提出・実行した。
host修復や失敗の補充ではない。手作業のreviewed全acceptや数値Eと同値で、優位性は主張しない。
候補9/12枠終了（5完了／4失敗）、T code-and-graph G1へ進行。未使用評価はまだ開始前。

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

## 修正sourceの実校正を通過し、native worldへ

clean671436ad207688dc230596e8d0c4a8f5f1a87d76で183件pass／64.39秒。
JUnit file SHA256=`fbc994fb39476287393b0152a41071724cd225f08923b695ebba7782137e16da`。
新しいimmutable checkoutは`science-utopia-lab-experiments/native-institution-loop-v1-a3`、
rawはその`outputs/native-institution-loop-v1-a3/`。
plan file SHA256=`c563c0b15554ad5a03040397954ff9474f7b22692000c133ad68de5c57618022`、
content SHA256=`ae486b90ce3ada4b4aeee7bb8af06fa01c2018f30ef4dd8431c1110bf2f94d2b`。
08:17:03UTC／PID37093で開始。actual editor28/28の全controlsとcold replayがpass、
numeric T/Eともliteral提案・replayがpassし、08:20:00UTCからopen-seed参照worldに入った。
08:22UTCには元のSimulationで研究方向、資金申請・評価のQwen呼出が進行。
copy校正の通過は自由提案の理解・成功や損失改善を示すものではない。
使用seed・目的・予算・失敗停止条件を変更せず、そのまま有限実験を継続する。

待ち時間には別branch上で新閉ループ専用のcold auditorを実装。
凍結sourceを先頭に置いた別interpreterでnative libraryを読み、各proposalのfresh校正、
その時点で存在した他目的の履歴prefix、実dispatch時の校正age、全null、selection前後、
shared physical jobを検証する。科学モデル呼出・生成codeの再実行はしない。
26 synthetic guardsが3.91秒でpass。実閉鎖データの全auditはまだ実行していない。

08:27:18UTCにopen-seed参照が四年完了、08:34:09UTCにlegacyも完了。
前者のA/Q/Rは2/8/42、T=-2、E=13。これは初期参照で、探索による改善ではない。
別interpreterで両completed cellのoriginal-source physical proofをreplayし、
model/corpus/source、全応答、初期〜四年checkpoint、measurementの一致を確認した。
open-seedのcheckpoint SHA256=`0e70be0f32b7351c69347c397a21a94e001e73e37ad1494084f3f829370b6560`、
proof content SHA256=`4a569c2c30f47694ed9b9f632dc9d5d92caac21a9b079389fe2c0a7ee5206c8a`。
legacyはそれぞれ`13d49de310f6c149fbb6d5913286648fb859d9b4bad1a944eff6f7fa3ec1e35c`、
`8d6d383b5ca9d1e6bb5c49c3b6781bef3041060c0fe12348d6ed4571e0480126`。
これは二つのcompleted cellのみの診断であり、全pilotの閉鎖監査ではない。

解析source c50f0cfでは新旧のreport/cost/audit等132件が36.73秒でpass。
三method、seed62001/62011/62017の新図、全12候補／8参照、logicalとphysicalの共有を
synthetic dataで検証した。以前のreport schema／seed／図の既定値は維持して回帰した。
追加したread-only後処理chainは科学writerの消失と正常terminalを両方要求し、
全audit・費用・図を二回再構築して比較する。推論や科学worldの再dispatch機能は持たない。
chainの初回4pass/1failはテスト用時計に必要な三回目の値がなくStopIterationとなったfixtureミス。
時計fixtureだけを修正して5/5pass。停止・timeout・PID再利用・図の差のguardは弱めていない。
このchain自身の完了もpublication-ready判定には使わない。

chainの全段階をscripted subprocessで通す二条件（正常／初回audit失敗）も追加し、
7/7pass。science再起動なし、失敗後の次段階なし、consumed出力の再使用拒否を確認。
clean d11e4314d4c409f005ccbe3ce5e4d0c5f392c66fの別analysis checkoutで39件が6.96秒でpassし、
08:40:42UTCにPID40332でread-only待機を開始した。
rawは`science-utopia-lab-experiments/native-institution-loop-analysis-v1-a1/outputs/native-institution-loop-analysis-v1-a1/`。
最大待機24時間で、科学writer／sourceには一切手を入れない。科学writerはPID37093のまま。
その時点では参照3/8完了、no-review-accept-all実行中。候補search／選択後評価はまだ未開始。

待機後の可搬な再構築も別開発sourceに追加。全A/Q/Rと欠測statusからcross-scoreを再計算し、
全候補順序、tie、選択policy、labelと実worldの共有、図4fileのbytesを確認できる。
literalなsource／node／wire／schedule差分の抽出も新12枠へ対応。
新旧の合計64 synthetic report/rebuild/changeチェックが32.20秒でpass。
これは凍結d11e431の待機chainへ遡及変更せず、閉鎖後に追加で適用する。

## 09:52UTC観測：4候補の結果と1つの生成code失敗

session52939と48610は継続し、sourceを再起動／変更していない。
参照8/8の後、T数値G0=-7、E数値G0=-11.166666666666668、
T固定graph G0=-2がcomplete。E固定graph G0は技術的失敗でloss=null。
T code-and-graph G0のfresh readinessを経て、新しいauthoringに進んだ。
全pilotのcold auditは閉鎖後であり、ここは進行中stateのdated observationである。

T固定graph候補の最終patchは3回のaddressed-selection置換で、最終的にbias4、
thresholds0/0、memory_cost0となる。任意codeを許すmethod labelを、実際にsourceや
graphを変更したという結果へ言い換えない。初期よりT損失が下がったとも主張しない。

E固定graphは提出／compileを通過し、元native worldで生成関数を実行した。
実例外は`outputs['world']`に必要な`{'payload': object}` envelopeがないこと。
受信source自身に`'world': [observations[0]['payload']]`とあるため、実行器が
有効なrecordを勝手に壊した証拠はなく、この観測は生成された関数の契約違反と整合する。
source全体／全運用がbug-freeという意味ではない。例外は原rawに保持し、hostで包み直さない。
authoring response content SHA256は
`90c8b3f2312fd44ed814aecc9503aa80d714a982fcf16b68bd743973ac00c839`、
observationは`observation-native-adaptive-97df5e66ef462728cea78a54`。
G1は固定予算内で自身の失敗を受け取れるが、枠の補充／新しいbaselineへのfallbackはしない。

待ち時間にADAPT／Mining MAS Workflows／AI Scientific Communityの一次HTMLを追加読解し、
abstractのみだった比較メモを対象節付きへ更新した。全履歴保存、構造と実装不良の分離、
LLMと勾配の併用そのものを初出と主張しない。47頁稿はそれ以前のsourceへ固定して保持し、
新しい主比較が閉じた後の科学的解釈と関連研究更新へ反映する。

## 10時50分UTCの停止と次の実験の区別

実writer37093/session52939は10:50:27UTCにexit1、read-only chain40332/session48610も
科学terminalがstoppedであることを検出してexit1となった。どちらも継続中とは表示しない。
元671436aとrawは変更しない。8参照、11候補提出のうち5complete/6技術null、評価0。
残ったT数値G1を補充・再提出せず、失敗certificateは失敗のまま保持する。

最後のfresh数値readinessはTが形式エラー後の予算内2回目で提出完了、Eが1回目で
`done=true,done_reason=length,eval_count=8192`を返した。raw assistant contentは1960文字、
prompt_eval_count4306、HTTP200。token数をcontent文字数から推測せず、provider値を保持する。
Eはrequired literal submissionを完了せず、証明書passed=false。通信timeout／未知完了ではない。
certificate content SHA256は`3691acbdf2047af7d05b885858b798c82c13fb89e23ede4735f71174054922a8`、
terminal content SHA256は`945883e54bc43fa049c7a7dfa6dd25af31f5b669fd361c6342ed741852bb7f8d`。

生成codeの6失敗は3件float添字、1件features KeyError、2件world record envelope欠落。
任意sourceを許した8枠のうち、実行完了はT固定graph G0とE固定graph G1の2枠。
前者はtensor parameter置換、後者はsource変更を行う。許容した自由度と実際の変更を区別する。
これらをhostが自動修理するのでなく、将来の有限authoring内で実入力のcomponent testを
設計者自身が利用できる仕組みを検討する。native lossの追加oracleとは分ける。

停止prefix専用の監査scopeを追加した。通常のclosed監査は変更せず停止runを拒否する。
新scopeは既知の数値readiness停止・予定順のprefix・pendingなし・選択／評価なしを要求し、
失敗readinessもliteral replayする。synthetic24チェックは4.17秒でpass。
これにより失敗を成功closedへ変えず、既に得た候補の再構築と別評価protocolを準備する。
別評価を行う場合は11提出と欠けた1枠をそのまま固定し、新候補生成・baseline代入を行わない。

停止prefixの原source監査を二回実施し、45,294,018bytesの出力が完全一致した。
content SHA256は`15f042d65d55fffb2c4e750038f88ba25fb74ecce6f953cf5b590902c4019b46`。
19実world、2162raw files、11authoring、14readiness scopeを検証し、推論も生成source実行も追加しない。
出力は開発worktreeの`outputs/native-loop-stopped-prefix-a1.json`と`-a2.json`。

別の固定候補評価protocol／runner／cold auditorを追加した。元runのresume機能は持たず、
既存4枠の完了候補だけから最小loss・最初のtieを選び、全滅した2枠は選択なしとする。
open-seedを含む6参照と3つの未使用seed、上限30world、designer生成POST0。
元のsource/rawをwriter lockとinventoryで保持し、候補・job・lossを応答前に固定する。
まだ実験はdispatchしていない。

初回synthetic QAは44pass/5fail。再利用job projectionが、selectionのcontent hashを
要求する既存helperへhashなしの一時objectを渡していた実装ミス。元helperのguardを弱めず、
projection入力とselectionの両方を正しくhashして修正。再実行49/49pass、6.83秒。
初回JUnitも保持。元の19worldや候補の修正・追加はない。

clean d2b6651では関連79/79pass（19.69秒）。停止実験の費用projection二回も一致し、
1796 scientist応答（1,615,207input/181,308output tokens）、428auxiliary intentsとなる。
内訳はeditor readiness256、staged proposal112、numeric readiness13、numeric proposal3、
designer load25、scientist load19。費用content SHAは
`e80b30b27ff6a03a8d45ea27748f49de8d26de163c12b8259044d45178567d4b`。
重複alias／nested時間は足さず、未知load使用量を0へしない。

別evaluation a1をd2b6651でprepareし、30job／候補固定planを保存したが、runの
source/runtime/jobs検査で起動前に停止した。started.json、native world、model POSTはいずれも0。
保存時のsort_keysがselected辞書の順を変え、job projectionが辞書順に依存していた実装ミス。
明示arm_orderを保存し、そのlist順にのみselectedを走査するよう修正。
実際のsave→read→require_plan、およびJSON roundtrip後のjob一致を回帰に追加した。
a1のplan／sourceは書き換えず、新sourceで別prepareする。制度候補の補充ではない。

f1f8ddf4813f2252ab0a54b3f69c4f3f25c1eb9eでclean関連80/80pass（19.84秒）、
JUnit SHA256は`14c4c9cef6db16d23a1b0bca0701e4bd850cabc4021c49091fd0d6c332284057`。
a1の原sourceをread-onlyで診断しsource_equal/runtime_equal=true、jobs_equal=falseを確認。
最初の違いはevaluation-018で、元T数値から保存後E固定codeへ順が変わっていた。
sourceやbackendの書換え／候補の修復ではなく、明示順序を欠いたrunnerのバグだった。

別worktree`native-fixed-candidate-evaluation-v1-a2`を同sourceへ凍結。
prepareと実saved-plan guardが通り、11:25:10.241405UTCにPID59964/session62719で開始。
plan content SHA256は`1f35f65be17077fa37451ff48df5d8c75a16b9f08885bf2aa8a3a0830e618c14`。
元rawと科学writer lockを保持し、fresh seed inventoryもdispatch前に再確認した。
最初の世界でQwen3-8Bのresearch direction5件と資金申請の実応答を観測。
候補固定4label＋参照6label×3seed=30実world。追加designer生成は0。
原pilotの終端はstoppedのまま。publication-ready、method優位性、制度発明は主張しない。

開発側へcode実行attemptの別journalを追加した。既存recorderはdelegate成功後にのみ
contextを保存していたため、元6失敗のtrigger入力は当該journalに残っていない。
新実装は実行前にexact artifact/contextをfsyncし、returned／raisedを別eventで記録する。
成功時のlegacy bundle形式は保持し、cold replayはそのbijectionも検証する。
raised／pendingからremote実行完了を推定せず、旧rawの欠落を後で埋めない。
mocked executorのみの10チェックが0.69秒でpass。新しいcontainer／LLM／native world実行は0。
実scientist worldでの回帰と設計者toolへの統合はまだであり、これだけで発明精度の改善としない。
live固定候補評価のf1f8ddfには適用しない。

5cc8493のclean sourceでrecorder／physical proof／元native Simulationのzero-code経路／
固定候補evaluationを合わせ35/35pass（6.69秒）。実Qwen応答・新container実行ではなく、
scripted元Simulationとmock executorの範囲。試験中もsource／HEADを固定した。

別API `NativeComponentLab`は任意のliteral code artifactを記録済みcontextで試し、
原関数と同じ結果を要求せず、JSON契約と実行receiptだけを検証する。image／timeout／
最大8probeを固定し、invalid fixtureも課金枠として消費、pending時は再dispatchしない。
host修復・policy置換・新native lossはない。cold replayはcontainerを再実行しない。
元671436aの監査済み開発参照3種、selector／feature-extractorの実入力をstageするguardも追加。
未使用620xx worldには触れない。mockのみ24/24pass（0.81秒）。モデルtool接続前であり、
これを実LLM自己debug完了とは表示しない。実入力stageとtool接続を次へ進める。

なお、今回8code sessionの全実promptを読み、step1以降はliteral_current_system_includedが
trueでimplementation checkpointも複数回発生していることを確認した。「document byte上限で
実装phaseに全く入れない」という仮説はこのデータに当てはまらず、その理由でguardを変更しない。
既存自己履歴とsource読取だけでは実contextに対する実行テストの代替にならない。

5aaecdfのclean関連48/48pass（6.94秒）の後、実fixture stage a1は
`component artifact has ambiguous node identity`で停止。model／container／新worldは0。
original nativeのphase10 intrinsic handlerも内部でcode実行をdelegateし、そのartifactは
graph node.parameters.code_artifactには直接格納されていない。全recordを直接code nodeへ
逆引きしようとしたstagerが、対象外のこの正規実行を誤ってambiguousと扱っていた。
対象2nodeに一致するrecordだけを選び、その中の一意性と各nodeの非欠落を要求するよう修正。
対象外の全physical recordも原auditとのhash／event attribution確認は維持し、native本体は変更しない。
intrinsic handlerを含むscripted fixtureを回帰へ追加。失敗a1は空の出力directoryのまま保持する。

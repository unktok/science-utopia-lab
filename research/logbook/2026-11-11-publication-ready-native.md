# 投稿準備ゴールの再開とnative閉ループ

## November12の原稿更新準備

15:38:49UTCに別固定候補評価は28/30完了、evaluation-028へ進行。
code-testedの新writerは依然として前実験の独立監査closure待ち。
実行中source・候補・予算・lossを変更せず、原稿へ閉じた証拠を統合する。
新節は停止した671436aの全12枠／19world、原literalな6失敗、既知の
length termination、別評価との区別、component feedbackの実装と未実証の境界、
条件付きT/Eの全採択誘因、旧44worldの176年次checkpoint／880actor観測を扱う。
本文の表をretained numeric vectorsから再計算する回帰を含め30件が3.32秒でpass。
draft PDFの初回cache-only buildは51ページ、layout警告／未解決参照なし。
これはまだ最終PDFの全ページ目視検証・新source二回build receiptではない。
AFlow、ADAPT、Mining MAS Workflows、AI Scientific Communityの公式arXiv metadataを
再確認し、trajectory保存やexecution feedback等を独自発明としない関連研究を追加。
原47頁と旧build receiptは一切変更しない。主会議ready判定は未達のまま。

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

a54a776307b0cf608dead42a76d4897a172fa5c2で実stage a2/a3が両方成功し、
fixtures.json／summary.jsonのbytesも一致。24入力（selector12、feature-extractor12）、
三つの開発参照×四年、全てseed61001。new model/container/worldは0。
raw bank SHA256は`01dc82787c86d3b4d5db1a229183b2f93d23ccbbee7797fa04baf1ef33ca2f08`、
summary file SHA256は`e45b7810464fb8dd3ef51c7e5a9dc2553954a374fdbf68fe2b6763600095a2a3`、
summary contentは`5ad39187bf99f0cab7dfc0939025dad0aa682f7feb33087986ddd9e3ea2e1f18`。
3.9MBのraw contextはignored outputに残し、9.5KBのsource/event manifestをGitへ保持。
これは実source-bound入力の確認であり、設計者がtoolを使った／自己debugしたという結果ではない。

次のcontainer確認は3callだけを事前固定する。元open-seedのyear1 selector実入力一つへ、
baseline、元T固定code G1のfloat失敗source、元E固定code G0のenvelope失敗sourceを順に適用。
baselineが失敗したら停止、候補が期待どおり失敗しなくてもfixtureやsourceを変えて補充しない。
caller自身もcodeを修復せず、元の入力・source・出力／例外を保持する。
元の全world失敗の再現、LLM自己debug、損失改善の検証とは別のcomponent診断。
入力選択とAPI／stageの17 scripted QAは0.89秒でpass。

3c0ba8c33009bb05327129f5625848c89028cc14で実container3callを完了。
statusはreturned／returned／raised。baselineは過去出力hashを再現した。
E旧envelope欠落はCodeExecutionErrorとして検出、T旧float添字は今回発火しなかった。
この入力ではscores.recordsとscores.valuesが空で、sourceの`values[i][0]`を含むloopに入らない。
従って「古い失敗2件を両方再現」とは書かず、事前3callのまま閉じ、追加fixtureで補充しない。
各caller観測時間は0.236／0.191／0.199秒。LLM応答費用や新world時間ではない。
summary contentは`78c7657a965805df43c573a38dedf678f1ddc7ee198ce69ea600e261fa545aec`。

別の二つのfresh Python processで、execute禁止executorを与えたcold replayが共にexit0。
replay SHAは`c51a59cfb2ccb4246865fc9078d15b3a4e8bf828a6c3fb92bb631bc1c2c5cf7c`で一致し、
追加container／LLMは0。自動code修復、全native failure再現、発明やloss改善の結果ではない。
この結果からモデルtool側は「単一empty fixtureを通れば安全」ではなく、事前に固定した
empty／nonempty・複数年のsuiteを選べるようにする。新institutionをgolden出力へ同一化しない。

固定候補30worldが終わった後の有限read-only chainを追加。writer59964の正常終了とPID不在を
最大24時間待ち、元f1f8ddf sourceのcold audit二回、実費用projection二回を比較する。
科学writerの再起動／再試行／推論／欠けたterminalの生成は持たず、stoppedならchainも停止。
図・原稿・科学的解釈とpublication-ready判定は、その後の根拠に一致する作業として残す。
新旧chainの12 scripted checksが0.04秒でpass。次に別のimmutable analysis checkoutで待機させる。

read-only chainはa123aff8d37a5b5e9e1d938ecb72e5769325bfc6で12:18:37.619011UTCに
開始、session46822。clean24/24pass（1.34秒）、JUnit SHA256は
`bea079a8fa59708d23c9694a3d9253db956555617d85b0a510bdb7e95cb7a261`。
13:29:32UTCの科学progressは14/30 complete、evaluation-014実行中。

post-edit adapterを開発側に接続。既存literal toolのcode変更後、固定open-seed61001の
四年contextを実行し、次promptへエラーとexact archive pointerを返す。最大8probe、
15秒/container。失敗によるfinish veto、原sourceへの復元、自動修復、loss変更はしない。
new/unconfigured interfaceは未試験のまま許す。完全結果はstep archiveへ保持し、
大きな本文をactive promptへ反復挿入しない。pendingは次のmodel call前に停止。
fresh certificateには同一contractが必要で、旧certを流用できない。

scripted session QA a1は63pass、bounded shape追加a2は71pass/1fail。
feedback NOTEが最終V44 action markerを押し下げたため、既存decoderが正規actionを読めなかった。
NOTEをmarkerより前へ移動しa3は72/72pass（17.66秒）。raw結果は保持。
bounded workerとrole bindingを合わせたQAは42/42pass（60.92秒）。
追加したfresh-contract回帰の初回は、test helperへ空action listを渡してmax_steps=0にしたため
3fail/19pass。runtime guardを緩めず、未実行finish一件を使うfixtureへ修正。
これらはfake backend/executorの検証で、実35Bの自己修復や新native lossとは数えない。
実モデルcalibration／有限assayはlocal inferenceを共用する現30world終了後に行う。

clean56e2331bcfaf29a23b2a22e12637b672c9888be9で広域12moduleを固定実行。
初回は178pass/17fail、全17件が既存Docker socketのpermission denied。
source／HEAD／検査を変えずDocker access付きで同じsuiteを実行し195/195pass（199.90秒）。
JUnit SHA256は`ba0e44917a4c28cedc0fc0b004f766279658a579281613b1d2d7d2fde265490f`。
元Simulation/scripted研究者とcorpus／実Docker、全scientist payloadの時計・identity回帰も含む。
実Qwen／designer生成0。初回の失敗JUnitも保持し、別科学sample数へ足さない。

候補固定評価用のportable reportとread-only後段chainを追加。元12slot／全ties、
二つのpolicyなしarmの6seed-row、共有physical jobを残し、閉鎖audit二回一致後だけ生成する。
scoreはcheckpointのliteral A/Q/Rから再計算し、全参照とのpaired差を保持する。
模擬データの図を内部previewし、実結果と明確に区別した。
初回10pass/1failはSVG IDの非決定性で、plotting hash saltを宣言して解消。
続くCLI試験の一回は不存在のtest filenameを指定し0件実行、ファイル名を確認して再実行。
new report/chain/既存reportの32checkが13.55秒でpass。新native world／LLM呼出は0。
13:49:25UTCの科学progressは16/30完了、evaluation-016実行中。

clean cd383cc6467c9531b059ed26091c6d203639427dでreport／旧reproducer／evaluation
関連73/73pass（29.69秒）、JUnit SHA256は
`38977a3217456a34e28e130ed7a22367a9aa0fd91621248548ebf2a89e6ed24f`。
同sourceの別analysis worktreeで13:55:14.203804UTC、session5365にreport chainを起動。
既存a123aff監査・cost chainの正常終了を待ち、実データreport二回生成／全byte比較を行う。
新しいmodel／world／candidate選択はない。実図の目視と原稿への解釈は終了後へ残す。

post-edit modeの起動経路点検で、proposal向けbank必須guardがcalibrationにも掛かる不備を
実モデル使用前に発見した。calibrationではmodeを宣言するだけでprobe実行しないよう分離。
更にactual calibration workerからcold certificateへ通す新回帰で、factoryが
require_certificateのsummaryをfull certificateだと仮定していた不備を発見。
以前のfactory unit mockが実APIにはないplanを返していたため、195checkには検出力がなかった。
verifierから検証済みdeclared contractをsummaryへ明示し、factoryはその値を比較する。
全calibration frameにも宣言を含める。候補実行前であり、既存実験の修正・補充はない。

失敗JUnit a1（22pass/1fail、summaryへのplan access）とa2（42pass/1fail、control frame宣言欠落）
を保持。a3は43pass。続けて、mock cert／mock model classを使わず実role/factory/transportで
scripted HTTP calibration→実cert検証→BAD code→返却error→literal GOOD code→finish→cold replay
を通し、関連44/44pass（20.49秒）。fake HTTP／executorであり、実35Bの能力実証ではない。
同種の境界誤認を防ぐため、実公開APIを使う全経路検証をAGENTSへ追記した。

clean58bc16d8ed1976a45308d55e297768989d94a36aで16module、244/244pass（209.92秒）。
JUnit SHA256は`f2618833f9329345797c65b7ec94a99708a42075753e2c79d098f932b97d150d`。
actual校正worker／summary API／role factoryのscripted全経路、新旧report・reproducer、
元native Simulation・実Docker・全scientist payload回帰を含む。実model推論0。
元の195checkの範囲限界を遡及消去せず、今回の境界修正と新sourceを別に保持する。

次の[code-tested loop protocol](../protocols/campaigns/native-code-tested-loop-v1.md)を
14:10UTC以前に固定。T/E unchanged、code-and-graph二群×二世代、T0/E0/E1/T1、
fresh参照三つと候補四つの最大七native world。61001は明示的な開発再利用で未使用とは呼ばない。
component bankは元の開発入力だけ、最大8probe/提案。新620xx結果は入力へ渡さない。
実行前に現f1f8ddf科学writerとa123aff独立audit/costの正常終了を待つ。
各提案のfresh実backend校正、literal提出→元世界測定→own-history改訂を繋ぎ、
失敗枠／基準へのfallback／component pass gateは入れない。今回の改善からfeedback一般の優位性は推定しない。
runner、閉鎖時source-bound監査、既存cost projectionへの明示scopeを実装中。
saved-plan JSON roundtrip、四つのnull枠、pending完了で次群を止める回帰等が通る。
これはまだ新モデル推論の開始観測ではない。

clean93076b477b023a6bcb78cac5568fcbe795fa9a52で新loop、既存cost/audit、実public
校正API／role、旧mode、候補固定evaluation/reportを合わせ146/146pass（82.90秒）。
JUnit SHA256は`825da646e78cc8e14a6d27ae5770e7a5ba79e5628d0f36aae0845f98fe3893bc`。
同sourceの新worktree`native-code-tested-loop-v1-a1`で、既存local backendへのGETと
実bank/hash照合だけを行うprepareが成功。実saved-planのrequire guardも通った。
plan content SHA256は`8b818742271f1ea5f38bc02e4700fcb0b4752ba056f4ebb3909a99619d35fdb4`、
file SHA256は`70ac3c016a31a7455bc764ac6d3eed2588fdefe039a0ff556915f7547e532e7b`。

14:28:45.968131UTCにPID77538/session91390で新loop processを起動。
stageはwaiting-for-preceding-closureで、旧30worldの実科学writerとa123aff独立audit/costが
正常終了するまで推論は0。新modeのfresh実backend校正、LLM自己debug、native改善は
この起動観測では未実施。旧評価progressは14:23:34UTC時点で20/30完了。
三つのread-only／待機processを、三つの実科学実験が並行推論中とは呼ばない。

R2をコード提出率だけの問題にしないため、既存のlossの識別範囲も点検した。
査読結果・review workload・将来への影響を固定し、各q_iが非負ならT/Eは共に全採択を
条件付きで好む。これはdynamic世界の全体最適性ではなく、同じ受理ruleが選ばれる理由の一部。
過去62388a7の保持reportから完走44world／非完走5をそのまま抽出すると、
最終active authorsは44/44で5、総最終resourcesは540〜780。単独の終端活動stockは
この観測済み完走集合を識別しないが、個人の資源十分性／途中退出／全制度での不変性は示さない。
新しいlossや制約は選んでいない。次の重要な制度／情報／資源／時点の研究質問を考える材料。

`scripts.reports.native_objective_support_v1`で保持reportから独立に二回生成。
両outputとretained JSONのbytesが一致、file SHA256は
`6f87cf48ef52591133c8d9b7762b0ea0eac8adeb581a2a91097a538f7818c231`、
content SHA256は`50860495ea4d0dbe096d87d5cca3f8edf02b95f5431e7f7abe67320ca0c38675`。
四つの解析／欠測回帰が0.64秒でpass。原raw全監査の再実行、new world／model呼出は0。
cohortは過去閉鎖reportだけであり、進行中620xxの結果を使っていない。

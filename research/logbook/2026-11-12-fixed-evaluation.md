# 固定候補評価の閉鎖と次の実行

別の固定候補評価f1f8ddfはNovember11 16:00:06UTCに30/30で正常終了。
開始11:25:10UTCから16496.75秒。元671436aは停止のままで、候補の補充／baseline代入なし。
独立原source監査二回は16:01:43／16:03:07UTCにpassしbytes一致。
費用二回も一致し後処理chainは16:03:09UTCに閉鎖した。
audit content65b76951、filef061823e、cost file1b710fe1。
4590 scientist応答、input4,923,237／output426,066、30loadのusage不明を維持。

cd383ccのreport chainは16:03UTCにreport-1で停止。
原因はclosure progressの候補がarm単位で並び、physical worldsはdispatch順なのに
両配列をindexでzipしたこと。原監査／原world／科学lossの誤りではない。
候補を一意なarm/generationでjoinし、全keysが予定prefixへ一致するguardを追加。
grouped fixture／duplicate keyを回帰し、停止したa1 source/logは書き換えない。

可搬な再構築の新testは初回25pass/1failで、保存後JSONのdict順の変化による
図のlabel順とCSV列順の差を検出した。explicit label/score orderを記録し、
旧rendererの既定動作を保って修正。26系を含む36件pass後a434cf8へcommit。
新read-only a2 checkoutで67件pass、checkout完了後の確実なclean再確認でも
67件46.47秒、JUnit SHA256c1e4a3314c1e0c776c205fc5a7df217fe38ea63b60d48c6e3b1abc2affab69af。
同sourceで二回reportを作り16:08:25UTCに全7files一致で閉鎖。
actualな共通score図／停止探索path図を目視確認した。

次の93076b4は予定どおり前chain閉鎖を受けて16:03:18UTCにfresh実校正開始。
certificate content8e3238d1を生成し16:06:43UTCにopen-seed参照worldへ進んだ。
新proposal／自己修復／損失改善はまだ観測していない。
このwriterと08f671bの監査待機は継続し、source／budget／lossを変更しない。

[実結果](../results/native-fixed-evaluation-v1.md)ではT数値が強い全採択と同じA、
E数値は通常査読全採択と小さなmixed差、1人査読全採択には全3seedで劣る。
graph全滅の二armへpolicyを捏造しない。重要な主会議結果の不足をseed数やQA数で
埋めたことにせず、次の主研究の作用／観測／時点の識別へ持ち越す。
49頁PDFはこの閉鎖前snapshotとして保持し、新実図の原稿への統合は次に行う。

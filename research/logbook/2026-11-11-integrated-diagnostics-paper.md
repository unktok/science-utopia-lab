# 統合原稿：制度設計／測定診断の追加

publication-ready goalはactive。進行中671436aの科学sourceとd11e431の
read-only後処理sourceは変更せず、session52939／48610の継続を確認した。
09:39UTCには参照8/8、T／E数値G0の2枠がcomplete、T固定graphコードG0を実行中。
未使用評価は未開始。これらの部分結果を完成した比較として本文へ追加していない。

PDF skillとwrite-page skillを読み、既存LaTeX書式／repository Markdownを維持。
本文へ実際の権限と実行時点、全8提出の部分probe表、実cost、Qの内生観測、
元62388a7固定記録のpanel感度図を追加。過去の構造・勾配・UI・全比較を保持した。
無制限に頁を削るのではなく、測定対象と未達の主張を明示するworking manuscriptとする。

旧37頁receiptのテストは更新済みcurrent TeXと旧hashを比較しており、
変更前1701a7bで2 fail/3 pass。`outputs/integrated-diagnostic-prior-baseline.xml`を保存。
旧source5fcf2b7のGit blobを実際に取得すると旧hashと一致するため、
旧receiptのsource／asset／evidenceはそのcommitで検査するよう修正した。
保存済みPDFとpreserved artifactは今も実ファイルで検査し、歴史を再ラベルしていない。
旧原稿／pre-scale checksは7 pass。新稿は別の実data／build検査を付ける。

新稿data testの初回は9 pass/1 fail。境界文の期待語句`already performed`が
本文の`actually performed`と異なるテスト記述ミスであり、期待語句だけを修正。
元JUnitは`outputs/integrated-diagnostics-paper-prebuild.xml`に保持。
部分probeの8行、候補fingerprint、未読file、28 return/24 coverage、costの欠測、
44完了／5途中失敗、217査読付き／46査読なしdecisionを保持資料と照合する。

preliminary buildはcached/untrusted Tectonic0.17.0で48頁。
未定義参照／overfull／underfullなし。UTF8 inputencと既存h→htのbenign noticeのみ。
これはdirty sourceの事前組版確認であり、clean-source最終buildの証拠には数えない。
最終source固定後、別名PDF、二回buildのtext一致、全頁renderと目視を行う。
旧44／41／37頁PDFとreceiptは変更せず、新稿も投稿readyを意味しない。

clean92b6484で二回のcached buildはtext SHA256
`eda5701599c16476b5298d2b65b0f34893e765a56b7aa8d3ee25a8bb8ca36414`で一致。
48頁全contactと新sectionの個別renderを目視し、bboxのoff-page wordは0。
新table／図は判読可能だが、目次末尾だけでほぼ空の1頁が生じたため、
目次だけsmallへ変更して再buildする。48頁v1のrender／logも保持し、最終PDFとはしない。
最終data/prose checksは10 pass、2.22秒。09:44UTCには候補3/12完了、
E固定graphコードG0のfresh readiness中。sourceと実験条件は変えていない。

clean d4ea1a2でfinal-v2／rebuild-v2を実行し、47頁のtextが一致。
text SHA256=`11ff4fa76240ae700bfbfb714aa52b08905233fb9fb47a9f8f8571a0c517b136`、
PDF SHA256=`26832b71d69680b552b4ec9b0b104c2d5537e17583aebfc5a87f0e094812fb1d`。
20図／18表、全47頁contactと新table／図の120dpi renderを目視。
off-page word0、未定義参照0、overfull／underfull0、二つの旧h→ht noticeのみ。
別名`science-utopia-lab-integrated-diagnostics-working-paper.pdf`へ保存した。
旧44／41／37頁hashは一致し、旧receiptを変更していない。
11 recursive TeX／20図／4support／35evidenceのpath→SHA mapを別receiptへbindした。
clean-source QAは25 pass/1.98秒、build後のsource閉包とPDF同一性を含むQAは27 pass/3.17秒。
原稿更新から新しい科学結果やpublication-readyを主張しない。

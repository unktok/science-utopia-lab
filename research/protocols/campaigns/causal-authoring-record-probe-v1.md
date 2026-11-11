# 生成された採否コードの保存入力上での動作確認

2026年11月11日。8件のauthoring assayに続く、post-hocな部分機構の診断。
新しいモデル呼出とnative worldは0。世界の損失や長期効果の測定ではない。

元実験open-seed/seed41001の4年分の実selection入力を全て使う。
コード記録のbundle、context、artifact、result hash、元SystemSpec、sourceを検証する。
元コード4件のDocker再実行が結果の完全一致を満たしてから、新候補を実行する。
8候補全てを対象とし、失敗や適用不能も枠から除かない。成功案の選別後の比較ではない。
候補のfingerprintは元authoring sourceでのcold auditと一致する必要がある。

各入力は元のstate・period・phase・random seed・全入力を保持する。
parametersだけは実候補のものを使い、削除・追加したパラメータを元の値へ戻さない。
年を跨ぐ候補stateのrolloutや、新graphの上流・下流の再実行はしない。
配線や上流を変えた候補では特に、これは候補全体の再現にはならない。

元コード4回＋最大8候補×4入力＝36 Docker実行。1回15秒、networkなし、
read-only、host mountなし、既存固定image。生成コードのhost実行、修復、
失敗補充、LLMによる追加案の作成は行わない。元コードの再実行失敗は全候補を止める。

保存するのは全入力・結果・receipt、例外、出力decision label数とpaper identityの被覆。
出力されたacceptを、native receiverで採択された件数や新しいA/Q/Rへ読み替えない。
過去の固定入力に動くことは、実世界でのloss改善・安全性・科学の改善を証明しない。
8件のassayの条件・source・成否は変更しない。

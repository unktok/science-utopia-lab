# 制度の作用経路と次の研究設計

ユーザーの依頼は、現稿の重要性・実証の不足を踏まえ、研究として価値のある比較を設計して実現すること。
[研究計画](../publication/institution-causal-design-plan.md)では、graphという構文の必要性と、
情報・操作・時点を変更する効果を混同しない。前者は同じ権限を持つ任意コードで代替可能な場合がある。
目的関数を新配線が勝つように変えず、固定family、同じ権限を持つ表現、説明介入を分ける。

開発は新worktree/branch`feature/institution-causal-design-v1`、元実験は変更しない。
旧fixed-production-v1が既存typed review-routingを拒否することを再現し、新しい明示scopeのみで許可する。
現在の80/90/130という実順序と、APIの105/110既定例の不一致を説明するread-only経路を追加。
strategy→campaign request→bounded virtual file→明示finish→cold replayまで接続した。

clean28d5991の9module検証は169pass/1fail。初回査読前のモデル入力は一致したが、実batchは
submission_timeだけ異なった。旧JUnitと3worldをignored outputsへ保持し、raw値は削らなかった。
同一対照内でhost clockを固定し、別clockでも繰り返す検証へ変更した。
cleanbf2d202で171pass/54.92s、cold replayの追加後clean446cd29で173pass/55.52s。
Docker、元Simulation、scripted研究者HTTP/corpus。新しいlocal LLM呼出0。

3条件×2clockで初年の実査読件数4/8/8、翌年の投稿数8/8/4を確認。
2年のA/Q/Rは0/0/12、0/0/24、8/32/16。2clockは科学的な独立seedとは数えない。
同年の処理順序と、採否→翌年の再投稿という動的帰結を別に扱う接続根拠として保存する。
手作業ルールの成績を、LLMの自動発明やoptimizerの優位性として扱わない。

元の実行SystemSpecをretained dataへ同一バイトで保持し、実行順序reportを独立に2回生成。
retained inputからの再生成も同一バイト。raw full auditや新native実行ではない。
25 active文書/409 local links/6歴史snapshotと、新規3文書/5リンクの検証がpass。

[結果とsource/hash記録](../results/institution-causal-design-v1.md)をまとめてローカルmainへ統合する。
既存44ページPDFは変更しない。新しい科学的結果を得る前に原稿の主張を強くしない。
次は二つのrequest履歴とsourceを固定し、fresh readiness後の最大8 authoring session比較。
現時点では未dispatchであり、実験が裏で動いているとは報告しない。新サービス・モデル・課金・pushなし。

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

## 後続の実モデル診断開始

上の未dispatchは初回実装時点の記録。ユーザーの自律継続依頼を受け、
[8セッションの有限protocol](../protocols/campaigns/causal-authoring-assay-v1.md)と実行器を
clean `a2fb13caab1169c5ff6f07119f7689db28ed888f` で固定した。
独立experiment worktree `causal-authoring-assay-v1-a1` を使い、元実験は変更しない。
新規の停止・再dispatch拒否・履歴保持等6件と既存経路を合わせ27件がpass（2.79秒）。

plan file SHA256は`2047a9d9b24595b4b336249c1a421c9bb826b6ca148b9d3306083ba9e3220ac2`、
content digestは`d18fb45f7d5d3bb5598e21d401fa2798da3d168425f0cd379abb087742b93bad`。
T/Eの旧code-and-graph G0/G1 requestをそのまま履歴として固定し、両群とも新domainを使う。
元world_bindingと履歴値を新sourceの実測値へ付け替えず、両sourceの区別をモデルにも表示する。
説明条件でrequest-bindingとdecode seedも変わりうるため、共通乱数・確証的な効果量とは呼ばない。

新実モデルreadinessを説明条件別に29件ずつ開始。説明なし29件は通過。
完全コピー差2件は原文・解釈を保存した診断で、実行可能性は通過した。
この時点では説明あり側を実行中で、本比較の成績はまだない。
研究者推論・native worldはこのprotocolでは0、新サービス・課金・pushなし。

実行中、capability一覧にはreview-routingの実装identityはあるが詳細cardがないことを確認した。
実験checkoutは変更せず、開発側にsnapshot／routingの入出力・hash・適格性・lineage・
再実行禁止・空taskの契約cardを追加。既知の制度コード、割当アルゴリズム、
自動配線は与えず、実validatorとの対応を検証する。
これは今回の未発明の原因同定ではない。`a2fb13c`の8件へは遡及適用しない。
将来このcatalogを使う実モデル実験には別sourceのfresh readinessが必要。
catalog単体28件pass（1.95秒）。

# Research readiness: evidence, not a larger debug transcript

2026-11-07。本試験への科学的な点検。実装・テスト完了だけで投稿可能としない。
V1とS1は完了・原source監査済み。V2は固定sourceで実行中であり、未完の結果と区別する。

## 何を論文として検証するか

中心は目的条件付きの科学制度最適化。三つの比較を分ける。

1. 目的を変えると、同じ候補群・探索空間から何が選ばれるか。
2. numeric tuningよりcode、codeより構造・配線が何を付け加えるか。
3. feedback packageが、目的を知って初回提案するだけの方式から何を変えるか。

G0の改善をfeedbackの効果と呼ばない。候補の無効率と、完走した候補の損失を
別々に示す。開発seedで選んだ値を、期待改善や未使用条件の性能として報告しない。

## 近接する先行研究から必要になること

[ScienceUtopia §2/F.2–F.4](https://arxiv.org/html/2610.01257v1#S2)は、長期の
研究者状態と文献検索に基づく研究活動を提供する。本研究はそのworldを使った
制度探索であり、新しい科学能力や実際の知識発見を測ったとはしない。
32B/thinkingの報告設定と、ローカル8Bの設定も区別する。

[AMD-LLM §3.1/5.3.1](https://arxiv.org/html/2502.12203v1#S3.SS1)は既に
生成コードの評価・改訂と手作業mechanismとの比較を行う。
我々も強い手作業基準を含める必要があり、単なるsource生成・初期値超え・
LLM＋既存推定器を新規性としない。自由なwhole-system設計の比較と知見が必要。
この二資料の対象箇所に絞った点検で、網羅的な優先権調査ではない。

## 現在の目的が測らないもの

T=-A、E=-Q+0.5R、C=4A-Q+0.1Rはengineering proxies。
Qは同じworld内の元の査読者判断であり、独立したtruth verifierではない。
表示final_scoreを書き換えても直接Qを変更できないことと、科学的な妥当性は別。
制度がreviewerの情報や割当を変えれば、Q自体の分布も変わりうる。

Cの採択debitは明示した価値選択で、隠れた最低品質条件ではない。
reviewを止めて全rejectするような単純基準も入れる。低活動・proxy攻略が最小なら
それを報告し、科学が改善したと呼ばない。目的の望ましくなさを理由に、結果から
都合の悪い候補を除外したり目的の重みを後付け変更したりしない。

二年・五人のworldではcareer・fundingの長期効果を十分には観測できない。
固定選択後の四年条件はその一部を検査するが、現実制度への一般化を保証しない。
外側評価はloss・raw outcomes・未使用条件で行い、採用制約を後から付けない。

## 採否だけを自由にした条件付き問題

完了済みのdecision recordとreviewer返信・総review数Rを固定し、採否だけを
独立なz_i∈{0,1}とする。各recordの元review平均をq_i、査読なしをq_i=0とすると、

```text
T = -Σ z_i                     固定recordでは全採択
E = 0.5R - Σ z_i q_i            q_i>0は採択、q_i=0は同点
C = 0.1R + Σ z_i(4-q_i)         q_i>4は採択、q_i<4は却下、=4は同点
```

これは新しい探索法や世界のoracleではなく、既存lossの代数的な帰結。
Cの0.1Rはこの条件付き問題では定数で、reviewが既に発生しているなら閾値は4。
世界全体で無査読・全却下のC=0と比べる別の条件は、A>0で
`Q/A > 4 + 0.1R/A`。両者を取り違えない。

このdecision-flag relaxationを、元のcheckpointから読み直して計算する
`scripts/reports/native_selection_relaxation.py`を実装。有限flag全列挙でLossSpecとの
数値一致を検査し、欠測reviewによって条件付き下限だけが不明でも、元の有効な
測定を棄却しない。再加算順による微小差とauditの元の数値を別々に保存する。
既に固定されたV2の目的・重み・予算やproposer入力は変更しない。

S1で全採択のT/Eがこの条件付き最小に達しても、自由制度の探索が成功したという
十分条件ではない。逆に大きなgapも、それだけでは実行可能な改善余地とは言えない。
採否を変えると未来の研究者状態・投稿・再投稿・reviewが変わるため、recordそのものが
変わる。固定recordの最適採否を実policyとしてそのまま適用できるとは限らない。
この自明な符号効果を越えて何が見つかったかが、V2で説明すべき問いである。

## 制限された探索空間と提示方法の解釈

V2の初期二つのparameter-only提案は、codeを書き換えて範囲違反のfinishとなった。
実際の保存済み入力では、制約はuser message冒頭側の
`declared_benchmark_design_space`に明示され、全16操作で保持されている。
一方、共通system messageは任意のPython・制度・配線を作れる汎用authoring環境を
説明し、parameter-only専用のsystem-level注意は含まない。範囲検証が動作したことと、
この提示が各domainで同程度に理解しやすいことは別である。

これは「入力から制限が消えた」ことや、提示位置が失敗の唯一の原因だという証拠
ではない。固定interface・designerによるend-to-end結果を、抽象的な探索自由度
そのものの効果と混同しない。特にnumeric-armの範囲違反だけから、code/graphが
必要・優れているとは主張できない。終端エラーだけでなく実際の操作・拒否理由と
共通prompt条件を報告する。無効率は利用可能な候補の損失と分ける。

進行中のsource・入力・予算は変えない。提示の改善を検証するなら別の事前固定条件、
新source・fresh校正で行い、現在の失敗を置換・refillしない。失敗の説明を
「設計者の能力不足」「runnerのバグ」のどちらかに、因果的な根拠なく断定しない。

By the live117-slot snapshot, all24 LLM-numeric authoring slots have ended in
generation errors with no native observations, while all24 uniform-numeric
slots have complete observations in their per-arm records. This is not yet the
closed original-source V2 audit. Final T numeric G3 also attempts edit actions
with undeclared fields (rationnales; field_updates/mechanism_id) before switching
to out-of-domain source editing. Separate those schema rejections from the
later declared-space finish rejections and from native execution failures.
The resulting comparison is end-to-end designer/interface behavior, not an
unconfounded measurement of intrinsic numeric-versus-code expressivity. Preserve
all nulls and actual costs; do not repair/refill the active campaign or relabel
the predeclared initial-system selection option as successful numeric invention.

## 検証・型契約の範囲

自由度群の名前は許容する編集範囲であり、実際の構造変更の証拠ではない。
既存の原source監査は候補の完全なSystemSpecと親／初期系に対するlineageを保持し、
compact reportもlineageを保存する。コード変更はmechanism parametersの変更にも
数えられるため、構成変更数とsource変更数を足して発明数にしない。lineageは
明示したfieldの差分で、actor/artifact typeやglobal invariantを含む全仕様差分の
完全な代用ではない。完全な仕様、実消費箇所と実行receiptを併せて読み、群名や
fingerprint変更だけから「構造を最適化できた」「新制度が作用した」と結論しない。

SystemSpecの型付きportと宣言したJSON Schemaの検証は、任意のPython本体の
型安全性や全入力での実行可能性の証明ではない。V2のselective technical-only G2は
score列のscalar要素を`values_s[i][0]`として扱い、TypeErrorで停止した。
この候補のscores入力schemaは`{"type":"object"}`で、fieldのrankまでは制約しない。
上流programのcolumn操作と、下流コードの仮定を分けて読む必要がある。

この観測から静的検証済み・校正済みを「全ての新制度が動く」と表現しない。
一方、生成された全Pythonを保守的な限定言語に置換したことにしたり、実行済みの
失敗をhostが黙って修正したりもしない。実行時の技術的失敗・費用・欠測として
残し、interfaceの使いやすさと制度の科学的帰結を別々に議論する。
進行中のABI・schema・promptを変えず、最終原稿でもこの検証範囲を明示する。

### A native information/action path is not yet a causal benefit

V2 live case102 (run02 C code/graph G2) explicitly rejects every real addressed
paper and stores final_score0. It completes C2.1,A0/Q0/R21 on development
seed42, below initial C2.4 but above reviewer-free reject C0. Earlier G0/G1
have execution nulls, not numerical losses to improve upon. The actual edits
replace selection source; permitted graph freedom is not actual rewiring.

A read-only trace follows native_kernel._apply_decisions into the publication
commit, PaperTracker.review_history.score and BaseAgent.get_resubmission_prompt.
Three real year2 wire requests include the year1 score0 history. Each joins one
committed response with stop termination and a parsed empty resubmitted_papers
list; checksums and exact locators are in the chronological log. This establishes
an exercised source-to-scientist-input/action path, not just a changed parameter
name. It also rules out describing final_score as globally cosmetic solely
because it is not the direct Q measurement.

It does not isolate the causal effect of score0 on resubmission, review count,
resources or loss: other source behavior and fresh oracle realizations differ.
Do not turn this observed development difference into an expected improvement,
feedback advantage, new institution or real scientific-policy gain. The full
study and selected-policy unused-condition evaluation remain open; no hidden
penalty or veto is introduced for the low-activity result.

Live case110 (C fixed-code G2) gives a different behavior with the same raw C2.1:
A1/Q4/R21 instead of102's A0/Q0/R21. Its receipt shows one original mean4
paper accepted while authored final_score remains0. The scalar-score indexing
exception is caught and replaced by0; the actual scalar accept signal1 selects
that paper. This is not a demonstrated scalar-parser correction. Algebraically,
4A-Q cancels for this one accepted paper, so both measured rows leave0.1R=2.1.
Equal objective values do not imply equivalent policies, equal outside metrics
or equivalent future trajectories. Keep the distinct definitions and all declared
ties; do not add a preference for either outcome after seeing them. This is a
consequence of the declared proxy, not a new optimum theorem or causal comparison.

## 投稿に残る判断

### 同じseed・同じ制度と、同じoracle実現は別

11月7日16:41UTCまでの限定診断では、run01 uniform T/C G1のcandidateが
完全一致していても、Qは22と21.666666666666668に分かれた。元sourceの
transport検証を使うread-only点検で、最初の五つの研究者request payloadが
完全一致し、最初のreplyのreasonが既に異なることを確認した。そのreasonは
六番目のrequestのRecentExperiencesへ入る。詳細と不変な入力hashは
[当日の記録](../logbook/2026-11-07-submission-goal.md#run01-g1-closed-first-g2-and-response-variation-diagnostic)
に残す。これは全試験の閉監査や、特定backend動作を唯一の原因とする診断ではない。

したがってpaired seedという設計は、LLM研究者の全応答を完全に結合した
counterfactual実験を意味しない。全ての観測を保持し、同一制度の差を制度効果と
解釈しない。最終解析では指定したworld単位・欠測・物理共有を保ち、同seedの
fresh oracle実現が異なりうることも明示する。この少数事例から分散を推定したり、
同一制度の結果を統合・選別してselection値を書き換えたりしない。
条件や予算を変更する提案ではなく、既定比較を解釈する際の証拠上の限界である。

現時点の自己点検（外部・独立査読を受けたという意味ではない）：

| 論文の要件 | 現状 | 閉じるために必要な証拠 |
| --- | --- | --- |
| 目的と自由度を分けた実行可能な問題設定 | 実装・有限protocolあり | 主張を既存のLLM program/mechanism探索との差に限定し、比較から得た知見を示す |
| 強い基準との比較 | S1は閉監査済み、V2の同source参照9件は終了 | V2全探索・選択後評価を閉じ、原制度・単純規則とのpaired値を報告 |
| 自由度の価値 | V2稼働中、未実証 | 全120slotの経路・失敗・費用。提示への準拠率と、完走policyの帰結を分ける |
| 機構の説明 | V1の全採択はtrace済み | V2選択policyの実消費箇所、実行receipt、研究者入力・行動への作用。source差分だけで代用しない |
| 一般化と不確実性 | 未使用条件の実評価は未実施 | 選択固定後の五world seed、別horizon、全raw paired差と欠測。小標本から手法優位を断定しない |
| 再現性 | tracked figure/PDF再構築と原source audit手順あり | 閉V2 audit・compact結果・費用。35B上流revision/変換recipeの不足と匿名配布境界を解消または明確に限定 |
| 原稿と図 | 十一ページworking draft、render QA済み。資源・リスク・AI補助を追記 | V2実測の反映、最終主張と証拠の対応、対象cycleの形式・匿名性・AI利用・著者資格を公式確認 |

未実証の比較をprotocolやソフトウェアtest数で埋めない。単なる弱いseed超えや
「自由度を実装した」という記述だけで、top-conference向け研究完成と判定しない。
逆に、肯定的な差が出ないこと自体を実験失敗とはせず、重要な問いへ何を答えたかを
全結果から評価する。追加の計算・方式変更が必要なら理由と新protocolを残す。

- 同じsource・worldで、原制度と単純基準を超える／超えない結果を説明できるか。
- 構造変更が実行され、研究者の入力・活動へ作用したという証拠があるか。
- 目的の違いと設計自由度の関係に、既知の自明な符号効果以上の知見があるか。
- 限定されたbenchmarkの結果であることと、将来の研究プログラムを分けているか。
- 再現資料、費用、失敗、同点、欠測、独立単位、出典と権利、著者貢献が明瞭か。

現在これらが全て満たされたとは扱わない。負の結果にも説明すべき重要な問いと
十分な裏付けが必要で、計算量だけでは補えない。本試験前後にこの表へ戻って
主張を吟味し、最終的な投稿判断を行う。

## Local release review: concrete observations, not publication clearance

2026-11-07UTC, integration source ad6e756. This read-only review runs while
the separate frozen V2 writer remains live; it changes no experiment inputs.
It does not authorize release, establish license compatibility, complete a
credential/PII audit, or claim anonymous submission readiness.

The current working PDF has SHA256
0511e6c08b86743329e0e5aa90dbab68f3ba627638774b7a1780344050cade59.
Poppler reports11 pages, zero embedded files, no form/JavaScript and no custom
metadata or metadata stream. Its17 URL annotations point to arxiv.org(14) or
proceedings.mlr.press(3); none contains the inspected operator/path literals.
Extracted text has no `/Users/`, `/home/`, `shiro` or `unktok` literal. These
checks do not replace visual review, cover every possible identifying string,
or attest to every PDF object. The source explicitly uses the preprint option
and a Science Utopia Lab working-draft author block; it is not an anonymous
submission copy. No PDF bytes, metadata or historical build receipt are edited.

At this source, Git tracks1922 files. A narrow filename check finds no tracked
files under outputs/, data/, .cache/, .venv/ or tmp/, no .env/.env.* names and
no .pem/.key/.gguf/.safetensors/.sqlite/.sqlite3/.pth/.pt suffixes. This is not
proof that every secret, private cache, model format or derived text is absent.
A literal `/Users/shiro` scan of tracked UTF-8 files up to10MB finds134 files:
research100, game-ui-v2 20, paper6, scripts2, tests6. The ordered matching
filename list has SHA256
5f70af724e647463dbdbfeb5ef1e2b10dba7f0e28be3fd446744fe2430052596.
An entire checkout or Git history is therefore not an anonymous reviewer bundle.
Many matches are intentional historical evidence locators; do not rewrite those
immutable raw/snapshot records to satisfy an anonymity check.

| Material | Verified local observation | Required before any actual release |
| --- | --- | --- |
| Source and attribution | README identifies the ScienceUtopia fork; root Apache2.0 LICENSE is unchanged since local initial commit ec42d18 | Preserve upstream attribution and applicable notices. Check the final selected files and upstream terms, not only the root license label |
| Root license identity | LICENSE SHA2560dc1811264bb76e119d3f58a8e775d79abeb1708c9486d3861354c1688062350 includes the literal copyright line2020 Rémi Louf | Resolve its upstream provenance/coverage before treating that line as this project's authorship or blanket permission for dependencies/data/models; do not silently replace it |
| Conference template | Bundled neurips_2025.sty retains its original credit header, SHA25667a960f35da6fecb5a0ce0202fa400459f4c8bb6c294f1a3fdd82fbbd39244c2 | Use the selected cycle's actual official template and rules; retain required credits/notices in source. The current2025 preprint style is not future-cycle compliance |
| Corpus and scientist inputs | Workflow records exact SciEvo/retriever revisions, ordered corpus hash and the limited current-card license observation | Do not bundle literature-derived raw text/author metadata by default. Separately verify redistribution terms for the intended subset; a dataset-card declaration alone is insufficient |
| Model/server artifacts | Local digests and selected backend hashes are recorded;35B upstream revision/conversion remains unknown | Do not redistribute weights or promise a publicly retrievable exact35B model. Clearly distinguish recorded-summary rebuild, local raw audit and a fresh-machine inference rerun |
| Game and generated art | Existing asset provenance separates code-authored production SVGs from13 generated concept PNGs not loaded by the runtime manifest | Omit unrelated UI/concept assets from a minimal research bundle; if included, retain provenance and review their terms/metadata separately. Do not present them as empirical evidence |
| Human/agent provenance | Paper discloses coding-agent assistance and leaves human authorship unresolved | User finalizes human authors/contributions and intended AI-use disclosure; assistance is not independent empirical verification |
| Operational evidence | Source IDs/checksums are needed for audit; historical locators contain operator paths | Prepare a separate explicit allowlist and verified locator mapping. Keep original evidence unchanged; omit .git, operator configs, caches, weights and unapproved raw archives |

The inspected production-asset provenance file SHA256 is
3df8c244790e69d5e10bb78abe7da5425a3f94b03a2cad23da16ed9d02493482;
its authorship statements are repository records, not an independent rights audit.
No new package, model, external query or generated artwork is used by this review.

After the scientific results close, stage only the necessary paper sources,
figures, compact measured results, exact-source identifiers, software tests and
reproduction instructions in a fresh local directory. Inspect that actual
allowlist for secrets, identifying metadata/links, third-party attribution and
missing dependencies, then rebuild the staged paper and verify its full rendered
pages. A checksum inventory is not enough to show that a clean-machine run works.
State model/raw-data gaps rather than substituting resources or claiming complete
independent reproduction. External sharing, push/upload and submission still
require user approval. This packaging review is not a scientific selection veto.

## 既存surveyメモの扱い

過去の二つの目的メモは、規範的な制約を提案していた。その後のユーザー指示で
現在の既定にはしない。歴史的本文を残して冒頭に明示し、文献上の注意を現在の
実験への指示・採用vetoとして持ち込まない。survey repoの内部解釈も独立した
一次実証や、この論文の新規性の証明として数えない。

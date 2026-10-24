# ADR-0002: 単一lossではなく四層の目的アーキテクチャを採用する

- Status: accepted
- Date: 2026-10-24

## Context

ScienceUtopia全体を最適化するには、制度軌跡を評価するouter objectiveが必要になる。しかしScience of Science、研究評価、metascience、国家科学政策、および `ai-scientist-survey` の既存議論は、publication、citation、acceptance、semantic novelty、国家KPIのいずれも科学的価値そのものではなく、単独最大化に耐えないことを示す。

複数指標を固定weightで足しても、新しい単一proxyになり、normativeな重みが技術的係数へ隠れる。また、integrity、研究の自由、appeal、重大な安全性などは成果増加と交換すべきでない。

## Decision

制度評価を次の四層で扱う。

1. **Constitutional hard constraints**  
   integrity、最低限のevidence coverage、重大なdisparate harm、appeal、研究の自律性など、不許容状態を除外する。
2. **Capability-preservation constraints / objectives**  
   独立検証、訂正、rollback、branch reopening、長期memory、provider撤退後のcontinue/fork/repair能力を保存する。
3. **Commitment-specific objective vector**  
   exploratory、confirmatory、mission、commonsなど用途ごとに目的ベクトルを持ち、Pareto、epsilon-constraint、scenario比較を使う。
4. **Objective-and-evaluator governance**  
   metric、evaluator、decision policy自身のversion、authorized use、expiry、gaming、変更権限、異議申立て、proxy failureからの回復を評価する。

探索アルゴリズム内部で一時的なscalarizationを使うことは許すが、それを「科学の総価値」や恒久的な制度順位とは呼ばない。全構成指標と制約状態を保存する。

## Evaluation unit

可能になった段階で、評価単位をsystemまたはpaper全体ではなく、次の型付き関係へ移す。

```text
subject × claim × artifact version × autonomy slice
        × evaluator relation/version × decision policy version
```

evaluation、decision、allocation、appeal/correctionは別機構として実装する。

## State and science policy

国家missionは正当なcommitment-specific objectiveになりうるが、科学全体のground truthではない。mission attainment、epistemic independence、public-value distribution、agenda plurality、contestability、counter-capacity、temporal robustness、policy learningをvectorで保持し、「国益score」へ圧縮しない。

国家、研究者、市民、被影響者、国際的knowledge commons、将来世代を別stakeholderとして扱い、benefit、burden、voice、exit/appealを分ける。

## Measurement roadmap

v1候補は次の9群である。

1. epistemic reliability
2. correction capacity
3. useful exploration
4. epistemic diversity
5. resource efficiency
6. equitable opportunity
7. researcher sustainability
8. resilience / capability
9. mission / public value

現行simulatorで一部しか測れない構成概念を、測れたように扱わない。hidden truth、replication、claim lineage、correction、capability/shock、mission/outcome modelを先に実装する。

## Consequences

- Metric Cards v0はpipeline検証用の暫定proxyへ位置づけ直す。
- noveltyとresource equalityを無条件に単調最大化しない。
- metricは分析columnではなく、version、用途、owner、期限、gaming監視を持つ制度オブジェクトへ発展させる。
- optimizerのbest scoreだけでなく、Pareto front、分布、時間軸、stress test、shadow metricsを報告する。
- event schemaはclaim、evaluator、decision、appeal、correction、branch、objective/metric revisionを表現する必要がある。

## Evidence

- [Science of Science / metascience 調査](../literature/science-of-science-objectives.md)
- [`ai-scientist-survey` 内部調査](../literature/ai-scientist-survey-objectives.md)
- [科学政策としての目的設定](../science-policy-frame.md)


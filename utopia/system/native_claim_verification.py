"""Opt-in, independently computed claims about the actual native world.

This is a minimal auditable research activity, not an oracle for scientific
truth or a new default optimization objective. Authored values cannot assign
their own verification verdicts. Corrections retain the earlier false record.
"""
from copy import deepcopy
from dataclasses import replace

from . import (ArtifactTypeSpec, ChannelKind, ConnectionSpec, MechanismFamily,
               MechanismSpec, PortSpec, ScheduleSpec, validate_system_spec)
from .runtime import GraphRuntimeError, MechanismEvent, MechanismResult, MechanismValue
from .design_patch import digest

IMPLEMENTATION = 'native.world.claim-verification.v1'
CLAIM = 'native-world-count-claim-v1'
VERDICT = 'native-world-count-verification-v1'
METRICS = ('accepted-decisions', 'rejected-decisions', 'review-records')
EVENT = 'native.system.claim_verified'


def attach_claim_verifier(spec, *, source, source_port, verifier='claim-verifier',
                          receiver='verified-evidence-context', phase=191, latency=0):
    """Connect an arbitrary claim producer to an independent native consumer.

    Producers may be authored code, an LLM institution, or another mechanism.
    The verifier cannot be replaced by a candidate's self-reported verdict.
    This helper adds no producer and makes no assertion about its usefulness.
    """
    from .native_kernel import add_context_receiver
    known={a.artifact_type_id for a in spec.artifact_types}
    node=MechanismSpec(verifier,MechanismFamily.CUSTOM,IMPLEMENTATION,
        inputs=(PortSpec('claims',ChannelKind.ARTIFACT,CLAIM,required=False),),
        outputs=(PortSpec('verifications',ChannelKind.ARTIFACT,VERDICT,required=False),))
    spec=replace(spec, artifact_types=(*spec.artifact_types,
        *(ArtifactTypeSpec(a) for a in (CLAIM,VERDICT) if a not in known)),
        mechanisms=(*spec.mechanisms,node), schedules=(*spec.schedules,ScheduleSpec(verifier,phase)),
        connections=(*spec.connections,ConnectionSpec(source,source_port,verifier,'claims',ChannelKind.ARTIFACT)))
    spec=add_context_receiver(spec,source=verifier,source_port='verifications',
                              receiver=receiver,phase=235,latency=latency)
    validate_system_spec(spec).require_valid()
    return spec


def evaluate_claim(kernel, claim, *, year):
    required = {'schema','claim_id','metric','after_year','through_year','asserted_value','supersedes'}
    if (not isinstance(claim,dict) or set(claim)!=required or claim['schema']!=CLAIM
            or not isinstance(claim['claim_id'],str) or not 1 <= len(claim['claim_id']) <= 200
            or claim['metric'] not in METRICS
            or any(type(claim[k]) is not int for k in ('after_year','through_year','asserted_value'))
            or not 0 <= claim['after_year'] < claim['through_year'] <= year
            or claim['asserted_value'] < 0
            or claim['supersedes'] is not None and not isinstance(claim['supersedes'],str)):
        raise GraphRuntimeError('literal typed claim about a completed native interval required')
    # Read the real simulator, NOT an authored "world" input or declared result.
    records = []
    for paper in kernel._simulation.paper_tracker.papers_by_id.values():
        for review in paper.review_history:
            if claim['after_year'] < review['year'] <= claim['through_year']:
                # Keep native operational wall times in the original ledger,
                # but do not make this count-evidence identity depend on them.
                # Only the source-owned top-level review_time is projected;
                # arbitrary scientific text/timestamps remain literal.
                reviews=[{k:deepcopy(v) for k,v in item.items() if k!='review_time'}
                         for item in review.get('reviews',[])]
                records.append({'paper_id':paper.id,'year':review['year'],
                    'decision':review.get('decision'), 'reviews':reviews})
    if claim['metric']=='accepted-decisions':
        expected = sum(r['decision']=='accept' for r in records)
    elif claim['metric']=='rejected-decisions':
        expected = sum(r['decision']=='reject' for r in records)
    else:
        expected = sum(len(r['reviews']) for r in records)
    evidence = sorted(records,key=lambda r:(r['paper_id'],r['year'],str(r['decision'])))
    return {'schema':VERDICT, 'claim':deepcopy(claim), 'expected_value':expected,
        'matches_native_records':claim['asserted_value']==expected,
        'evidence_sha256':digest(evidence), 'native_record_count':len(evidence),
        'verified_at_year':year, 'scope':'Native count consistency, not truth of a scientific paper.'}


def validated_records(kernel, records, *, year):
    """Do not accept a designer-seeded state containing a fabricated verdict."""
    if not isinstance(records,dict):
        raise GraphRuntimeError('verification record state must be an object')
    verified={};pending=dict(records)
    while pending:
        progressed=False
        for identity,record in list(pending.items()):
            if (not isinstance(record,dict) or not isinstance(record.get('claim'),dict)
                    or record['claim'].get('claim_id')!=identity
                    or type(record.get('verified_at_year')) is not int
                    or not 0 < record['verified_at_year'] <= year):
                raise GraphRuntimeError('invalid retained verification record')
            expected=evaluate_claim(kernel,record['claim'],year=record['verified_at_year'])
            previous=record['claim']['supersedes']
            if previous is not None:
                if previous not in verified:
                    continue
                old=verified[previous]['claim']
                if any(old[k]!=record['claim'][k] for k in ('metric','after_year','through_year')):
                    raise GraphRuntimeError('retained correction changed measured object')
                expected['superseded_verification_sha256']=digest(verified[previous])
            if expected!=record:
                raise GraphRuntimeError('retained verification differs from actual native evidence')
            verified[identity]=record;del pending[identity];progressed=True
        if not progressed:
            raise GraphRuntimeError('retained corrections have an unknown or cyclic predecessor')
    return verified


def verify_claims(kernel,context):
    if kernel._frame is None or kernel._frame['year']!=context.period:
        raise GraphRuntimeError('claim verification requires the current native year')
    state=deepcopy(dict(context.state))
    saved=validated_records(kernel,state.get('records',{}),year=context.period)
    prepared=[]; seen=set()
    for value in context.inputs.get('claims',()):
        claim=deepcopy(value.payload)
        verdict=evaluate_claim(kernel,claim,year=context.period)
        identity=claim['claim_id']
        if not value.lineage_event_ids or identity in seen:
            raise GraphRuntimeError('causal claim identity without duplicate batch writers required')
        seen.add(identity)
        if identity in saved:
            if saved[identity]['claim']!=claim:
                raise GraphRuntimeError('claim ID reused for different literal assertion')
            continue
        previous=claim['supersedes']
        if previous is not None:
            if previous not in saved:
                raise GraphRuntimeError('correction references an unknown prior claim')
            old=saved[previous]['claim']
            if any(old[k]!=claim[k] for k in ('metric','after_year','through_year')):
                raise GraphRuntimeError('correction must address the same measured object and interval')
            verdict['superseded_verification_sha256']=digest(saved[previous])
        population=kernel._simulation.ecosystem.agent_population
        if any(a not in population or not getattr(population[a],'can_author',False) for a in value.actor_ids):
            raise GraphRuntimeError('verification recipients must be actual native researchers')
        prepared.append((identity,verdict,value))
    # All validation occurs before the returned next_state is committed.
    outputs=[];events=[]
    for identity,verdict,value in prepared:
        saved[identity]=verdict
        outputs.append(MechanismValue(verdict,actor_ids=value.actor_ids))
        events.append(MechanismEvent(EVENT,actor_ids=value.actor_ids,payload={
            'claim_id':identity,'matches_native_records':verdict['matches_native_records'],
            'verification_sha256':digest(verdict), 'evidence_sha256':verdict['evidence_sha256'],
            'supersedes':verdict['claim']['supersedes']}))
    state['records']=saved
    return MechanismResult(outputs={'verifications':tuple(outputs)},events=tuple(events),next_state=state)


def register_native_claim_verification(kernel,registry):
    registry.register(IMPLEMENTATION,1,lambda context:verify_claims(kernel,context))

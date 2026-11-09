"""Read-only consumer proof QA, with synthetic input/cache fixtures only."""
import json
from pathlib import Path
import sqlite3

import pytest

from scripts.audit_pre_scale_information_v1 import dossier_inputs,main
from utopia.system.model_provenance_view import render_provenance_view
from utopia.system.design_patch import digest
from utopia.utils.seeding import derive_seed


def fixture(cell,*,same_content=False,year=2):
    messages=[];actors=[]
    for i in range(2):
        message={'message_id':'opaque-'+str(i),'input_event_ids':['event-'+str(i)],
            'received_year':1,'emitted_year':1,'source':'history-dossier-receiver',
            'payload':{'schema':'native-research-history-dossier-v1',
                'records':['society-history' if same_content else 'own-history-'+str(i)]}}
        messages.append(message);actors.append({'id':'researcher-'+str(i),'institutional_context':[message]})
    payload={'messages':[{'role':'user','content':'Scientific prompt\n'+render_provenance_view([messages[0]])}],
        'extra_body':{'seed':derive_seed(41001,'phase1_directions',year,0,0)}}
    wire={'year':year,'payload':payload,'payload_sha256':digest(payload)}
    (cell/'replies').mkdir()
    with sqlite3.connect(cell/'replies/responses.sqlite') as db:
        db.execute('CREATE TABLE replies (payload_sha TEXT,outcome TEXT)')
        db.execute('INSERT INTO replies VALUES (?,?)',(wire['payload_sha256'],'response'))
    (cell/'wire-requests.jsonl').write_text(json.dumps(wire)+'\n')
    return {'ecosystem_data':{'agents':actors}},messages


@pytest.mark.parametrize('same_content',[False,True])
def test_actual_renderer_not_raw_audit_hashes_and_recipient_ambiguity_preserved(tmp_path,same_content):
    saved,messages=fixture(tmp_path,same_content=same_content)
    proof=dossier_inputs(tmp_path,saved,41001)
    row=proof['completed_dossier_inputs'][0]
    assert proof['first_direction_input_year']==2
    assert row['direction_namespace_seed_match']
    assert row['recipient_attribution']==('ambiguous-rendered-prefix' if same_content else 'unique-rendered-prefix')
    assert len(row['possible_recipient_prefixes'])==(2 if same_content else 1)
    assert row['possible_recipient_prefixes'][0]['raw_message_ids']==['opaque-0']
    assert saved['ecosystem_data']['agents'][0]['institutional_context'][0]==messages[0]
    # The old raw-string test would miss this genuine rendered occurrence.
    assert json.dumps(messages[0],sort_keys=True) not in json.loads((tmp_path/'wire-requests.jsonl').read_text())['payload']['messages'][0]['content']


def test_future_deliveries_are_not_retroactively_counted_as_current_input(tmp_path):
    saved,_=fixture(tmp_path,year=1)
    proof=dossier_inputs(tmp_path,saved,41001)
    assert proof['completed_dossier_inputs'][0]['recipient_attribution']=='marker-without-matched-complete-prefix'
    # A marker alone is not independently joined to a delivered prefix.
    assert not proof['completed_dossier_inputs'][0]['possible_recipient_prefixes']


def test_running_study_is_rejected_before_audit_or_subprocess_dispatch(tmp_path,monkeypatch):
    monkeypatch.setattr('sys.argv',['audit','--run',str(tmp_path),'--output',str(tmp_path/'separate.json'),
        '--frozen-source',str(tmp_path)])
    monkeypatch.setattr('subprocess.run',lambda *a,**kw:pytest.fail('must not launch a partial audit'))
    with pytest.raises(ValueError,match='not closed'):main()

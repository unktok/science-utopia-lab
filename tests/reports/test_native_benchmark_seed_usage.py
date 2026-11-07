"""Seed firewall history tests; all SQLite contents are scripted fixtures."""
import json
import sqlite3
from scripts.native_benchmark_seed_usage import usage_inventory


def journal(path,seed):
    path.parent.mkdir(parents=True,exist_ok=True)
    with sqlite3.connect(path) as db:
        db.execute('CREATE TABLE metadata (binding TEXT)')
        db.execute('INSERT INTO metadata VALUES (?)',(json.dumps({'seed':seed,'model':'SCRIPTED','protocol':'SCRIPTED'}),))


def test_numeric_seed_not_hash_substring_is_the_unit_and_prior_matches_remain_visible(tmp_path):
    journal(tmp_path/'actual'/'responses.sqlite',42)
    journal(tmp_path/'software-verification'/'responses.sqlite',31001)
    a=usage_inventory(tmp_path,[31001,31013]);assert a['valid']
    assert len(a['bindings'])==len(a['excluded_software_verification_paths'])==1
    journal(tmp_path/'actual-new'/'responses.sqlite',31001)
    b=usage_inventory(tmp_path,[31001,31013])
    assert not b['valid'] and b['prior_matching_runs'][0]['seed']==31001


def test_unreadable_or_unknown_journal_does_not_claim_unseen_seed(tmp_path):
    path=tmp_path/'broken'/'responses.sqlite';path.parent.mkdir();path.write_bytes(b'SCRIPTED not SQLite')
    result=usage_inventory(tmp_path,[31001]);assert not result['valid'] and result['errors']
    assert path.read_bytes()==b'SCRIPTED not SQLite'

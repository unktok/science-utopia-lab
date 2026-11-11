"""Exact retained actual readout bytes and unit-count interpretation."""
from collections import Counter
import json
from pathlib import Path

from utopia.optimization.native_numeric_designer import checked
from utopia.utils.data_utils import file_sha256

ROOT=Path(__file__).resolve().parents[2]
DATA=ROOT/'research/data/native-common-content-readout-v1'


def test_actual_readout_manifest_matches_retained_data_and_figures():
    read=lambda path:json.loads(path.read_text())
    report=checked(read(DATA/'report.json'));manifest=checked(read(DATA/'manifest.json'))
    receipt=read(ROOT/'research/results/native-common-content-readout-closed-verification-v1.json')
    assert file_sha256(DATA/'report.json')==receipt['report_file_sha256']
    assert report['content_sha256']==receipt['report_content_sha256']
    for name,sha in manifest['files'].items():
        path=DATA/name if (DATA/name).exists() else ROOT/'paper/figures/native-common-content-readout-v1'/name
        assert file_sha256(path)==sha


def test_actual_critic_contents_decisions_and_worlds_are_distinct_units():
    report=checked(json.loads((DATA/'report.json').read_text()))
    assert report['physical_attempts']==228 and len(report['content_rows'])==76
    assert report['content_panels_available']==76 and report['content_panels_unavailable']==0
    assert len(report['world_rows'])==44 and report['accepted_decision_records']==263
    scores=Counter(v for r in report['content_rows'] for v in r['critic_scores'])
    assert dict(scores)=={2:6,3:71,4:151}
    assert sum(r['mean_score']<3 for r in report['content_rows'])==2
    assert sum(r['mean_score']==3 for r in report['content_rows'])==20
    assert sum(r['mean_score']>3 for r in report['content_rows'])==54
    assert sum(r['within_content_range']==0 for r in report['content_rows'])==70
    assert sum(w['accepted_decisions'] for w in report['world_rows'])==263
    assert not any(report['interpretation'].values())

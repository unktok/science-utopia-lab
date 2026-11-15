"""Cheap missing-global diagnostic; supplements actual public execution."""
import builtins
from pathlib import Path
import symtable
import pytest

ROOT=Path(__file__).resolve().parents[2]
FILES=('scripts/run_native_topic_free_optimization_v1.py',
       'scripts/audit_native_topic_free_optimization_v1.py',
       'scripts/finish_native_topic_free_optimization_v1.py',
       'scripts/reports/native_legacy_topic_pilot_v1.py',
       'scripts/reports/native_topic_free_readout_v1.py',
       'scripts/finish_native_topic_free_readouts_v1.py',
       'utopia/optimization/native_topic_objectives_v1.py',
       'utopia/optimization/native_institution_workflow_domain_v6.py')


@pytest.mark.parametrize('name',FILES)
def test_new_operator_referenced_global_names_are_bound(name):
    tree=symtable.symtable((ROOT/name).read_text(),name,'exec')
    known=set(dir(builtins))|{'__file__','__name__','__package__','__doc__'}
    known|={s.get_name() for s in tree.get_symbols() if s.is_assigned() or s.is_imported() or s.is_namespace()}
    pending=[tree]; errors=[]
    while pending:
        scope=pending.pop(); pending.extend(scope.get_children())
        errors.extend((scope.get_name(),scope.get_lineno(),s.get_name()) for s in scope.get_symbols()
                      if s.is_global() and s.is_referenced() and s.get_name() not in known)
    assert not errors,errors

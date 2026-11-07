"""Restore source-defined mapping order, never alter JSON values or list order.

Pure analysis helpers. The caller supplies the exact experiment's spec/driver;
using a later experiment implementation is not a compatible reconstruction.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from types import FunctionType


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=False, allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def same_values(left, right):
    # Python equality alone equates True/1 and 1/1.0. Here only mapping
    # insertion order may change; scalar types and every ordered list remain.
    return canonical(left) == canonical(right)


def checked_content(value, schema):
    if (not isinstance(value, dict) or value.get('schema') != schema
            or value.get('content_sha256') != digest({
                k: v for k, v in value.items() if k != 'content_sha256'})):
        raise ValueError('exact schema and canonical content hash required')


def restore_plan(saved, *, spec, source, seed_usage_sha256):
    checked_content(saved, spec.SCHEMA)
    if saved.get('source_commit') != source:
        raise ValueError('plan source differs from expected experiment')
    rebuilt = spec.build_plan(source=source, scientist=saved['scientist'],
        designer=saved['designer'], runtime_seed=saved['runtime_seed_binding'],
        backend=saved['backend'], seed_usage_sha256=seed_usage_sha256)
    if not same_values(saved, rebuilt):
        raise ValueError('study plan differs from source-pinned reconstruction')
    return rebuilt


def restore_selection(root, saved, *, plan, driver, campaign_loader):
    checked_content(saved, driver.spec.SCHEMA + '.selection')
    if saved.get('plan_sha256') != plan['content_sha256']:
        raise ValueError('selection plan binding differs')
    rebuilt = driver.selection_payload(root, plan, frozen_utc=saved['frozen_utc'],
                                      campaign_loader=campaign_loader)
    if not same_values(saved, rebuilt):
        raise ValueError('frozen selection differs from all candidates and exact ties')
    return rebuilt


def with_ordered_reader(original, reader):
    """Keep the exact function body and every other original dependency."""
    private = dict(original.__globals__)
    private['read'] = reader
    return FunctionType(original.__code__, private, original.__name__,
                        original.__defaults__, original.__closure__)


class OrderedSourceReader:
    """Replace only two exact reads with equal-valued source-ordered objects.

    Re-read and compare each time to catch mutation after preparation. This is
    not a JSON decoder patch and never rewrites raw files or other observations.
    """
    def __init__(self, original_read, root, *, saved_plan, ordered_plan,
                 saved_selection, ordered_selection):
        root = Path(root).resolve()
        self.original_read = original_read
        self.entries = {}
        for filename, saved, ordered in (
                ('plan.json', saved_plan, ordered_plan),
                ('selection.json', saved_selection, ordered_selection)):
            if not same_values(saved, ordered):
                raise ValueError('order restoration may not change any JSON value')
            self.entries[root / filename] = (canonical(saved), deepcopy(ordered))

    def __call__(self, path):
        value = self.original_read(path)
        entry = self.entries.get(Path(path).resolve())
        if entry is None:
            return value
        expected, ordered = entry
        if canonical(value) != expected:
            raise ValueError('raw ordered input changed after preparation')
        return deepcopy(ordered)

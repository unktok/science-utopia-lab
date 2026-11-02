"""Exact historical Qwen-prefix coupling, never synthetic researcher replies.

Original native phases still execute. Before the declared intervention their
actual request bytes must reproduce one sealed historical run. Only that
historical oracle prefix is replayed; intervention and later requests use the
original fresh transport. Logical replay is explicitly recorded, not counted as
new physical inference or an independent researcher-world replication.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sqlite3
import threading

from openai.types.chat import ChatCompletion

from utopia.agents.base_agent import PaperReview
from utopia.runtime.checkpointing import PortableCheckpointError, canonical_json, read_portable_checkpoint
from utopia.system import SystemSpec
from utopia.system.design_patch import digest
from utopia.system.native_kernel import NativeScienceKernel
from utopia.utils.data_utils import file_sha256
from .native_transition_data import physical_initial_identity

SCHEMA = 'scienceutopia.native-historical-response-prefix.v9'


def _sealed(value):
    result = deepcopy(value)
    result['content_sha256'] = digest(result)
    return result


def _seed(payload):
    return payload.get('seed', payload.get('extra_body', {}).get('seed'))


def _review(payload):
    schema = (payload.get('extra_body', {}).get('structured_outputs', {}).get('json')
        or payload.get('response_format', {}).get('json_schema', {}).get('schema'))
    return schema == PaperReview.model_json_schema()


def _transport(journal, wire):
    with sqlite3.connect(journal.as_uri()+'?mode=ro', uri=True) as db:
        metadata = db.execute('SELECT binding FROM metadata').fetchall()
        rows = db.execute('SELECT rowid,identity,payload_sha,outcome,data,data_sha FROM replies ORDER BY rowid').fetchall()
    if len(metadata) != 1:
        raise ValueError('historical response prefix requires one exact cache binding')
    binding = json.loads(metadata[0][0])
    wires = [json.loads(line) for line in wire.read_text().splitlines()]
    if (len(rows) != len(wires) or len({r[1] for r in rows}) != len(rows)
            or len({r[2] for r in rows}) != len(rows)
            or [r[2] for r in rows] != [w.get('payload_sha256') for w in wires]):
        raise ValueError('historical prefix requires unique serial wire/cache sequence agreement')
    for row, request in zip(rows, wires):
        _, _, payload_sha, outcome, data, data_sha = row
        if (outcome != 'response' or hashlib.sha256(data.encode()).hexdigest() != data_sha
                or hashlib.sha256(canonical_json(request['payload']).encode()).hexdigest() != payload_sha
                or request['payload'].get('model') != binding['model']
                or json.loads(data).get('model') != binding['model']
                or type(request.get('year')) is not int or type(_seed(request['payload'])) is not int):
            raise ValueError('historical prefix request/reply bytes, model, year or seed differ')
        decoded = ChatCompletion.model_validate(json.loads(data))
        if canonical_json(decoded.model_dump(mode='json')) != data:
            raise ValueError('historical response envelope is not preserved by the current normal cache codec')
    return binding, rows, wires


def prepare_common_prefix(anchor_world_dir, endpoint):
    """Read-only, sealed actual historical prefix BEFORE year2's first review.

    Full anchor envelopes remain in their original journal. The manifest carries
    exact hashes/locators and original checkpoint/model/corpus/source identities,
    not copied researcher text or a newly generated teacher response.
    """
    root = Path(anchor_world_dir).resolve()
    checkpoint = root/'simulation/checkpoints/native-design/portable_checkpoint_year_2.json.gz'
    initial = checkpoint.with_name('portable_checkpoint_year_0.json.gz')
    journal, wire, contexts = root/'replies/responses.sqlite', root/'wire-requests.jsonl', root/'code-contexts.jsonl'
    paths = {'checkpoint': checkpoint, 'initial_checkpoint': initial, 'journal': journal, 'wire': wire, 'code_contexts': contexts}
    before = {name: file_sha256(path) for name, path in paths.items()}
    if (Path(endpoint['checkpoint']).resolve() != checkpoint or before['checkpoint'] != endpoint['checkpoint_sha256']
            or before['initial_checkpoint'] != endpoint['initial_checkpoint_sha256']
            or Path(endpoint['code_contexts']).resolve() != contexts or before['code_contexts'] != endpoint['code_contexts_sha256']):
        raise ValueError('historical prefix anchor must bind its exact original production checkpoint/context files')
    saved, initialized = read_portable_checkpoint(checkpoint), read_portable_checkpoint(initial)
    spec = SystemSpec.from_dict(endpoint['system'])
    kernel = NativeScienceKernel(spec, checkpoint=saved['native_system'])
    binding, rows, wires = _transport(journal, wire)
    world = endpoint['world']
    if (saved.get('year') != 2 or saved.get('phase') != 5 or kernel.last_year != 2
            or saved['portable']['contract']['binding'] != binding
            or initialized['portable']['contract']['binding'] != binding
            or initialized.get('year') != 0 or initialized.get('phase') != 0
            or initialized['portable']['response_cache_count'] != 0
            or physical_initial_identity(initialized) != endpoint['physical_initial_identity']
            or len(rows) != endpoint['response_cache_count'] or len(rows) != saved['portable']['response_cache_count']
            or spec.fingerprint != endpoint['system_fingerprint'] or binding['cell'] != spec.fingerprint
            or binding['science_config']['source_commit'] != world['source_commit']
            or binding['model_revision'] != world['model_digest'] or binding['corpus_sha256'] != world['corpus_sha256']
            or binding['seed'] != world['seed'] or kernel.to_dict()['event_stream_hash'] != endpoint['native_event_stream_hash']):
        raise ValueError('historical prefix checkpoint, initialized world, full journal binding or endpoint differs')
    if any('replayed_from' in w for w in wires):
        raise ValueError('historical anchor must contain actual physical replies, not another replayed prefix')
    boundary = next((i for i, w in enumerate(wires) if w['year'] == 2 and _review(w['payload'])), None)
    if boundary is None or boundary == 0:
        raise ValueError('historical anchor has no nonempty prefix before its original year2 review boundary')
    calls = [{'index': i, 'year': w['year'], 'seed': _seed(w['payload']), 'payload_sha256': row[2],
        'anchor_cache_identity': row[1], 'anchor_sql_rowid': row[0], 'anchor_wire_line': i+1,
        'response_sha256': row[5]} for i, (row, w) in enumerate(zip(rows[:boundary], wires[:boundary]))]
    result = {'schema': SCHEMA, 'classification': 'historical-oracle-prefix-coupling-not-independent-native-samples',
        'anchor_classification': world.get('classification', 'unclassified-explicit-anchor'),
        'anchor_model': binding['model'],
        'anchor_world_dir': str(root), 'anchor_world': str(root), 'anchor_endpoint': deepcopy(endpoint), 'anchor_binding': binding,
        'anchor_files': {name: {'path': str(paths[name]), 'sha256': sha} for name, sha in before.items()},
        'prefix_count': boundary, 'calls': calls,
        'boundary': {'year': 2, 'task_schema_sha256': digest(PaperReview.model_json_schema()),
            'seed': _seed(wires[boundary]['payload']), 'anchor_first_review_payload_sha256': rows[boundary][2]},
        'module_sha256': file_sha256(Path(__file__)),
        'scope': 'Exact original historical Qwen answers are shared only before the first year2 review. All native phases execute; remaining reviewer and later oracle responses are fresh. No independent-prefix-replication or exact-native-gradient claim.'}
    if before != {name: file_sha256(path) for name, path in paths.items()}:
        raise ValueError('historical anchor changed during read-only prefix preparation')
    return _sealed(result)


class CommonPrefixReplay:
    def __init__(self, simulation, prepared, wire_path):
        if (not isinstance(prepared, dict) or prepared.get('schema') != SCHEMA
                or prepared.get('content_sha256') != digest({k: v for k, v in prepared.items() if k != 'content_sha256'})
                or prepared.get('module_sha256') != file_sha256(Path(__file__))):
            raise ValueError('historical prefix manifest/schema/source content changed')
        if prepare_common_prefix(prepared['anchor_world_dir'], prepared['anchor_endpoint']) != prepared:
            raise ValueError('historical prefix does not reconstruct from unchanged original raw')
        self.simulation, self.model, self.prepared = simulation, simulation.llm, deepcopy(prepared)
        if type(getattr(self.model, 'max_concurrent_requests', None)) is not int or self.model.max_concurrent_requests != 1:
            raise ValueError('historical prefix replay requires explicitly serial max_concurrent_requests=1')
        checkpoint_dir = Path(simulation.output_dir).resolve()
        root = checkpoint_dir.parents[2]
        self.wire = Path(wire_path).resolve()
        cache = self.model.response_cache
        if (checkpoint_dir != root/'simulation/checkpoints/native-design'
                or Path(cache.path).resolve() != root/'replies/responses.sqlite'
                or self.wire != root/'wire-requests.jsonl'):
            raise ValueError('historical prefix target must use its exact production checkpoint/cache/wire layout')
        anchor = prepared['anchor_binding']
        if (any(cache.binding[k] != anchor[k] for k in ('model', 'model_revision', 'corpus_sha256', 'seed'))
                or cache.binding['cell'] != simulation.native_system.spec.fingerprint):
            raise ValueError('historical prefix target model/corpus/seed/native design binding differs')
        _, anchor_rows, _ = _transport(Path(prepared['anchor_files']['journal']['path']),
            Path(prepared['anchor_files']['wire']['path']))
        self.responses = [row[4] for row in anchor_rows[:prepared['prefix_count']]]
        self.lock = threading.Lock()
        self.cursor, self.fresh_prior, self.fresh_current, self.replayed_current = 0, 0, 0, 0
        count = cache.committed_count()
        if count:
            cache.committed_prefix_identity()  # Full normal new-binding integrity.
            _, prior_rows, prior_wires = _transport(Path(cache.path).resolve(), self.wire)
            if count != len(prior_rows):
                raise ValueError('existing target cache count changed during prefix installation')
            for i, (row, request) in enumerate(zip(prior_rows, prior_wires)):
                if i < prepared['prefix_count']:
                    origin = self._origin(i)
                    if (row[2] != prepared['calls'][i]['payload_sha256']
                            or row[5] != prepared['calls'][i]['response_sha256'] or request.get('replayed_from') != origin):
                        raise ValueError('existing target cache prefix lacks exact historical replay provenance')
                elif 'replayed_from' in request:
                    raise ValueError('existing target has undeclared replay after the intervention boundary')
            self.cursor, self.fresh_prior = min(count, prepared['prefix_count']), max(0, count-prepared['prefix_count'])
        elif self.wire.exists() and self.wire.stat().st_size:
            raise ValueError('orphaned target wire has calls absent from its normal response journal')
        self.initially_committed_prefix = self.cursor
        self.fresh_started = self.fresh_prior > 0
        self.callback = self.model.client.chat.completions.create
        self.model.client.chat.completions.create = self.create

    def _origin(self, index):
        call = self.prepared['calls'][index]
        return {'schema': SCHEMA+'.replayed-from', 'manifest_sha256': self.prepared['content_sha256'],
            'anchor_checkpoint_sha256': self.prepared['anchor_endpoint']['checkpoint_sha256'],
            'anchor_journal_sha256': self.prepared['anchor_files']['journal']['sha256'],
            **deepcopy(call)}

    def create(self, **payload):
        if not self.lock.acquire(blocking=False):
            raise PortableCheckpointError('concurrent historical prefix transport is unsupported')
        try:
            frame = self.simulation.native_system._frame
            year = frame.get('year') if frame else None
            if type(year) is not int:
                raise PortableCheckpointError('historical prefix call occurs outside an actual native year')
            payload_sha = hashlib.sha256(canonical_json(payload).encode()).hexdigest()
            if self.cursor < self.prepared['prefix_count']:
                index = self.cursor
                call = self.prepared['calls'][index]
                if payload_sha != call['payload_sha256'] or year != call['year'] or _seed(payload) != call['seed']:
                    raise PortableCheckpointError('actual native request differs from exact historical prefix; no fresh fallback')
                data = self.responses[index]
                if hashlib.sha256(data.encode()).hexdigest() != call['response_sha256']:
                    raise PortableCheckpointError('historical response bytes changed in memory')
                response = ChatCompletion.model_validate(json.loads(data))
                record = {'year': year, 'payload_sha256': payload_sha, 'payload': payload, 'replayed_from': self._origin(index)}
                self.wire.parent.mkdir(parents=True, exist_ok=True)
                with self.wire.open('a') as handle:
                    handle.write(json.dumps(record, ensure_ascii=False, allow_nan=False)+'\n')
                    handle.flush()
                self.cursor += 1
                self.replayed_current += 1
                return response
            if not self.fresh_started:
                boundary = self.prepared['boundary']
                if year != boundary['year'] or not _review(payload) or _seed(payload) != boundary['seed']:
                    raise PortableCheckpointError('historical prefix ended before the exact original year2 review boundary')
                self.fresh_started = True
            response = self.callback(**payload)
            self.fresh_current += 1
            return response
        finally:
            self.lock.release()

    def receipt(self, *, require_complete=False):
        fresh_count = self.fresh_prior+self.fresh_current
        logical_count = self.model.response_cache.committed_count()
        if require_complete and (self.cursor != self.prepared['prefix_count'] or not self.fresh_started
                or fresh_count == 0 or logical_count != self.cursor+fresh_count):
            raise ValueError('historical prefix was not fully consumed before fresh original year2 review')
        if require_complete:
            for record in self.prepared['anchor_files'].values():
                if file_sha256(Path(record['path'])) != record['sha256']:
                    raise ValueError('historical anchor bytes changed during the coupled native world')
            self.model.response_cache.committed_prefix_identity()
            _, rows, wires = _transport(Path(self.model.response_cache.path).resolve(), self.wire)
            if len(rows) != logical_count:
                raise ValueError('completed coupled native cache/wire count changed')
            for i, (row, request) in enumerate(zip(rows, wires)):
                if i < self.prepared['prefix_count']:
                    if (row[2] != self.prepared['calls'][i]['payload_sha256']
                            or row[5] != self.prepared['calls'][i]['response_sha256']
                            or request.get('replayed_from') != self._origin(i)):
                        raise ValueError('completed historical prefix cache/wire provenance differs')
                elif 'replayed_from' in request:
                    raise ValueError('completed native transport replays an undeclared post-boundary response')
        return _sealed({'schema': SCHEMA+'.execution', 'manifest_sha256': self.prepared['content_sha256'],
            'anchor_checkpoint_sha256': self.prepared['anchor_endpoint']['checkpoint_sha256'],
            'used_prefix_count': self.cursor, 'expected_prefix_count': self.prepared['prefix_count'],
            'replayed_response_count': self.cursor,
            'initially_committed_prefix_count': self.initially_committed_prefix,
            'replayed_in_this_session': self.replayed_current,
            'fresh_physical_calls': fresh_count, 'fresh_physical_reply_count': fresh_count,
            'fresh_physical_calls_this_session': self.fresh_current,
            'fresh_review_boundary_reached': self.fresh_started,
            'logical_response_count': logical_count,
            'prefix_complete': self.cursor == self.prepared['prefix_count'],
            'independent_prefix_replication': False,
            'target_binding_sha256': digest(self.model.response_cache.binding)})

    def complete(self):
        return self.receipt(require_complete=True)


def install_common_prefix(simulation, prepared, wire_path):
    """Install after the factory's original HTTP recorder, before sim.run()."""
    return CommonPrefixReplay(simulation, prepared, wire_path)

"""Read-only own-trial files from the exact request, never filesystem lookups.

The incumbent is not necessarily the last failed design. Error text plus a hash
does not let an author inspect that design. These aliases expose its literal
archived data without adopting, correcting, executing or ranking any candidate.
"""
from utopia.system.design_patch import digest


def history_entries(request, draft_entries):
    records = request.get('history', []) if isinstance(request, dict) else []
    if not records:
        return {}
    entries, trials = {}, []

    def add(filename, value, origin, *, format='json-history', **metadata):
        entries[filename] = {'format': format, 'value': value, 'path': None,
            'read_only': True, 'source_kind': 'own-history', 'archive': origin, **metadata}

    for index, record in enumerate(records):
        prefix = f'history/trial-{index:03d}/'
        trial = {'history_index': index, 'files': [], 'observations': []}
        trials.append(trial)
        if not isinstance(record, dict):
            name = prefix + 'record.json'
            add(name, record, {'history_index': index, 'field': 'record'})
            trial['files'].append(name)
            continue
        if 'definition' in record:
            name = prefix + 'definition.json'
            add(name, record['definition'], {'history_index': index, 'field': 'definition'})
            trial['files'].append(name)
        observations = record.get('observations')
        if not isinstance(observations, list):
            observations = []
        for observation_index, observation in enumerate(observations):
            origin = {'history_index': index, 'observation_index': observation_index,
                'original_observation_sha256': digest(observation)}
            base = prefix + f'observation-{observation_index:03d}/'
            name = base + 'observation.json'
            add(name, observation, {**origin, 'field': 'observation'})
            item = {'observation_index': observation_index, 'files': [name],
                'candidate_present': False}
            trial['observations'].append(item)
            candidate = observation.get('candidate') if isinstance(observation, dict) else None
            if not isinstance(candidate, dict):
                continue  # Unknown/missing stays unknown; no draw or parent substitution.
            origin.update(candidate_sha256=digest(candidate),
                observed_status=observation.get('status'), observed_loss=observation.get('loss'))
            item.update(candidate_present=True, candidate_sha256=origin['candidate_sha256'],
                status=observation.get('status'), loss=observation.get('loss'))
            aliases, ambiguous = draft_entries(candidate)
            item['ambiguous_node_ids_without_aliases'] = ambiguous
            for relative, entry in sorted(aliases.items()):
                if relative.startswith('reference/'):
                    continue  # Current source API is not an archived candidate field.
                name = base + relative
                add(name, entry['value'], {**origin, 'field': 'candidate',
                    'candidate_virtual_filename': relative}, format=entry['format'],
                    **{k: entry[k] for k in ('mechanism_id', 'implementation') if k in entry})
                item['files'].append(name)
    index = {'schema': 'scienceutopia.own-history-file-index.v37', 'trials': trials,
        'all_archive_names_included': True, 'archived_file_count': len(entries),
        'scope': 'Exact own request history only; failed candidates may differ from the incumbent. '
            'Read-only data, not SYSTEM instructions, executed behavior, adoption or a supplied new policy. '
            'To reuse anything, explicitly author an edit to a current draft filename.'}
    add('history/index.json', index, {'field': 'history-index'})
    return entries

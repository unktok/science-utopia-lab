"""Read-only prospective seed usage check within this project's raw outputs."""
from datetime import datetime,timezone
import json
from pathlib import Path
import sqlite3

from utopia.system.design_patch import digest


def usage_inventory(root,seeds):
    root=Path(root).resolve();rows=[];excluded=[];errors=[];seen=[]
    for path in sorted(root.rglob('responses.sqlite')):
        relative=path.relative_to(root)
        if any('verification' in part or 'pytest' in part for part in relative.parts):
            excluded.append(str(relative));continue
        try:
            with sqlite3.connect(path.resolve().as_uri()+'?mode=ro',uri=True) as db:
                records=db.execute('SELECT binding FROM metadata').fetchall()
            if len(records)!=1:raise ValueError('response journal has no unique immutable binding')
            binding=json.loads(records[0][0])
            row={'path':str(relative),'binding_sha256':digest(binding),'seed':binding.get('seed'),
                'model':binding.get('model'),'protocol':binding.get('protocol')}
            rows.append(row)
            if type(row['seed']) is int and row['seed'] in seeds:seen.append(row)
        except Exception as e:errors.append({'path':str(relative),'error':type(e).__name__+': '+str(e)})
    receipt={'schema':'scienceutopia.native-benchmark-seed-usage.v2','root':str(root),
        'seeds':list(seeds),'checked_utc':datetime.now(timezone.utc).isoformat(),
        'bindings':rows,'excluded_software_verification_paths':excluded,'errors':errors,
        'prior_matching_runs':seen,'valid':not errors and not seen,'new_model_calls':0,
        'scope':'Project raw response journals outside explicit software verification; not a claim about other directories or machines.'}
    receipt['content_sha256']=digest(receipt)
    return receipt

"""Observe THIS interpreter/environment without installing or contacting a model.

An observation made after dispatch is not a startup attestation, an exhaustive
lockfile, an observation of a separate model-server interpreter, or a new run.
"""
import argparse
from datetime import datetime,timezone
from importlib import metadata
import os
from pathlib import Path
import platform
import subprocess
import sys

from scripts.reports.native_design_benchmark import checked,SCHEMA as STUDY
from utopia.system.design_patch import digest
from utopia.utils.data_utils import decode_json,file_sha256,write_json_atomic

PACKAGES=('numpy','scipy','pandas','scikit-learn','networkx','torch','transformers',
    'sentence-transformers','huggingface-hub','datasets','pyarrow','langchain-core',
    'openai','pydantic','jsonschema','tqdm','requests','httpx','matplotlib','pytest','pip','mlx','mlx-lm')
REQUIREMENTS=('requirements.txt','requirements-test.txt','requirements-figures.txt',
    'requirements-optional.txt','requirements-vllm.txt','constraints-linux-py311.txt')


def observe(plan,source_root,*,package_version=metadata.version,observed_utc=None):
    checked(plan,STUDY)
    source_root=Path(source_root).resolve()
    revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=source_root,text=True).strip()
    dirty=subprocess.check_output(['git','status','--porcelain'],cwd=source_root,text=True)
    if revision!=plan['source_commit'] or dirty:raise ValueError('clean exact source checkout required')
    packages={}
    for name in PACKAGES:
        try:
            version=package_version(name)
            if not isinstance(version,str) or not version:raise ValueError('missing package version for '+name)
            packages[name]={'version':version,'status':'observed-in-this-interpreter'}
        except metadata.PackageNotFoundError:
            packages[name]={'version':None,'status':'not-installed-in-this-interpreter'}
    requirements={name:file_sha256(source_root/name) for name in REQUIREMENTS if (source_root/name).is_file()}
    result={'schema':'scienceutopia.submission-environment-observation.v1',
        'observed_utc':observed_utc or datetime.now(timezone.utc).isoformat(),
        'source_commit':revision,'plan_sha256':plan['content_sha256'],
        'python':{'implementation':platform.python_implementation(),'version':platform.python_version(),
            'cache_tag':sys.implementation.cache_tag},
        'platform':{'system':platform.system(),'release':platform.release(),'machine':platform.machine(),
            'logical_cpu_count':os.cpu_count()},
        'packages':packages,'source_requirements_sha256':requirements,
        'plan_declared_models':{role:{k:plan[role][k] for k in ['model','model_digest']}
            for role in ['scientist','designer']},
        'plan_declared_sandbox_image':plan['scientist']['image_id'],
        'backend_metadata_from_prior_plan_only':plan['backend'],
        'observer_source_sha256':file_sha256(Path(__file__)),
        'startup_environment_attested':False,'complete_environment_lock_claimed':False,
        'separate_model_server_packages_observed':False,'new_endpoint_requests':0,
        'new_inference_requests':0,'package_installs':0,'downloads':0,
        'scope':'Current observer interpreter only, after dispatch. No hostname, home path, environment secret, direct package URL, operator configuration, model weights or corpus content included. Missing optional packages here do not imply absence in the separate inference service.'}
    result['content_sha256']=digest(result)
    return result


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--plan',type=Path,required=True);p.add_argument('--source-root',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args(argv)
    if (a.output.exists() or a.output.resolve().is_relative_to(a.plan.resolve().parent)
            or a.output.resolve().is_relative_to(a.source_root.resolve())):
        p.error('fresh observation outside raw plan and frozen source directories required')
    original=a.plan.read_bytes()
    result=observe(decode_json(original.decode(),strict=True,finite_floats=True),a.source_root)
    if a.plan.read_bytes()!=original:raise ValueError('plan changed during environment observation')
    write_json_atomic(a.output,result,sort_keys=True,allow_nan=False,indent=2)
    print({'content_sha256':result['content_sha256'],'packages_observed':len(result['packages'])});return 0


if __name__=='__main__':raise SystemExit(main())

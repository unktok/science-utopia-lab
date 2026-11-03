import { describe, expect, it } from 'vitest';
import { existsSync } from 'node:fs';
import { execFileSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { decodeAuthorTrace } from '../src/authoringChronicle';
const backend = process.env.SCIENCE_UTOPIA_V15_BACKEND ?? fileURLToPath(new URL('../../', import.meta.url));
describe.skipIf(!existsSync(`${backend}/utopia/optimization/native_staged_author_v15.py`))('actual production projector with SCRIPTED model (no Qwen)', () => {
  it('accepts rejected/inspect/edit/finish trace emitted by the real Python journal implementation', () => {
    const text = execFileSync('/Users/shiro/unktok/dev/science-utopia-lab/.venv/bin/python', ['-c', `import json,tempfile
from pathlib import Path
from tests.optimization.test_native_authoring_ir import ALPHA,BINDING,IMAGE,request
from tests.optimization.test_native_search_generator_v14 import Model
from utopia.optimization.native_staged_author_v15 import StagedVocabularyGenerator,project_authoring_trace
actions=[{'tool':'shell','command':'NEVER EXECUTED'}, {'tool':'inspect','selector':{'mechanism_id':ALPHA},'path':''}, {'tool':'edit','operations':[{'op':'replace','selector':{'mechanism_id':ALPHA},'path':'/parameters/gain','value':1.2}]}, {'tool':'finish','rationale':'SCRIPTED software interoperability only'}]
with tempfile.TemporaryDirectory(prefix='SCRIPTED-v15-UI-projection-') as directory:
    root=Path(directory)
    result=StagedVocabularyGenerator(Model(actions),root,image_id=IMAGE,provider_binding=BINDING,max_steps=4,max_tokens=2048)(request())
    trace=project_authoring_trace(root)
    print(json.dumps(trace))
`], { cwd: backend, encoding: 'utf8', env: { ...process.env, PYTHONDONTWRITEBYTECODE: '1' } });
    const trace = decodeAuthorTrace(JSON.parse(text)); expect(trace?.warnings).toEqual([]); expect(trace?.generations).toHaveLength(1); expect(trace?.generations[0]?.steps.map(step => step.status)).toEqual(['rejected', 'applied', 'applied', 'finished']); expect(trace?.generations[0]?.steps[0]?.tool).toBe('shell'); expect(trace?.generations[0]?.definition_sha256).toMatch(/^[a-f0-9]{64}$/);
  });
});

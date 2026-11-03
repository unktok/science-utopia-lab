// Software/fully intercepted browser QA only. Never starts a native worker/model.
import assert from 'node:assert/strict';
import { spawnSync, execFileSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { readFile, mkdir, writeFile } from 'node:fs/promises';
import { resolve, isAbsolute } from 'node:path';
const args = Object.fromEntries(process.argv.slice(2).map(value => { const [key, ...rest] = value.replace(/^--/, '').split('='); return [key, rest.join('=')]; }));
assert(typeof args.output === 'string' && isAbsolute(args.output), 'Absolute fresh output directory required');
assert.equal(execFileSync('git', ['status', '--porcelain', '--', '.'], { encoding: 'utf8' }), '', 'Commit UI changes before source-bound verification');
const output = resolve(args.output), sha = value => createHash('sha256').update(value).digest('hex'), head = execFileSync('git', ['rev-parse', 'HEAD'], { encoding: 'utf8' }).trim();
const files = execFileSync('git', ['ls-files', '-z', 'src', 'test', 'scripts', 'native.html', 'package.json', 'package-lock.json', 'STAGED_FOUNDRY_V15.md'], { encoding: 'utf8' }).split('\0').filter(Boolean);
const sources = Object.fromEntries(await Promise.all(files.map(async file => [file, sha(await readFile(file))])));
await mkdir(output); const checks = [];
for (const [name, command, argv] of [['tests', 'npm', ['test']], ['typecheck', 'npm', ['run', 'typecheck']], ['build', 'npm', ['run', 'build']], ['operator-guards', process.execPath, ['--test', 'scripts/test-native-search-operator-v14.mjs']], ['SCRIPTED-legacy-browser', process.execPath, ['scripts/verify-native-search-browser.mjs']], ['SCRIPTED-staged-browser', process.execPath, ['scripts/verify-native-search-browser.mjs', '--staged-v15']]]) {
  const started = new Date().toISOString(), result = spawnSync(command, argv, { encoding: 'utf8', maxBuffer: 16 * 1024 * 1024 }), text = `${result.stdout ?? ''}${result.stderr ?? ''}`, file = `${name}.log`; await writeFile(resolve(output, file), text);
  checks.push({ name, command: [command, ...argv], started_utc: started, ended_utc: new Date().toISOString(), exit_code: result.status, error: result.error ? String(result.error) : null, log_file: file, log_sha256: sha(text) });
  if (result.status !== 0) break;
}
const sourcesAfter = Object.fromEntries(await Promise.all(files.map(async file => [file, sha(await readFile(file))])));
const receipt = { schema: 'scienceutopia.staged-foundry-software-checks.v15', classification: 'SOFTWARE-AND-SCRIPTED-NOT-NATIVE-RESULTS', git_head: head, source_sha256s: sources, source_unchanged: JSON.stringify(sourcesAfter) === JSON.stringify(sources), no_inference: true, no_native_worker: true, checks, all_pass: checks.length === 6 && checks.every(check => check.exit_code === 0) && JSON.stringify(sourcesAfter) === JSON.stringify(sources) };
await writeFile(resolve(output, 'ui-software-checks.json'), `${JSON.stringify(receipt, null, 2)}\n`); console.log(JSON.stringify({ output, ...receipt })); if (!receipt.all_pass) process.exitCode = 1;

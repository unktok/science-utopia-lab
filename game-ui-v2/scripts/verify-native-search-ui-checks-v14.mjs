// Durable local software checks only. Never starts the native worker or model.
import assert from 'node:assert/strict';
import { spawnSync, execFileSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { readFile, mkdir, writeFile } from 'node:fs/promises';
import { resolve, isAbsolute } from 'node:path';
const args = Object.fromEntries(process.argv.slice(2).map(value => { const [key, ...rest] = value.replace(/^--/, '').split('='); return [key, rest.join('=')]; }));
assert(typeof args.output === 'string' && isAbsolute(args.output), 'Absolute output directory required');
const output = resolve(args.output), sha = bytes => createHash('sha256').update(bytes).digest('hex'), head = execFileSync('git', ['rev-parse', 'HEAD'], { encoding: 'utf8' }).trim();
const sourceFiles = ['native.html', 'src/native.ts', 'src/nativeSearchContract.ts', 'src/nativeSearchView.ts', 'src/nativeSearchAudit.ts', 'src/nativeSearch.css', 'test/nativeSearch.test.ts', 'test/nativeSearchAudit.test.ts', 'scripts/verify-native-search-ui-checks-v14.mjs'];
const sources = Object.fromEntries(await Promise.all(sourceFiles.map(async file => [file, sha(await readFile(file))])));
await mkdir(output, { recursive: true }); const checks = [];
for (const [name, command, argv] of [['tests', 'npm', ['test']], ['typecheck', 'npm', ['run', 'typecheck']], ['build', 'npm', ['run', 'build']], ['operator-guards', process.execPath, ['--test', 'scripts/test-native-search-operator-v14.mjs']]]) {
  const started = new Date().toISOString(), result = spawnSync(command, argv, { encoding: 'utf8', maxBuffer: 16 * 1024 * 1024 }), text = `${result.stdout ?? ''}${result.stderr ?? ''}`, file = `${name}.log`; await writeFile(resolve(output, file), text);
  checks.push({ name, command: [command, ...argv], started_utc: started, ended_utc: new Date().toISOString(), exit_code: result.status, error: result.error ? String(result.error) : null, log_file: file, log_sha256: sha(text) });
  if (result.status !== 0) break;
}
const receipt = { schema: 'scienceutopia.native-search-ui-software-checks.v14', git_head: head, source_sha256s: sources, no_inference: true, no_native_worker: true, checks, all_pass: checks.length === 4 && checks.every(check => check.exit_code === 0) };
await writeFile(resolve(output, 'ui-software-checks.json'), `${JSON.stringify(receipt, null, 2)}\n`); console.log(JSON.stringify({ output, ...receipt })); if (!receipt.all_pass) process.exitCode = 1;

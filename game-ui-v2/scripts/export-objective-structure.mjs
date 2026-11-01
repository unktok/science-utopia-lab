#!/usr/bin/env node
import { createHash } from "node:crypto";
import { mkdir, readFile, writeFile } from "node:fs/promises";
import { basename, dirname, resolve } from "node:path";

const [, , sourceArg, outputArg] = process.argv;
if (!sourceArg) {
  console.error("usage: node scripts/export-objective-structure.mjs /absolute/path/native-objective-structure-v8-a2.json [public/data/native-objective-structure-v8-a2.json]");
  process.exit(2);
}
const source = resolve(sourceArg);
const output = resolve(outputArg ?? new URL("../public/data/native-objective-structure-v8-a2.json", import.meta.url).pathname);
const bytes = await readFile(source);
const report = JSON.parse(bytes.toString("utf8"));
if (report.schema !== "scienceutopia.native-objective-structure-audit.v8") throw new Error("unsupported objective-structure audit schema");
if (report.classification !== "actual-native-qwen-objective-structure-development-v8") throw new Error("only independently audited actual evidence may enter the actual UI channel");
if (!/^[0-9a-f]{64}$/.test(report.content_sha256) || !/^[0-9a-f]{40}$/.test(report.source_commit)) throw new Error("audit hash/source binding is malformed");
if (!['complete', 'budget-complete-with-failures'].includes(report.status)) throw new Error("actual UI export requires a terminal audited report");
if (report.held_out_metrics?.status !== "not-defined-or-measured" || report.promotion_policy?.status !== "not-defined-or-applied") throw new Error("v8 development evidence cannot be relabelled held-out or promoted");
const fileHash = createHash("sha256").update(bytes).digest("hex");
const receipt = {
  schema: "scienceutopia.native-objective-structure-ui-export.v8",
  report_file: basename(output), report_file_sha256: fileHash,
  report_content_sha256: report.content_sha256, classification: report.classification,
  exported_without_transform: true,
};
await mkdir(dirname(output), { recursive: true });
await writeFile(output, bytes);
await writeFile(output.replace(/\.json$/, ".ui-export.json"), `${JSON.stringify(receipt, null, 2)}\n`);
console.log(JSON.stringify({ output, ...receipt }));

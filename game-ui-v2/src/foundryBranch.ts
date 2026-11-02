import { parseEditableSystemSpec, structuralCheck } from './nativeDesignGraph';
import { sha256Text } from './methodObservatoryContract';

export const FOUNDRY_BRANCH_KEY = 'scienceutopia.foundry.prepared-branch.v13';
export interface PreparedFoundryBranch {
  schema: 'scienceutopia.foundry-prepared-branch.v13';
  state: 'local-unexecuted-draft';
  origin: { source_binding: Record<string, unknown>; objective_id: string; observation_id: string; system_fingerprint: string };
  parent_system: Record<string, any>; system: Record<string, any>; loss_spec: Record<string, any>;
  seed: number; years: number; no_execution: true; no_adoption: true;
}

// A structural precheck is not runtime validation, source execution, or adoption.
export function prepareFoundryBranch(origin: PreparedFoundryBranch['origin'], parent: Record<string, any>, systemText: string, loss: Record<string, any>): PreparedFoundryBranch {
  const system = parseEditableSystemSpec(JSON.parse(systemText));
  const checked = structuralCheck(system,{allowOpenFamilies:true});
  if (!checked.valid) throw new Error(`Local structural check failed: ${checked.errors.join('; ')}`);
  if (!origin.observation_id || !/^[a-f0-9]{64}$/.test(origin.system_fingerprint)) throw new Error('Observed parent identity required');
  // Preserve the exact edited JSON object, including absent optional fields:
  // parseEditableSystemSpec normalizes only its temporary checking copy.
  return structuredClone({schema:'scienceutopia.foundry-prepared-branch.v13',state:'local-unexecuted-draft',origin,parent_system:parent,
    system:JSON.parse(systemText),loss_spec:loss,seed:42,years:2,no_execution:true,no_adoption:true});
}

export async function readPreparedFoundryBranch(text: string, expectedHash: string): Promise<PreparedFoundryBranch> {
  if (!/^[a-f0-9]{64}$/.test(expectedHash) || await sha256Text(text) !== expectedHash) throw new Error('Prepared draft hash differs');
  const branch = JSON.parse(text) as PreparedFoundryBranch;
  if (branch.schema !== 'scienceutopia.foundry-prepared-branch.v13' || branch.state !== 'local-unexecuted-draft'
      || branch.no_execution !== true || branch.no_adoption !== true || branch.seed !== 42 || branch.years !== 2
      || !branch.loss_spec || typeof branch.loss_spec !== 'object' || !branch.parent_system || !branch.origin?.source_binding) throw new Error('Unsupported prepared draft');
  prepareFoundryBranch(branch.origin, branch.parent_system, JSON.stringify(branch.system), branch.loss_spec);
  return branch;
}

export function initializeFoundryBranch(container: HTMLElement, selected: () => {row: Record<string,any>;objective: string;loss: Record<string,any>;binding: Record<string,unknown>;fixture: boolean;unsafeSystemIntegerPaths:string[]}): void {
  container.innerHTML = `<header><div><p class="eyebrow">LOCAL DESIGN BRANCH / NEVER AN EXECUTION RECEIPT</p><h2>TAKE THE CIRCUIT INTO THE WORKSHOP.</h2></div><span>EDIT → LOCAL CHECK → EXACT EXPORT → EXPLICIT CONSENT ELSEWHERE</span></header><p class="foundry-note">Copy the selected observed institution, change its source, ports, wiring or schedules, then prepare a new branch. The audit and original world stay immutable. No inferred outcome, loss, job, or society adoption is created.</p><div class="branch-controls"><button type="button" id="foundry-copy">COPY SELECTED OBSERVED SYSTEM</button><button type="button" id="foundry-check" disabled>CHECK & PREPARE LOCAL BRANCH</button><button type="button" id="foundry-download" disabled>DOWNLOAD EXACT BRANCH JSON</button><a id="foundry-workbench" hidden href="./native.html#design-console">OPEN EXISTING DESIGN WORKBENCH ↗</a></div><p id="foundry-branch-status" role="status">NO LOCAL DRAFT / SELECT AN ACTUAL OBSERVATION ABOVE</p><label class="foundry-draft-label" for="foundry-draft">EDITABLE FULL SYSTEMSPEC / THIS DRAFT HAS NOT RUN</label><textarea id="foundry-draft" spellcheck="false" aria-label="Local unexecuted institutional design draft" disabled></textarea><details><summary>EXACT PREPARED BRANCH / SOURCE BINDING / NO EXECUTION</summary><pre id="foundry-prepared"></pre></details>`;
  const get = <T extends HTMLElement>(id: string): T => container.querySelector(`#${id}`)!;
  const editor = get<HTMLTextAreaElement>('foundry-draft'), check = get<HTMLButtonElement>('foundry-check'), download = get<HTMLButtonElement>('foundry-download'), workbench = get<HTMLAnchorElement>('foundry-workbench');
  let captured: ReturnType<typeof selected> | null = null, prepared = '', revision = 0;
  const invalidate = (): void => {revision++;prepared='';download.disabled=true;workbench.hidden=true;get('foundry-prepared').textContent='';};
  get('foundry-copy').addEventListener('click',()=>{
    const value=selected();invalidate();captured=null;editor.value='';editor.disabled=true;check.disabled=true;
    if (!value.row.system || value.row.status!=='complete' || !value.row.observation_id) {get('foundry-branch-status').textContent='NO COMPLETE OBSERVED SYSTEM TO COPY / FAILURE REMAINS NULL';return;}
    if(value.unsafeSystemIntegerPaths.length){captured=null;editor.disabled=true;check.disabled=true;get('foundry-branch-status').textContent='EXACT SYSTEMSPEC CONTAINS UNSAFE INTEGER TOKENS / LOSSLESS SERVER-SIDE IMPORT REQUIRED / NO ROUNDED DRAFT OR HANDOFF CREATED';return;}
    captured=structuredClone(value);editor.value=JSON.stringify(captured.row.system,null,2);editor.disabled=false;check.disabled=false;
    get('foundry-branch-status').textContent=`LOCAL UNEXECUTED DRAFT FROM ${captured.row.observation_id} / AUDIT UNCHANGED${captured.fixture?' / SCRIPTED UI FIXTURE':''}`;
  });
  editor.addEventListener('input',()=>{invalidate();get('foundry-branch-status').textContent='EDITED LOCAL DRAFT / CHECK REQUIRED / NOT VALIDATED BY RUNTIME OR EXECUTED';});
  check.addEventListener('click',()=>{void(async()=>{try{
    if(!captured)throw new Error('Copy an observed system first');
    const ticket=revision,source=editor.value;
    const branch=prepareFoundryBranch({source_binding:captured.binding,objective_id:captured.objective,observation_id:captured.row.observation_id,system_fingerprint:captured.row.system_fingerprint},captured.row.system,source,captured.loss);
    const text=`${JSON.stringify(branch,null,2)}\n`,digest=await sha256Text(text);
    if(ticket!==revision||source!==editor.value)return;
    prepared=text;get('foundry-prepared').textContent=text;download.disabled=false;
    // Synthetic browser fixtures may exercise local editing/export but must
    // never seed the real native workbench or an execution/adoption request.
    if(!captured.fixture){try{sessionStorage.setItem(FOUNDRY_BRANCH_KEY,text);workbench.href=`./native.html?prepared-branch=${digest}#design-console`;workbench.hidden=false;}catch{/* Exact download remains available without browser storage. */}}
    get('foundry-branch-status').textContent=`LOCAL STRUCTURAL PRECHECK PASS / SHA256 ${digest} / NOT SERVER-VALIDATED, EXECUTED OR ADOPTED${captured.fixture?' / FIXTURE HANDOFF DISABLED':''}`;
  }catch(error){invalidate();get('foundry-branch-status').textContent=String(error);}})();});
  download.addEventListener('click',()=>{if(!prepared)return;const url=URL.createObjectURL(new Blob([prepared],{type:'application/json'})),link=document.createElement('a');link.href=url;link.download='institution-local-unexecuted-branch.json';link.click();URL.revokeObjectURL(url);});
}

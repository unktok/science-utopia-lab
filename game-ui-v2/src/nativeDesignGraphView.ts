import {
  addMechanism, channelKinds, mechanismFamilies, parseEditableSystemSpec, removeConnection,
  removeMechanism, removePort, renameMechanism, serializeSystemSpec, setConnection, structuralCheck,
  type DesignConnection, type DesignMechanism, type DesignPort, type EditableSystemSpec,
} from "./nativeDesignGraph";

const byId = <T extends HTMLElement>(id: string): T => {
  const node = document.getElementById(id); if (!node) throw new Error(`Missing graph authoring element ${id}`); return node as T;
};
const escape = (value: unknown): string => String(value).replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;");
const option = (value: string, label = value): HTMLOptionElement => new Option(label, value);
const clone = <T>(value: T): T => JSON.parse(JSON.stringify(value)) as T;

export function initializeNativeDesignGraph(textarea: HTMLTextAreaElement): void {
  const canvas = byId("graph-canvas"), undo = byId<HTMLButtonElement>("graph-undo"), redo = byId<HTMLButtonElement>("graph-redo");
  const nodeFields = byId("graph-node-fields"), noSelection = byId("graph-no-selection"), localCheck = byId("graph-local-check");
  const idInput = byId<HTMLInputElement>("graph-node-id"), family = byId<HTMLSelectElement>("graph-node-family"), implementation = byId<HTMLInputElement>("graph-node-implementation");
  const phase = byId<HTMLInputElement>("graph-node-phase"), trigger = byId<HTMLInputElement>("graph-node-trigger"), parameters = byId<HTMLTextAreaElement>("graph-node-parameters");
  const sourceNode = byId<HTMLSelectElement>("wire-source-node"), sourcePort = byId<HTMLSelectElement>("wire-source-port"), targetNode = byId<HTMLSelectElement>("wire-target-node"), targetPort = byId<HTMLSelectElement>("wire-target-port");
  const latency = byId<HTMLInputElement>("wire-latency"), wireCommit = byId<HTMLButtonElement>("wire-commit"), wireCancel = byId<HTMLButtonElement>("wire-cancel");
  let spec: EditableSystemSpec | null = null, selected = "", editedWire: number | null = null, internal = false;
  const past: string[] = [], future: string[] = [];
  family.replaceChildren(...mechanismFamilies.map(value => option(value)));

  const currentText = (): string => spec ? serializeSystemSpec(spec) : textarea.value;
  const dispatch = (): void => { textarea.dispatchEvent(new Event("input", { bubbles: true })); };
  const setSpec = (next: EditableSystemSpec, record = true): void => {
    if (record && spec) { past.push(serializeSystemSpec(spec)); if (past.length > 60) past.shift(); future.length = 0; }
    spec = clone(next); internal = true; textarea.value = serializeSystemSpec(spec); internal = false; dispatch(); render();
  };
  const edit = (change: (draft: EditableSystemSpec) => EditableSystemSpec): void => { if (spec) setSpec(change(clone(spec))); };
  const selectedNode = (): DesignMechanism | undefined => spec?.mechanisms.find(node => node.mechanism_id === selected);

  const sync = (): void => {
    if (internal || !textarea.value.trim()) return;
    try {
      const next = parseEditableSystemSpec(JSON.parse(textarea.value));
      if (!spec || serializeSystemSpec(next) !== serializeSystemSpec(spec)) { spec = next; selected = next.mechanisms.some(node => node.mechanism_id === selected) ? selected : next.mechanisms[0]?.mechanism_id || ""; past.length = 0; future.length = 0; }
      render();
    } catch (error) {
      localCheck.className = "graph-local-check invalid"; localCheck.textContent = `JSON NOT PROJECTABLE / ${String(error)} / authoritative validation unavailable until repaired.`;
    }
  };

  const renderPorts = (direction: "inputs" | "outputs", ports: DesignPort[]): void => {
    const root = byId(direction === "inputs" ? "graph-inputs" : "graph-outputs");
    root.innerHTML = ports.length ? ports.map((port, index) => `<div class="port-row" data-direction="${direction}" data-index="${index}"><input data-port-field="port_id" value="${escape(port.port_id)}" aria-label="${direction} port id"/><select data-port-field="channel" aria-label="${direction} channel">${channelKinds.map(value => `<option ${value === port.channel ? "selected" : ""}>${value}</option>`).join("")}</select><input data-port-field="artifact_type" value="${escape(port.artifact_type ?? "")}" placeholder="artifact type" aria-label="${direction} artifact type"/><label class="port-required"><input type="checkbox" data-port-field="required" ${port.required === false ? "" : "checked"}/>REQ</label><button type="button" data-remove-port="${escape(port.port_id)}" aria-label="Remove ${escape(port.port_id)}">×</button></div>`).join("") : `<p class="empty-port">NO ${direction.toUpperCase()}</p>`;
  };

  const fillWirePorts = (): void => {
    const source = spec?.mechanisms.find(node => node.mechanism_id === sourceNode.value), target = spec?.mechanisms.find(node => node.mechanism_id === targetNode.value);
    const oldSource = sourcePort.value, oldTarget = targetPort.value;
    sourcePort.replaceChildren(...(source?.outputs || []).map(port => option(port.port_id, `${port.port_id} / ${port.channel}`)));
    targetPort.replaceChildren(...(target?.inputs || []).map(port => option(port.port_id, `${port.port_id} / ${port.channel}`)));
    if (Array.from(sourcePort.options).some(row => row.value === oldSource)) sourcePort.value = oldSource;
    if (Array.from(targetPort.options).some(row => row.value === oldTarget)) targetPort.value = oldTarget;
  };

  const editWire = (index: number): void => {
    const edge = spec?.connections[index]; if (!edge) return; editedWire = index;
    sourceNode.value = edge.source_mechanism; targetNode.value = edge.target_mechanism; fillWirePorts();
    sourcePort.value = edge.source_port; targetPort.value = edge.target_port; latency.value = String(edge.latency);
    wireCommit.textContent = "APPLY REWIRE"; wireCancel.hidden = false; wireCommit.focus();
  };

  const render = (): void => {
    if (!spec) return;
    const check = structuralCheck(spec,{allowOpenFamilies:true}), phases = new Map(spec.schedules.map(row => [row.mechanism_id, row.phase]));
    localCheck.className = `graph-local-check ${check.valid ? "valid" : "invalid"}`;
    localCheck.textContent = check.valid ? `LOCAL PRECHECK PASS / ${spec.mechanisms.length} mechanisms / ${spec.connections.length} connections / ${check.warnings.length} warning(s) / still not server-validated or executed.` : `LOCAL PRECHECK FAIL / ${check.errors.length} issue(s) / ${check.errors[0]}`;
    undo.disabled = past.length === 0; redo.disabled = future.length === 0;
    const ordered = [...spec.mechanisms].sort((a, b) => (phases.get(a.mechanism_id) ?? 999999) - (phases.get(b.mechanism_id) ?? 999999) || a.mechanism_id.localeCompare(b.mechanism_id));
    canvas.innerHTML = `<div class="author-rail" aria-hidden="true"></div><div class="author-nodes">${ordered.map((node, index) => `<button type="button" class="author-node family-${escape(node.family)}" data-author-node="${escape(node.mechanism_id)}" aria-pressed="${node.mechanism_id === selected}"><span class="author-node-index">${String(index + 1).padStart(2, "0")}</span><span class="author-node-phase">PHASE ${phases.get(node.mechanism_id) ?? "—"}</span><strong>${escape(node.mechanism_id)}</strong><span>${escape(node.family)} / ${node.inputs.length} IN · ${node.outputs.length} OUT</span><i class="node-sockets input" aria-hidden="true">${node.inputs.map(() => "◆").join(" ") || "·"}</i><i class="node-sockets output" aria-hidden="true">${node.outputs.map(() => "◆").join(" ") || "·"}</i></button>`).join("")}</div>`;
    canvas.querySelectorAll<HTMLButtonElement>("[data-author-node]").forEach(button => button.addEventListener("click", () => { selected = button.dataset.authorNode || ""; render(); }));
    const node = selectedNode(); nodeFields.hidden = !node; noSelection.hidden = Boolean(node);
    if (node) {
      if(!Array.from(family.options).some(value=>value.value===node.family))family.add(option(node.family,`${node.family} / DECLARED CUSTOM FAMILY`));
      idInput.value = node.mechanism_id; family.value = node.family; implementation.value = node.implementation;
      const schedule = spec.schedules.find(row => row.mechanism_id === node.mechanism_id); phase.value = schedule ? String(schedule.phase) : ""; trigger.value = schedule?.trigger || "";
      parameters.value = JSON.stringify(node.parameters, null, 2); renderPorts("inputs", node.inputs); renderPorts("outputs", node.outputs);
    }
    const previousSource = sourceNode.value, previousTarget = targetNode.value;
    sourceNode.replaceChildren(...spec.mechanisms.filter(node => node.outputs.length).map(node => option(node.mechanism_id)));
    targetNode.replaceChildren(...spec.mechanisms.filter(node => node.inputs.length).map(node => option(node.mechanism_id)));
    if (Array.from(sourceNode.options).some(row => row.value === previousSource)) sourceNode.value = previousSource;
    if (Array.from(targetNode.options).some(row => row.value === previousTarget)) targetNode.value = previousTarget;
    fillWirePorts();
    byId("wire-list").innerHTML = spec.connections.length ? spec.connections.map((edge, index) => `<article class="wire-row"><span class="wire-channel ${escape(edge.channel)}">${escape(edge.channel)}</span><code>${escape(edge.source_mechanism)}.${escape(edge.source_port)}</code><span aria-hidden="true">→</span><code>${escape(edge.target_mechanism)}.${escape(edge.target_port)}</code><small>+${edge.latency}</small><button type="button" data-edit-wire="${index}">REWIRE</button><button type="button" data-remove-wire="${index}" aria-label="Remove wire ${index + 1}">×</button></article>`).join("") : `<p>NO DECLARED CONNECTIONS</p>`;
    document.querySelectorAll<HTMLButtonElement>("[data-edit-wire]").forEach(button => button.addEventListener("click", () => editWire(Number(button.dataset.editWire))));
    document.querySelectorAll<HTMLButtonElement>("[data-remove-wire]").forEach(button => button.addEventListener("click", () => edit(value => removeConnection(value, Number(button.dataset.removeWire)))));
  };

  byId("graph-add-node").addEventListener("click", () => { if (!spec) return; const next = addMechanism(spec, "new-mechanism"); selected = next.mechanisms.at(-1)?.mechanism_id || ""; setSpec(next); });
  byId("graph-remove-node").addEventListener("click", () => { if (selected && spec) { const next = removeMechanism(spec, selected); selected = next.mechanisms[0]?.mechanism_id || ""; setSpec(next); } });
  undo.addEventListener("click", () => { if (!spec || !past.length) return; future.push(currentText()); spec = parseEditableSystemSpec(JSON.parse(past.pop()!)); internal = true; textarea.value = serializeSystemSpec(spec); internal = false; dispatch(); render(); });
  redo.addEventListener("click", () => { if (!spec || !future.length) return; past.push(currentText()); spec = parseEditableSystemSpec(JSON.parse(future.pop()!)); internal = true; textarea.value = serializeSystemSpec(spec); internal = false; dispatch(); render(); });
  idInput.addEventListener("change", () => { if (!spec || !selected || idInput.value === selected) return; const before = selected; selected = idInput.value; setSpec(renameMechanism(spec, before, selected)); });
  family.addEventListener("change", () => edit(value => { value.mechanisms.find(node => node.mechanism_id === selected)!.family = family.value; return value; }));
  implementation.addEventListener("change", () => edit(value => { value.mechanisms.find(node => node.mechanism_id === selected)!.implementation = implementation.value; return value; }));
  phase.addEventListener("change", () => edit(value => { let row = value.schedules.find(item => item.mechanism_id === selected); if (!row) { row = { mechanism_id: selected, phase: 0, trigger: "annual" }; value.schedules.push(row); } row.phase = Number(phase.value); return value; }));
  trigger.addEventListener("change", () => edit(value => { let row = value.schedules.find(item => item.mechanism_id === selected); if (!row) { row = { mechanism_id: selected, phase: 0, trigger: "annual" }; value.schedules.push(row); } row.trigger = trigger.value; return value; }));
  parameters.addEventListener("change", () => { try { const value = JSON.parse(parameters.value); if (!value || typeof value !== "object" || Array.isArray(value)) throw new Error("Parameters must be an object"); edit(draft => { draft.mechanisms.find(node => node.mechanism_id === selected)!.parameters = value; return draft; }); } catch (error) { localCheck.className = "graph-local-check invalid"; localCheck.textContent = String(error); } });
  const addPort = (direction: "inputs" | "outputs"): void => edit(value => { const node = value.mechanisms.find(item => item.mechanism_id === selected)!; const used = new Set([...node.inputs, ...node.outputs].map(port => port.port_id)); let id = direction === "inputs" ? "input" : "output", index = 2; while (used.has(id)) id = `${direction === "inputs" ? "input" : "output"}-${index++}`; node[direction].push({ port_id: id, channel: "artifact", artifact_type: null, required: true }); return value; });
  byId("graph-add-input").addEventListener("click", () => addPort("inputs")); byId("graph-add-output").addEventListener("click", () => addPort("outputs"));
  for (const rootId of ["graph-inputs", "graph-outputs"]) byId(rootId).addEventListener("change", event => {
    const target = event.target as HTMLInputElement | HTMLSelectElement, row = target.closest<HTMLElement>("[data-direction]"); if (!row || !spec) return;
    const direction = row.dataset.direction as "inputs" | "outputs", index = Number(row.dataset.index), field = target.dataset.portField; if (!field) return;
    edit(value => { const port = value.mechanisms.find(node => node.mechanism_id === selected)![direction][index]!; if (field === "required") port.required = (target as HTMLInputElement).checked; else if (field === "artifact_type") port.artifact_type = target.value || null; else (port as unknown as Record<string, unknown>)[field] = target.value; return value; });
  });
  for (const rootId of ["graph-inputs", "graph-outputs"]) byId(rootId).addEventListener("click", event => { const button = (event.target as HTMLElement).closest<HTMLButtonElement>("[data-remove-port]"); const row = button?.closest<HTMLElement>("[data-direction]"); if (button && row && spec) edit(value => removePort(value, selected, row.dataset.direction as "inputs" | "outputs", button.dataset.removePort!)); });
  sourceNode.addEventListener("change", fillWirePorts); targetNode.addEventListener("change", fillWirePorts);
  wireCommit.addEventListener("click", () => {
    if (!spec || !sourcePort.value || !targetPort.value) return;
    const output = spec.mechanisms.find(node => node.mechanism_id === sourceNode.value)?.outputs.find(port => port.port_id === sourcePort.value);
    const edge: DesignConnection = { source_mechanism: sourceNode.value, source_port: sourcePort.value, target_mechanism: targetNode.value, target_port: targetPort.value, channel: output?.channel || "artifact", latency: Number(latency.value) };
    setSpec(setConnection(spec, editedWire, edge)); editedWire = null; wireCommit.textContent = "ADD WIRE"; wireCancel.hidden = true;
  });
  wireCancel.addEventListener("click", () => { editedWire = null; wireCommit.textContent = "ADD WIRE"; wireCancel.hidden = true; });
  textarea.addEventListener("input", sync);
  document.addEventListener("keydown", event => { if (!(event.metaKey || event.ctrlKey) || event.altKey) return; if (event.key.toLowerCase() === "z") { event.preventDefault(); (event.shiftKey ? redo : undo).click(); } else if (event.key.toLowerCase() === "y") { event.preventDefault(); redo.click(); } });
  sync();
}

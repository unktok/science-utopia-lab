# Open native actors, scientific records and action capabilities v7

This extends the **original native research world**. Institution algorithms are
authored in arbitrary sandboxed Python/LLM/process mechanisms; neither a fixed
institution catalogue nor a numeric substitute world is introduced. New actor
types/roles and scientific artifact types are data declarations. Their persistent
records and typed actions can affect real existing researchers, not merely append
an institution ledger. All verification here uses scripted researcher replies and
real Docker, not new live inference or evidence of scientific invention/benefit.

## Three distinct layers

1. A SystemSpec declares freely named `AgentTypeSpec(type, roles)` and
   `ArtifactTypeSpec(type)` entries. Receiver parameters may supply safe JSON
   schemas for actor state and artifact content. No host Python class or catalogue
   entry is needed for each new institutional actor, role or record type.
2. Sandboxed source/process nodes implement behavior, memory, communication,
   scheduling and decision algorithms, emitting explicit typed commands. Actors
   act through those processes; their behavior is not inferred from their labels.
3. A capability receiver validates the **entire** command batch, stages its
   persistent data/native effects, then commits. Its roles/grants are technical
   authority contracts, not loss terms, research-quality tests or fairness vetoes.

There is no automatic source repair, missing wire, implicit institution algorithm,
hidden choice of objective, new LLM training or generated-code host execution.

## Public graph/API contract

`utopia.system.native_open_domain` exposes:

- `IMPLEMENTATION = 'native.domain.commands.v1'`: consumes optional `commands`
  DeliveredValues and emits a `domain` snapshot when an output port is declared.
- `OBSERVER = 'native.domain.observe.v1'`: emits the current data-only `domain`
  snapshot (`native-open-domain-state-v1`), without mutating it. Original native
  world observations additionally expose `open_domain` once this extension is used.
- `add_domain_action_receiver(spec, source=..., source_port=..., capabilities=...,
  receiver=..., phase=..., latency=..., actor_schemas=..., artifact_schemas=...)`:
  explicitly grants the connected source authority. It adds no policy/source node.
  The producer's protocol name/channel can be arbitrary; the command envelope is
  checked by the actual receiver, so source-authored protocol adapters are legal.
- `apply_domain_commands(kernel, context)`: the same atomic entry point for a
  custom process invocation. `context.inputs['commands']` contains typed delivered
  values and the kernel must be executing a real native year. Direct calls do not
  circumvent its schema/ID/capability/accounting/source checks.
- `NativeActionRegistry.register(action_id, payload_schema, prepare_handler)`:
  register further trusted typed capabilities, not a finite institution menu.

One source message has exactly:

```json
{
  "schema": "native-domain-command-v1",
  "command_id": "unique-command-within-source-port-and-emitted-year",
  "actor_id": "my-new-cooperative",
  "action": "native.context",
  "payload": {
    "actor_ids": ["an-actual-native-researcher-id"],
    "content": {"any-authored-research-proposal": "..."},
    "artifact_ids": ["my-new-scientific-record"]
  }
}
```

The source must deliver real causal event IDs. IDs are explicit bounded strings;
there is no silent name normalization. Native IDs must exist. New actor IDs cannot
collide with native/custom actors. New artifact IDs cannot collide with actual
native papers, other custom records or legacy artifact-store owners. Entity
references must resolve before use; the host does not invent missing entities.

Receiver parameters explicitly contain:

```json
{
  "capabilities": {
    "bootstrap": ["actor.create"],
    "roles": {
      "a-freely-declared-role": ["actor.update", "artifact.create", "state.put", "native.context"]
    }
  },
  "actor_schemas": {"a-freely-declared-actor-type": {"type": "object"}},
  "artifact_schemas": {"a-freely-declared-record-type": {"type": "object"}}
}
```

`actor_id='$mechanism'` has only explicit bootstrap grants. All other principals
must be persistent custom actors whose data-declared roles grant the requested
action. These are broad named capabilities; more specific authority/semantics may
be implemented as another registered typed action. Type schemas are persisted with
records. A changed schema/role declaration must explicitly use a versioned type;
it does not silently reinterpret old records during migration.

## Generic primitives, not institution algorithms

| Action | Exact payload fields | Real effect |
| --- | --- | --- |
| `actor.create` | `id,type,roles,state` | Persistent actor with arbitrary schema-validated JSON state and roles. |
| `actor.update` | `id,expected_revision,roles,state` | Optimistic-revision update, not blind overwrite. |
| `artifact.create` | `id,type,owner_actor,content,actor_ids,artifact_ids,native_paper_ids` | Scientific record with validated native/custom identity links. |
| `artifact.update` | `id,expected_revision,content,actor_ids,artifact_ids,native_paper_ids` | Content/link revision preserving owner/type/history. |
| `state.put` | `key,value,expected_revision` | Arbitrary JSON memory, namespaced by its custom actor; null revision means create. |
| `native.context` | `actor_ids,content,artifact_ids` | Actual native researcher prompt inputs, including exact linked custom record content. |
| `native.project` | `assignment` | Actual native project dates/ResearchDirection/focus, using the v6 activity contract. |
| `native.transfer` | `from_actor,to_actor,amount` | Actual native author resources and accounting through the existing conserving v5 bridge. |

Create a record/actor before referring to it. An actor's state and scientific
record content are not limited to predefined fields; the design supplies its
schema. The primitive operation names describe storage/domain effects. Allocation,
assessment, discovery, organizational and communication algorithms belong entirely
to authored source. Custom records can link actual native papers and are visible
to subsequent mechanisms/researcher inputs, but do not fabricate peer-reviewed
papers or change accepted-paper counts by being called publications.

Native project updates validate real author IDs, positive declared duration and
coherent dates. To change native research assignment through this route, schedule
before its producer, or explicitly wire a matching updated typed plan afterward.
A stale downstream plan is rejected; there is no private-frame fallback.

Transfers still require distinct existing native authors, positive finite
representable amounts, sufficient funds and exact debit/credit conservation. No
new hidden allocation policy is introduced. Custom actor JSON balances do not
silently mint native resources. Additional accounting/domain laws require explicit
typed capabilities, not relabelling arbitrary data as native money/papers.

## Extending typed actions

Register trusted plugins through `NativeScienceKernel(...,
registry_extension=register_extensions)`. The kernel reconstructs its default
action registry before calling this extension on every annual runtime/migration
preview/cold worker, so registrations do not accidentally duplicate or disappear.

```python
def register_extensions(kernel, mechanism_registry):
    def prepare(tx, payload, principal):
        tx.put_state("new-memory", payload, principal=principal)
        tx.deliver_context(payload["researcher_ids"], payload["proposal"], principal=principal)
    kernel.domain_actions.register("my.typed.capability", MY_SAFE_JSON_SCHEMA, prepare)
```

`DomainTransaction` provides `deliver_context`, `set_project`, `transfer`,
`put_state`, identity checks and staged persistent records. Plugins must only
prepare/stage effects through that contract, not mutate unrelated host state.
They are developer-trusted, source-pinned simulator code; generated Python cannot
register/import host handlers or gain host object access. Arbitrary source stays
inside the existing pinned, networkless, no-host-mount Docker boundary.

## Atomicity, replay and persistence

All inputs are validated/staged before mutation. Resource transfers preflight
against shadow base-native actors/a copied ledger using the **unchanged** v5
bridge. Commit uses the real same bridge. A base-native commit failure restores
resources/activity/context/project attributes, the attached ledger in place and
the per-year resource receipt map; custom domain state is installed only on
success. No failed batch partly creates entities or delivers inputs.
Generic runtime output/event validation also runs before commit, so a malformed
trusted-plugin result or incorrect receiver output declaration cannot leave
native effects behind before the graph runner rejects its result.

Atomicity is one action batch, not the whole scientific year. Earlier independent
native phases remain effects; restore the preceding complete portable checkpoint
after a failed year. Arbitrary side effects of developer-written custom setters/
plugins outside the transaction contract cannot be promised rollback.

Producer+port+emitted year+command ID is the global replay identity across receivers
and years. Exact duplicate delivery is idempotent; a different body under the same
identity fails closed. Separate actors from one producer must still use distinct
command IDs. Receipt hash chains bind complete commands, producer event IDs,
received year and domain-content hashes. Actor/artifact creation has ordinary
typed replay declarations; native input deliveries preserve the existing
`native.system.context_delivered` event and metric meaning per real recipient.

The domain is kernel-wide, not owned by a mechanism's disposable memory. Its
optional `open_domain` checkpoint field persists actors/roles, artifact records,
custom state/type schemas and receipts even when their creating process changes.
Restore checks its content/receipt chain against actual committed events. Native
migration receipts include the prior domain snapshot **only when used**, allowing
exact historical parent-hash reconstruction. Cold bootstrap from the original
founding design verifies the whole migration/domain chain. The extension is not
omitted or silently reset on adoption/removal of a creator.

When unused, the field/observation additions are absent and legacy serialized
state/events/requests stay identical. Custom JSON fields such as `timestamp` are
preserved verbatim; the observation's operational timestamp filtering must not
silently delete user-defined scientific state.

## Evidence and boundaries

`tests/system/test_native_open_domain.py` exercises original native scientific
phases with scripted HTTP/retrieval and real Docker source execution:

- Six-year original-world scientific checkpoint state and every model request
  remain exactly equal when the extension is absent.
- A freely named cooperative actor/role and novel scientific artifact type are
  created and updated for six years, carry custom memory and native-paper links,
  and actually deliver input/change projects/conserve resources through ledger
  transactions. First-year native direction calls change4→3 because the new
  actor has assigned a real project; its actual intention prompt uses that plan.
- A disconnected source has no such effect. Delayed actor creation/input queues
  survive a cold checkpoint and affect the actual first eligible year.
- Interrupted-year/cold resume yields the same full scientific state and native
  events. Same-society migration removes the creator, receiver and data-type
  declaration, then cold bootstrap preserves existing domain state and lineage.
- Unknown IDs, missing capability, conflicting revisions, invalid schemas,
  missing real-paper links and unrepresentable/overdrawn resources are rejected
  atomically; a later real credit failure rolls back the batch.
- A newly registered typed plugin performs an unanticipated real input/custom
  memory action; malformed plugin results are rejected before native commit.
  State/receipt corruption or omission fails restoration without replacing the
  valid in-memory kernel.

Custom actors are data-defined participants executing authored processes, not
silently injected subclasses into every old native `isinstance` branch. Their
effects use explicit capabilities. Their records are scientific **artifacts**,
not automatically asserted discoveries or new native corpus documents. This
implementation closes extensible entity/action coupling; epistemic validation,
external scientific value, optimization benefit and universal world autograd are
not inferred from software QA.

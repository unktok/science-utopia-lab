# Designer-only model change: authorization and prospective implementation

## User decision

The user permits changing only the institution designer if needed. Researchers
remain Qwen3-8B. A new external service or additional spending requires prior
confirmation. This does not authorize changing a running frozen experiment,
relabelling old authoring, downloading a model, or changing shared backend
settings. V36 continues unchanged, including its finite failed slots.

## Local read-only discovery

At 2026-11-06 05:39:46 UTC, local GET /api/tags lists, among others:

- qwen3:8b, digest
  500a1f067a9f782620b40bee6f7b0c89e17ae61f686b92c24933e4ca4b2b8b41.
- qwen3.6:35b-mlx-64k, digest
  f3ddc74319e42fad1cce455555e9f6864372665bcf9f0578b600f554787cbcc8.
- qwen3.6:35b-mlx-32k, digest
  12789202659dc66361d8ca9429ae0b917cf6d2a1fc6bb044dbfe251b207b7dd2.
- qwen3.5-abliterated:35b-a3b-q6, digest
  329cacf4f070cfe92f03b641a2450c3854ab935865eeec2e08aeb33e1547f5d2.

GET /api/ps reports only Qwen3-8B loaded, context40960. Metadata /api/show for
the 32k alias reports a local safetensors/nvfp4 35.1B architecture; this is not
an inference compatibility, memory-fit, speed or scientific-quality result.
The serving listener is local ollama PID3355. No model is loaded/unloaded,
no generation is sent, and no download or backend reconfiguration is made.

## Prospective boundary

Develop separately from V37's committed-source checks. A new explicit request
and plan must bind the designer model/digest independently of the unchanged
scientist/corpus/runtime binding. Keep old v14/v15 requests fixed to Qwen3-8B;
do not broaden public endpoints or silently replace a requested designer.
Authoring, certificates, cold replay, traces and costs must identify the actual
designer, while native caches and world audits remain bound to Qwen3-8B.

Before actual use, close V36 and audit it using its original source; verify the
new software; freeze a separate source/protocol; and run fresh, exact-backend
interface controls. Existing downloaded model names are not working-provider
evidence. No future model or budget is yet launched or claimed successful.

## Implemented prospective path, not actual new-model evidence

New v38 request/controller/queue/driver retain the fixed scientist provider and
separately bind the designer provider. Legacy v14/v15 guards still reject an
unannounced stronger designer. The new class uses the unchanged loopback literal
staged transport; fresh source/backend/model-bound controls are still mandatory.
Certificates, generation journals, cold replay, traces, losses and read-only
audits distinguish actual roles. No remote endpoint/key option is introduced.

Metadata discovery also confirms Qwen3-8B's model-file parameters do not declare
a num_ctx default. Consequently a second model could evict it and cause later
scientist requests to inherit a different backend default. Preserve scientist
wire bodies: require both models loaded at40960 before launch and observe the
scientist40960 again before every world. These are read-only, recorded GETs,
not automatic preload calls or inferred context guarantees. A failed/unknown
gate cannot yield a measured scientific loss. The scheduler serializes roles
and does not switch models during a world; external backend reconfiguration
remains outside this guarantee.

Development checks so far (uncommitted source; not actual model use):

- Initial role/scheduler scope:31 pass/5.08s.
- Expanded scope:150 pass,1 test-fixture failure/201.72s. The fake server listed
  only the stronger model; asking it to validate the intentionally wrong Qwen
  certificate raised StopIteration for its missing tag rather than the expected
  ValueError. Preserve this log, SHA
  110bb2989c9adb0c1d304e2dfaced887d02c31142abbdb1f79470021fb0e94b6.
- Correct the fake inventory to contain both locally present model identities;
  do not alter production rejection or salvage a certificate. Corrected role
  suite:21 pass/25.61s, log SHA
  b560af7ed3f5875d9bb8acd3816ce5cf631157b8d8f829b1bf75c842ad347649.
- Expanded role/loaded-context suite:36 pass/24.65s. Covers raw metadata/cold
  replay, unchanged scientist delegation, missing/duplicate/wrong context,
  transport unknowns, rehashed outcome/cost/body tampering, and no auto loading.

The earlier V37 broad run at unchanged742027b ends1 failed/1398 passed/1232.44s.
Its old region-repair test's second valid SCRIPTED response encountered a Docker
cleanup timeout (`docker rm -f`,10s), then exhausted its two supplied fake
responses. Raw region receipts identify this error; it is not attributed to
the new history helper or a scientific candidate. Original JUnit SHA
9962cf221df46da3355ca75f099c27dd673208d0a1999cbbca92037a38a6b679.
Same-source isolated test passes1/9.18s, JUnit
ed4ae543ced18c47163a469df908787f698246df21fb3b8915ddd55f8beba817.
The named cleanup container is absent on read-only inspection. No Docker
timeout, production retry or test assertion is loosened. A separate full repeat
at the same742027b is running; retain both outcomes, never overwrite the first.

V36 remains frozen/live; four throughput candidates all fail actual execution
(matrix shape, impact_score, record envelope, impact_scores respectively).
This strengthens the practical reason to test a separately declared designer,
but does not prove a stronger model or the retrieval repair will solve it.

## Committed-source and successful software-path checks

At b834867349ecd3c3594129bbdd7775f131733a15,259 exact runtime/driver/helper/
protocol source blobs verify. The28 proposed calibration targets have digest
3c32606374f77ff9cbb17ef1c29da99a41f78ad76fd7568b12f4827209da9277;
removing the one own-history read leaves all27 original V36 controls exactly
equal, including literal operand values. No controls have been dispatched.

Committed-source non-Docker affected scope:164 pass/168.57s,2 real-Docker cases
deliberately deselected to avoid overlap with V37's broad repeat. JUnit SHA
48ad84d8f6f2dd69e133873d69a1a492984e2cddb6fd41a7c0c4313609059771.
The full eventual scope must include those cases; this is not a full-suite pass.

Additional test-only successful path:1 pass/6.12s, JUnit
c38fedc372ad66800fc646df149d579b417ee2d6d9ec6ed7ce3fdd82f23a21b4.
Uses actual simulator code with explicitly SCRIPTED corpus and responses, not
actual Qwen/35B inference. Two completed worlds retain scientist cache/wire
identity; the separate designer's next prompt receives the actual preceding
test loss; live response counts/cache binding/role-specific trace match.
Parent retention is explicit and no scientific invention is claimed.

Prepare outputs/native-designer-roles-v38-provider/operator-config.json by
changing only model/model_digest from the V26 operator provider. Every corpus,
dataset, horizon and image value compares exactly equal. Designer binding
digest3f27c8fc54dd715900a7a89a76843e0ec832b6a2a751b2f0beeeff30b83ed4eb;
original scientist binding
ce535a2dd3d1c3f504a82a28dd64ef2e38b507087c5cf50a4cc3dad781fd6716.
This file preparation is not a source freeze, real calibration or pilot launch.

Read-only /api/show of the exact64k alias reports num_ctx65536, temperature1,
presence_penalty1.5 and repeat_penalty1, with nvfp4/safetensors35.1B metadata.
The prospective request still explicitly sends context40960/T.6/topP.95/
topK20/minP0; do not assume the route honors those from metadata alone. The
loaded-context check must observe40960. Unspecified model defaults are bound
to the actual model digest, not asserted identical to Qwen3-8B. No generation,
loading, backend change or new external service has occurred in this preparation.

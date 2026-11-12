# Instruction-control preparation: permission stop and prospective successor

At 2026-11-12 02:12:20 UTC, continuation `native-instruction-timing-continuation-v1-a1`
stopped in `prepare` after its parent evaluation normally closed. Its literal
log reports `Operation not permitted` on GET `127.0.0.1:11434/api/version`.
This is a launcher sandbox/network-permission failure, not an HTTP response,
model failure, scientific loss, or evidence that the server was unavailable.

The original source remains `5925d5b7d77bf7f13406730420022986e3fdac1f`.
Read-only checks found no assay plan and no science-start journal at its a1
output. No control slot or scientist POST was dispatched. The original
continuation and downstream summary both retain stopped status; neither is
rewritten or resumed.

A separate a2 continuation/output is prospectively authorized under the same
three-control protocol and exact source, message, losses, seed and budgets,
using an explicitly network-capable launcher. This changes launch permissions,
not scientific treatment or response acceptance. It does not refill any failed
scientific slot. The original no-retry contract still applies within each run;
any scientific failure in a2 stops without replacement. A new launch handle and
normal closure are required before claiming execution or results. No new paid
service, model download, designer generation or source mutation is introduced.

The original summary watcher stops on a1 as designed. Any a2 summary must be
separately launched and bound to a2; it cannot adopt a1's terminal identity.

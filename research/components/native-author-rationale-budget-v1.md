# Prospective rationale budget, not output repair

The active f47270b9 staged study repeatedly rejects `write_file` solely because
the optional, non-executable `rationale` exceeds4096 characters. Those are valid
historical rejections under that frozen contract. Do not rewrite their status,
strip notes to salvage an action, refill a slot or change the active source.

This separate development branch removes only that per-rationale maxLength.
Rationale remains an optional nonempty string on ordinary tools, preserved
verbatim as untrusted annotations. Existing response token/wire/session budgets,
operative action fields/types/paths, static graph/ABI validation, explicit finish
and other schema checks remain unchanged. No generated code or world is run by
this change. Accepting a note does not make a candidate valid or improve loss.

The shared field definition drives host validation, planner/editor schemas and
function advertisements. Its changed schema/source digests explicitly bind a
new prospective contract; old exact-source audits keep the4096 limit. This is
not a different loss, new institutional authority or an unrecorded retry.

Light SCRIPTED tests cover4096/4097/16384-character notes, exact string/source
preservation, sender/host schemas, unchanged rejection of invalid operative
arguments and unknown keys, and edit/explicit-finish/cold replay without code
execution or network. They are not actual designer readiness or a full native
campaign proof. Test execution is pending at this initial implementation commit.

Keep this change off main and out of the live experiment. Before any future
designer dispatch, commit/freeze the prospective source and complete the public
outer/inner staged production/calibration/cold-audit integration under its new
binding, followed by finite actual backend readiness as required. Heavy checks
wait for the current real inference to terminate. The current search and its
selection-fixed evaluation must not be delayed or repaired by adopting this
unverified future author interface.

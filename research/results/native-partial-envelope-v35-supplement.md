# Supplemental partial-envelope diagnosis, not a rewritten experiment

V35a2 throughputG2step04 returns HTTP200/doneFalse after35.7354243749287s.
Its193-character content ends with31 whitespace characters (29 line feeds);
thinking has1837 characters, final token counts are unknown. Original step SHA
2c2208248acadb05641a9ad555bf7b5c7f70e46c0097c331a8fc4ba270b46cce.

The matching47 server-log lines5577565–5577611 are byte-copied into
outputs/diagnostics-v35-partial-envelope/server-window-5577565-5577611.log,
4312 bytes/SHA17ae10c353ab6576bc825cffa1c26242866a7d86861166c5362db7a602cb59b4.
They show cancellation with context40960/truncated0, not its initiator.

The version-tagged [completion wrapper](https://github.com/ollama/ollama/blob/v0.33.3/llm/llama_server.go#L1578)
can return nil at its repetition guard without a terminal frame. The
[non-streaming aggregator](https://github.com/ollama/ollama/blob/v0.33.3/server/routes.go#L2233)
can consequently return200/doneFalse. A local stdlib-only Go mechanism probe
reproduces that path, with normal-final and already-cancelled-context controls;
zero model calls/backend requests/configuration changes. This is not replay of
the installed server or proof of the historical event's actual branch.

Probe source SHAcd31d5cd919c4554dc512638d530eb704a4f408e73719ab1b39f236f020fb6e1;
result SHA326ebeddaa98a5a5e90a6d9f0d4b6d904d0b3fe85bf178c39c387f5c5f138895,
under outputs/diagnostics-v35-partial-envelope. Installed build reportsv0.33.3+dirty,
revisionb79067b0db7417f20108363bc22adb97f35c966a/vcs.modified=true. The binary
contains the guard diagnostic string, but the retained log has no matching
debug message; exact installed-source equivalence/per-token SSE is unavailable.

Thus this is a concrete consistent hypothesis, not a proven universal cause.
V36 efficiencyG3step6 has no trailing whitespace and remains a separate unknown.
The strict client correctly rejects incomplete envelopes. No shared backend is
modified, no raw response is salvaged, and original costs/audits stay unchanged.

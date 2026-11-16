# Full original native document regression data

These three files are exact SystemSpec values from the frozen705b5259 study,
serialized canonically with a trailing newline. They are not raw model/cache
responses and are never executed by the boundary tests. Original raw evidence
and its formatting/timestamps remain unchanged. Canonical value equality and
file hashes are checked in the [retained manifest](../../../research/results/native-author-workflow-visibility-correction-v1.json).

The zero/terminal parents come from their original reference observations;
after-feature-write comes from the actual free/history1/U/g0 world system.
Compact/spaced sizes are61892/65479,62755/66342 and62032/65619 UTF-8 bytes.
The difference matters: V45 really includes all three compact documents, while
the old inherited spaced-byte rule disabled checkpoints for the latter two.

Tests cover all three without an optional local-cache dependency. Docker/code
execution is forbidden. Scripted generator/wire/replay cases preserve the real
document/image identifiers; they are not real Qwen or native-world evidence.

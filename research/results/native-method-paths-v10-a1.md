# Native method paths v10 independent audit

- Status: `complete`
- Source: `5ea52a520d7fcfbfeec7fb450ce8122c804cfe4a`
- Content SHA-256: `b6e221170c36250d60a199c55d34e550f65c6e0d1a87bce18300d1b530aef5b6`
- Fresh/logical/replayed responses: 186 / 504 / 318

| arm | step | theta | native loss |
|---|---:|---:|---:|
| gradient | 0 | 0.6 | 0.9 |
| blackbox | 0 | 0.65 | 0.9 |
| gradient | 1 | 0.648809131 | 0.816666667 |
| blackbox | 1 | 0.725 | 0.816666667 |
| gradient | 2 | 0.748809131 | 0.816666667 |
| blackbox | 2 | 0.7625 | 0.816666667 |

Both methods are charged the same three shared historical observations and three fresh native attempts.
This is one common-prefix-coupled development path, not held-out evidence, independent replication, optimizer superiority or optimality.

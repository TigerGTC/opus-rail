| task | arm | pass | wall s | cost $ | out tok | fresh-in tok | turns | dispatches | main edits | rails | model ok |
|---|---|---|---|---|---|---|---|---|---|---|---|
| config-bughunt | baseline | PASS | 68.6 | 0.48 | 3627 | 22682 | 14 | - | 3 | no | ok |
| config-bughunt | rail | PASS | 90.8 | 0.55 | 5193 | 24569 | 14 | - | 3 | yes | ok |
| config-bughunt | rail-plus | PASS | 80.3 | 0.51 | 4743 | 23838 | 12 | - | 3 | yes | ok |
| kv-ttl-store | baseline | PASS | 48.7 | 0.42 | 3119 | 21523 | 10 | - | 2 | no | ok |
| kv-ttl-store | rail | PASS | 157.4 | 0.76 | 6112 | 24973 | 10 | executor(2210) | 0 | yes | ok |
| kv-ttl-store | rail-plus | FAIL | 637.3 | 0.31 | 2073 | 21426 | 3 | redteam(1083) | 0 | yes | ok |
| log-triage | baseline | PASS | 54.1 | 0.42 | 3464 | 22239 | 11 | - | 2 | no | ok |
| log-triage | rail | PASS | 59.9 | 0.43 | 3682 | 22078 | 10 | - | 2 | yes | ok |
| log-triage | rail-plus | PASS | 56.6 | 0.40 | 3165 | 22256 | 9 | - | 1 | yes | ok |

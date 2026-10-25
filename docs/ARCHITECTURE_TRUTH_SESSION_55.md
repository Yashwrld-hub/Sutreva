# Architecture Truth — Session 55

## Live vs. scaffold status

Session 55 closes a set of discrepancies where tested modules looked production-ready but were not connected to the runtime path.

| Component | Session 54 | Session 55 |
|---|---|---|
| `units.py` | Tested helper; conversion not in audit comparison | Live in `compare_against_schema()` for numeric fields and inline/evidence units |
| `normalize_numeric_value()` | Dead production helper | Reused by the live normalization contract |
| `extraction_contract.py` | Test-only scaffolding | Live audit-boundary records attached to comparison rows |
| `conflict_detection.py` | Test-only scaffolding | Live model-vs-deterministic conflict gate; conflicting fields become `NEEDS_REVIEW` |
| `governance.py` | Test-only primitives | Live reviewer disposition events recorded from Review Queue |

## Unit policy

Numeric values are normalized to the template target unit before max/min/expected comparisons. Explicit units embedded in a value take precedence. If the evidence line contains exactly one compatible numeric/unit pair, that source value can provide the normalized comparison value. Gauge/absolute pressure conversions require explicit ambient pressure context and are never guessed.

## Architectural boundary

`core.py` remains the authoritative comparison engine. AI remains advisory; source evidence, deterministic overrides, configured rules, and human review retain authority.


## Validation

- **207 tests collected and passing** after the Session 55 integration tests.
- Deployment sanity check passes.
- Offline Nebius preflight passes.
- Hackathon demo rehearsal passes with 2 intentional exceptions, 5 evidence references, 2 review findings, and a passing evaluation gate.
- No live provider call is made by the offline rehearsal.

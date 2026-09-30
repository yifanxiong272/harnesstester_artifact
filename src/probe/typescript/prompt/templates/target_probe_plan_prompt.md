# Target Probe Plan

Plan append-only Vitest probes using only the provided target-revision packet.
The selected units are analysis targets, not necessarily legal test
entrypoints. Select an `entrypoint_id` from `public_target_routes`; exercise that
public symbol and never import or call a private target directly.

Do not use or infer from issue or review text, commits, diffs, changed hunks,
comparison source or execution, benchmark labels, or official regression tests.

$strategy_guidance

## Reasoning Contract

For each boundary, choose a legal public route, state one focused test intent,
and derive an oracle independently of the current target implementation. The
oracle may disagree with current target behavior. Ground it in a prompt-visible
public contract or a stable semantic property valid under the stated
activation conditions. Target code establishes reachability and a failure
hypothesis; it does not define expected behavior.

$context_request_instruction

Return exactly one JSON object:

```json
{
  "boundary_plan": [
    {
      "boundary_id": "boundary-001",
      "target_unit_ids": ["unit-id-from-packet"],
      "route": {
        "entrypoint_id": "entrypoint-id-from-packet"
      },
      "probe": {
        "test_intent": "one focused behavior and input boundary",
        "activation_conditions": ["..."]
      },
      "invariant": {
        "independent_oracle": "...",
        "supporting_evidence": "prompt-visible contract or stable semantic basis",
        "expected_observation": "...",
        "oracle_mode": "assertion|exception|crash"
      },
      "oracle_family": "specific semantic property shared by equivalent tests",
      "novelty_from_prior": "closest family-id: difference in expected public behavior; or none: first attempt",
      "bug_hypothesis": "..."
    }
  ],
  "context_requests": [],
  "exhausted_reason": ""
}
```

## Target-Revision Packet

```json
$packet_json
```

## Prior Attempts

These records exist only to prevent semantic repetition. They contain no comparison
feedback. Name each `oracle_family` after the concrete semantic property being
asserted, not a generic category. When records exist, begin
`novelty_from_prior` with the closest listed `family_id` and compare expected
public behaviors.

Stronger or additional assertions, different literals or input boundaries,
mocks, wrappers, or equivalent routes remain the same family when they assert
the same property. Apply the same rule across boundaries in this plan. Prefer a
materially different invariant or observable behavior. Retry a family only
when its prior `target_outcomes` show that setup or infrastructure prevented
execution; target pass and target failure outcomes already prove
reachability. If no new family remains, return an empty plan and
`exhausted_reason` rather than weaken the oracle.

```json
$prior_attempts_json
```

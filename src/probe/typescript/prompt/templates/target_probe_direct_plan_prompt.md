# Direct Target Probe Plan

Plan a minimal-harness Vitest probe using only the provided target-revision
packet. The selected unit is an analysis target. Select a legal
`entrypoint_id` from `public_target_routes`; exercise that public symbol and
never import a private target.

Do not use or infer from issue or review text, commits, diffs, changed hunks,
comparison source or execution, benchmark labels, or official regression tests.

$strategy_guidance

Construct a compact chain: public route, one focused test intent with activation
conditions, an independently justified oracle, and a target-revision violation
hypothesis. The oracle may conflict with the current implementation. Current
code establishes reachability and the hypothesis; it does not define expected
behavior.

$context_request_instruction Return exactly one JSON object:

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

Name each `oracle_family` after the concrete semantic property being asserted,
not a generic category. When records exist, begin `novelty_from_prior` with the
closest listed `family_id` and compare expected public behaviors.

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

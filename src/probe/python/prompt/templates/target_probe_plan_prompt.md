# Target Probe Plan

Plan deterministic pytest probes for a target Python revision. Target units are
already selected. Use only the target-revision packet and prior-attempt summaries.
Do not use or infer issue/PR text, commit messages, diffs, comparison source,
benchmark labels, official triggering tests, validation feedback, live model
behavior, credentials, network behavior, or external services.

$strategy_guidance

## Requirements

- The primary task is to generate tests that can reveal a real bug.
- Select an `entrypoint_id` listed for each target in `public_target_routes`.
- State one focused `test_intent`, its non-empty `activation_conditions`, and
  one independently justified public invariant.
- The current target output is reachability evidence, not an oracle.
- Ground `supporting_evidence` in prompt-visible code, public tests/contracts,
  or stable language/API semantics. Do not guess a contract from a name.
- Prefer public return values, state, payloads, stable exceptions, or crashes
  over private implementation details.
- Use `assertion`, `exception`, or `crash` as `oracle_mode`.
- Keep each `oracle_family` to one semantic property. Do not repeat a prior
  family merely with different literals, mocks, or stronger assertions.
- Retry a prior family only when its target outcomes show that setup or
  infrastructure prevented execution; a pass or target-reaching failure means
  the family has already been exercised.
$context_request_instruction
- If no defensible untried family remains, return an empty plan with a concrete
  `exhausted_reason`.

Return exactly one JSON object:

```json
{
  "boundary_plan": [
    {
      "boundary_id": "boundary-001",
      "target_unit_ids": ["unit-id-from-packet"],
      "route": {"entrypoint_id": "entrypoint-id-from-packet"},
      "probe": {
        "test_intent": "one focused bug-revealing behavioral question",
        "activation_conditions": ["condition needed to reach the behavior"]
      },
      "invariant": {
        "independent_oracle": "public contract or stable semantic invariant",
        "supporting_evidence": "short prompt-visible evidence",
        "expected_observation": "one externally observable result",
        "oracle_mode": "assertion|exception|crash"
      },
      "oracle_family": "semantic property shared by equivalent tests",
      "novelty_from_prior": "closest family-id and behavioral difference, or none",
      "bug_hypothesis": "why the target code may violate the invariant"
    }
  ],
  "context_requests": $context_request_example,
  "exhausted_reason": ""
}
```

## Target Packet

```json
$packet_json
```

## Prior Attempts

These summaries are diversity evidence only and contain no comparison-revision result.

```json
$prior_attempts_json
```

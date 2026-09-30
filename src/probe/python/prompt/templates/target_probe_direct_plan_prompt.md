# Direct Target Probe Plan

Plan an immediately implementable deterministic pytest probe for a target
Python revision. Target units are already selected. Use only the target-revision
packet and prior-attempt summaries. Do not use or infer issue/PR text, commit
messages, diffs, comparison source, benchmark labels, official triggering tests,
validation feedback, live model behavior, credentials, network behavior, or
external services.

$strategy_guidance

## Requirements

- Keep the bug-reveal objective primary.
- Select an `entrypoint_id` listed in `public_target_routes`.
- Prefer a direct public return, state, payload, stable exception, or crash
  invariant that can be implemented from the supplied packet.
- State one `test_intent`, non-empty `activation_conditions`, and one
  independently justified invariant. Current target output is not an oracle.
- Keep each `oracle_family` to one semantic property and avoid prior families
  that differ only in literal, mock, wrapper, or assertion strength.
- Retry a prior family only when its target outcomes show that setup or
  infrastructure prevented execution; a pass or target-reaching failure means
  the family has already been exercised.
$context_request_instruction
- If no defensible plan remains, return an empty plan and `exhausted_reason`.

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
  "context_requests": [],
  "exhausted_reason": ""
}
```

## Target Packet

```json
$packet_json
```

## Prior Attempts

```json
$prior_attempts_json
```

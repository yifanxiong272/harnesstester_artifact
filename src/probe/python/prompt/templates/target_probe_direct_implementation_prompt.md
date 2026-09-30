# Direct Target Probe Implementation

Implement immediately runnable append-only pytest assets from the canonical
plan. Use only the target-revision packet, plan, existing/retrieved test context,
and prior-attempt summaries. Do not use or infer issue/PR text, commit
messages, diffs, comparison source, benchmark labels, official triggering tests,
validation feedback, live model behavior, credentials, network behavior, or
external services.

$strategy_guidance

## Requirements

- Keep the bug-reveal objective primary.
- Return at most $max_assets assets and at most one per planned oracle family.
- Reference one `boundary_id`; the framework supplies all canonical intent and
  oracle metadata from the plan.
- When `focus_target_unit_id` is present, each asset must exercise that focused
  unit.
- Place each `.py` file under a listed `generated_test_roots` path.
- Use exactly one top-level `test_...` function and one primary behavioral
  oracle.
- Import and exercise only the selected entrypoint declared in
  `public_target_routes`; a target unit name is not permission to import a
  private symbol. Use deterministic direct construction or narrowly scoped
  mocks.
- Keep target behavior real. Do not use live model/network calls, credentials,
  external services, unbounded timing, process-state inspection, or host side
  effects.
- Do not convert internal errors into the expected oracle unless the plan
  establishes that exact public contract.
- Use prior attempts to avoid repeating an equivalent semantic oracle family.

Return exactly one JSON object:

```json
{
  "assets": [
    {
      "asset_id": "short-stable-id",
      "boundary_id": "boundary-001",
      "input_construction": "deterministic inputs, fixtures, and mocks",
      "observable_oracle": "externally observable assertion",
      "primary_oracle": "the one oracle this test stands or falls on",
      "test_file": "$generated_test_file_example",
      "append_code": "def test_probe_001(...):\\n    ...\\n",
      "mocking_plan": "optional concise setup explanation"
    }
  ]
}
```

## Boundary Plan

```json
$plan_json
```

## Prior Attempts

```json
$prior_attempts_json
```

## Target Packet

```json
$packet_json
```

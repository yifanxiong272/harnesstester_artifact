# Target Probe Harness Repair

The original pytest asset produced a structured non-assertion failure on the
target revision. Decide whether the trace is target behavior or a repairable
test-harness problem.

Use only the target-revision packet, canonical plan, original asset, target summary,
traceback context, and requested repair context. Never use comparison-revision evidence.
The missing context has now been resolved. Return a direct repair or retain the
original; do not request more context.

## Requirements

- If the failure plausibly is the intended target behavior, or no justified
  repair exists, return `{"assets": []}`; the original remains retained.
- Preserve the plan boundary, public entrypoint, behavioral question,
  activation conditions, independent oracle, and primary oracle.
- The repaired candidate need not pass on the target revision, but it must continue to test
  the same public behavior. Never import or call a private target directly.
- You may rebuild deterministic test setup. Repair only imports, fixtures,
  constructor/setup details, payload construction, sync/async invocation, and
  collaborator mocks.
- Never replace target project modules with stubs; keep target behavior real.
- Do not weaken the oracle, assert the harness error as expected, use live
  services, inspect process state, or add host side effects.

Return exactly one JSON object using the compact implementation schema:

```json
{
  "assets": [
    {
      "asset_id": "short-stable-id",
      "boundary_id": "boundary-001",
      "input_construction": "repaired deterministic setup",
      "observable_oracle": "same observable oracle",
      "primary_oracle": "same primary oracle",
      "test_file": "$generated_test_file_example",
      "append_code": "def test_probe_001(...):\\n    ...\\n",
      "mocking_plan": "what setup changed and why"
    }
  ]
}
```

## Target Packet
```json
$packet_json
```
## Boundary Plan
```json
$plan_json
```
## Original Asset
```json
$asset_json
```
## Target Validation Summary
```json
$buggy_summary_json
```
## Traceback Context
```json
$traceback_context_json
```
## Repair Context
```json
$repair_context_json
```

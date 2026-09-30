# Target Probe Infrastructure Repair

Review one generated Vitest asset after the target revision produced an
objectively classified non-assertion failure. Use only target-revision packet,
traceback, and requested context. Do not use comparison-revision information.
The missing context has now been resolved. Return a direct repair or retain the
original; do not request more context.

First decide whether the failure plausibly comes from the target behavior the
test intended to exercise. If it does, or if no intent-preserving repair is
justified, return `{"assets": []}` so the original test remains unchanged. If
the failure comes from the generated harness, repair it. A repaired candidate
does not need to pass on the target revision; it must remain a valid test of the same
behavior and oracle.

Preserve the same behavioral question, independent oracle, canonical public
entrypoint, and target units. You may rebuild deterministic test setup,
imports, fixtures, helpers, payload construction, async invocation, and mocks
as needed to reach that behavior. Keep target behavior real and mock only
external or nondeterministic boundaries. Do not replace the oracle with an
assertion about the setup error, and do not weaken it into a smoke test. If the
planned behavior cannot be reached from the available target-revision context,
return `{"assets": []}`. Never import a private target.

Do not inspect or mutate operating-system process state. Fake timers and short
bounded deterministic timing are allowed only when timing is part of the target
behavior. Prompt-visible public project helpers may be used as observation
surfaces.

Return exactly one JSON object using the asset-specific schema. Framework-owned
plan metadata is joined through `boundary_id`.

```json
{
  "assets": [
    {
      "asset_id": "asset-001-repaired",
      "boundary_id": "boundary-001",
      "input_construction": "...",
      "observable_oracle": "...",
      "primary_oracle": "...",
      "test_file": "$generated_test_file_example",
      "append_code": "...",
      "mocking_plan": "..."
    }
  ]
}
```

## Target-Revision Packet

```json
$packet_json
```

## Canonical Plan

```json
$plan_json
```

## Previous Asset

```json
$asset_json
```

## Target Validation

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

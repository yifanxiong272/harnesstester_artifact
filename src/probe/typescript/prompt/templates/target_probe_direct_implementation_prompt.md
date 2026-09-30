# Direct Target Probe Implementation

Implement minimal-harness append-only Vitest assets for the canonical
target-revision plan. Exercise the selected public entrypoint; never import a
private target. Preserve the planned test intent, activation conditions,
independent oracle, and observation.

Do not use or infer from issue or review text, commits, diffs, changed hunks,
comparison source or execution, benchmark labels, official regression tests,
network services, credentials, or validation feedback.

$strategy_guidance

Return up to $max_assets independent assets. For every asset:

- Define exactly one `it(...)` or `test(...)` call directly at module top
  level. Do not use `describe(...)`, `suite(...)`, or any other test wrapper.
- Use exactly one `expect(...)` call in total for assertion or exception mode,
  and no `expect(...)` for crash mode.
- Import and exercise only the selected entrypoint declared in
  `public_target_routes`; a target unit name is not permission to import a
  private symbol.
- Use only deterministic setup.
- Implement at most one asset per planned oracle family.
- Do not inspect or mutate operating-system process state. Fake timers and
  short bounded deterministic timing are allowed only when timing is part of
  the target behavior. Prompt-visible public project helpers may be used as
  observation surfaces.

The framework joins all plan-owned metadata through `boundary_id`.

Return exactly one JSON object:

```json
{
  "assets": [
    {
      "asset_id": "asset-001",
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

## Canonical Plan

```json
$plan_json
```

## Prior Attempts

```json
$prior_attempts_json
```

## Target-Revision Packet

```json
$packet_json
```

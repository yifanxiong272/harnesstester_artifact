# Target Probe Implementation

Implement append-only Vitest assets for the canonical target-revision plan. Use the
selected public entrypoint and preserve the plan's test intent, activation
conditions, independent oracle, and expected observation. Do not import a
private target.

Do not use or infer from issue or review text, commits, diffs, changed hunks,
comparison source or execution, benchmark labels, official regression tests,
network services, credentials, or prior validation feedback.

$strategy_guidance

## Requirements

- Return up to $max_assets independent assets.
- Implement at most one asset per planned oracle family.
- Reference one canonical `boundary_id`; the framework supplies all plan-owned
  metadata from that ID.
- Put each self-contained file under a configured `generated_test_roots` path.
- Define exactly one `it(...)` or `test(...)` call directly at module top
  level. Do not use `describe(...)`, `suite(...)`, or any other test wrapper.
- Use exactly one primary `expect(...)` for assertion or exception mode, and no
  `expect(...)` for crash mode.
- Import and exercise only the selected entrypoint declared in
  `public_target_routes`; a target unit name is not permission to import a
  private symbol. Use deterministic inputs and bounded mocks. Keep target
  behavior real.
- Do not inspect source, Git state, revisions, or the filesystem outside the
  test workspace. Do not inspect or mutate operating-system process state.
- Fake timers and short bounded deterministic timing are allowed only when
  timing is part of the target behavior. Prompt-visible public project APIs,
  test helpers, or session registries may be used as observation surfaces.
- Do not repeat a prior semantic attempt.

Return exactly one JSON object. Do not repeat target IDs or plan metadata:

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

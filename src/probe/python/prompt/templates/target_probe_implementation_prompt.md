# Target Probe Implementation

Implement append-only pytest assets for the supplied canonical boundary plan.
Use only the target-revision packet, plan, retrieved context, existing tests, and
prior-attempt summaries. Do not use or infer issue/PR text, commit messages,
diffs, comparison source, benchmark labels, official triggering tests, validation
feedback, live model behavior, credentials, network behavior, or external
services.

$strategy_guidance

## Requirements

- The primary task is to produce tests capable of revealing a real bug.
- Return at most $max_assets assets and at most one per planned oracle family.
- Reference one plan `boundary_id`; the framework supplies its target units,
  public entrypoint, activation conditions, invariant, and oracle mode.
- When `focus_target_unit_id` is present, each asset must exercise that focused
  unit. A `whole_target_pass` may use any supplied sibling boundary.
- Put each `.py` file under a listed `generated_test_roots` path.
- Use exactly one top-level `test_...` function plus local helpers for that
  test. Keep one primary behavioral oracle.
- Split independent behavioral claims into separate assets.
- Express the planned invariant as a conservative public assertion.
- Import and exercise only the selected entrypoint declared in
  `public_target_routes`; a target unit name is not permission to import a
  private symbol.
- Use deterministic setup. Mock only external or nondeterministic
  collaborators while keeping target behavior real.
- Do not use live model/network calls, credentials, external services,
  unbounded timing, process-state inspection, or host side effects.
- Do not assert raw internal errors as desired behavior unless the canonical
  invariant establishes that exact public behavior.
- Existing/retrieved context may support setup and public contracts but does
  not authorize copying current target behavior into the oracle.
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

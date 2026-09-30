# Target Probe Harness Repair Decision

The generated pytest asset produced a structured non-assertion failure on the
target revision. Diagnose its root cause from the failure evidence and exact
project frames, then choose the smallest justified action: repair directly,
request exact missing context, or retain the original when the failure plausibly
is target behavior or no sound harness repair exists.

Do not change the boundary or oracle intent. Do not ask for issue reports, PR
text, commit messages, source diffs, changed hunks, comparison source, official
tests, live model behavior, network behavior, credentials, or external
services.

Request context only when it would resolve a concrete harness or collaborator
uncertainty visible in the failure. Requests are exact only: project-relative
`filepath`, and exact AST `qualname` except for `module_context`. If the failure
already looks like target behavior, retain the original. If existing evidence is
sufficient, repair directly without requesting context.
For mock-object failures, request context only for the collaborator shape or
target-visible helper needed to provide missing attributes or methods.

Return exactly one JSON object and no surrounding explanation.

Direct repair:

```json
{
  "action": "repair",
  "diagnosis": "evidence-based root cause",
  "assets": [
    {
      "asset_id": "short-stable-id",
      "boundary_id": "boundary-001",
      "input_construction": "repaired deterministic setup",
      "observable_oracle": "same observable oracle",
      "primary_oracle": "same primary oracle",
      "test_file": "$generated_test_file_example",
      "append_code": "def test_probe_001(...):\n    ...\n",
      "mocking_plan": "what setup changed and why"
    }
  ]
}
```

$context_request_section

Or retain the original:

```json
{
  "action": "retain_original",
  "diagnosis": "why the observed failure should not be repaired as harness setup"
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

## Previous Asset

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

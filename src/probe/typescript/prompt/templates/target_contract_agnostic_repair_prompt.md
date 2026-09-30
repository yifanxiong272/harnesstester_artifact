# Target Probe Execution Repair

The generated test encountered a non-assertion failure on the target revision.
Use the original packet, plan, test, and execution output below to decide whether
the test setup needs correction. Make the smallest justified test-only repair.
Additional source retrieval is unavailable.

Preserve the public entrypoint, activation conditions, behavioral question,
independent invariant, and primary oracle. The repaired test need not pass on
the target revision. Do not weaken assertions, replace the target with a stub,
or treat a setup error as expected behavior. Keep execution deterministic and
respect the packet's safety constraints.

If the failure could be the intended target behavior or the evidence does not
support a repair, retain the original. Never use fixing patches, comparison
source or execution outcomes, issue/PR text, or other hidden defect evidence.

Return exactly one JSON object. To repair:

```json
{
  "action": "repair",
  "diagnosis": "correction supported by the execution evidence",
  "assets": [{
    "asset_id": "short-stable-id",
    "boundary_id": "boundary-001",
    "input_construction": "corrected deterministic setup",
    "observable_oracle": "same observable oracle",
    "primary_oracle": "same primary oracle",
    "test_file": "$generated_test_file_example",
    "append_code": "import { expect, test } from 'vitest';\ntest('probe', () => { /* ... */ });\n"
  }]
}
```

To retain: `{"action": "retain_original", "diagnosis": "reason"}`.

## Original Packet
```json
$packet_json
```
## Canonical Plan
```json
$plan_json
```
## Original Test
```json
$asset_json
```
## Target Execution Output
```json
$buggy_summary_json
```

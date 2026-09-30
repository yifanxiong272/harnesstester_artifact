# Revealing Probe Minimization

Minimize a stable failing asset using only the target-revision packet, frozen
asset, and target failure record. Comparison-revision information is hidden.

Only delete existing statements while preserving their order. Do not add or
rewrite imports, mocks, helpers, inputs, target calls, or the primary oracle.
The result must keep one top-level test and the same public entrypoint.

Return exactly one JSON object. Repeat the descriptive fields and test path
exactly; framework-owned metadata is joined through `boundary_id`.

```json
{
  "assets": [
    {
      "asset_id": "asset-001-minimized",
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

## Original Asset

```json
$asset_json
```

## Target Validation

```json
$buggy_summary_json
```

$retry_context_section

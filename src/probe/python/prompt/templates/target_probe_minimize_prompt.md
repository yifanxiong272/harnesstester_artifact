# Revealing Probe Minimization

Minimize a stable failing pytest asset using only the target-revision packet,
frozen asset, and target failure record. Comparison-revision information is hidden.

Delete existing statements only and preserve order. Do not add or rewrite
imports, decorators, fixtures, mocks, helpers, inputs, target calls, or the
primary oracle. Repeat the compact asset fields exactly; only `asset_id` and
`append_code` may differ. If no deletion is safe, return the original code.

Return exactly one JSON object:

```json
{
  "assets": [
    {
      "asset_id": "short-stable-id",
      "boundary_id": "boundary-001",
      "input_construction": "unchanged",
      "observable_oracle": "unchanged",
      "primary_oracle": "unchanged",
      "test_file": "$generated_test_file_example",
      "append_code": "def test_probe_001(...):\\n    ...\\n",
      "mocking_plan": "unchanged"
    }
  ]
}
```

## Target Packet
```json
$packet_json
```
## Original Asset
```json
$asset_json
```
## Target Validation Summary
```json
$buggy_summary_json
```
$retry_context_section

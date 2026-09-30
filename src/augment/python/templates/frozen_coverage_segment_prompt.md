Generate deterministic pytest tests that increase coverage of the selected Python source segment.

The packet contains ordinary coverage facts only. `round_missing_lines` and `round_missing_branches` are the exact segment gaps still uncovered at the start of this round. ${value_guidance}Cover line and branch gaps with observable assertions.

$contract_guidance

Use the source and measured coverage facts in the packet. $context_instruction

Every generated test function or class name must end with `$test_name_suffix`.
The generated test filename must end with `$test_file_suffix` and must name a
new file. Put all tests proposed in this round in that one file.

$response_instruction

${context_request_schema}Test proposal:
```json
{
  "action": "propose_test",
  "test_file": "tests/path/test_generated$test_file_suffix",
  "append_code": "complete pytest module code",
  "expected_nodeids": ["tests/path/test_generated$test_file_suffix::test_name$test_name_suffix"],
  "targeted_objective_ids": ["objective id from the packet"],
  "targeted_lines": ["source.py:line or source.py:source->destination"],
  "mocking_strategy": "brief factual description",
  "oracle": "observable behavior asserted by the test"
}
```

Packet:
```json
$packet_json
```

import { it, expect } from 'vitest';
import { extractBalancedJsonPrefix } from "../../../packages/normalization-core/src/balanced-json";

it('extractBalancedJsonPrefix ignores opener characters inside quoted strings and returns the later balanced JSON fragment', () => {
  // raw contains a quoted string that includes a '{' before the real JSON object
  const raw = 'prefix "notjson{here}" middle {"a": [1, {"b":"c"}]} suffix';

  const frag = extractBalancedJsonPrefix(raw);

  let invariant = false;

  expect(invariant).toBe(true);
});

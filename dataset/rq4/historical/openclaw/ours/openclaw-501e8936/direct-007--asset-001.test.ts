import { test, expect } from "vitest";
import { buildFtsQuery } from "../../memory/hybrid";

// Single top-level test; exactly one expect call below.
test("buildFtsQuery preserves contiguous Unicode letters and AND-joins tokens", () => {
  // Activation inputs
  const unicodeOnly = "mañana";
  const mixed = "hello mañana";

  const outUnicode = buildFtsQuery(unicodeOnly);
  const outMixed = buildFtsQuery(mixed);

  // Single composite assertion asserting both independent oracle expectations.
  expect(`${outUnicode}|||${outMixed}`).toBe('"mañana"|||"hello" AND "mañana"');
});

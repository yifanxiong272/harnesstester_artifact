import { test, expect } from "vitest";
import { findCodeRegions } from "../../shared/text/code-regions";

// Single top-level test exercising the public entrypoint findCodeRegions
test("findCodeRegions does not report mismatched backtick-run inline span (```a``)", () => {
  const text = "before ```a`` after"; // opening run of 3 backticks, closing run of 2, single line
  const regions = findCodeRegions(text);
  const slices = regions.map((r) => text.slice(r.start, r.end));

  // Independent CommonMark-like oracle: opening and closing backtick runs must match in length.
  // Assert that the mismatched candidate is not reported as a discovered slice.
  expect(slices).not.toContain('```a``');
});

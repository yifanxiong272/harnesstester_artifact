import { it, expect } from "vitest";
import { findCodeRegions } from "../../shared/text/code-regions";

it("does not report a mismatched-run inline code span (opening 3 backticks, closing 2)", () => {
  const text = "before ```a`` after";
  const regions = findCodeRegions(text);
  const slices = regions.map((r) => text.slice(r.start, r.end));

  // Primary oracle: mismatched backtick runs must not be reported as an inline code region.
  expect(slices).not.toContain('```a``');
});

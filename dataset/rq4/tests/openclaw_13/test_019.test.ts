import { test, expect } from "vitest";
import { findCodeRegions } from "../../shared/text/code-regions";

test("findCodeRegions recognizes an inline code span using two backticks to include a single backtick (`` ` ``)", () => {
  const text = "before `` ` `` after";
  const regions = findCodeRegions(text);
  const slices = regions.map((r) => text.slice(r.start, r.end));
  expect(slices).toContain("`` ` ``");
});

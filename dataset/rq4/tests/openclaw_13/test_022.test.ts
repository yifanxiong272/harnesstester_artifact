import { it, expect } from "vitest";
import { findCodeRegions } from "../../shared/text/code-regions";

const text = "before `` `code` `` after";

it("recognizes an inline code span delimited by two backticks even when the interior contains single backticks", () => {
  const regions = findCodeRegions(text);
  const slices = regions.map((r) => text.slice(r.start, r.end));
  expect(slices).toContain("`` `code` ``");
});

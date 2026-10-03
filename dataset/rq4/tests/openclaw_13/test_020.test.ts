import { it, expect } from "vitest";
import { findCodeRegions } from "../../shared/text/code-regions";

it("does not treat a 3-backtick opener closed by 2 backticks on the same line as an inline code region", () => {
  const text = "before ```a`` after";
  const regions = findCodeRegions(text);
  const slices = regions.map((r) => text.slice(r.start, r.end));
  expect(slices).not.toContain("```a``");
});

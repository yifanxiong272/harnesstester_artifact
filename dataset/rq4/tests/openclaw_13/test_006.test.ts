import { it, expect } from "vitest";
import { findCodeRegions } from "../../shared/text/code-regions";

it("does not report an inline region when opening and closing backtick runs differ on one line", () => {
  const text = "before ```a`` after";
  const regions = findCodeRegions(text);
  const slices = regions.map((r) => text.slice(r.start, r.end));
  expect(slices).not.toContain("```a``");
});

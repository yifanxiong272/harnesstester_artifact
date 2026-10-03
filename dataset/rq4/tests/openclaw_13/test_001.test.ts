import { test, expect } from "vitest";
import { findCodeRegions } from "../../shared/text/code-regions";

test("does not report inline region when opening and closing backtick runs differ in length", () => {
  const text = "before ```a`` after";
  const regions = findCodeRegions(text);
  const slices = regions.map((r) => text.slice(r.start, r.end));
  expect(slices).not.toContain("```a``");
});

import { it, expect } from "vitest";
import { findCodeRegions } from "../../shared/text/code-regions";

it("does not recognize an inline code span when opening and closing backtick counts differ", () => {
  const text = "before ``code` after";
  const regions = findCodeRegions(text);
  const slices = regions.map((r) => text.slice(r.start, r.end));

  // Primary oracle: mismatched backtick counts (`` ... `) must not be reported as a code region
  expect(slices).not.toContain("``code`");
});

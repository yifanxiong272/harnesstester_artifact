import { test, expect } from "vitest";
import { findCodeRegions } from "../../shared/text/code-regions";

// Single top-level test exercising the public entrypoint. The input keeps the candidate
// on one line so it cannot be a fenced block: opening run of 3 backticks, closing run of 2.
const text = "before ```a`` after";

test("findCodeRegions must NOT report inline code for mismatched-count backtick runs", () => {
  const regions = findCodeRegions(text);
  const slices = regions.map((r) => text.slice(r.start, r.end));
  // Single primary assertion: the mismatched candidate must not be reported as a region.
  expect(slices).not.toContain("```a``");
});

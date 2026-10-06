import { it, expect } from "vitest";
import { findCodeRegions } from "../../shared/text/code-regions";

// Single deterministic top-level test exercising the public entrypoint only.
it("does not treat mismatched backtick runs as an inline code region", () => {
  const text = "before ``code` after";
  const regions = findCodeRegions(text);
  const slices = regions.map((r) => text.slice(r.start, r.end));

  // Primary oracle: the mismatched-run candidate must NOT appear among discovered slices.
  expect(slices).not.toContain("``code`");
});

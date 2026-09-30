import { test, expect } from "vitest";
import { mergeStreamingText } from "../../../extensions/feishu/src/streaming-card";

// Direct probe: overlapping suffix/prefix should not be duplicated when merged.
test("mergeStreamingText avoids duplicating overlapping suffix/prefix", () => {
  const previous = "abcde";
  const next = "cdefg";
  const merged = mergeStreamingText(previous, next);
  expect(merged).toBe("abcdefg");
});

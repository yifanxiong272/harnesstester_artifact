import { test, expect } from "vitest";
import { mergeStreamingText } from "../../../extensions/feishu/src/streaming-card";

test("mergeStreamingText avoids duplicating overlapping suffix/prefix", () => {
  const previous = "abcde";
  const next = "cdefg";
  const merged = mergeStreamingText(previous, next);
  expect(merged).toBe("abcdefg");
});

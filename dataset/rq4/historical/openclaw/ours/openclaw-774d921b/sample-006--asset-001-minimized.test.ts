import { it, expect } from "vitest";
import { mergeStreamingText } from "../../../extensions/feishu/src/streaming-card";

it("merges overlapping streaming fragments without duplicating the overlap", () => {
  const previous = "hel";
  const next = "ello";

  const result = mergeStreamingText(previous, next);

  expect(result).toBe("hello");
});

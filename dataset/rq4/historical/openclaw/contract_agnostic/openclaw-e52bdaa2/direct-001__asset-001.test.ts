import { it, expect, vi } from "vitest";
import { shortenMeta } from "../../auto-reply/tool-meta";

it("shortenMeta preserves multi-colon suffixes while shortening HOME-prefixed path", () => {
  vi.stubEnv("HOME", "/Users/test");
  const out = shortenMeta("/Users/test/dir/file:12:3");
  expect(out).toBe("~/dir/file:12:3");
});

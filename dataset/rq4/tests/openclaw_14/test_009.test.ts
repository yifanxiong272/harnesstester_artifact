import { it, expect } from "vitest";
import { sanitizeForPlainText } from "../../infra/outbound/sanitize-text.js";

it("converts block-level tags with attributes into surrounding newlines", () => {
  const p = sanitizeForPlainText('<p class="x">para</p>');
  const d = sanitizeForPlainText('<div id="y">block</div>');
  expect(p === "\npara\n" && d === "\nblock\n").toBe(true);
});

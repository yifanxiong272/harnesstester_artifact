import { it, expect } from "vitest";
import { sanitizeForPlainText } from "../../infra/outbound/sanitize-text";

it("preserves block semantics for <p> and <div> tags that include attributes by converting them to surrounding newlines", () => {
  const outP = sanitizeForPlainText('<p class="x">para</p>');
  const outDiv = sanitizeForPlainText('<div id="y">block</div>');
  expect(outP === "\npara\n" && outDiv === "\nblock\n").toBe(true);
});

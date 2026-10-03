import { it, expect } from "vitest";
import { sanitizeForPlainText } from "../../infra/outbound/sanitize-text";

it("preserves block semantics for <p> and <div> with attributes by converting to surrounding newlines", () => {
  const pHtml = '<p class="x">para</p>';
  const divHtml = '<div id="y">block</div>';

  const outP = sanitizeForPlainText(pHtml);
  const outDiv = sanitizeForPlainText(divHtml);

  // Single combined assertion: both conversions must preserve surrounding newlines.
  expect(outP === "\npara\n" && outDiv === "\nblock\n").toBe(true);
});
